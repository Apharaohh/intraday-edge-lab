"""RVOL: today's cumulative volume vs trailing time-of-day baseline.

Mirrors schwab-scalper's rvol_at_bar: RVOL(i) = cumvol_today(i) /
mean over trailing N sessions of cumvol at same bar-of-day. Sessions with
different bar counts truncate to the shortest baseline session.

No lookahead: baseline uses strictly prior sessions only.
"""
from __future__ import annotations
import numpy as np


def compute_rvol(volume: np.ndarray, day_id: np.ndarray,
                 baseline_sessions: int = 20, min_history: int = 5) -> np.ndarray:
    volume = np.asarray(volume, dtype=float)
    day_id = np.asarray(day_id)
    rvol = np.full(len(volume), np.nan)
    sessions = np.unique(day_id)
    # per-session volume lists + cumulative
    vols = {d: volume[day_id == d] for d in sessions}
    cums = {d: np.cumsum(v) for d, v in vols.items()}
    pos_in_day = np.zeros(len(volume), dtype=int)
    for d in sessions:
        m = day_id == d
        pos_in_day[m] = np.arange(int(m.sum()))
    for k, d in enumerate(sessions):
        prior = sessions[max(0, k - baseline_sessions):k]
        prior = [p for p in prior if len(vols[p]) > 0]
        if len(prior) < min_history:
            continue
        min_len = min(len(vols[p]) for p in prior)
        if min_len == 0:
            continue
        base = np.zeros(min_len)
        for p in prior:
            base += cums[p][:min_len]
        base /= len(prior)
        m = day_id == d
        idx = np.where(m)[0]
        for j, i in enumerate(idx):
            b = base[min(j, min_len - 1)]
            rvol[i] = cums[d][j] / b if b > 0 else np.nan
    return rvol
