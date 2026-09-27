"""Strategy library: pure functions of PAST bars only.

Each entryfn(bars_up_to_close, i, params) -> -1/0/+1 position for next bar.
Exits are handled by backtest (stop/target/time/flat-close) so entry logic
stays auditable. Keep these dumb on purpose — edge must survive simplicity.
"""
from __future__ import annotations
import numpy as np

def orb_breakout(closes, highs, lows, i: int, p: dict) -> int:
    """Opening-range breakout: range = first `orb_min` bars; enter on break + volume proxy."""
    orb_min = int(p.get("orb_min", 5))
    day_start = (i // 390) * 390
    if i - day_start < orb_min + 1:
        return 0
    orb_h = float(np.max(highs[day_start:day_start + orb_min]))
    orb_l = float(np.min(lows[day_start:day_start + orb_min]))
    px = closes[i]
    if px > orb_h:
        return 1
    if px < orb_l:
        return -1
    return 0

def vwap_reclaim(closes, vwap, i: int, p: dict) -> int:
    """VWAP pullback-continuation: 5-bar EMA trend + cross back through VWAP."""
    if i < 10:
        return 0
    c = closes[max(0, i-5):i+1]
    ema = float(np.mean(c))  # cheap SMA proxy; replace with EMA9/20 in v2
    px, v = closes[i], vwap[i]
    prev_px, prev_v = closes[i-1], vwap[i-1]
    if ema > v and prev_px <= prev_v and px > v:
        return 1
    if ema < v and prev_px >= prev_v and px < v:
        return -1
    return 0

def gap_and_go(opens, closes, i: int, p: dict) -> int:
    """Gap vs prior close beyond `gap_bp`, enter in gap direction at first bar."""
    day_start = (i // 390) * 390
    if i != day_start:  # only first bar of day
        return 0
    if day_start == 0:
        return 0
    prev_close = closes[day_start - 1]
    gap_bp = (opens[day_start] / prev_close - 1) * 1e4
    thresh = float(p.get("gap_bp", 50))
    if gap_bp >= thresh:
        return 1
    if gap_bp <= -thresh:
        return -1
    return 0

def late_reversal(closes, i: int, p: dict) -> int:
    """Late-day reversal (from GEX H3 hint: negative-autocorr regime).
    If day move to 15:00 exceeds `day_bp`, fade it into the close."""
    day_start = (i // 390) * 390
    bar_in_day = i - day_start
    entry_bar = int(p.get("entry_bar", 360))  # ~15:30 in 390-bar day
    if bar_in_day != entry_bar:
        return 0
    day_ret_bp = (closes[i] / closes[day_start] - 1) * 1e4
    thresh = float(p.get("day_bp", 100))
    if day_ret_bp >= thresh:
        return -1
    if day_ret_bp <= -thresh:
        return 1
    return 0

def noise_momentum(closes, opens_day, i: int, p: dict, sigma: float) -> int:
    """Replication of Zarattini noise-area: above/below trailing |open|-band.
    sigma = trailing 14d mean |move| (passed in by backtest)."""
    day_start = (i // 390) * 390
    if day_start == 0:
        return 0
    px = closes[i]
    ref_up = max(opens_day, closes[day_start - 1] if day_start > 0 else opens_day)
    ref_dn = min(opens_day, closes[day_start - 1] if day_start > 0 else opens_day)
    if px > ref_up * (1 + sigma):
        return 1
    if px < ref_dn * (1 - sigma):
        return -1
    return 0

ENTRYFNS = {
    "orb_breakout": orb_breakout,
    "vwap_reclaim": vwap_reclaim,
    "gap_and_go": gap_and_go,
    "late_reversal": late_reversal,
    "noise_momentum": noise_momentum,
}
