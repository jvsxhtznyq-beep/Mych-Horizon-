"""Tests for mych-cloud-infrastructure (infra_tool.py) and mych-runpod (runpod_tool.py, handler template)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from support import REPO_ROOT

CLOUD = REPO_ROOT / "specialists" / "mych-cloud-infrastructure" / "scripts" / "infra_tool.py"
RUNPOD = REPO_ROOT / "specialists" / "mych-runpod" / "scripts" / "runpod_tool.py"
HANDLER = REPO_ROOT / "specialists" / "mych-runpod" / "assets" / "serverless_handler.py"


def load(path, name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


infra = load(CLOUD, "mych_infra_tool")
rp = load(RUNPOD, "mych_runpod_tool")


def run(script, *args, env=None):
    return subprocess.run([sys.executable, "-B", str(script)] + [str(a) for a in args], capture_output=True, text=True,
                          env=env)


class CostTest(unittest.TestCase):
    PLAN = {"currency": "USD", "monthly_budget": 500, "items": [
        {"name": "app servers", "unit": "hour", "unit_price": 0.05, "quantity": 2,
         "price_source": "provider pricing page", "price_date": "2026-11-01"},
        {"name": "object storage", "unit": "gb-month", "unit_price": 0.02, "quantity": 100,
         "price_source": "provider pricing page", "price_date": "2026-11-01"},
        {"name": "egress", "unit": "gb", "unit_price": 0.09, "quantity": 50, "price_source": "pricing page",
         "price_date": "2026-11-01"}]}

    def test_monthly_total_from_supplied_prices(self):
        report = infra.estimate_cost(self.PLAN)
        self.assertTrue(report["ok"], report["errors"])
        self.assertAlmostEqual(report["monthly_total"], 0.05 * 2 * 730 + 0.02 * 100 + 0.09 * 50, places=2)
        self.assertFalse(any("egress" in w for w in report["warnings"]))

    def test_unsourced_prices_are_refused_or_flagged(self):
        plan = json.loads(json.dumps(self.PLAN))
        del plan["items"][0]["price_source"]
        self.assertFalse(infra.estimate_cost(plan)["ok"])
        flagged = infra.estimate_cost(plan, allow_unsourced=True)
        self.assertTrue(flagged["ok"])
        self.assertTrue(any("unverified estimate" in w for w in flagged["warnings"]))

    def test_budget_and_missing_egress(self):
        plan = {"currency": "USD", "monthly_budget": 10, "items": [
            {"name": "gpu server", "unit": "hour", "unit_price": 1.0, "quantity": 1, "price_source": "x", "price_date": "y"}]}
        report = infra.estimate_cost(plan)
        self.assertTrue(any("exceeds the monthly budget" in e for e in report["errors"]))
        self.assertTrue(any("egress" in w for w in report["warnings"]))


class PlanDnsDockerTest(unittest.TestCase):
    def test_plan_review_findings(self):
        plan = {"environment": "production", "region": "eu-north", "data_classification": "personal",
                "resources": [
                    {"name": "uploads", "type": "bucket", "public": True},
                    {"name": "db", "type": "database", "zones": 1, "encryption_at_rest": False,
                     "ingress": [{"source": "0.0.0.0/0", "port": 5432}]},
                    {"name": "api", "type": "service", "env": {"DB_PASSWORD": "hunter2", "API_TOKEN": "secret:api-token"}}],
                "backups": {"retention_days": 30}, "monitoring": {"alerts": ["5xx rate"]},
                "rollback": ["redeploy previous image"], "teardown": ["delete stack"], "approvals": {"deploy": "Kim"}}
        report = infra.check_plan(plan)
        text = " ".join(report["errors"] + report["warnings"])
        for expected in ("storage is public", "encryption at rest is disabled", "PostgreSQL (port 5432) is open",
                         "DB_PASSWORD holds a literal secret", "'spend' approval is not recorded",
                         "single availability zone", "restores have not been tested", "no budget"):
            self.assertIn(expected, text)
        self.assertNotIn("API_TOKEN holds", text)

    def test_complete_plan_passes(self):
        plan = {"environment": "staging", "region": "eu-north", "data_classification": "internal",
                "resources": [{"name": "api", "type": "service", "tls": True}],
                "backups": {"retention_days": 14, "restore_tested": "2026-10-30"},
                "monitoring": {"alerts": ["error rate"], "owner": "Kim", "budget_alert": 50},
                "rollback": ["previous image"], "teardown": ["delete stack"], "approvals": {"deploy": "Kim", "spend": "Kim"}}
        self.assertTrue(infra.check_plan(plan)["ok"])

    def test_dns_review(self):
        zone = {"origin": "example.com", "records": [
            {"name": "@", "type": "CNAME", "value": "host.example.net", "ttl": 300},
            {"name": "@", "type": "TXT", "value": "v=spf1 include:a.example -all", "ttl": 300},
            {"name": "@", "type": "TXT", "value": "v=spf1 include:b.example -all", "ttl": 300},
            {"name": "mail", "type": "CNAME", "value": "mx.provider.example", "ttl": 30},
            {"name": "@", "type": "MX", "value": "10 mail.example.com.", "ttl": 3600}]}
        report = infra.check_dns(zone)
        text = " ".join(report["errors"] + report["warnings"] + report["info"])
        for expected in ("CNAME at the zone apex", "2 SPF records", "target mail.example.com is a CNAME",
                         "TTL 30 is outside", "no CAA record"):
            self.assertIn(expected, text)

    def test_dockerfile_review(self):
        bad = "FROM python:latest\nENV API_KEY=abc123\nRUN curl -fsSL https://x.example/i.sh | sh\n" \
              "RUN apt-get update && apt-get install -y gcc\nCMD [\"python\", \"app.py\"]\n"
        report = infra.check_dockerfile(bad)
        text = " ".join(report["errors"] + report["warnings"] + report["info"])
        for expected in ("not pinned", "runs as root", "API_KEY sets a secret", "pipes a download", "HEALTHCHECK",
                         "apt-get install"):
            self.assertIn(expected, text)
        good = "FROM python:3.13-slim\nRUN useradd -m app\nUSER app\nHEALTHCHECK CMD python -c 'print(1)'\n"
        self.assertTrue(infra.check_dockerfile(good)["ok"])
        self.assertEqual(infra.check_dockerfile(good)["warnings"], [])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "cost.json"
            plan.write_text(json.dumps(CostTest.PLAN))
            self.assertEqual(run(CLOUD, "cost", plan).returncode, 0)
            broken = Path(tmp) / "broken.json"
            broken.write_text("{not json")
            self.assertEqual(run(CLOUD, "check-plan", broken).returncode, 2)
            empty = Path(tmp) / "empty.json"
            empty.write_text("{}")
            self.assertEqual(run(CLOUD, "check-plan", empty).returncode, 1)


class RunPodTest(unittest.TestCase):
    def test_vram_estimate_matches_hand_calculation(self):
        result = rp.estimate_vram(8, "fp16", context=8192, batch=1, layers=32, kv_heads=8, head_dim=128)
        weights = 8e9 * 2 / 1024 ** 3
        kv = 2 * 32 * 8 * 128 * 8192 * 1 * 2 / 1024 ** 3
        self.assertAlmostEqual(result["weights_gib"], round(weights, 2))
        self.assertAlmostEqual(result["kv_cache_gib"], round(kv, 2))
        self.assertAlmostEqual(result["total_gib"], round((weights + kv) * 1.2, 2), places=2)
        self.assertEqual(rp.recommend_gpu(result["total_gib"], [16, 24, 48, 80])["single_gpu_gib"], 24)
        full = rp.estimate_vram(70, "bf16", mode="full")
        self.assertGreater(full["total_gib"], 1000)
        self.assertEqual(rp.recommend_gpu(full["total_gib"], [80])["gpus_needed"], 16)
        self.assertTrue(any("not estimated" in a for a in rp.estimate_vram(7, "int4")["assumptions"]))

    def test_plan_requires_price_source_and_warns_about_persistence(self):
        base = ["plan", "--type", "pod", "--gpu", "TEST-GPU", "--gpu-price-hour", "0.5", "--hours-per-day", "4",
                "--days", "10", "--container-disk-gb", "50", "--storage-price-gb-month", "0.1", "--json"]
        missing = run(RUNPOD, *base)
        self.assertEqual(missing.returncode, 1)
        result = run(RUNPOD, *base, "--price-source", "runpod.io pricing page, 2026-11-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["compute_cost"], 20.0)
        self.assertAlmostEqual(plan["storage_cost"], round(50 * 0.1 * 10 / 30, 2))
        self.assertIn("all data is lost when the pod stops", plan["persistence_and_billing"][0])
        self.assertIn("Approval needed", plan["approval_request"])

    def test_endpoint_client_is_dry_run_by_default_and_uses_documented_paths(self):
        dry = run(RUNPOD, "endpoint", "--endpoint-id", "abc123", "--operation", "run", "--input", '{"prompt": "hi"}',
                  env=dict(os.environ, RUNPOD_API_KEY="rp-secret-key-value"))
        self.assertEqual(dry.returncode, 0, dry.stderr)
        request = json.loads(dry.stdout)
        self.assertEqual((request["method"], request["url"]), ("POST", "https://api.runpod.ai/v2/abc123/run"))
        self.assertEqual(request["body"], {"input": {"prompt": "hi"}})
        self.assertNotIn("rp-secret-key-value", dry.stdout)
        status = json.loads(run(RUNPOD, "endpoint", "--endpoint-id", "abc123", "--operation", "status",
                                "--job-id", "job-1").stdout)
        self.assertEqual((status["method"], status["url"]), ("GET", "https://api.runpod.ai/v2/abc123/status/job-1"))
        self.assertEqual(run(RUNPOD, "endpoint", "--endpoint-id", "a", "--operation", "cancel").returncode, 1)

    def test_execute_sends_with_key_to_a_stub(self):
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                seen.append((self.path, self.headers.get("Authorization"), json.loads(body)))
                payload = json.dumps({"id": "job-9", "status": "IN_QUEUE"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            base = "http://127.0.0.1:{}".format(server.server_address[1])
            no_key = run(RUNPOD, "endpoint", "--endpoint-id", "e1", "--operation", "run", "--execute", "--base-url", base,
                         env={k: v for k, v in os.environ.items() if k != "RUNPOD_API_KEY"})
            self.assertEqual(no_key.returncode, 1)
            self.assertIn("nothing was sent", no_key.stderr)
            sent = run(RUNPOD, "endpoint", "--endpoint-id", "e1", "--operation", "run", "--input", '{"x": 1}',
                       "--execute", "--base-url", base, env=dict(os.environ, RUNPOD_API_KEY="rp-test-key"))
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(sent.returncode, 0, sent.stderr)
        self.assertEqual(seen, [("/e1/run", "Bearer rp-test-key", {"input": {"x": 1}})])
        self.assertEqual(json.loads(sent.stdout)["body"]["status"], "IN_QUEUE")

    def test_handler_template_runs_locally_without_the_sdk(self):
        handler = load(HANDLER, "mych_serverless_handler")
        ok = handler.handler({"id": "t1", "input": {"prompt": "  hello  "}})
        self.assertEqual(ok["output"], {"echo": "hello", "characters": 5})
        self.assertEqual(handler.handler({"id": "t2", "input": {"prompt": ""}}), {"error": "input.prompt must be a non-empty string"})
        self.assertIn("error", handler.handler({"id": "t3", "input": "nope"}))


if __name__ == "__main__":
    unittest.main()
