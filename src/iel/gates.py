"""GO / FRAGILE / NO-GO gates. Pre-register thresholds in the hypothesis YAML.

Defaults encode portfolio lessons:
- n>=30 for verdict (n>=20 suggestive only)
- net Sharpe > 0.5 at 1bp/side (vrp-harvester C1 bar)
- break-even >= 1.5bp/side (above basket best 1.8? no — must clear realistic retail)
- post-pub / odd-even must keep sign
"""
from __future__ import annotations

MIN_N_VERDICT = 30
MIN_N_SUGGESTIVE = 20

def verdict(n: int, sharpe_1bp: float, breakeven_bp: float,
            sharpe_postpub: float | None = None,
            sharpe_odd: float | None = None, sharpe_even: float | None = None) -> str:
    if n < MIN_N_SUGGESTIVE:
        return "INSUFFICIENT"
    if n < MIN_N_VERDICT:
        return "SUGGESTIVE-ONLY"
    splits = [s for s in (sharpe_postpub, sharpe_odd, sharpe_even) if s is not None]
    stable = all(s > 0 for s in splits) if splits else True
    if sharpe_1bp > 0.5 and breakeven_bp >= 1.5 and stable:
        return "GO"
    if sharpe_1bp > 0 or breakeven_bp >= 1.0:
        return "FRAGILE"
    return "NO-GO"
