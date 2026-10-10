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

def _session_vwap(highs, lows, closes, volume, day_id: np.ndarray) -> np.ndarray:
    """Cumulative session VWAP on typical price. Resets each session.
    Falls back to close when cumulative volume is zero."""
    typ = (np.asarray(highs, dtype=float) + np.asarray(lows, dtype=float)
           + np.asarray(closes, dtype=float)) / 3.0
    vol = np.asarray(volume, dtype=float)
    out = np.full(len(typ), np.nan)
    for d in np.unique(day_id):
        m = np.flatnonzero(day_id == d)
        pv = np.cumsum(typ[m] * vol[m])
        cv = np.cumsum(vol[m])
        with np.errstate(invalid="ignore", divide="ignore"):
            v = pv / cv
        v[cv <= 0] = np.nan
        out[m] = v
    return out

def _wilder_atr(highs, lows, closes, length: int = 14) -> np.ndarray:
    """Wilder ATR, causal. Undefined (nan) for the first `length` bars,
    mirroring Pine ta.atr warmup."""
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    prev_c = np.empty_like(c)
    prev_c[0] = c[0]
    prev_c[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    out = np.full(len(c), np.nan)
    if len(c) >= length:
        out[length - 1] = float(np.mean(tr[:length]))
        for k in range(length, len(c)):
            out[k] = (out[k - 1] * (length - 1) + tr[k]) / length
    return out

def _ema(values, span: int) -> np.ndarray:
    """Classic EMA seeded with the SMA of the first `span` bars.
    Undefined (nan) before the seed bar, mirroring Pine ta.ema warmup."""
    x = np.asarray(values, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= span and span >= 1:
        k = 2.0 / (span + 1.0)
        out[span - 1] = float(np.mean(x[:span]))
        for j in range(span, len(x)):
            out[j] = x[j] * k + out[j - 1] * (1.0 - k)
    return out

def _prior_day_levels(highs, lows, closes, day_id: np.ndarray):
    """Prior completed session's high/low/close, aligned per bar.
    Session 0 (no prior day) is nan — no signals may fire there."""
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    sessions = np.unique(day_id)
    sess_h = {d: float(np.max(h[day_id == d])) for d in sessions}
    sess_l = {d: float(np.min(l[day_id == d])) for d in sessions}
    sess_c = {d: float(c[np.flatnonzero(day_id == d)[-1]]) for d in sessions}
    n = len(c)
    pdh = np.full(n, np.nan)
    pdl = np.full(n, np.nan)
    pdc = np.full(n, np.nan)
    for k, d in enumerate(sessions):
        if k == 0:
            continue
        prev = sessions[k - 1]
        m = day_id == d
        pdh[m], pdl[m], pdc[m] = sess_h[prev], sess_l[prev], sess_c[prev]
    return pdh, pdl, pdc

def levels_rvol(closes, highs, lows, opens, i: int, p: dict, S: dict, ctx: dict) -> int:
    """Port of TradingView Intraday Levels + RVOL strategy (frozen defaults).

    Breakout mode (RVOL > elevated): close crossing R1/R2/prior-high (long)
    or S1/S2/prior-low (short), confirmed by bar volume, VWAP and HTF trend.
    Fade mode (RVOL < low, near VWAP): wick-through + close-back-inside at
    Camarilla/pivot extension levels. See hypotheses/09-levels-rvol.yaml
    for the frozen parameter map and documented deviations from the Pine
    original (premarket levels dropped — RTH data; risk unit is entry-bar
    range, not ATR).
    """
    if S["day_start"] == 0 or i < 1:
        return 0
    pdh, pdl, pdc = ctx["pdh"][i], ctx["pdl"][i], ctx["pdc"][i]
    if not (np.isfinite(pdh) and np.isfinite(pdl) and np.isfinite(pdc)):
        return 0
    pp = (pdh + pdl + pdc) / 3.0
    r1 = 2 * pp - pdl
    s1 = 2 * pp - pdh
    r2 = pp + (pdh - pdl)
    s2 = pp - (pdh - pdl)
    rng = pdh - pdl
    cam_r3 = pdc + rng * 1.1 / 4
    cam_r4 = pdc + rng * 1.1 / 2
    cam_s3 = pdc - rng * 1.1 / 4
    cam_s4 = pdc - rng * 1.1 / 2
    r3 = pdh + 2 * (pp - pdl)
    s3 = pdl - 2 * (pdh - pp)

    c = closes[i]
    h = highs[i]
    low = lows[i]
    prev_c = closes[i - 1]
    vwap = ctx["vwap"][i]
    atr = ctx["atr"][i]
    ema = ctx["ema"][i]
    rv = ctx["rvol"][i]

    lookback = int(p.get("barvol_lookback", 20))
    mult = float(p.get("barvol_mult", 1.0))
    vol = ctx["volume"]
    if i < lookback - 1:
        bar_vol_ok = False
    else:
        bar_vol_ok = vol[i] > float(np.mean(vol[i - lookback + 1:i + 1])) * mult

    rvol_hi = bool(np.isfinite(rv) and rv > float(p.get("rvol_elevated", 1.5)))
    rvol_lo = bool(np.isfinite(rv) and rv < float(p.get("rvol_low", 0.8)))

    trend_long = bool(np.isfinite(vwap) and np.isfinite(ema) and c > vwap and c > ema)
    trend_short = bool(np.isfinite(vwap) and np.isfinite(ema) and c < vwap and c < ema)
    band = float(p.get("fade_vwap_atr_band", 0.5))
    fade_ok = bool(np.isfinite(atr) and atr > 0 and np.isfinite(vwap)
                   and abs(c - vwap) <= band * atr)

    def cross_up(lvl: float) -> bool:
        return bool(np.isfinite(lvl) and prev_c <= lvl and c > lvl)

    def cross_dn(lvl: float) -> bool:
        return bool(np.isfinite(lvl) and prev_c >= lvl and c < lvl)

    if rvol_hi and bar_vol_ok:
        if trend_long and (cross_up(r1) or cross_up(r2) or cross_up(pdh)):
            ctx.get("diag", {})["leg"] = "breakout"
            return 1
        if trend_short and (cross_dn(s1) or cross_dn(s2) or cross_dn(pdl)):
            ctx.get("diag", {})["leg"] = "breakout"
            return -1
    if rvol_lo and bar_vol_ok and fade_ok:
        if any(h > lvl and c < lvl for lvl in (cam_r4, cam_r3, r3, r2)
               if np.isfinite(lvl)):
            ctx.get("diag", {})["leg"] = "fade"
            return -1
        if any(low < lvl and c > lvl for lvl in (cam_s4, cam_s3, s3, s2)
               if np.isfinite(lvl)):
            ctx.get("diag", {})["leg"] = "fade"
            return 1
    return 0

ENTRYFNS = {
    "orb_breakout": orb_breakout,
    "vwap_reclaim": vwap_reclaim,
    "gap_and_go": gap_and_go,
    "late_reversal": late_reversal,
    "noise_momentum": noise_momentum,
    "levels_rvol": levels_rvol,
}
