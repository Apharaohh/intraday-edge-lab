"""Signal COUNTER for 06-liquidity-shock-reversal — counts only, never P&L.

Per the pre-registration, 1-min OHLC trade bars cannot establish fills, so
this script MUST NOT print expectancy, Sharpe, dollars, or any GO/NO-GO
verdict. It reports the filter funnel (how many bars pass each stage) and
signal counts per symbol/day, using closes as a midquote proxy (labeled).

Stages (spec §signal_1m, 10:00-14:30 ET, 1-min bars):
  S1 return_t <= -0.60%
  S2 return_t <= -3σ (same clock-minute, prior 20 sessions, causal)
  S3 volume_t >= 3x median (same clock-minute, prior 20 sessions)
  S4 idiosyncratic: (stock - QQQ) <= -0.40pp and QQQ > -0.30%

Usage:
  PYTHONPATH=src python scripts/shock_signal_count.py --symbols AAPL,MSFT,NVDA --source sqlite
  PYTHONPATH=src python scripts/shock_signal_count.py --symbols SPY,QQQ --source yfinance1m
"""
from __future__ import annotations
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from datetime import time as dtime

import numpy as np
import pandas as pd

from iel.data import load_bars

RET_MAX = -0.006
SIGMA_K = 3.0
VOL_MULT = 3.0
IDIO_MAX_PP = -0.40
QQQ_FLOOR = -0.003
T_START, T_END = dtime(10, 0), dtime(14, 30)
HIST = 20
MIN_HIST = 10


def clock_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = out["close"].pct_change()
    out["clock"] = out.index.time
    out["day"] = out.index.date
    return out


def count_signals(df: pd.DataFrame, qqq: pd.DataFrame | None, symbol: str) -> dict:
    """Causal same-clock-minute stats. Returns funnel counts + signal list."""
    px = clock_returns(df)
    in_win = px[(px["clock"] >= T_START) & (px["clock"] <= T_END)].copy()
    funnel = {"bars_in_window": len(in_win), "S1_ret": 0, "S2_sigma": 0, "S3_vol": 0, "S4_idio": 0}
    signals = []
    qret = None
    if qqq is not None:
        q = clock_returns(qqq)
        qret = q["ret"]

    days = sorted(in_win["day"].unique())
    for day in days:
        daybars = in_win[in_win["day"] == day]
        prior_days = sorted(d for d in px["day"].unique() if d < day)[-HIST:]
        if len(prior_days) < MIN_HIST:
            continue
        prior = px[px["day"].isin(prior_days)]
        for ts, row in daybars.iterrows():
            r = row["ret"]
            if not np.isfinite(r) or r > RET_MAX:
                continue
            funnel["S1_ret"] += 1
            same = prior[prior["clock"] == row["clock"]]["ret"].dropna()
            if len(same) < MIN_HIST or not (r <= -SIGMA_K * float(same.std())):
                continue
            funnel["S2_sigma"] += 1
            vols = prior[prior["clock"] == row["clock"]]["volume"].dropna()
            if len(vols) < MIN_HIST or not (row["volume"] >= VOL_MULT * float(vols.median())):
                continue
            funnel["S3_vol"] += 1
            if qret is None or ts not in qret.index or not np.isfinite(qret[ts]):
                continue  # no synced QQQ -> cannot test idiosyncratic; skip, don't assume
            qr = float(qret[ts])
            if (r - qr) * 100 > IDIO_MAX_PP or qr <= QQQ_FLOOR:
                continue
            funnel["S4_idio"] += 1
            signals.append((str(ts), round(r * 1e4, 1), round(qr * 1e4, 1)))
    return {"symbol": symbol, "funnel": funnel, "signals": signals}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="AAPL,MSFT,NVDA,AMD,TSLA,SPY")
    ap.add_argument("--source", default="auto")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    syms = [s.strip() for s in a.symbols.split(",")]

    print("NOTE: closes stand in for midquotes (proxy). COUNTS ONLY — no P&L, no Sharpe, no verdict.")
    bars, sources = {}, {}
    for s in syms:
        df, src = load_bars(s, source=a.source)
        bars[s], sources[s] = df, src
        print(f"{s}: {src}, {len(df)} bars, {bars[s].index[0]} -> {bars[s].index[-1]}")
    qqq = bars.get("QQQ")

    rows = []
    for s in syms:
        if s == "QQQ":
            continue
        # synced QQQ required: same source + overlapping index
        q = qqq if (qqq is not None and sources.get("QQQ") == sources[s]) else None
        r = count_signals(bars[s], q, s)
        f = r["funnel"]
        rows.append((s, f["bars_in_window"], f["S1_ret"], f["S2_sigma"], f["S3_vol"], f["S4_idio"]))
        print(f"{s}: window={f['bars_in_window']} S1={f['S1_ret']} S2={f['S2_sigma']} "
              f"S3={f['S3_vol']} S4_idio={f['S4_idio']}" + ("" if q is not None else " (no synced QQQ)"))
    if a.out:
        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# shock signal counts (proxy closes; counts only)", "",
                 "| sym | bars | S1 | S2 | S3 | S4 |", "|---|---|---|---|---|---|"]
        lines += [f"| {s} | {w} | {a1} | {a2} | {a3} | {a4} |" for s, w, a1, a2, a3, a4 in rows]
        out.write_text("\n".join(lines) + "\n")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
