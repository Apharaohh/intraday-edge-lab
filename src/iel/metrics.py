"""Metrics: Sharpe, t-stat, maxDD, exposure. Population-std to match quant-platform."""
from __future__ import annotations
import numpy as np

ANN = 252.0

def sharpe(daily: np.ndarray) -> float:
    daily = np.asarray(daily, dtype=float)
    if len(daily) < 2 or float(np.std(daily)) == 0:
        return 0.0
    return float(np.mean(daily) / np.std(daily) * np.sqrt(ANN))

def t_stat(daily: np.ndarray) -> float:
    daily = np.asarray(daily, dtype=float)
    if len(daily) < 2 or float(np.std(daily)) == 0:
        return 0.0
    return float(np.mean(daily) / np.std(daily) * np.sqrt(len(daily)))

def max_drawdown(equity: np.ndarray) -> float:
    eq = np.asarray(equity, dtype=float)
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float(np.min(eq / np.where(peak == 0, 1, peak) - 1.0))

def summarize(daily: np.ndarray) -> dict:
    daily = np.asarray(daily, dtype=float)
    eq = (1 + daily).cumprod() if len(daily) else np.array([1.0])
    yrs = len(daily) / ANN if len(daily) else 0.0
    cagr = float(eq[-1] ** (1 / yrs) - 1) if yrs > 0 and eq[-1] > 0 else 0.0
    return {
        "n": int(len(daily)),
        "cagr": cagr,
        "vol": float(np.std(daily) * np.sqrt(ANN)) if len(daily) > 1 else 0.0,
        "sharpe": sharpe(daily),
        "t": t_stat(daily),
        "maxdd": max_drawdown(eq),
        "win": float(np.mean(daily > 0)) if len(daily) else 0.0,
        "traded_pct": float(np.mean(daily != 0)) if len(daily) else 0.0,
    }
