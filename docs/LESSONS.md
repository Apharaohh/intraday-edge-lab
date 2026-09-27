# What the rest of ~/Projects already proved — read before proposing anything
# Sources: strategy-lab/{README,RESULTS,INTRADAY,BASKET,GEX*}, quant-platform README,
#   vrp-harvester docs/design, daytrading-agents CLAUDE.md, schwab-scalper README.

1. COST IS THE EDGE. Avg 2.8 sides/traded-day means 1bp/side ≈ full Sharpe killer
   on SPY (0.92 gross → 0.26 @1bp → -0.39 @2bp). Any hypothesis without a
   break-even ≥1.5bp/side is entertainment, not a strategy.

2. SCORE DECISION-TIME, NOT OUTCOME. quant-platform move forensics: selecting on
   outcome inflated edge by ~0.8 ATR. Log every bar where entry conditions fire
   at that bar's close; report gross mean per signal vs round-trip cost
   (0.0859 ATR measured there) separately.

3. CROSS-SECTION OR IT DIDN'T HAPPEN. basket.py: 0/8 survive on 51 stocks and
   0/8 on 15 ETFs. QQQ noise-momentum Sharpe 1.00 @1bp is tech-regime/chance —
   negative on 13/15 ETFs. Require ≥2 ETFs or own the regime label.

4. TIME-SPLIT EVERYTHING. Full-sample Sharpe lies. Report full + post-2024-05
   (noise-area pub) + odd/even years. SPY noise-area went 0.26 → -0.66 post-pub.

5. N≥30 OR SILENCE. schwab-scalper flags n<20, suggestive-only <30. Option-Flow
   refuses backtest <20. This lab refuses verdicts <30.

6. VOL ≠ DIRECTION. GEX H1 (neg-GEX → +21% wider next-day range, OOS t=6.6) is
   the only surviving GEX result and forecasts volatility. H3 continuation is
   significantly *reversal* (t=-3.1, hypothesis-only). gex_entry NOT CONFIRMED.
   Use GEX/VIX for sizing/stops, and vrp-harvester proved richer credit in
   neg-GEX outweighs wider ranges over 30-day holds — the opposite of gating.

7. VRP IS THE ONLY FUNDED EDGE. vrp-harvester short put-spread: Sharpe
   0.81→0.87 skew-adjusted, 92-96% win, 12 trades/yr, costs <7% gross. Intraday
   work should complement it (vol timing, entry sizing) not compete with it.

8. DATA REALITY. No historical L2 (capture forward only — schwab-scalper
   daemon). No Schwab history >~50 days. Spread gate uncheckable on OHLCV.
   State the missing piece in every FINDINGS.md rather than assuming it away.
