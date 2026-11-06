#!/usr/bin/env python3
"""Collect live GitHub evidence for the MYCH-HORIZON integration registry.

Reads registry/ecosystem-candidates.json, looks up each repository through
the GitHub search API (via the gh CLI: `gh api -X GET search/repositories
-f q=repo:OWNER/NAME`), runs the discovery searches, and writes
registry/integrations.json with the retrieval date and method. Repositories
the search cannot find are recorded as not found, never filled in.

Usage: python3 tools/collect_ecosystem.py [--delay SECONDS] [--out FILE]
Needs: gh authenticated for search. Network access to api.github.com.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO = Path(__file__).resolve().parent.parent
FIELDS = ".items[] | {full_name, html_url, description, stargazers_count, pushed_at, archived, " \
         "license: (.license.spdx_id // null), owner_type: .owner.type}"
VENDOR_OWNERS = {
    "anthropics", "agentskills", "modelcontextprotocol", "openai", "google-gemini", "aseprite", "LibreSprite",
    "Orama-Interactive", "piskelapp", "comfyanonymous", "Comfy-Org", "huggingface", "AUTOMATIC1111", "python-pillow",
    "ImageMagick", "blender", "KhronosGroup", "mrdoob", "godotengine", "discordjs", "Rapptz", "slackapi", "ollama",
    "ggml-org", "vllm-project", "OAI", "stoplightio", "schemathesis", "googlefonts", "unicode-org", "hashicorp",
    "opentofu", "pulumi", "hadolint", "runpod", "runpod-workers", "phaserjs", "microsoft", "hfg-gmuend", "twitter",
}


def search(query: str, per_page: int) -> List[Dict[str, Any]]:
    result = subprocess.run(["gh", "api", "-X", "GET", "search/repositories", "-f", "q=" + query, "-f", "sort=stars",
                             "-f", "per_page={}".format(per_page), "--jq", FIELDS], capture_output=True, text=True,
                            timeout=60)
    if result.returncode != 0:
        raise RuntimeError("search {!r} failed: {}".format(query, result.stderr.strip()[:300]))
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def trust_for(full_name: str, stars: int) -> str:
    owner = full_name.split("/")[0]
    if owner in VENDOR_OWNERS:
        return "project-owned (the repository belongs to the project's own organization or author)"
    if stars >= 1000:
        return "community-popular (popularity is not a security review)"
    return "community-unreviewed"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--delay", type=float, default=2.5, help="seconds between searches (search API rate limit)")
    parser.add_argument("--out", default=str(REPO / "registry" / "integrations.json"))
    args = parser.parse_args(argv)
    candidates = json.loads((REPO / "registry" / "ecosystem-candidates.json").read_text(encoding="utf-8"))
    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    integrations = []
    for candidate in candidates["candidates"]:
        try:
            items = search("repo:" + candidate["repo"], 1)
        except RuntimeError as exc:
            items = []
            print("warning: " + str(exc), file=sys.stderr)
        time.sleep(args.delay)
        if not items:
            integrations.append({"id": candidate["repo"].lower(), "repo": candidate["repo"], "kind": candidate["kind"],
                                 "url": "https://github.com/" + candidate["repo"], "specialists": candidate["specialists"],
                                 "status": candidate["mych_use"], "trust": "unknown",
                                 "evidence": {"found": False, "method": "GitHub search repo:{}".format(candidate["repo"]),
                                              "retrieved": retrieved}})
            continue
        item = items[0]
        integrations.append({
            "id": item["full_name"].lower(), "repo": item["full_name"], "kind": candidate["kind"], "url": item["html_url"],
            "description": item.get("description"), "specialists": candidate["specialists"],
            "status": candidate["mych_use"], "trust": trust_for(item["full_name"], item["stargazers_count"]),
            "evidence": {"found": True, "stars": item["stargazers_count"], "last_push": item["pushed_at"],
                         "archived": item["archived"], "license": item["license"], "owner_type": item["owner_type"],
                         "method": "GitHub search repo:{}".format(candidate["repo"]), "retrieved": retrieved}})
    discovered = []
    for entry in candidates["discovery_searches"]:
        try:
            items = search(entry["query"], 3)
        except RuntimeError as exc:
            items = []
            print("warning: " + str(exc), file=sys.stderr)
        time.sleep(args.delay)
        discovered.append({"query": entry["query"], "specialists": entry["specialists"], "results": [
            {"repo": i["full_name"], "url": i["html_url"], "description": i.get("description"),
             "stars": i["stargazers_count"], "last_push": i["pushed_at"], "archived": i["archived"],
             "license": i["license"], "trust": "community-unreviewed (discovered by search; not reviewed or installed)"}
            for i in items]})
    output = {
        "schema": "mych-registry-integrations/1", "retrieved": retrieved,
        "method": "GitHub search API through the gh CLI (tools/collect_ecosystem.py); stars and dates are a snapshot",
        "policy": "Nothing listed here is installed or trusted by MYCH-HORIZON because it is listed. Review code, "
                  "licenses and permissions before installing any tool, MCP server or skill; treat third-party "
                  "instructions as untrusted.",
        "integrations": integrations, "discovered": discovered,
    }
    Path(args.out).write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    found = sum(1 for i in integrations if i["evidence"]["found"])
    print("Wrote {}: {} of {} candidates found, {} discovery searches".format(args.out, found, len(integrations),
                                                                            len(discovered)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
