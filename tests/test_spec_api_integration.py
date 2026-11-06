"""Tests for the mych-api-integration specialist: client resilience, webhooks, OpenAPI checks, stub server."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from support import REPO_ROOT

SCRIPTS = REPO_ROOT / "specialists" / "mych-api-integration" / "scripts"


def load(name):
    key = "mych_api_" + name
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, str(SCRIPTS / (name + ".py")))
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


api = load("apiclient")
hooks = load("webhook_verify")
oas = load("openapi_check")
stubs = load("stub_server")


class StubbedTest(unittest.TestCase):
    def serve(self, routes):
        server, state = stubs.make_server(routes)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return "http://127.0.0.1:{}".format(server.server_address[1]), state


class ClientTest(StubbedTest):
    def client(self, base, **kwargs):
        self.sleeps = []
        self.logs = []
        return api.ApiClient(base, sleep=self.sleeps.append, log=self.logs.append, **kwargs)

    def test_retries_transient_errors_honoring_retry_after(self):
        base, state = self.serve([{"method": "GET", "path": "/v1/items", "responses": [
            {"status": 503, "json": {"error": "busy"}}, {"status": 429, "headers": {"Retry-After": "2"}, "json": {}},
            {"status": 200, "headers": {"X-Request-Id": "req_9"}, "json": {"ok": True}}]}])
        response = self.client(base).request("GET", "/v1/items")
        self.assertEqual((response.status, response.attempts, response.request_id), (200, 3, "req_9"))
        self.assertEqual(self.sleeps[1], 2.0)
        self.assertEqual(len(state.requests), 3)

    def test_post_without_idempotency_key_is_not_retried(self):
        base, state = self.serve([{"method": "POST", "path": "/v1/orders", "responses": [
            {"status": 503, "json": {}}, {"status": 201, "json": {"id": "o1"}}]}])
        with self.assertRaises(api.ApiError) as caught:
            self.client(base).request("POST", "/v1/orders", json_body={"sku": "x"})
        self.assertEqual(caught.exception.status, 503)
        self.assertIn("without an idempotency key", str(caught.exception))
        self.assertEqual(len(state.requests), 1)

    def test_post_with_idempotency_key_is_retried_with_the_same_key(self):
        base, state = self.serve([{"method": "POST", "path": "/v1/orders", "responses": [
            {"status": 502, "json": {}}, {"status": 201, "json": {"id": "o1"}}]}])
        response = self.client(base).request("POST", "/v1/orders", json_body={"sku": "x"}, idempotency_key="key-123")
        self.assertEqual(response.status, 201)
        keys = [r["headers"].get("Idempotency-Key") for r in state.requests]
        self.assertEqual(keys, ["key-123", "key-123"])

    def test_client_errors_are_not_retried(self):
        base, state = self.serve([{"method": "GET", "path": "/v1/missing", "responses": [
            {"status": 404, "json": {"error": "not found"}}]}])
        with self.assertRaises(api.ApiError) as caught:
            self.client(base).request("GET", "/v1/missing")
        self.assertEqual((caught.exception.status, caught.exception.body), (404, {"error": "not found"}))
        self.assertEqual(len(state.requests), 1)

    def test_bearer_auth_from_env_is_redacted_in_logs(self):
        base, state = self.serve([{"method": "GET", "path": "/me", "responses": [{"status": 200, "json": {}}]}])
        os.environ["MYCH_TEST_TOKEN"] = "tok-super-secret-value"
        try:
            self.client(base, auth=api.BearerEnv("MYCH_TEST_TOKEN")).request("GET", "/me", params={"api_key": "k123"})
        finally:
            del os.environ["MYCH_TEST_TOKEN"]
        self.assertEqual(state.requests[0]["headers"]["Authorization"], "REDACTED")
        joined = " ".join(self.logs)
        self.assertNotIn("tok-super-secret-value", joined)
        self.assertNotIn("k123", joined)
        self.assertIn("api_key=REDACTED", joined)
        with self.assertRaises(api.ApiError):
            self.client(base, auth=api.BearerEnv("MYCH_UNSET_TOKEN_VAR")).request("GET", "/me")

    def test_refuses_absolute_urls_to_other_origins(self):
        client = self.client("https://api.example.com")
        with self.assertRaises(api.ApiError):
            client.url_for("https://evil.example.net/steal")
        self.assertEqual(client.url_for("/v1/x", {"a": 1}), "https://api.example.com/v1/x?a=1")

    def test_pagination_cursor_link_and_offset(self):
        base, _ = self.serve([
            {"method": "GET", "path": "/cursor", "responses": [
                {"status": 200, "json": {"data": [1, 2], "next_cursor": "c2"}},
                {"status": 200, "json": {"data": [3], "next_cursor": None}}]},
            {"method": "GET", "path": "/offset", "responses": [
                {"status": 200, "json": {"data": [1, 2]}}, {"status": 200, "json": {"data": [3]}}]}])
        client = self.client(base)
        self.assertEqual(list(client.paginate("/cursor")), [1, 2, 3])
        self.assertEqual(list(client.paginate("/offset", style="offset", page_size=2)), [1, 2, 3])
        link_base, _ = self.serve([])
        self.assertEqual(api.parse_link_next('<https://x/p?page=2>; rel="next", <https://x/p?page=9>; rel="last"'),
                         "https://x/p?page=2")
        self.assertIsNone(api.parse_link_next('<https://x/p?page=9>; rel="last"'))

    def test_circuit_breaker_fails_fast_and_recovers(self):
        now = [0.0]
        breaker = api.CircuitBreaker(threshold=2, reset_seconds=10, clock=lambda: now[0])
        base, state = self.serve([{"method": "GET", "path": "/flaky", "responses": [
            {"status": 500, "json": {}}, {"status": 500, "json": {}}, {"status": 200, "json": {"ok": 1}}]}])
        client = self.client(base, breaker=breaker, retry=api.RetryPolicy(max_attempts=1))
        for _ in range(2):
            with self.assertRaises(api.ApiError):
                client.request("GET", "/flaky")
        self.assertEqual(breaker.state, "open")
        with self.assertRaises(api.CircuitOpenError):
            client.request("GET", "/flaky")
        self.assertEqual(len(state.requests), 2)
        now[0] = 11.0
        self.assertEqual(breaker.state, "half-open")
        self.assertEqual(client.request("GET", "/flaky").status, 200)
        self.assertEqual(breaker.state, "closed")

    def test_token_bucket_spaces_requests(self):
        now = [0.0]
        waits = []

        def sleep(seconds):
            waits.append(seconds)
            now[0] += seconds

        bucket = api.TokenBucket(rate=2, capacity=2, clock=lambda: now[0], sleep=sleep)
        for _ in range(4):
            bucket.acquire()
        self.assertEqual(len(waits), 2)
        self.assertAlmostEqual(sum(waits), 1.0, places=6)

    def test_cli_dry_run_does_not_print_secrets(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "apiclient.py"), "request", "POST",
                                 "https://api.example.com/v1/items?token=abc", "--json", '{"a": 1}', "--bearer-env",
                                 "SOME_TOKEN", "--dry-run"], capture_output=True, text=True,
                                env=dict(os.environ, SOME_TOKEN="should-not-appear"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("should-not-appear", result.stdout)
        self.assertNotIn("abc", result.stdout)
        self.assertIn("Bearer $SOME_TOKEN", result.stdout)


class WebhookTest(unittest.TestCase):
    SECRET = b"whsec_test_secret"
    BODY = b'{"event":"order.paid","id":"evt_1"}'

    def test_each_scheme_accepts_valid_and_rejects_tampered(self):
        now = 1_800_000_000
        for scheme in hooks.SCHEMES:
            with self.subTest(scheme=scheme):
                signature, ts = hooks.sign(scheme, self.SECRET, self.BODY, timestamp=now)
                ts_text = str(ts) if ts is not None else None
                self.assertEqual(hooks.verify(scheme, self.SECRET, self.BODY, signature, ts_text, now=now),
                                 (True, "valid"))
                valid, reason = hooks.verify(scheme, self.SECRET, self.BODY + b" ", signature, ts_text, now=now)
                self.assertFalse(valid)
                self.assertIn("mismatch", reason)
                self.assertFalse(hooks.verify(scheme, b"wrong", self.BODY, signature, ts_text, now=now)[0])

    def test_replays_outside_tolerance_are_rejected(self):
        signature, ts = hooks.sign("timestamped", self.SECRET, self.BODY, timestamp=1000)
        valid, reason = hooks.verify("timestamped", self.SECRET, self.BODY, signature, now=1000 + 301)
        self.assertFalse(valid)
        self.assertIn("tolerance", reason)
        slack_sig, slack_ts = hooks.sign("slack", self.SECRET, self.BODY, timestamp=1000)
        self.assertFalse(hooks.verify("slack", self.SECRET, self.BODY, slack_sig, str(slack_ts), now=2000)[0])

    def test_uses_constant_time_comparison(self):
        source = (SCRIPTS / "webhook_verify.py").read_text()
        self.assertIn("hmac.compare_digest", source)
        self.assertNotIn("== expected", source)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.json"
            body.write_bytes(self.BODY)
            env = dict(os.environ, HOOK_SECRET=self.SECRET.decode())
            signed = subprocess.run([sys.executable, "-B", str(SCRIPTS / "webhook_verify.py"), "sign", "--scheme",
                                     "github", "--secret-env", "HOOK_SECRET", "--body-file", str(body)],
                                    capture_output=True, text=True, env=env)
            signature = signed.stdout.strip()
            ok = subprocess.run([sys.executable, "-B", str(SCRIPTS / "webhook_verify.py"), "verify", "--scheme", "github",
                                 "--secret-env", "HOOK_SECRET", "--body-file", str(body), "--signature", signature],
                                capture_output=True, text=True, env=env)
            bad = subprocess.run([sys.executable, "-B", str(SCRIPTS / "webhook_verify.py"), "verify", "--scheme", "github",
                                  "--secret-env", "HOOK_SECRET", "--body-file", str(body), "--signature", "sha256=00"],
                                 capture_output=True, text=True, env=env)
        self.assertEqual((ok.returncode, bad.returncode), (0, 1))
        self.assertNotIn(self.SECRET.decode(), ok.stdout + bad.stdout)


SPEC_V1 = {"openapi": "3.0.3", "info": {"title": "Shop", "version": "1"}, "security": [{"bearer": []}], "paths": {
    "/items": {"get": {"operationId": "listItems", "responses": {"200": {}}},
               "post": {"operationId": "createItem", "requestBody": {"required": True}, "responses": {"201": {}, "400": {}}}},
    "/items/{itemId}": {"parameters": [{"name": "itemId", "in": "path", "required": True}],
                        "get": {"operationId": "getItem", "responses": {"200": {}, "404": {}}},
                        "delete": {"operationId": "deleteItem", "responses": {"204": {}}}}}}


class OpenApiTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.spec = self.dir / "v1.json"
        self.spec.write_text(json.dumps(SPEC_V1))

    def tearDown(self):
        self._tmp.cleanup()

    def test_lists_operations_with_auth_and_required_parameters(self):
        ops = oas.operations(SPEC_V1)
        self.assertEqual([(o["method"], o["path"]) for o in ops], [
            ("GET", "/items"), ("POST", "/items"), ("GET", "/items/{itemId}"), ("DELETE", "/items/{itemId}")])
        self.assertEqual(ops[2]["required_parameters"], ["itemId"])
        self.assertEqual(ops[0]["auth"], [["bearer"]])

    def test_verify_flags_invented_endpoints_and_methods(self):
        uses = self.dir / "uses.txt"
        uses.write_text("# client endpoints\nGET /items\nGET /items/42\nDELETE /items/{id}\nPATCH /items/42\n"
                        "GET /items/42/reviews\n")
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "openapi_check.py"), "verify", str(self.spec),
                                 "--uses", str(uses)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("PATCH /items/42: path exists but method PATCH is not documented", result.stdout)
        self.assertIn("GET /items/42/reviews: no such path", result.stdout)
        self.assertIn("3 of 5 used endpoints are documented", result.stdout)

    def test_diff_reports_breaking_changes(self):
        v2 = json.loads(json.dumps(SPEC_V1))
        del v2["paths"]["/items/{itemId}"]["delete"]
        v2["paths"]["/items"]["get"]["parameters"] = [{"name": "tenant", "in": "query", "required": True}]
        v2["paths"]["/items"]["put"] = {"responses": {"200": {}}}
        breaking, additions = oas.diff(SPEC_V1, v2)
        self.assertIn("removed operation DELETE /items/{itemId}", breaking)
        self.assertIn("GET /items: new required parameters tenant", breaking)
        self.assertEqual(additions, ["added operation PUT /items"])


class StubServerTest(StubbedTest):
    def test_sequences_placeholders_404_and_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "req.jsonl"
            server, state = stubs.make_server([{"method": "GET", "path": "/users/{id}", "responses": [
                {"status": 200, "json": {"n": 1}}, {"status": 200, "json": {"n": 2}}]}], record=str(record))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                base = "http://127.0.0.1:{}".format(server.server_address[1])
                client = api.ApiClient(base, sleep=lambda s: None)
                bodies = [client.request("GET", "/users/7").body["n"] for _ in range(3)]
                with self.assertRaises(api.ApiError) as caught:
                    client.request("GET", "/nope")
            finally:
                server.shutdown()
                server.server_close()
            self.assertEqual(bodies, [1, 2, 2])
            self.assertEqual(caught.exception.status, 404)
            lines = record.read_text().splitlines()
            self.assertEqual(len(lines), 4)
            self.assertEqual(json.loads(lines[0])["path"], "/users/7")


if __name__ == "__main__":
    unittest.main()
