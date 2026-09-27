"""Two-step Schwab OAuth for headless use (I can't click your browser for you).

Step 1 (me):  python scripts/schwab_login.py url
  -> prints the Schwab authorization URL. Open it, log in, approve.
  -> browser lands on https://127.0.0.1:8182/?code=...&session=...
     (page won't load — that's fine). Copy the FULL URL from the address bar.
Step 2 (me):  python scripts/schwab_login.py finish "PASTE_FULL_URL_HERE"
  -> exchanges it for tokens, writes .schwab_token.json, verifies with a quote.

Creds come from .env (copy .env.example) or QP_SCHWAB_ENV pointing at tickforge's.
Uses the same schwab-py primitives as client_from_manual_flow, split in two.
"""
from __future__ import annotations
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN = ROOT / ".schwab_token.json"


def _creds():
    for cand in (os.environ.get("QP_SCHWAB_ENV"), str(ROOT / ".env")):
        if cand and pathlib.Path(cand).exists():
            for raw in pathlib.Path(cand).read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    try:
        return (os.environ["SCHWAB_APP_KEY"], os.environ["SCHWAB_APP_SECRET"],
                os.environ["SCHWAB_CALLBACK_URL"])
    except KeyError as m:
        sys.exit(f"Missing {m}: fill .env (see .env.example) first.")


def cmd_url():
    key, _secret, callback = _creds()
    from schwab.auth import get_auth_context
    ctx = get_auth_context(key, callback)
    print(ctx.authorization_url)
    print("\nOpen the URL above, approve, then copy the FULL redirect URL and run:")
    print('  python scripts/schwab_login.py finish "PASTE_URL_HERE"')


def cmd_finish(redirect: str):
    key, secret, callback = _creds()
    from schwab.auth import get_auth_context, client_from_received_url
    ctx = get_auth_context(key, callback)
    client = client_from_received_url(key, secret, ctx, redirect, str(TOKEN))
    print(f"token written to {TOKEN}")
    r = client.get_quote("SPY")
    print("verify SPY quote:", r.status_code)
    if r.status_code != 200:
        sys.exit("WARNING: token saved but quote check failed — app may lack Market Data entitlement.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("url", "finish"):
        sys.exit("usage: schwab_login.py url | finish \"<redirect-url>\"")
    if sys.argv[1] == "url":
        cmd_url()
    else:
        if len(sys.argv) < 3:
            sys.exit("usage: schwab_login.py finish \"<redirect-url>\"")
        cmd_finish(sys.argv[2])
