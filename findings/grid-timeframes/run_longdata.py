"""LONGDATA: grid entries on longest stitched intraday per symbol.

5min-lab 2020/2022 Alpaca slices + QP 5-min (dedup keep-QP), tz-naive ET,
session VWAP recomputed. Runs entries x {5,15,30,60} + 09 separately.
Usage: QP_DB_PATH=... python findings/grid-timeframes/run_longdata.py
"""
import io
import os
import sqlite3
import urllib.request

import numpy as np
import pandas as pd
import yaml

from iel.backtest import run
from iel.data import resample
from iel.evaluate import evaluate

LAB = "https://raw.githubusercontent.com/Apharaohh/intraday-5min-lab/main"
TOK = os.environ.get("GITHUB_TOKEN", "")
HDR = {"Authorization": f"Bearer {TOK}"} if TOK else {}
SYMS = ["SPY", "QQQ", "IWM"]
SLICES = {"SPY": ["SPY_5m_2020", "SPY_5m_2022"],
          "QQQ": ["QQQ_5m_2020", "QQQ_5m_2022"],
          "IWM": ["IWM_5m_2022"]}
ENTRIES = ["orb_breakout", "vwap_reclaim", "gap_and_go", "late_reversal",
           "noise_momentum"]
TFS = [5, 15, 30, 60]


def qp_frame(sym: str) -> pd.DataFrame:
    db = os.environ["QP_DB_PATH"]
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    df = pd.read_sql_query(
        "select ts, open, high, low, close, volume from intraday_bars "
        "where symbol=? order by ts", c, params=(sym,))
    c.close()
    df["ts"] = pd.to_datetime(df["ts"])
    return df.set_index("ts").sort_index()


def slice_frame(sym: str, name: str) -> pd.DataFrame:
    req = urllib.request.Request(f"{LAB}/{name}.csv", headers=HDR)
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    df = pd.read_csv(io.BytesIO(raw))
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(
        "America/New_York").dt.tz_localize(None)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                             "Close": "close", "Volume": "volume"})
    return df.set_index("ts").sort_index()[["open", "high", "low", "close", "volume"]]


def session_vwap(df: pd.DataFrame) -> pd.Series:
    typ = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = (typ * df["volume"]).groupby(df.index.normalize()).cumsum()
    cv = df["volume"].groupby(df.index.normalize()).cumsum()
    return (pv / cv).where(cv > 0, df["close"])


def build(sym: str) -> pd.DataFrame:
    frames = [slice_frame(sym, n) for n in SLICES[sym]]
    frames.append(qp_frame(sym))
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df["vwap"] = session_vwap(df)
    return df


def verdict_line(tr, sym, tag):
    r = evaluate(tr, sym)
    sp = r.get("splits", {})

    def _f(k):
        d = sp.get(k)
        return f"{k}={d['sharpe_1bp']:.2f}(n={d['n']})" if d and d["sharpe_1bp"] is not None else f"{k}=n/a"
    print(f"{tag} {sym}: n={r['n']} t_gross={r.get('t_gross', 0):.2f} "
          f"be={r.get('breakeven_bp', 0):.2f}bp t_1bp={r.get('t_1.0bp', 0):.2f} "
          f"verdict={r['verdict']} | {_f('first')} {_f('second')} {_f('odd')} {_f('even')}",
          flush=True)


hyps = []
for p in sorted(__import__("pathlib").Path("hypotheses").glob("0[1-578]-*.yaml")):
    cfg = yaml.safe_load(p.read_text())
    if str(cfg.get("status", "")).startswith("BLOCKED"):
        continue
    params = dict(cfg.get("params", {}))
    params.update(cfg.get("filters", {}))
    hyps.append((p.stem, cfg["entry"], params))

for sym in SYMS:
    print(f"===== {sym} (stitched) =====", flush=True)
    base = build(sym)
    print(f"bars={len(base)} {base.index.min()} -> {base.index.max()}", flush=True)
    for tf in TFS:
        df = base if tf == 5 else resample(base, tf)
        for name, entry, params in hyps:
            tr = run(df, entry, params)
            verdict_line(tr, f"{sym}/{tf}m", f"{name}:{entry}")
    tr = run(base, "levels_rvol",
             yaml.safe_load(__import__("pathlib").Path("hypotheses/09-levels-rvol.yaml").read_text()).get("params", {}))
    verdict_line(tr, f"{sym}/5m", "levels_rvol[09]")
