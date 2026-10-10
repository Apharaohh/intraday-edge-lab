# 09-levels-rvol — leg attribution (diagnostic, not a re-run)

Same frozen config, same trades (n=345/311/196 verified identical), with
each trade labeled breakout|fade at entry. No parameter changed; this is
forensics, not tuning. Sharpe-proxy @1bp/side, splits n>=15 shown.

## Per-leg table

| sym/leg | n | breakeven_bp | t_1bp | mean_net_1bp | first | second | odd | even | postpub |
|---|---|---|---|---|---|---|---|---|---|
| SPY/breakout | 193 | 1.24 | 0.15 | 0.5 | 0.93 | -0.69 | 0.23 | 0.10 | -0.72 |
| SPY/fade | 152 | 1.74 | 0.62 | 1.5 | 0.39 | 1.32 | 1.87 | -0.52 | 1.24 |
| QQQ/breakout | 175 | 1.45 | 0.18 | 0.9 | 0.18 | 0.24 | 0.85 | -0.67 | 0.73 |
| QQQ/fade | 136 | 0.80 | -0.09 | -0.4 | 0.40 | -0.91 | -0.47 | 0.23 | -0.58 |
| IWM/breakout | 114 | 2.33 | 0.36 | 2.7 | -1.71 | 3.73 | 1.53 | -0.23 | 0.54 |
| IWM/fade | 82 | 5.07 | 1.51 | 8.1 | 0.40 | 4.82 | 1.65 | 3.66 | 2.65 |

## Reading

1. **Breakout leg is dead everywhere.** Best split profile is ~zero (QQQ);
   SPY postpub -0.72, IWM first/second -1.71/+3.73. The RVOL>1.5 level-break
   carries no stable edge on any of the three ETFs.
2. **All edge lives in the fade leg — and it is universe-specific.** IWM
   fade keeps sign on every split with breakeven 5.07bp; SPY fade is mixed
   (even -0.52); QQQ fade is negative (t_1bp -0.09, postpub -0.58).
   Small-cap mean-reversion plausibly explains the ordering, but a story
   is not evidence.
3. **IWM fade is NOT promoted.** It is the best of 6 post-hoc symbol×leg
   cells — selecting it now would be the cherry-picking this design
   exists to prevent. Hypothesis-level verdict stays FRAGILE.

## Follow-up (requires its own pre-registration)

A fade-only hypothesis on the SAME universe [SPY, QQQ, IWM] testing
whether the fade leg alone passes the cross-ETF gate. Not an IWM-only
follow-up — that universe would itself be cherry-picked.
