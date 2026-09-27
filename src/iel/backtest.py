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

    starts, ends, day_id = _sessions(idx)
    start_of = {s: s for s in starts}
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
        sigma = float(np.mean(np.abs(day_closes[1:15] / day_opens[:14] - 1))) if len(day_opens) >= 3 else 0.002
    else:
        sigma = 0.002

    rows = []
    pos = 0
    entry_px = 0.0
    risk = 0.0
    bars_held = 0

    n = len(df)
    day_open = opens[0]
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
                rows.append({"idx": i, "side": pos, "gross": ret, "sides": 2.0,
                             "exit": exit_ or "eod", "held": bars_held})
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
            else:
                sig = 0
            # enter at next open only if next bar is same session
            if sig != 0 and i + 1 < n and day_id[i + 1] == day_id[i]:
                pos = sig
                entry_px = opens[i + 1]
                bar_range = max(highs[i] - lows[i], entry_px * 1e-4)
                risk = bar_range / entry_px
                bars_held = 0
    trades = pd.DataFrame(rows)
    if not trades.empty:
        for bp in C.COST_LADDER_BP:
            trades[f"net_{bp}bp"] = trades["gross"] - trades["sides"] * bp / 1e4
    return trades
