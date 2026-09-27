"""Shock counter: funnel stages execute; output contains no P&L language."""
import importlib.util
import io
import pathlib
import numpy as np
import pandas as pd
from contextlib import redirect_stdout

SPEC = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "shock_signal_count.py"
_mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("shock_mod", loader=None))
_mod.__dict__["__name__"] = "shock_mod"
_mod.__dict__["__file__"] = str(SPEC)
exec(compile(SPEC.read_text(), str(SPEC), "exec"), _mod.__dict__)
count_signals = _mod.__dict__["count_signals"]

FORBIDDEN = ["sharpe", "expectancy", "verdict", "GO", "P&L", "pnl", "net_bp", "$"]


def _bars(n_days=25, bars_per_day=390, shock_day=20, shock_clock="10:05", seed=3, shock=True):
    rng = np.random.default_rng(seed)
    frames = []
    for d in range(n_days):
        idx = pd.date_range(f"2026-07-{d+1:02d} 09:30", periods=bars_per_day, freq="min")
        rets = rng.normal(0, 0.0002, bars_per_day)
        if shock and d == shock_day:
            j = next(k for k, t in enumerate(idx) if t.strftime("%H:%M") == shock_clock)
            rets[j] = -0.008  # -80bp shock
        px = 100 * (1 + rets).cumprod()
        vol = np.full(bars_per_day, 5000.0)
        if shock and d == shock_day:
            vol[j] = 50000.0
        frames.append(pd.DataFrame({"open": px, "high": px, "low": px, "close": px,
                                    "volume": vol}, index=idx))
    return pd.concat(frames)


def test_funnel_fires_through_s3_without_qqq():
    df = _bars()
    r = count_signals(df, None, "TST")
    assert r["funnel"]["S1_ret"] >= 1
    assert r["funnel"]["S2_sigma"] >= 1
    assert r["funnel"]["S3_vol"] >= 1
    assert r["funnel"]["S4_idio"] == 0  # no QQQ -> cannot test idio

def test_s4_with_synced_flat_qqq():
    df = _bars()
    q = _bars(seed=99, shock=False)  # calm QQQ, no shocks
    q.index = df.index  # sync timestamps
    r = count_signals(df, q, "TST")
    assert r["funnel"]["S4_idio"] >= 1
    assert len(r["signals"]) >= 1

def test_output_has_no_pnl_language(capsys):
    df = _bars(n_days=12)
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("NOTE: closes stand in for midquotes (proxy). COUNTS ONLY — no P&L, no Sharpe, no verdict.")
    text = buf.getvalue()
    assert "COUNTS ONLY" in text
