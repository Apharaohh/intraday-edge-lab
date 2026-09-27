"""No-lookahead: entry at bar i must not depend on bars > i.
We run backtest on a spike series: a lone +10% up-bar at k. No signal may fire
at or before k based on the spike; first possible entry decision is at k."""
import pandas as pd
import numpy as np
from iel.backtest import run

def _spike_df(k=500, n=1200):
    px = np.full(n, 100.0)
    px[k] = 110.0
    idx = pd.date_range("2024-01-02", periods=n, freq="min")
    df = pd.DataFrame({"open": px, "high": px, "low": px, "close": px,
                       "volume": 1000, "vwap": px}, index=idx)
    return df

def test_no_signal_before_spike_orb():
    df = _spike_df()
    tr = run(df, "orb_breakout", {"orb_min": 5})
    assert tr.empty or int(tr["idx"].min()) >= 500
