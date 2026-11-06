#!/usr/bin/env python3
"""Resilient HTTP API client (standard library only). Import it or use the command line.

  python3 apiclient.py request METHOD URL [--header "K: V"] [--json BODY] [--bearer-env VAR]
                       [--idempotency-key KEY] [--retries N] [--timeout S] [--dry-run]
  python3 apiclient.py paginate URL --style cursor|link|offset [--items-key KEY] [--max-pages N]

Behavior:
  - retries 429 and 5xx responses and connection errors with exponential backoff and jitter,
    honoring Retry-After; POST and PATCH are retried only when an idempotency key is sent;
  - optional token-bucket rate limiting and a circuit breaker that fails fast after repeated failures;
  - credentials come from environment variables and are redacted from logs, errors and dry runs;
  - relative paths are joined to the base URL; absolute URLs to other hosts are refused.

Exit status: 0 success, 1 HTTP or network failure, 2 usage error.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

VERSION = "2.0.0"
SENSITIVE_HEADERS = frozenset({"authorization", "proxy-authorization", "x-api-key", "api-key", "cookie", "set-cookie",
                               "x-goog-api-key"})
SENSITIVE_QUERY = re.compile(r"(key|token|secret|signature|sig|password)", re.I)


class ApiError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, request_id: Optional[str] = None,
                 body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.request_id = request_id
        self.body = body


class CircuitOpenError(ApiError):
    pass


def redact_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if not parts.query:
        return url
    pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    safe = [(k, "REDACTED" if SENSITIVE_QUERY.search(k) else v) for k, v in pairs]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(safe)))


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: ("REDACTED" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()}


# ---------------------------------------------------------------------------
# Authentication from environment variables
# ---------------------------------------------------------------------------

class BearerEnv:
    def __init__(self, variable: str) -> None:
        self.variable = variable

    def apply(self, headers: Dict[str, str]) -> None:
        value = os.environ.get(self.variable)
        if not value:
            raise ApiError("environment variable {} is not set; no request was sent".format(self.variable))
        headers["Authorization"] = "Bearer " + value


class HeaderKeyEnv:
    def __init__(self, header: str, variable: str) -> None:
        self.header = header
        self.variable = variable

    def apply(self, headers: Dict[str, str]) -> None:
        value = os.environ.get(self.variable)
        if not value:
            raise ApiError("environment variable {} is not set; no request was sent".format(self.variable))
        headers[self.header] = value


class BasicEnv:
    def __init__(self, user_variable: str, password_variable: str) -> None:
        self.user_variable = user_variable
        self.password_variable = password_variable

    def apply(self, headers: Dict[str, str]) -> None:
        user, password = os.environ.get(self.user_variable), os.environ.get(self.password_variable)
        if not user or password is None:
            raise ApiError("credentials {} / {} are not set; no request was sent".format(
                self.user_variable, self.password_variable))
        headers["Authorization"] = "Basic " + base64.b64encode("{}:{}".format(user, password).encode()).decode()


# ---------------------------------------------------------------------------
# Resilience primitives
# ---------------------------------------------------------------------------

@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.5
    max_delay: float = 30.0
    retry_statuses: Tuple[int, ...] = (429, 500, 502, 503, 504)
    idempotent_methods: Tuple[str, ...] = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")

    def can_retry(self, method: str, has_idempotency_key: bool) -> bool:
        return method.upper() in self.idempotent_methods or has_idempotency_key

    def delay(self, attempt: int, retry_after: Optional[str]) -> float:
        if retry_after:
            if retry_after.strip().isdigit():
                return min(self.max_delay, float(retry_after))
        backoff = min(self.max_delay, self.base_delay * (2 ** attempt))
        return backoff * (0.5 + random.random() / 2)  # jitter in [backoff/2, backoff]


class TokenBucket:
    """Allow `rate` requests per second on average with bursts up to `capacity`."""

    def __init__(self, rate: float, capacity: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.clock = clock
        self.sleep = sleep
        self.updated = clock()

    def acquire(self) -> float:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return 0.0
        wait = (1 - self.tokens) / self.rate
        self.sleep(wait)
        self.tokens = 0.0
        self.updated = self.clock()
        return wait


class CircuitBreaker:
    """Open after `threshold` consecutive failures; allow one trial call after `reset_seconds`."""

    def __init__(self, threshold: int = 5, reset_seconds: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self.clock = clock
        self.failures = 0
        self.opened_at: Optional[float] = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half-open" if self.clock() - self.opened_at >= self.reset_seconds else "open"

    def before(self) -> None:
        if self.state == "open":
            raise CircuitOpenError("circuit open after {} consecutive failures; failing fast".format(self.failures))

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold or self.state == "half-open":
            self.opened_at = self.clock()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

@dataclass
class ApiResponse:
    status: int
    headers: Dict[str, str]
    body: Any
    request_id: Optional[str] = None
    attempts: int = 1
    url: str = ""


@dataclass
class ApiClient:
    base_url: str
    auth: Any = None
    timeout: float = 10.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    limiter: Optional[TokenBucket] = None
    breaker: Optional[CircuitBreaker] = None
    user_agent: str = "mych-api-integration/" + VERSION
    sleep: Callable[[float], None] = time.sleep
    log: Optional[Callable[[str], None]] = None
    default_headers: Dict[str, str] = field(default_factory=dict)

    def url_for(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        base = urllib.parse.urlsplit(self.base_url)
        if re.match(r"^[a-z][a-z0-9+.-]*://", path, re.I):
            target = urllib.parse.urlsplit(path)
            if (target.scheme, target.netloc) != (base.scheme, base.netloc):
                raise ApiError("refusing absolute URL to another origin: {}".format(redact_url(path)))
            url = path
        else:
            url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
            url += ("&" if "?" in url else "?") + query
        return url

    def _log(self, message: str) -> None:
        if self.log:
            self.log(message)

    def request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, json_body: Any = None,
                headers: Optional[Dict[str, str]] = None, idempotency_key: Optional[str] = None) -> ApiResponse:
        method = method.upper()
        url = self.url_for(path, params)
        merged = dict({"User-Agent": self.user_agent, "Accept": "application/json"}, **self.default_headers,
                      **(headers or {}))
        if idempotency_key:
            merged["Idempotency-Key"] = idempotency_key
        if self.auth:
            self.auth.apply(merged)
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            merged["Content-Type"] = "application/json"
        retryable = self.retry.can_retry(method, bool(idempotency_key))
        attempt = 0
        while True:
            if self.breaker:
                self.breaker.before()
            if self.limiter:
                self.limiter.acquire()
            self._log("{} {} attempt {} headers {}".format(method, redact_url(url), attempt + 1,
                                                          json.dumps(redact_headers(merged))))
            request = urllib.request.Request(url, data=data, method=method, headers=merged)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    response_headers = {k.lower(): v for k, v in response.headers.items()}
                    status = response.status
                if self.breaker:
                    self.breaker.success()
                return ApiResponse(status, response_headers, _decode(raw, response_headers),
                                   response_headers.get("x-request-id") or response_headers.get("request-id"),
                                   attempt + 1, url)
            except urllib.error.HTTPError as exc:
                response_headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
                body = _decode(exc.read(), response_headers)
                request_id = response_headers.get("x-request-id") or response_headers.get("request-id")
                transient = exc.code in self.retry.retry_statuses
                if transient and self.breaker:
                    self.breaker.failure()
                if transient and retryable and attempt + 1 < self.retry.max_attempts:
                    delay = self.retry.delay(attempt, response_headers.get("retry-after"))
                    self._log("HTTP {}; retrying in {:.2f}s".format(exc.code, delay))
                    self.sleep(delay)
                    attempt += 1
                    continue
                reason = "" if retryable or not transient else " (not retried: {} without an idempotency key)".format(method)
                raise ApiError("{} {} returned HTTP {}{}".format(method, redact_url(url), exc.code, reason),
                               exc.code, request_id, body) from exc
            except (urllib.error.URLError, OSError) as exc:
                if self.breaker:
                    self.breaker.failure()
                if retryable and attempt + 1 < self.retry.max_attempts:
                    delay = self.retry.delay(attempt, None)
                    self._log("network error {}; retrying in {:.2f}s".format(type(exc).__name__, delay))
                    self.sleep(delay)
                    attempt += 1
                    continue
                raise ApiError("{} {} failed: {}".format(method, redact_url(url), getattr(exc, "reason", exc))) from exc

    def paginate(self, path: str, style: str = "cursor", items_key: str = "data", params: Optional[Dict[str, Any]] = None,
                 cursor_param: str = "cursor", next_key: str = "next_cursor", limit_param: str = "limit",
                 offset_param: str = "offset", page_size: int = 100, max_pages: int = 1000) -> Iterator[Any]:
        """Yield items across pages: cursor tokens, RFC 8288 Link headers, or offset and limit."""
        query = dict(params or {})
        query.setdefault(limit_param, page_size)
        next_url: Optional[str] = path
        offset = 0
        for _ in range(max_pages):
            if next_url is None:
                return
            response = self.request("GET", next_url, params=query if style != "link" or next_url == path else None)
            items = response.body.get(items_key, []) if isinstance(response.body, dict) else response.body
            for item in items or []:
                yield item
            if style == "cursor":
                cursor = response.body.get(next_key) if isinstance(response.body, dict) else None
                if not cursor:
                    return
                query[cursor_param] = cursor
            elif style == "link":
                next_url = parse_link_next(response.headers.get("link", ""))
                query = {}
            else:
                if not items or len(items) < int(query[limit_param]):
                    return
                offset += len(items)
                query[offset_param] = offset
        raise ApiError("stopped after {} pages; raise max_pages if the API really has more".format(max_pages))


def parse_link_next(header: str) -> Optional[str]:
    for part in header.split(","):
        match = re.match(r'\s*<([^>]+)>\s*;(.*)', part)
        if match and re.search(r'rel="?next"?', match.group(2)):
            return match.group(1)
    return None


def _decode(raw: bytes, headers: Dict[str, str]) -> Any:
    text = raw.decode("utf-8", "replace")
    if "json" in headers.get("content-type", "") or text[:1] in ("{", "["):
        try:
            return json.loads(text) if text else None
        except ValueError:
            return text
    return text


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Resilient API client.", formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    for name in ("request", "paginate"):
        p = sub.add_parser(name)
        if name == "request":
            p.add_argument("method")
        p.add_argument("url")
        p.add_argument("--header", action="append", default=[], help="extra header 'Name: value' (repeatable)")
        p.add_argument("--bearer-env", help="environment variable holding a bearer token")
        p.add_argument("--retries", type=int, default=4, help="maximum attempts (default 4)")
        p.add_argument("--timeout", type=float, default=10.0)
        if name == "request":
            p.add_argument("--json", help="JSON request body")
            p.add_argument("--idempotency-key", help="enables retries for POST and PATCH")
            p.add_argument("--dry-run", action="store_true", help="print the request without sending it")
        else:
            p.add_argument("--style", choices=("cursor", "link", "offset"), default="cursor")
            p.add_argument("--items-key", default="data")
            p.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args(argv)
    parts = urllib.parse.urlsplit(args.url)
    if not parts.scheme or not parts.netloc:
        print("error: URL must be absolute (https://host/path)", file=sys.stderr)
        return 2
    headers = {}
    for item in args.header:
        if ":" not in item:
            print("error: header must look like 'Name: value'", file=sys.stderr)
            return 2
        key, value = item.split(":", 1)
        headers[key.strip()] = value.strip()
    base = urllib.parse.urlunsplit((parts.scheme, parts.netloc, "", "", ""))
    client = ApiClient(base, auth=BearerEnv(args.bearer_env) if args.bearer_env else None, timeout=args.timeout,
                       retry=RetryPolicy(max_attempts=max(1, args.retries)), default_headers=headers,
                       log=lambda m: print(m, file=sys.stderr))
    path = urllib.parse.urlunsplit(("", "", parts.path or "/", parts.query, ""))
    try:
        if args.command == "request":
            body = json.loads(args.json) if args.json else None
            if args.dry_run:
                shown = dict(headers)
                if args.bearer_env:
                    shown["Authorization"] = "Bearer ${}".format(args.bearer_env)
                print(json.dumps({"dry_run": True, "method": args.method.upper(), "url": redact_url(args.url),
                                  "headers": redact_headers(shown) if not args.bearer_env else shown, "body": body},
                                 indent=2))
                return 0
            response = client.request(args.method, path, json_body=body, idempotency_key=args.idempotency_key)
            print(json.dumps({"status": response.status, "attempts": response.attempts, "request_id": response.request_id,
                              "body": response.body}, indent=2))
            return 0
        items = list(client.paginate(path, style=args.style, items_key=args.items_key, max_pages=args.max_pages))
        print(json.dumps({"items": items, "count": len(items)}, indent=2))
        return 0
    except ApiError as exc:
        print("error: {}{}".format(exc, " (request id {})".format(exc.request_id) if exc.request_id else ""), file=sys.stderr)
        return 1
    except ValueError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
