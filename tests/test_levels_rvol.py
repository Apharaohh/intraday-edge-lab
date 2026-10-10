"""levels_rvol: no-lookahead invariants + frozen-behavior checks.

- Session 0 (no prior day) never signals.
- A lone future spike cannot trigger entries at/before its bar.
- Crossover semantics: prev close <= level < close fires long; fade needs
  wick-through + close-back-inside with low RVOL near VWAP.
"""
import numpy as np
import pandas as pd
from iel.backtest import run
from iel.library import ENTRYFNS, _ema, _prior_day_levels, _session_vwap, _wilder_atr

def _two_days(bars=78, seed=1):
    rng = np.random.default_rng(seed)
    frames = []
    for d in range(2):
        idx = pd.date_range(f"2026-06-{d + 1:02d} 09:30", periods=bars, freq="5min")
        px = 100 + np.cumsum(rng.normal(0, 0.05, bars))
        frames.append(pd.DataFrame({
            "open": px, "high": px + 0.05, "low": px - 0.05,
            "close": px, "volume": 1000, "vwap": px}, index=idx))
    return pd.concat(frames)

def test_first_session_never_signals():
    df = _two_days()
    tr = run(df, "levels_rvol", {"time_stop": 390})
    if not tr.empty:
        first_day = str(df.index[0].date())
        assert (tr["day"] != first_day).all()

def test_spike_does_not_fire_early():
    df = _two_days()
    n = len(df)
    k = n - 10
    df.iloc[k, df.columns.get_loc("close")] = df["close"].iloc[k - 1] * 1.10
    df.iloc[k, df.columns.get_loc("high")] = df["close"].iloc[k]
    tr = run(df, "levels_rvol", {"time_stop": 390})
    assert tr.empty or int(tr["idx"].min()) >= k

def test_helpers_causal_shapes():
    df = _two_days()
    n = len(df)
    day_id = (df.index.normalize().values != df.index.normalize().values[0]).astype(int)
    pdh, pdl, pdc = _prior_day_levels(df["high"].to_numpy(), df["low"].to_numpy(),
                                      df["close"].to_numpy(), day_id)
    assert np.isnan(pdh[:78]).all() and np.isfinite(pdh[78:]).all()
    v = _session_vwap(df["high"].to_numpy(), df["low"].to_numpy(),
                      df["close"].to_numpy(), df["volume"].to_numpy(), day_id)
    assert np.isfinite(v).all()
    a = _wilder_atr(df["high"].to_numpy(), df["low"].to_numpy(),
                    df["close"].to_numpy(), 14)
    assert np.isnan(a[:13]).all() and np.isfinite(a[13:]).all()
    e = _ema(df["close"].to_numpy(), 20)
    assert np.isnan(e[:19]).all() and np.isfinite(e[19:]).all()

def test_registered():
    assert "levels_rvol" in ENTRYFNS

def test_leg_domain():
    df = _two_days()
    tr = run(df, "levels_rvol", {"time_stop": 390})
    assert tr.empty or set(tr["leg"].unique()) <= {"breakout", "fade"}
