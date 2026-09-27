"""Bar loader — uses what you already have, free.

Priority:
 1. ./data/{SYM}_1min.pkl   (strategy-lab Alpaca SIP layout)
 2. ./data/{SYM}.parquet    (tickforge / schwab-scalper flattened bars)
 3. SQLite intraday_bars: ./data/market.db, $QP_DB_PATH, then the
    daytrading-agents test fixture (5-min, SPY/AAPL/MSFT/NVDA/AMD/TSLA,
    2026-05-22..2026-08-21) — real bars, short window, good for plumbing.
 4. yfinance (free): cached to ./data/{SYM}_{interval}.pkl; 1m = last 7d
    (true 1-min, runnable now, no creds), 1h = 2y, 1d fallback.
 5. synthetic seeded random walk (zero-data smoke test).

Env: QP_DB_PATH=/path/to/market.db to point at any quant-platform-format DB.
"""
from __future__ import annotations
import os
import pathlib
import sqlite3
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
FIXTURE_DB = pathlib.Path("/home/apharaohh/Projects/daytrading-agents/tests/fixtures/market.db")

def _from_sqlite(db: pathlib.Path, symbol: str) -> pd.DataFrame | None:
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        q = ("select ts, open, high, low, close, volume from intraday_bars "
             "where symbol=? order by ts")
        df = pd.read_sql_query(q, c, params=(symbol,))
        c.close()
    except Exception:
        return None
    if df.empty:
        return None
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.set_index("ts").sort_index()
    df["vwap"] = (df["close"].rolling(6, min_periods=1).mean())
    return df[["open", "high", "low", "close", "volume", "vwap"]]

def _from_yfinance(symbol: str, interval: str = "1h") -> pd.DataFrame | None:
    try:
        import yfinance as yf
    except ImportError:
        return None
    cache = DATA / f"{symbol}_{interval}.pkl"
    if cache.exists():
        try:
            return pd.read_pickle(cache)
        except Exception:
            pass
    period = {"1m": "7d", "1h": "2y"}.get(interval, "max")
    try:
        df = yf.download(symbol, period=period,
                         interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_convert("America/New_York").tz_localize(None)
        if "vwap" not in df.columns:
            typ = (df["high"] + df["low"] + df["close"]) / 3
            df["vwap"] = (typ * df["volume"]).rolling(6, min_periods=1).sum() / df["volume"].rolling(6, min_periods=1).sum()
            df["vwap"] = df["vwap"].fillna(df["close"])
        DATA.mkdir(parents=True, exist_ok=True)
        df[["open", "high", "low", "close", "volume", "vwap"]].to_pickle(cache)
        return df[["open", "high", "low", "close", "volume", "vwap"]]
    except Exception:
        return None

def load_bars(symbol: str, start=None, end=None, source: str = "auto") -> tuple[pd.DataFrame, str]:
    """Returns (bars, source_name). source_name in pkl/parquet/sqlite/yfinance1m/yfinance1h/yfinance1d/synthetic."""
    pkl = DATA / f"{symbol}_1min.pkl"
    pq = DATA / f"{symbol}.parquet"
    if source in ("auto", "pkl") and pkl.exists():
        return pd.read_pickle(pkl), "pkl"
    if source in ("auto", "parquet") and pq.exists():
        df = pd.read_parquet(pq)
        if "ts" in df.columns:
            df = df.set_index("ts").sort_index()
        return df, "parquet"
    if source in ("auto", "sqlite"):
        for cand in [DATA / "market.db",
                     pathlib.Path(os.environ["QP_DB_PATH"]) if os.environ.get("QP_DB_PATH") else None,
                     FIXTURE_DB]:
            if cand is not None and pathlib.Path(cand).exists():
                df = _from_sqlite(pathlib.Path(cand), symbol)
                if df is not None:
                    return df, f"sqlite:{cand.name}"
    # NB: 1m (7d window) only on explicit request — too short for splits;
    # auto prefers the 2y hourly series so verdicts stay time-split.
    if source in ("yfinance1m",):
        df = _from_yfinance(symbol, "1m")
        if df is not None and len(df) > 100:
            return df, "yfinance1m"
    if source in ("auto", "yfinance", "yfinance1h"):
        df = _from_yfinance(symbol, "1h")
        if df is not None:
            return df, "yfinance1h"
    if source in ("auto", "yfinance", "yfinance1d"):
        df = _from_yfinance(symbol, "1d")
        if df is not None:
            return df, "yfinance1d"
    return synthetic(symbol), "synthetic"

def available_sources() -> dict:
    out = {"pkl": sorted(p.name for p in DATA.glob("*_1min.pkl")),
           "parquet": sorted(p.name for p in DATA.glob("*.parquet")),
           "sqlite": [], "yfinance_cache": sorted(p.name for p in DATA.glob("*_1*.pkl"))}
    for cand in [DATA / "market.db", FIXTURE_DB]:
        if cand.exists():
            try:
                c = sqlite3.connect(f"file:{cand}?mode=ro", uri=True)
                syms = [r[0] for r in c.execute("select distinct symbol from intraday_bars")]
                c.close()
                out["sqlite"].append(f"{cand}: {syms}")
            except Exception as e:
                out["sqlite"].append(f"{cand}: err {e}")
    return out

def synthetic(symbol: str, days: int = 252, seed: int = 7) -> pd.DataFrame:
    """1-min bars, 390/day, zero-edge random walk + overnight gaps."""
    rng = np.random.default_rng(seed + abs(hash(symbol)) % 10_000)
    idx = pd.date_range("2024-01-02", periods=days * 390, freq="min")
    rets = rng.normal(0, 0.00012, len(idx))
    gaps = rng.normal(0, 0.0015, days)
    for d, g in enumerate(gaps):
        rets[d * 390] += g
    px = 100 * (1 + rets).cumprod()
    df = pd.DataFrame({
        "open": px,
        "high": px * (1 + np.abs(rng.normal(0, 0.0001, len(idx)))),
        "low": px * (1 - np.abs(rng.normal(0, 0.0001, len(idx)))),
        "close": px,
        "volume": rng.integers(100, 5000, len(idx)),
    }, index=idx)
    df["vwap"] = df["close"].rolling(30, min_periods=1).mean()
    return df
