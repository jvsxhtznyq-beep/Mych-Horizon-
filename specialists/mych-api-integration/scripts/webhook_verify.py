#!/usr/bin/env python3
"""Sign and verify webhook signatures (HMAC-SHA256) for three common schemes.

Schemes:
  timestamped  header "t=UNIX_SECONDS,v1=HEX" over "{t}.{body}" (the style used by several payment providers)
  slack        X-Slack-Signature "v0=HEX" over "v0:{timestamp}:{body}" with X-Slack-Request-Timestamp
  github       X-Hub-Signature-256 "sha256=HEX" over the raw body (no timestamp)

Usage:
  python3 webhook_verify.py verify --scheme S --secret-env VAR --signature HEADER --body-file FILE
                                    [--timestamp T] [--tolerance 300]
  python3 webhook_verify.py sign   --scheme S --secret-env VAR --body-file FILE [--timestamp T]

Verification uses constant-time comparison, rejects timestamps outside the
tolerance window (replay protection) and never prints the secret.
Exit status: 0 valid, 1 invalid or expired, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import sys
import time
from typing import Optional, Sequence, Tuple

SCHEMES = ("timestamped", "slack", "github")


def _mac(secret: bytes, message: bytes) -> str:
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def sign(scheme: str, secret: bytes, body: bytes, timestamp: Optional[int] = None) -> Tuple[str, Optional[int]]:
    """Return (signature header value, timestamp used)."""
    if scheme == "github":
        return "sha256=" + _mac(secret, body), None
    ts = int(time.time()) if timestamp is None else int(timestamp)
    if scheme == "timestamped":
        return "t={},v1={}".format(ts, _mac(secret, str(ts).encode() + b"." + body)), ts
    if scheme == "slack":
        return "v0=" + _mac(secret, b"v0:" + str(ts).encode() + b":" + body), ts
    raise ValueError("unknown scheme {!r}".format(scheme))


def verify(scheme: str, secret: bytes, body: bytes, signature: str, timestamp: Optional[str] = None,
           tolerance: int = 300, now: Optional[float] = None) -> Tuple[bool, str]:
    """Return (valid, reason). Reasons never contain the secret."""
    current = time.time() if now is None else now
    if not secret:
        return False, "empty secret"
    if scheme == "github":
        if not signature.startswith("sha256="):
            return False, "signature must start with sha256="
        return (True, "valid") if hmac.compare_digest(signature[7:], _mac(secret, body)) else (False, "signature mismatch")
    if scheme == "timestamped":
        fields = dict(part.split("=", 1) for part in signature.split(",") if "=" in part)
        ts_text, candidates = fields.get("t"), [v for k, v in (p.split("=", 1) for p in signature.split(",") if "=" in p)
                                                  if k == "v1"]
        if not ts_text or not ts_text.isdigit() or not candidates:
            return False, "malformed signature header (expected t=...,v1=...)"
        ts = int(ts_text)
        if abs(current - ts) > tolerance:
            return False, "timestamp outside the {}s tolerance (possible replay)".format(tolerance)
        expected = _mac(secret, ts_text.encode() + b"." + body)
        return (True, "valid") if any(hmac.compare_digest(c, expected) for c in candidates) else (False, "signature mismatch")
    if scheme == "slack":
        if not timestamp or not timestamp.isdigit():
            return False, "missing or invalid request timestamp"
        if abs(current - int(timestamp)) > tolerance:
            return False, "timestamp outside the {}s tolerance (possible replay)".format(tolerance)
        if not signature.startswith("v0="):
            return False, "signature must start with v0="
        expected = _mac(secret, b"v0:" + timestamp.encode() + b":" + body)
        return (True, "valid") if hmac.compare_digest(signature[3:], expected) else (False, "signature mismatch")
    return False, "unknown scheme {!r}".format(scheme)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sign and verify webhook signatures.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    for name in ("verify", "sign"):
        p = sub.add_parser(name)
        p.add_argument("--scheme", choices=SCHEMES, required=True)
        p.add_argument("--secret-env", required=True, help="environment variable holding the signing secret")
        p.add_argument("--body-file", required=True, help="file with the exact raw request body")
        p.add_argument("--timestamp", help="request timestamp (slack verify; optional for sign)")
        if name == "verify":
            p.add_argument("--signature", required=True, help="the signature header value")
            p.add_argument("--tolerance", type=int, default=300, help="allowed clock difference in seconds")
    args = parser.parse_args(argv)
    secret = os.environ.get(args.secret_env, "").encode()
    if not secret:
        print("error: environment variable {} is not set".format(args.secret_env), file=sys.stderr)
        return 2
    try:
        with open(args.body_file, "rb") as stream:
            body = stream.read()
    except OSError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2
    if args.command == "sign":
        value, ts = sign(args.scheme, secret, body, int(args.timestamp) if args.timestamp else None)
        print(value if ts is None or args.scheme == "timestamped" else "{}\ntimestamp: {}".format(value, ts))
        return 0
    valid, reason = verify(args.scheme, secret, body, args.signature, args.timestamp, args.tolerance)
    print("{}: {}".format("VALID" if valid else "INVALID", reason))
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
