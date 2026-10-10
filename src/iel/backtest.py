"""Bar-by-bar backtest with no lookahead + decision-time logging.

Session-aware: works on 1-min (390/day), 5-min (78/day), hourly, daily.
For every bar i, entry uses only bars <= i (close). Fill at next bar open.
Exits: stop_R / target_R in units of entry-bar range, time_stop bars, flat EOD.
Logs EVERY signal (decision-time) so gross mean vs cost can't be hidden.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import costs as C

def _sessions(index: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (day_start_idx, day_end_idx, day_id) aligned to bars."""
    dates = pd.to_datetime(index).normalize().values
    uniq, day_id = np.unique(dates, return_inverse=True)
    starts = np.array([int(np.searchsorted(day_id, d)) for d in range(len(uniq))])
    counts = np.bincount(day_id, minlength=len(uniq))
    ends = starts + counts - 1
    return starts, ends, day_id

def run(df: pd.DataFrame, entry: str, params: dict | None = None) -> pd.DataFrame:
    from .library import ENTRYFNS
    params = params or {}
    fn = ENTRYFNS[entry]
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    vwap = df["vwap"].to_numpy() if "vwap" in df.columns else closes
    idx = pd.to_datetime(df.index)

    stop_R = float(params.get("stop_R", 1.0))
    target_R = float(params.get("target_R", 1.5))
    time_stop = int(params.get("time_stop", 10))
    rvol_min = params.get("rvol_min")
    rvol_max = params.get("rvol_max")
    price_min = float(params.get("price_min", 0.0))
    price_max = float(params.get("price_max", float("inf")))
    rvol_baseline = int(params.get("rvol_baseline", 20))
    day_rvol_min = params.get("day_rvol_min")
    day_rvol_max = params.get("day_rvol_max")
    day_rvol_lookback = int(params.get("day_rvol_lookback", 20))

    starts, ends, day_id = _sessions(idx)
    end_of_day = np.zeros(len(df), dtype=bool)
    end_of_day[ends] = True
    day_start_of = np.zeros(len(df), dtype=int)
    for s, e in zip(starts, ends):
        day_start_of[s:e + 1] = s
    day_len_of = np.zeros(len(df), dtype=int)
    for s, e in zip(starts, ends):
        day_len_of[s:e + 1] = e - s + 1

    # trailing sigma for noise_momentum: 14-session mean |open->close|
    day_opens = opens[starts]
    day_closes = closes[ends]
    if len(day_opens) > 2:
        k = min(len(day_opens) - 1, 14)
        sigma = float(np.mean(np.abs(day_closes[1:k + 1] / day_opens[:k] - 1)))
    else:
        sigma = 0.002

    # RVOL baseline (trailing, no lookahead). Computed only when gate is on.
    gate_on = rvol_min is not None or rvol_max is not None
    if gate_on:
        from .rvol import compute_rvol
        vols = df["volume"].to_numpy() if "volume" in df.columns else np.ones(len(df))
        rvol = compute_rvol(vols, day_id, baseline_sessions=rvol_baseline)
        lo = float(rvol_min) if rvol_min is not None else 0.0
        hi = float(rvol_max) if rvol_max is not None else float("inf")
    else:
        rvol = None
        lo = hi = None
    blocked_rvol = 0
    blocked_price = 0
    blocked_day = 0

    # Day-level RVOL: prior session's total volume vs trailing median.
    # Known at the open, so it never penalizes early entries for being early.
    day_gate_on = day_rvol_min is not None or day_rvol_max is not None
    if day_gate_on:
        vols_all = df["volume"].to_numpy() if "volume" in df.columns else np.ones(len(df))
        sess_vol = np.array([vols_all[(day_id == d)].sum() for d in range(len(starts))])
        dlo = float(day_rvol_min) if day_rvol_min is not None else 0.0
        dhi = float(day_rvol_max) if day_rvol_max is not None else float("inf")
        day_ok = np.zeros(len(starts), dtype=bool)
        for d in range(1, len(starts)):
            hist = sess_vol[max(0, d - 1 - day_rvol_lookback):d - 1]
            hist = hist[hist > 0]
            if len(hist) < 5 or sess_vol[d - 1] <= 0:
                continue  # insufficient history -> blocked
            day_ok[d] = dlo <= sess_vol[d - 1] / float(np.median(hist)) <= dhi
    else:
        day_ok = None

    rows = []
    pos = 0
    entry_px = 0.0
    risk = 0.0
    bars_held = 0
    entry_leg = ""
    n = len(df)
    day_open = opens[0]
    # levels_rvol context: all arrays causal per element (prior sessions,
    # cumulative-to-i, trailing-only). Built once; entry fn reads ctx[i].
    ctx = None
    if entry == "levels_rvol":
        from .library import _prior_day_levels, _session_vwap, _wilder_atr, _ema
        from .rvol import compute_rvol
        vols = df["volume"].to_numpy() if "volume" in df.columns else np.ones(len(df))
        pdh, pdl, pdc = _prior_day_levels(highs, lows, closes, day_id)
        ctx = {
            "pdh": pdh,
            "pdl": pdl,
            "pdc": pdc,
            "vwap": _session_vwap(highs, lows, closes, vols, day_id),
            "atr": _wilder_atr(highs, lows, closes, int(params.get("atr_len", 14))),
            "ema": _ema(closes, int(params.get("htf_ema_span", 20))),
            "rvol": compute_rvol(vols, day_id,
                                 baseline_sessions=int(params.get("rvol_baseline", 20))),
            "volume": vols,
            "diag": {},
        }
    for i in range(n - 1):
        ds = int(day_start_of[i])
        de = int(ds + int(day_len_of[i]) - 1)
        S = {"day_start": ds, "day_end": de, "day_pos": i - ds, "day_len": int(day_len_of[i])}
        if i == ds:
            day_open = opens[i]
        if pos != 0:
            bars_held += 1
            px = closes[i]
            pnl_R = (px / entry_px - 1) * pos / risk if risk > 0 else 0.0
            exit_ = None
            if pnl_R <= -stop_R:
                exit_ = "stop"
            elif pnl_R >= target_R:
                exit_ = "target"
            elif bars_held >= time_stop:
                exit_ = "time"
            last_today = end_of_day[i]
            if exit_ or last_today:
                fill = opens[i + 1] if i + 1 < n and not last_today else px
                ret = (fill / entry_px - 1) * pos
                rows.append({"idx": i, "day": str(idx[i].date()), "side": pos, "gross": ret,
                             "sides": 2.0, "exit": exit_ or "eod", "held": bars_held,
                             "leg": entry_leg})
                pos, bars_held = 0, 0
        if pos == 0:
            if entry == "noise_momentum":
                sig = fn(closes, day_open, i, params, S, sigma)
            elif entry == "orb_breakout":
                sig = fn(closes, highs, lows, i, params, S)
            elif entry == "vwap_reclaim":
                sig = fn(closes, vwap, i, params, S)
            elif entry == "gap_and_go":
                sig = fn(opens, closes, i, params, S)
            elif entry == "late_reversal":
                sig = fn(closes, i, params, S)
            elif entry == "levels_rvol":
                sig = fn(closes, highs, lows, opens, i, params, S, ctx)
            else:
                sig = 0
            # enter at next open only if next bar is same session
            if sig != 0 and i + 1 < n and day_id[i + 1] == day_id[i]:
                px_sig = closes[i]
                if not (price_min <= px_sig <= price_max):
                    blocked_price += 1
                elif gate_on and (not np.isfinite(rvol[i]) or not (lo <= rvol[i] <= hi)):
                    blocked_rvol += 1
                elif day_gate_on and not day_ok[day_id[i]]:
                    blocked_day += 1
                else:
                    pos = sig
                    entry_px = opens[i + 1]
                    entry_leg = (ctx.get("diag", {}).pop("leg", "") if ctx is not None
                                 else "")
                    bar_range = max(highs[i] - lows[i], entry_px * 1e-4)
                    risk = bar_range / entry_px
                    bars_held = 0
    trades = pd.DataFrame(rows)
    if not trades.empty:
        for bp in C.COST_LADDER_BP:
            trades[f"net_{bp}bp"] = trades["gross"] - trades["sides"] * bp / 1e4
    trades.attrs["blocked_rvol"] = blocked_rvol
    trades.attrs["blocked_price"] = blocked_price
    trades.attrs["blocked_day"] = blocked_day
    trades.attrs["rvol_gate"] = f"[{lo},{hi}]" if gate_on else "off"
    trades.attrs["day_gate"] = f"[{dlo},{dhi}]" if day_gate_on else "off"
    return trades
