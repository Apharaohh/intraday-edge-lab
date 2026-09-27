"""Cost model: per-side bps ladder + break-even computation.

Prior art: strategy-lab COST=1bp/side killed SPY noise-area (0.92 gross ->
0.26); basket break-evens 0.24-1.8bp/side; quant-platform round trip 0.0859 ATR.
"""
from __future__ import annotations

COST_LADDER_BP = (0.0, 0.5, 1.0, 2.0)  # per side

def apply_costs(gross_ret: float, sides: float, cost_bp: float) -> float:
    """Net return for one trade-day given gross return and sides traded."""
    return gross_ret - sides * cost_bp / 1e4

def breakeven_bp(mean_gross: float, mean_sides: float) -> float:
    """Per-side cost (bp) at which expectancy hits zero. inf if no turnover."""
    if mean_sides <= 0:
        return float("inf")
    return mean_gross / mean_sides * 1e4
