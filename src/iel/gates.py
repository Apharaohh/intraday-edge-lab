"""GO / FRAGILE / NO-GO gates. Pre-register thresholds in the hypothesis YAML.

Defaults encode portfolio lessons:
- n>=30 for verdict (n>=20 suggestive only)
- net Sharpe > 0.5 at 1bp/side (vrp-harvester C1 bar)
- break-even >= 1.5bp/side
- every reported split must keep sign (first/second half, odd/even, post-pub).
  Splits with n < MIN_N_SPLIT (15) are ignored as uninformative rather than
  failing — the full-sample n>=30 rule still applies.
"""
from __future__ import annotations

MIN_N_VERDICT = 30
MIN_N_SUGGESTIVE = 20
MIN_N_SPLIT = 15

def verdict(n: int, sharpe_1bp: float, breakeven_bp: float,
            sharpe_postpub: float | None = None,
            sharpe_odd: float | None = None, sharpe_even: float | None = None,
            sharpe_first: float | None = None, sharpe_second: float | None = None) -> str:
    if n < MIN_N_SUGGESTIVE:
        return "INSUFFICIENT"
    if n < MIN_N_VERDICT:
        return "SUGGESTIVE-ONLY"
    splits = [s for s in (sharpe_postpub, sharpe_odd, sharpe_even,
                          sharpe_first, sharpe_second) if s is not None]
    stable = all(s > 0 for s in splits) if splits else True
    if sharpe_1bp > 0.5 and breakeven_bp >= 1.5 and stable:
        return "GO"
    if sharpe_1bp > 0 or breakeven_bp >= 1.0:
        return "FRAGILE"
    return "NO-GO"
