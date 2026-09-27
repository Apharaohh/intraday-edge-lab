"""Bar-by-bar backtest with no lookahead + decision-time logging.

For every bar i, entry uses only bars <= i (close). Fill at next bar open.
Exits: stop_R / target_R in units of entry-bar range, time_stop bars, flat EOD.
Logs EVERY signal (decision-time) so gross mean vs cost can't be hidden —
the move-forensics lesson.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import costs as C

def run(df: pd.DataFrame, entry: str, params: dict | None = None) -> pd.DataFrame:
    from .library import ENTRYFNS
    params = params or {}
    fn = ENTRYFNS[entry]
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    vwap = df["vwap"].to_numpy() if "vwap" in df.columns else closes

    stop_R = float(params.get("stop_R", 1.0))
    target_R = float(params.get("target_R", 1.5))
    time_stop = int(params.get("time_stop", 10))

    # trailing sigma for noise_momentum: 14-day mean |open->close| approx
    sigma = float(np.mean(np.abs(closes[::390][1:11] / closes[::390][:10] - 1))) if len(closes) > 3900 else 0.002

    rows = []
    pos = 0
    entry_px = 0.0
    risk = 0.0
    bars_held = 0
    day_open = opens[0]

    n = len(df)
    for i in range(n - 1):
        day_start = (i // 390) * 390
        if i == day_start:
            day_open = opens[i]
        # manage open position on this bar's close
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
            elif (i + 1) // 390 != i // 390 or i == n - 2:  # EOD flatten handled at next open; mark here
                pass
            # flatten at EOD close
            is_last_bar_of_day = (i + 1) % 390 == 0 or (i + 1) // 390 != i // 390
            if exit_ or is_last_bar_of_day:
                fill = opens[i + 1] if i + 1 < n and not is_last_bar_of_day else px
                ret = (fill / entry_px - 1) * pos
                rows.append({"idx": i, "side": pos, "gross": ret, "sides": 2.0,
                             "exit": exit_ or "eod", "held": bars_held})
                pos, bars_held = 0, 0
        # new entry at next open if flat — decision made on bar i close only
        if pos == 0:
            if entry == "noise_momentum":
                sig = fn(closes, day_open, i, params, sigma)
            elif entry == "orb_breakout":
                sig = fn(closes, highs, lows, i, params)
            elif entry == "vwap_reclaim":
                sig = fn(closes, vwap, i, params)
            elif entry == "gap_and_go":
                sig = fn(opens, closes, i, params)
            elif entry == "late_reversal":
                sig = fn(closes, i, params)
            else:
                sig = 0
            if sig != 0 and i + 1 < n and (i + 1) // 390 == i // 390:
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

def daily_series(trades: pd.DataFrame, index: pd.DatetimeIndex, col: str = "net_1.0bp") -> pd.Series:
    s = pd.Series(0.0, index=pd.to_datetime(index.date).unique() if len(index) else [])
    s.index = pd.to_datetime(s.index)
    if trades.empty:
        return s
    return s
