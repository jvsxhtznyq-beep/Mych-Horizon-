#!/usr/bin/env python3
"""Cloud infrastructure planning checks (standard library only).

Commands:
  cost PLAN.json [--allow-unsourced]   monthly cost from owner-supplied prices; every price needs a source and date
  check-plan PLAN.json                 deployment plan review: backups, monitoring, rollback, teardown,
                                       approvals, exposure, encryption, redundancy, secrets
  check-dns ZONE.json                  DNS record review: CNAME conflicts, SPF duplicates, MX targets, TTLs, CAA
  check-dockerfile FILE                container hygiene: pinned base, non-root user, secrets, health checks

All checks are offline: nothing is deployed, queried or changed. Prices are
never invented; the cost command only multiplies the prices it is given.
Add --json for machine-readable output. Exit status: 0 no errors, 1 errors
found, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HOURS_PER_MONTH = 730  # average hours in a month (8760 / 12)
UNIT_FACTORS = {"hour": "hours", "month": "months", "gb-month": "gb-months", "gb": "gb", "million-requests": "millions",
                "unit": "units"}
SENSITIVE_PORTS = {22: "SSH", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis",
                   9200: "Elasticsearch", 11211: "Memcached", 2375: "Docker API"}
SECRET_NAME = re.compile(r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|access[_-]?key)", re.I)


def finding_report(errors: List[str], warnings: List[str], info: List[str], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    report = {"errors": errors, "warnings": warnings, "info": info, "ok": not errors}
    report.update(extra or {})
    return report


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------

def estimate_cost(plan: Dict[str, Any], allow_unsourced: bool = False) -> Dict[str, Any]:
    errors, warnings, info = [], [], []
    currency = plan.get("currency")
    if not currency:
        errors.append("plan needs a 'currency' (for example USD or NOK)")
    items = plan.get("items") or []
    if not items:
        errors.append("plan has no items")
    lines = []
    total = 0.0
    for index, item in enumerate(items):
        label = item.get("name") or "item {}".format(index + 1)
        unit = item.get("unit")
        price = item.get("unit_price")
        quantity = item.get("quantity", 1)
        if unit not in UNIT_FACTORS:
            errors.append("{}: unit must be one of {}".format(label, ", ".join(UNIT_FACTORS)))
            continue
        if not isinstance(price, (int, float)) or price < 0:
            errors.append("{}: unit_price must be a non-negative number".format(label))
            continue
        if not item.get("price_source") or not item.get("price_date"):
            message = "{}: price needs 'price_source' and 'price_date' (prices are never assumed)".format(label)
            if allow_unsourced:
                warnings.append(message + "; included as an unverified estimate")
            else:
                errors.append(message)
                continue
        if item.get("currency") and currency and item["currency"] != currency:
            errors.append("{}: currency {} differs from the plan's {}".format(label, item["currency"], currency))
            continue
        if unit == "hour":
            hours = item.get("hours_per_month", HOURS_PER_MONTH)
            if hours > HOURS_PER_MONTH:
                warnings.append("{}: {} hours per month exceeds {}".format(label, hours, HOURS_PER_MONTH))
            monthly = price * quantity * hours
            basis = "{} x {} x {} h".format(price, quantity, hours)
        else:
            monthly = price * quantity
            basis = "{} x {} {}".format(price, quantity, UNIT_FACTORS[unit])
        total += monthly
        lines.append({"name": label, "monthly": round(monthly, 2), "basis": basis,
                      "source": item.get("price_source"), "date": item.get("price_date")})
    names = " ".join(str(item.get("name", "")).lower() for item in items)
    if items and not any(word in names for word in ("egress", "transfer", "bandwidth")):
        warnings.append("no data transfer (egress) item: outbound traffic is often billed separately")
    if items and not any(word in names for word in ("backup", "snapshot")):
        info.append("no backup or snapshot storage item")
    budget = plan.get("monthly_budget")
    if isinstance(budget, (int, float)) and total > budget:
        errors.append("estimated {:.2f} {} exceeds the monthly budget of {:.2f}".format(total, currency or "", budget))
    info.append("estimate only: actual bills depend on usage, discounts, taxes and price changes")
    return finding_report(errors, warnings, info, {"currency": currency, "monthly_total": round(total, 2),
                                                   "lines": lines})


# ---------------------------------------------------------------------------
# Deployment plan review
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = ("environment", "region", "resources", "data_classification", "backups", "monitoring", "rollback",
                     "teardown", "approvals")


def check_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    errors, warnings, info = [], [], []
    for section in REQUIRED_SECTIONS:
        if not plan.get(section):
            errors.append("missing section '{}'".format(section))
    production = str(plan.get("environment", "")).lower() in ("production", "prod")
    backups = plan.get("backups") or {}
    if isinstance(backups, dict) and backups:
        if not backups.get("restore_tested"):
            warnings.append("backups: restores have not been tested; an untested backup is a hope, not a backup")
        if not backups.get("retention_days"):
            warnings.append("backups: retention is not defined")
        if not backups.get("offsite") and production:
            warnings.append("backups: no copy outside the primary region or account")
    monitoring = plan.get("monitoring") or {}
    if isinstance(monitoring, dict) and monitoring:
        if not monitoring.get("alerts"):
            errors.append("monitoring: no alerts defined")
        if not monitoring.get("owner"):
            warnings.append("monitoring: no owner who receives alerts")
        if not monitoring.get("budget_alert"):
            warnings.append("monitoring: no budget or spending alert")
    approvals = plan.get("approvals") or {}
    if isinstance(approvals, dict):
        for gate in ("spend", "deploy"):
            if not approvals.get(gate):
                errors.append("approvals: '{}' approval is not recorded".format(gate))
    for resource in plan.get("resources") or []:
        name = resource.get("name", resource.get("type", "resource"))
        kind = str(resource.get("type", "")).lower()
        if resource.get("public") and kind in ("bucket", "storage", "object-storage"):
            errors.append("{}: storage is public; serve public files through a CDN with a reviewed policy instead".format(name))
        if resource.get("encryption_at_rest") is False:
            errors.append("{}: encryption at rest is disabled".format(name))
        if resource.get("tls") is False:
            errors.append("{}: TLS is disabled".format(name))
        for rule in resource.get("ingress") or []:
            source = str(rule.get("source", ""))
            port = rule.get("port")
            if source in ("0.0.0.0/0", "::/0") and port in SENSITIVE_PORTS:
                errors.append("{}: {} (port {}) is open to the internet".format(name, SENSITIVE_PORTS[port], port))
        if production and kind in ("database", "db", "vm", "instance", "cluster") and resource.get("zones", 1) < 2:
            warnings.append("{}: single availability zone in production".format(name))
        for key, value in (resource.get("env") or {}).items():
            if SECRET_NAME.search(key) and isinstance(value, str) and value and not value.startswith(("secret:", "${")):
                errors.append("{}: environment variable {} holds a literal secret; reference a secret manager".format(
                    name, key))
    if plan.get("teardown") and isinstance(plan["teardown"], list) and len(plan["teardown"]) == 0:
        errors.append("teardown has no steps")
    if not plan.get("dns") and production:
        info.append("no DNS changes listed; DNS changes need their own approval and rollback")
    return finding_report(errors, warnings, info)


# ---------------------------------------------------------------------------
# DNS review
# ---------------------------------------------------------------------------

def check_dns(zone: Dict[str, Any]) -> Dict[str, Any]:
    errors, warnings, info = [], [], []
    origin = str(zone.get("origin", "")).rstrip(".").lower()
    records = zone.get("records") or []
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    def fqdn(raw: Any) -> str:
        name = str(raw).rstrip(".").lower()
        if name in ("@", ""):
            return origin
        if origin and name != origin and not name.endswith("." + origin):
            return name + "." + origin  # relative names belong to the zone
        return name

    for record in records:
        name = fqdn(record.get("name", "@"))
        by_name.setdefault(name, []).append(record)
        ttl = record.get("ttl")
        if isinstance(ttl, int) and (ttl < 60 or ttl > 86400):
            warnings.append("{} {}: TTL {} is outside 60-86400 seconds".format(name, record.get("type"), ttl))
    seen = set()
    for name, group in by_name.items():
        types = [str(r.get("type", "")).upper() for r in group]
        if "CNAME" in types:
            if name == origin:
                errors.append("{}: CNAME at the zone apex conflicts with SOA and NS records; use ALIAS/ANAME or A/AAAA "
                              "records".format(name))
            if len(types) > 1:
                errors.append("{}: CNAME cannot coexist with other records ({})".format(name, ", ".join(sorted(set(types)))))
        spf = [r for r in group if str(r.get("type", "")).upper() == "TXT" and str(r.get("value", "")).lower().startswith("v=spf1")]
        if len(spf) > 1:
            errors.append("{}: {} SPF records; a name must publish exactly one".format(name, len(spf)))
        for record in group:
            key = (name, str(record.get("type", "")).upper(), str(record.get("value", "")).lower())
            if key in seen:
                warnings.append("{} {}: duplicate record {}".format(name, key[1], record.get("value")))
            seen.add(key)
    cname_names = {n for n, g in by_name.items() if any(str(r.get("type", "")).upper() == "CNAME" for r in g)}
    for name, group in by_name.items():
        for record in group:
            if str(record.get("type", "")).upper() == "MX":
                target = fqdn(str(record.get("value", "")).split()[-1])
                if target in cname_names:
                    errors.append("{} MX: target {} is a CNAME; MX must point to a name with A/AAAA records".format(
                        name, target))
    if origin and not any(str(r.get("type", "")).upper() == "CAA" for r in by_name.get(origin, [])):
        info.append("{}: no CAA record; consider restricting which certificate authorities may issue".format(origin))
    return finding_report(errors, warnings, info, {"records": len(records)})


# ---------------------------------------------------------------------------
# Dockerfile review
# ---------------------------------------------------------------------------

def check_dockerfile(text: str) -> Dict[str, Any]:
    errors, warnings, info = [], [], []
    lines = []
    for raw in re.sub(r"\\\n", " ", text).splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    instructions = [(line.split(None, 1)[0].upper(), line.split(None, 1)[1] if " " in line else "") for line in lines]
    froms = [arg for inst, arg in instructions if inst == "FROM"]
    if not froms:
        errors.append("no FROM instruction")
    for arg in froms:
        image = arg.split()[0]
        if image.lower() == "scratch":
            continue
        if "@sha256:" in image:
            continue
        tag = image.rsplit(":", 1)[1] if ":" in image.split("/")[-1] else None
        if tag is None or tag == "latest":
            warnings.append("base image {} is not pinned to a version tag or digest".format(image))
    users = [arg.strip() for inst, arg in instructions if inst == "USER"]
    if not users or users[-1] in ("root", "0", "0:0"):
        warnings.append("the container runs as root; add a non-root USER")
    for inst, arg in instructions:
        if inst in ("ENV", "ARG"):
            for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)[= ]([^ ]+)", arg):
                if SECRET_NAME.search(match.group(1)) and match.group(2) and not match.group(2).startswith("$"):
                    errors.append("{} {} sets a secret in the image; pass secrets at runtime or use build secrets".format(
                        inst, match.group(1)))
        if inst == "ADD" and re.search(r"https?://", arg):
            warnings.append("ADD with a URL downloads without verification; use curl with a checksum in RUN")
        if inst == "RUN" and re.search(r"(curl|wget)[^|]*\|\s*(sh|bash)", arg):
            warnings.append("RUN pipes a download into a shell; download, verify a checksum, then run")
        if inst == "RUN" and "apt-get install" in arg and "rm -rf /var/lib/apt/lists" not in arg:
            info.append("apt-get install without cleaning /var/lib/apt/lists in the same layer increases image size")
    if not any(inst == "HEALTHCHECK" for inst, _ in instructions):
        info.append("no HEALTHCHECK; orchestrators that support it cannot detect a hung process")
    return finding_report(errors, warnings, info)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def print_report(title: str, report: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(title)
    if "monthly_total" in report:
        for line in report["lines"]:
            print("  {:<32} {:>12.2f} {}  ({}; source: {}, {})".format(line["name"], line["monthly"], report["currency"] or "",
                                                                     line["basis"], line["source"] or "none",
                                                                     line["date"] or "undated"))
        print("  {:<32} {:>12.2f} {} per month".format("TOTAL", report["monthly_total"], report["currency"] or ""))
    for level in ("errors", "warnings", "info"):
        for item in report[level]:
            print("{}: {}".format(level.rstrip("s") if level != "info" else "info", item))
    print("Result: {}".format("PASS" if report["ok"] else "FAIL"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline cloud infrastructure planning checks.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    for name in ("cost", "check-plan", "check-dns", "check-dockerfile"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--json", action="store_true")
        if name == "cost":
            p.add_argument("--allow-unsourced", action="store_true", help="include prices without a source, flagged")
    args = parser.parse_args(argv)
    try:
        text = Path(args.file).read_text(encoding="utf-8")
        if args.command == "check-dockerfile":
            report = check_dockerfile(text)
        else:
            data = json.loads(text)
            report = {"cost": lambda: estimate_cost(data, args.allow_unsourced), "check-plan": lambda: check_plan(data),
                      "check-dns": lambda: check_dns(data)}[args.command]()
    except (OSError, ValueError) as exc:
        print("error: cannot read {}: {}".format(args.file, exc), file=sys.stderr)
        return 2
    print_report("{} {}".format(args.command, args.file), report, args.json)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
