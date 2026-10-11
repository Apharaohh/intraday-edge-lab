# Timeframe grid (pre-registered 2026-10-10 — runs after this file is committed)

Question: does any established edge-lab entry hold across intraday timeframes
on index ETFs, or is every edge a timeframe artifact?

## Frozen matrix (60 cells)

- **Entries (5, all pre-existing — zero new strategies invented):**
  orb_breakout, vwap_reclaim, gap_and_go, late_reversal, noise_momentum
  with their committed default params (see hypotheses/01-05,07-08 yamls).
- **Timeframes (4):** 5, 15, 30, 60 min. Base data is QP 5-min RTH bars;
  15/30/60 are exact OHLCV resamples with session boundaries preserved and
  session VWAP recomputed (no lookahead: each resampled bar uses only its
  constituent 5-min bars; VWAP cumulative within session only).
- **Universe (3):** SPY, QQQ, IWM via QP_DB_PATH sqlite. IWM 5-min starts
  2024-07 (2yr vs 5yr for SPY/QQQ) — disclosed, splits still apply.
- **Costs/gates:** standard ladder 0/0.5/1/2bp + gates (min_n 30,
  min_sharpe_1bp 0.5, min_breakeven_bp 1.5) + full/postpub/odd/even splits.

## Reading rules (frozen)

- Report ALL 60 cells. Promote nothing from this grid.
- Timeframe-stability (same entry green on ≥3 TFs) is an observation, not
  a promotion — it would earn a paper track at most.
- Any best-cell claim is trial-counted at **N=60** (DSR bar ≈ unreachable
  by construction at this N — stated so nobody tries).
- Excluded: levels_rvol (under judgment in 09 — stays out of the grid).
