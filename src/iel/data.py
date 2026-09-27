"""Bar loader: auto-detect existing project data, else synthetic fixture.

Priority:
 1. ./data/{SYM}_1min.pkl  (strategy-lab Alpaca SIP layout: index=datetime, open/high/low/close/volume/vwap)
 2. ./data/{SYM}.parquet   (tickforge/schwab-scalper flattened bars)
 3. synthetic seeded random walk (so harness + tests run with zero data)
"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

def load_bars(symbol: str, start=None, end=None) -> pd.DataFrame:
    pkl = DATA / f"{symbol}_1min.pkl"
    pq = DATA / f"{symbol}.parquet"
    if pkl.exists():
        df = pd.read_pickle(pkl)
        df = df.tz_convert("America/New_York") if hasattr(df.index, "tz_convert") and df.index.tz is not None else df
        if start: df = df[df.index.date >= start] if hasattr(start, "year") else df
        return df
    if pq.exists():
        df = pd.read_parquet(pq)
        if "ts" in df.columns:
            df = df.set_index("ts").sort_index()
        return df
    return synthetic(symbol)

def synthetic(symbol: str, days: int = 252, seed: int = 7) -> pd.DataFrame:
    """1-min bars, 390/day, zero-edge random walk — harness must report NO-GO on this."""
    rng = np.random.default_rng(seed + abs(hash(symbol)) % 10_000)
    idx = pd.date_range("2024-01-02", periods=days * 390, freq="min")
    # keep only 09:30-16:00 ET approx: simulate day blocks
    rets = rng.normal(0, 0.00012, len(idx))
    # inject overnight gaps every 390 bars so gap_and_go fires sometimes
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
