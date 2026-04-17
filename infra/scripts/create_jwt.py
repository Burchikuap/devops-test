#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import time


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def build_token(secret: str, issuer: str | None, audience: str | None, ttl: int, subject: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": now, "nbf": now, "exp": now + ttl}
    if issuer:
        payload["iss"] = issuer
    if audience:
        payload["aud"] = audience

    signing_input = f"{b64url(json.dumps(header, separators=(',', ':')).encode())}.{b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(signature)}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an HS256 JWT for local smoke tests.")
    parser.add_argument("--secret", required=True)
    parser.add_argument("--issuer")
    parser.add_argument("--audience")
    parser.add_argument("--subject", default="local-smoke-test")
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(build_token(args.secret, args.issuer, args.audience, args.ttl_seconds, args.subject))


if __name__ == "__main__":
    main()

