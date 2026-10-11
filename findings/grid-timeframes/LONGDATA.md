# LONGDATA — grid on longest stitched intraday (2026-10-10)

SPY/QQQ: 2020 slice + 2022 slice + QP 2021-07+ (117k/98k bars).
IWM: 2022 slice + QP 2024-07+ (58k bars, no 2020 exists).
Deltas vs the 2021+ grid (same gates):

| cell | 2021+ | +crash/bear | read |
|---|---|---|---|
| noise QQQ 15m | GO 1.47 | FRAGILE (first 0.01, odd 0.02) | downgrade — crash killed it |
| noise QQQ 30m | GO 2.00 | GO (0.81/0.50/0.81/0.53) | holds |
| noise QQQ 60m | GO 1.86 | GO (1.88/0.32/1.35/0.96) | holds |
| gap SPY/QQQ 5m | FRAGILE | NO-GO | downgrade — flicker gone |
| late-rev IWM 30m | GO 2.22 | NO-GO | downgrade — was the luckiest draw, confirmed |
| 07-orb-rvol IWM 60m | GO (n=39) | GO (n=44, all splits +) | holds, still thin |
| 09 SPY/QQQ 5m | FRAGILE | FRAGILE | unchanged |
| 09 IWM 5m | FRAGILE | GO (0.25/2.37/2.20/0.59) | upgrade, second-half loaded |
| everything else | NO-GO | NO-GO | 07/08 long-data: only IWM-60m cells above FRAGILE |

## Reading

1. Crash + bear downgraded 3 cells and upgraded 1. Net: the grid is
   slightly WEAKER on long data — the honest direction (more regimes,
   fewer survivors).
2. Noise-QQQ 30/60m is the only entry×universe pair green on both windows.
   Still QQQ-only (dead SPY/IWM everywhere) — TF-robust, ETF-fragile.
   Paper track at most, unchanged stance.
3. 04-IWM-30m going GO→NO-GO validates the N=60 luckiest-draw call in
   MATRIX.md in real time.
4. Promote nothing. Long-data confirms the grid rather than overturning it.
