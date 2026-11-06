#!/usr/bin/env python3
"""A configurable local HTTP stub for contract tests and offline development.

Usage:
  python3 stub_server.py --routes ROUTES.json [--port 0] [--record requests.jsonl]

ROUTES.json:
  {"routes": [
     {"method": "GET", "path": "/v1/items", "responses": [
        {"status": 429, "headers": {"Retry-After": "1"}, "json": {"error": "slow down"}},
        {"status": 200, "json": {"data": [1, 2], "next_cursor": null}}]},
     {"method": "POST", "path": "/v1/items", "responses": [{"status": 201, "json": {"id": "it_1"}}]}]}

Each route replays its responses in order and repeats the last one. Paths
may use {placeholders}. Unknown routes return 404 with a JSON error. The
server binds to 127.0.0.1 only, prints "listening on http://127.0.0.1:PORT",
and records every request (method, path, headers with credentials redacted,
body) to --record when given.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Sequence, Tuple

REDACT = {"authorization", "x-api-key", "cookie", "proxy-authorization"}


class StubState:
    def __init__(self, routes: List[Dict[str, Any]], record: Optional[str]) -> None:
        self.routes = []
        for route in routes:
            pattern = "^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(route["path"])) + "$"
            self.routes.append({"method": route.get("method", "GET").upper(), "regex": re.compile(pattern),
                                "responses": route.get("responses") or [{"status": 200, "json": {}}], "count": 0})
        self.record = record
        self.lock = threading.Lock()
        self.requests: List[Dict[str, Any]] = []

    def respond(self, method: str, path: str, headers: Dict[str, str], body: bytes) -> Tuple[int, Dict[str, str], bytes]:
        entry = {"method": method, "path": path,
                 "headers": {k: ("REDACTED" if k.lower() in REDACT else v) for k, v in headers.items()},
                 "body": body.decode("utf-8", "replace")}
        with self.lock:
            self.requests.append(entry)
            if self.record:
                with open(self.record, "a", encoding="utf-8") as stream:
                    stream.write(json.dumps(entry) + "\n")
            bare = path.split("?", 1)[0]
            for route in self.routes:
                if route["method"] == method and route["regex"].match(bare):
                    index = min(route["count"], len(route["responses"]) - 1)
                    route["count"] += 1
                    response = route["responses"][index]
                    payload = json.dumps(response["json"]).encode() if "json" in response else \
                        str(response.get("body", "")).encode()
                    out_headers = dict({"Content-Type": "application/json" if "json" in response else "text/plain"},
                                       **response.get("headers", {}))
                    return int(response.get("status", 200)), out_headers, payload
        return 404, {"Content-Type": "application/json"}, json.dumps({"error": "no stub route for {} {}".format(
            method, path)}).encode()


def make_server(routes: List[Dict[str, Any]], port: int = 0, record: Optional[str] = None) -> Tuple[ThreadingHTTPServer, StubState]:
    state = StubState(routes, record)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def handle_any(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            status, headers, payload = state.respond(self.command, self.path, dict(self.headers), body)
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = handle_any

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server, state


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Configurable local HTTP stub.", epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--routes", required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--record")
    args = parser.parse_args(argv)
    try:
        routes = json.loads(open(args.routes, encoding="utf-8").read())["routes"]
    except (OSError, ValueError, KeyError) as exc:
        print("error: cannot read routes: {}".format(exc), file=sys.stderr)
        return 2
    server, _ = make_server(routes, args.port, args.record)
    print("listening on http://127.0.0.1:{}".format(server.server_address[1]), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
