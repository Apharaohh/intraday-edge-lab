"""resample(): clock-stable aggregation, exact OHLCV, recomputed session VWAP."""
import numpy as np
import pandas as pd
from iel.data import resample, synthetic

def _rth_day(date="2026-06-02", bars=78, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{date} 09:30", periods=bars, freq="5min")
    px = 100 + np.cumsum(rng.normal(0, 0.05, bars))
    return pd.DataFrame({
        "open": px, "high": px + 0.05, "low": px - 0.05,
        "close": px, "volume": 1000, "vwap": px}, index=idx)

def test_bar_counts_full_session():
    df = _rth_day()
    assert len(resample(df, 5)) == 78
    assert len(resample(df, 15)) == 26
    assert len(resample(df, 30)) == 13
    assert len(resample(df, 60)) == 7

def test_ohlcv_exact():
    df = _rth_day()
    out = resample(df, 15)
    first = out.iloc[0]
    g = df.iloc[:3]
    assert first["open"] == g["open"].iloc[0]
    assert first["high"] == g["high"].max()
    assert first["low"] == g["low"].min()
    assert first["close"] == g["close"].iloc[-1]
    assert first["volume"] == g["volume"].sum()
    assert out.index[0] == pd.Timestamp("2026-06-02 09:30")
    assert out.index[1] == pd.Timestamp("2026-06-02 09:45")

def test_vwap_recomputed_finite():
    df = _rth_day()
    for tf in (5, 15, 30, 60):
        v = resample(df, tf)["vwap"]
        assert np.isfinite(v).all()

def test_volume_conserved():
    df = _rth_day()
    for tf in (15, 30, 60):
        assert resample(df, tf)["volume"].sum() == df["volume"].sum()

def test_bad_minutes():
    import pytest
    with pytest.raises(ValueError):
        resample(_rth_day(), 0)
