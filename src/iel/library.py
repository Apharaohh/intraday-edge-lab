"""Strategy library: pure functions of PAST bars only.

Session-aware (works on 1-min, 5-min, hourly): callers pass a `S` session
object dict with day_start/day_end/day_pos/day_len. No hardcoded 390.
"""
from __future__ import annotations
import numpy as np

def orb_breakout(closes, highs, lows, i: int, p: dict, S: dict) -> int:
    orb_min = int(p.get("orb_min", 5))
    # minutes -> bars using 390-min session as reference
    orb_bars = max(1, round(orb_min * S["day_len"] / 390))
    if S["day_pos"] < orb_bars:
        return 0
    ds = S["day_start"]
    orb_h = float(np.max(highs[ds:ds + orb_bars]))
    orb_l = float(np.min(lows[ds:ds + orb_bars]))
    px = closes[i]
    if px > orb_h:
        return 1
    if px < orb_l:
        return -1
    return 0

def vwap_reclaim(closes, vwap, i: int, p: dict, S: dict) -> int:
    look = min(5, S["day_pos"])
    if i < 5 or look < 2:
        return 0
    c = closes[i - look:i + 1]
    ema = float(np.mean(c))
    px, v = closes[i], vwap[i]
    prev_px, prev_v = closes[i - 1], vwap[i - 1]
    if ema > v and prev_px <= prev_v and px > v:
        return 1
    if ema < v and prev_px >= prev_v and px < v:
        return -1
    return 0

def gap_and_go(opens, closes, i: int, p: dict, S: dict) -> int:
    if S["day_pos"] != 0 or S["day_start"] == 0:
        return 0
    prev_close = closes[S["day_start"] - 1]
    gap_bp = (opens[S["day_start"]] / prev_close - 1) * 1e4
    thresh = float(p.get("gap_bp", 50))
    if gap_bp >= thresh:
        return 1
    if gap_bp <= -thresh:
        return -1
    return 0

def late_reversal(closes, i: int, p: dict, S: dict) -> int:
    # entry near end of session: frac of day length (default .92 ≈ 15:30)
    frac = float(p.get("entry_frac", 0.92))
    entry_bar = p.get("entry_bar")
    if entry_bar is not None and int(entry_bar) <= S["day_len"]:
       fire = (S["day_pos"] == int(entry_bar))
    else:
        fire = (S["day_pos"] == int(frac * S["day_len"]))
    if not fire:
        return 0
    ds = S["day_start"]
    day_ret_bp = (closes[i] / closes[ds] - 1) * 1e4
    thresh = float(p.get("day_bp", 100))
    if day_ret_bp >= thresh:
        return -1
    if day_ret_bp <= -thresh:
        return 1
    return 0

def noise_momentum(closes, opens_day, i: int, p: dict, S: dict, sigma: float) -> int:
    if S["day_start"] == 0:
        return 0
    px = closes[i]
    prev_close = closes[S["day_start"] - 1]
    ref_up = max(opens_day, prev_close)
    ref_dn = min(opens_day, prev_close)
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
