# Timeframe grid — full 60-cell matrix (2026-10-10)

Base: QP 5-min RTH (SPY/QQQ 5yr, IWM 2yr); 15/30/60 exact resamples.
Verdicts per cell (t_1bp in parens). 06 blocked (needs TAQ). 09 out of grid.

| entry | 5m SPY/QQQ/IWM | 15m SPY/QQQ/IWM | 30m SPY/QQQ/IWM | 60m SPY/QQQ/IWM |
|---|---|---|---|---|
| 01 orb | N/N/N | N/N/N | N/F/N | N/F/N |
| 02 vwap-reclaim | N/N/N | N/N/N | N/F/F | N/F/N |
| 03 gap-and-go | F/F/N | N/N/N | N/N/N | N/N/N |
| 04 late-reversal | N/N/N | N/N/F | N/N/**G** | I/I/I |
| 05 noise-momentum | N/N/N | F/**G**/N | F/**G**/N | F/**G**/N |
| 07 orb-rvol | F/N/N | F/N/N | F/N/N | N/N/**G**(n=39) |
| 08 orb-dayrvol | N/N/N | N/N/N | N/N/N | N/N/F |

N=NO-GO, F=FRAGILE, G=GO, I=INSUFFICIENT.

## GO cells (split detail @1bp)

- **05 QQQ 15m** (n=655, t=1.47, be=3.00bp): first 1.24 / second 0.52 / odd 0.17 / even 1.55 / postpub 0.51
- **05 QQQ 30m** (n=428, t=2.00, be=5.12bp): first 2.35 / second 0.68 / odd 1.09 / even 1.94 / postpub 0.48
- **05 QQQ 60m** (n=345, t=1.86, be=5.33bp): first 1.89 / second 1.26 / odd 1.08 / even 2.03 / postpub 0.91
- **04 IWM 30m** (n=127, t=2.22, be=4.01bp): first 3.29 / second 3.04 / odd 3.35 / even 2.95 / postpub 3.13
- **07 IWM 60m** (n=39, t=0.79, be=6.79bp): splits n≈19-20 each — thin, all positive but fragile by n.

## Reading (frozen rules: promote nothing)

1. **Noise-momentum on QQQ is green on 15/30/60m and dead on 5m** — meets
   the pre-registered timeframe-stability observation (≥3 TFs). But it is
   dead on SPY and IWM at every TF: the same QQQ-only fragility this
   portfolio documented for the Zarattini replication (of which this IS the
   replication — 05 IS noise_momentum). TF-stable, ETF-fragile. Earns a
   paper track at most, not capital.
2. **04 IWM 30m** is an isolated cell (late-reversal dead in all 11 other
   cells). At N=60 trial counting it is indistinguishable from the luckiest
   of 60 draws. No track.
3. **07 IWM 60m** (n=39): GO by the letter, thin by n. No track.
4. ORB, vwap-reclaim, gap, dayrvol gates: nothing above FRAGILE anywhere.
   Gap-and-go's 5m SPY/QQQ FRAGILE decays to NO-GO at every higher TF.
