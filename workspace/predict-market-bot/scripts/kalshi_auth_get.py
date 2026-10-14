#!/usr/bin/env python3
"""Authenticated Kalshi GET. Uses env KALSHI_API_KEY_ID + PEM path. Never prints secrets."""
import argparse, base64, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", help="e.g. /portfolio/balance or full /trade-api/v2/...")
    p.add_argument("--base", default=os.environ.get("KALSHI_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2"))
    args = p.parse_args()
    kid = os.environ.get("KALSHI_API_KEY_ID")
    pem_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "/workspace/predict-market-bot/secrets/kalshi_private.pem")
    if not kid:
        print("missing KALSHI_API_KEY_ID", file=sys.stderr); sys.exit(1)
    key = serialization.load_pem_private_key(Path(pem_path).read_bytes(), password=None)
    base = args.base.rstrip("/")
    # Accept either /portfolio/balance or /trade-api/v2/portfolio/balance
    rel = args.path if args.path.startswith("/") else "/" + args.path
    if base.endswith("/trade-api/v2") and rel.startswith("/trade-api/v2"):
        url_path = rel
        url = "https://api.elections.kalshi.com" + rel if "elections" in base or "kalshi" in base else base.replace("/trade-api/v2","") + rel
        # normalize
        host = base[: -len("/trade-api/v2")]
        if not rel.startswith("/trade-api/v2"):
            rel_full = "/trade-api/v2" + rel
        else:
            rel_full = rel
        url = host + rel_full
        sign_path = rel_full.split("?")[0]
    else:
        if not rel.startswith("/trade-api/v2"):
            rel_full = "/trade-api/v2" + (rel if rel.startswith("/") else "/" + rel)
            # if base already includes /trade-api/v2
            if base.endswith("/trade-api/v2"):
                host = base[: -len("/trade-api/v2")]
                url = host + rel_full
                sign_path = rel_full.split("?")[0]
            else:
                url = base + rel
                sign_path = urllib.request.urlparse(url).path.split("?")[0]
        else:
            host = base[: -len("/trade-api/v2")] if base.endswith("/trade-api/v2") else base
            url = (host if host.startswith("http") else base) + rel
            sign_path = rel.split("?")[0]

    # simpler rewrite
    host = os.environ.get("KALSHI_HOST", "https://api.elections.kalshi.com")
    if args.path.startswith("/trade-api/v2"):
        sign_path = args.path.split("?")[0]
    else:
        ep = args.path if args.path.startswith("/") else "/" + args.path
        sign_path = "/trade-api/v2" + ep
    url = host + sign_path
    ts = str(int(time.time() * 1000))
    msg = f"{ts}GET{sign_path}"
    sig = base64.b64encode(key.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())).decode()
    req = urllib.request.Request(url, headers={
        "KALSHI-ACCESS-KEY": kid,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        sys.exit(e.code)

if __name__ == "__main__":
    main()
