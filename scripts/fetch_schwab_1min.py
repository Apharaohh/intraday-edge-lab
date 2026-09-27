"""Fetch 1-min RTH bars from Schwab history into ./data/{SYM}_1min.pkl.

Reuses tickforge.SchwabSource (10-day chunks, retry-on-incomplete, throttle) —
no duplicated API logic. Writes strategy-lab-compatible pickles so
iel.data.load_bars() picks them up with zero config.

Schwab history covers roughly the last 50 calendar days for 1-min.

Setup (one time):
  1. Schwab developer app (developer.schwab.com) with Market Data entitlement.
  2. cp .env.example .env  (in THIS repo) and fill SCHWAB_APP_KEY/SECRET/CALLBACK.
     Or reuse tickforge's: QP_SCHWAB_ENV=/path/to/tickforge/.env
  3. First run opens the manual OAuth flow in your browser; token cached at
     .schwab_token.json (gitignored), auto-refreshed after that.

Usage:
  python scripts/fetch_schwab_1min.py SPY QQQ IWM [--days 50] [--timeframe 1m]
  python scripts/fetch_schwab_1min.py --universe  # SPY QQQ IWM + AAPL MSFT NVDA AMD TSLA
"""
from __future__ import annotations
import argparse
import os
import pathlib
import sys
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

UNIVERSE = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMD", "TSLA"]

# Make tickforge importable (sibling checkout, same pattern schwab-scalper uses).
for cand in (pathlib.Path("/home/apharaohh/Projects/tickforge"),
             pathlib.Path.home() / "trading" / "tickforge"):
    if (cand / "tickforge" / "data" / "sources.py").exists() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))

ENV_EXAMPLE = """\
# Schwab developer-app credentials (developer.schwab.com, Market Data entitlement).
# First fetch runs the manual OAuth flow in your browser; token cached at
# .schwab_token.json next to this file (gitignored).
SCHWAB_APP_KEY=
SCHWAB_APP_SECRET=
SCHWAB_CALLBACK_URL=https://127.0.0.1:8182/
"""


def _load_env() -> pathlib.Path | None:
    """Load creds from QP_SCHWAB_ENV, ./tickforge .env, or this repo's .env."""
    for cand in (os.environ.get("QP_SCHWAB_ENV"),
                 "/home/apharaohh/Projects/tickforge/.env",
                 str(ROOT / ".env")):
        if cand and pathlib.Path(cand).exists():
            for raw in pathlib.Path(cand).read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
            return pathlib.Path(cand)
    return None


def to_rth_pandas(pl_df, symbol: str):
    """polars UTC bars -> pandas ET RTH-only OHLCV+vwap, strategy-lab layout."""
    import pandas as pd
    pdf = pl_df.filter(__import__("polars").col("symbol") == symbol).to_pandas()
    pdf["ts"] = pd.to_datetime(pdf["ts"], utc=True).dt.tz_convert("America/New_York")
    pdf = pdf.set_index("ts").sort_index()
    pdf = pdf.between_time("09:30", "15:59")
    pdf = pdf[["open", "high", "low", "close", "volume"]].astype(float, errors="ignore")
    typ = (pdf["high"] + pdf["low"] + pdf["close"]) / 3
    pdf["vwap"] = (typ * pdf["volume"]).groupby(pdf.index.date).cumsum() / \
        pdf["volume"].groupby(pdf.index.date).cumsum().replace(0, float("nan"))
    pdf["vwap"] = pdf["vwap"].fillna(pdf["close"])
    return pdf


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*", default=[])
    ap.add_argument("--universe", action="store_true")
    ap.add_argument("--days", type=int, default=50)
    ap.add_argument("--timeframe", default="1m", choices=["1m", "5m"])
    a = ap.parse_args()
    syms = list(dict.fromkeys((UNIVERSE if a.universe or not a.symbols else a.symbols)))
    DATA.mkdir(parents=True, exist_ok=True)

    if not (ROOT / ".env.example").exists():
        (ROOT / ".env.example").write_text(ENV_EXAMPLE)

    try:
        from tickforge.data.sources import SchwabSource
    except ImportError:
        print("tickforge not importable (looked in ~/Projects/tickforge). "
              "Clone it next to this repo or symlink it.", file=sys.stderr)
        return 2
    _load_env()
    missing = [k for k in ("SCHWAB_APP_KEY", "SCHWAB_APP_SECRET", "SCHWAB_CALLBACK_URL")
               if not os.environ.get(k)]
    if missing:
        print(f"Missing {missing}. Copy .env.example to .env and fill it, "
              f"or set QP_SCHWAB_ENV=/path/to/tickforge/.env", file=sys.stderr)
        return 2

    end = date.today()
    start = end - timedelta(days=a.days)
    src = SchwabSource()
    failed = 0
    for sym in syms:
        out = DATA / f"{sym}_{'1min' if a.timeframe == '1m' else '5min'}.pkl"
        if out.exists():
            print(f"{sym}: exists, skipping ({out}). Delete to refetch.")
            continue
        try:
            pl_df = src.fetch([sym], start, end, a.timeframe)
            pdf = to_rth_pandas(pl_df, sym)
            pdf.to_pickle(out)
            print(f"{sym}: {pdf.index[0].date()} -> {pdf.index[-1].date()} "
                  f"({len(pdf)} bars) -> {out.name}")
        except Exception as e:  # one symbol never aborts the batch
            print(f"{sym}: FAILED {type(e).__name__}: {e}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
