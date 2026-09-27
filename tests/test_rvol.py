import numpy as np
import pandas as pd
from iel.rvol import compute_rvol
from iel.backtest import run

def _flat_days(n_days=30, bars=78, seed=0):
    rng = np.random.default_rng(seed)
    frames = []
    for d in range(n_days):
        day = pd.date_range(f"2026-06-{d+1:02d} 09:30", periods=bars, freq="5min")
        vol = np.full(bars, 1000.0)
        if d >= 25:
            vol = vol * 2.5  # hot days at the end
        px = 100 + rng.normal(0, 0.05, bars).cumsum()
        frames.append(pd.DataFrame({"open": px, "high": px + .05, "low": px - .05,
                                    "close": px, "volume": vol,
                                    "vwap": px}, index=day))
    return pd.concat(frames)

def test_rvol_hot_days_high():
    df = _flat_days()
    day_id = pd.to_datetime(df.index).normalize().values
    _, day_idn = np.unique(day_id, return_inverse=True)
    r = compute_rvol(df["volume"].to_numpy(), day_idn)
    # last days run 2.5x volume -> rvol ~2.5; early days ~1.0
    assert np.nanmean(r[-78:]) > 1.7  # baseline partly includes hot days, so < 2.5
    assert 0.8 < np.nanmean(r[78 * 10:78 * 11]) < 1.2

def test_rvol_no_lookahead_spike():
    # a volume spike on day 20 must not inflate days 0-19
    df = _flat_days()
    vols = df["volume"].to_numpy().copy()
    vols[19 * 78:20 * 78] *= 10
    df2 = df.copy()
    df2["volume"] = vols
    day_id = pd.to_datetime(df.index).normalize().values
    _, day_idn = np.unique(day_id, return_inverse=True)
    r = compute_rvol(df2["volume"].to_numpy(), day_idn)
    assert np.nanmean(r[5 * 78:6 * 78]) < 1.5  # day 5 (with history) unaffected by day-19 spike
    assert np.isnan(r[0])  # day 0 has no history -> NaN -> gate blocks when on

def test_gate_blocks_and_reports():
    df = _flat_days()
    tr_off = run(df, "orb_breakout", {"orb_min": 5})
    tr_on = run(df, "orb_breakout", {"orb_min": 5, "rvol_min": 2.0, "rvol_max": 3.0})
    assert tr_on.attrs["blocked_rvol"] > 0
    assert len(tr_on) <= len(tr_off)
    assert tr_on.attrs["rvol_gate"] == "[2.0,3.0]"
