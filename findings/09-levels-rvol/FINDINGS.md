# 09-levels-rvol

entry=levels_rvol params={'stop_R': 1.0, 'target_R': 2.0, 'time_stop': 390, 'rvol_baseline': 20, 'rvol_elevated': 1.5, 'rvol_low': 0.8, 'atr_len': 14, 'barvol_lookback': 20, 'barvol_mult': 1.0, 'fade_vwap_atr_band': 0.5, 'htf_ema_span': 20}

_Splits are Sharpe-proxy @1bp/side on first/second half, odd/even sessions, post-2024-05. Splits with n<15 shown as – and ignored._

| sym | n | t_gross | breakeven_bp | t_1bp | mean_net_1bp | splits | verdict |
|---|---|---|---|---|---|---|---|
| SPY | 345 | 1.39 | 1.46 | 0.44 | 0.9 | firstᴺ=173/S=0.80 secondᴺ=172/S=-0.11 oddᴺ=178/S=1.42 evenᴺ=167/S=-0.77 postpubᴺ=154/S=-0.15 | FRAGILE |
| QQQ | 311 | 0.68 | 1.16 | 0.10 | 0.3 | firstᴺ=156/S=0.00 secondᴺ=155/S=0.18 oddᴺ=151/S=1.42 evenᴺ=160/S=-1.35 postpubᴺ=148/S=0.29 | FRAGILE |
| IWM | 196 | 1.44 | 3.48 | 1.02 | 5.0 | firstᴺ=95/S=-0.92 secondᴺ=101/S=3.93 oddᴺ=97/S=3.20 evenᴺ=99/S=-0.83 postpubᴺ=196/S=1.16 | FRAGILE |

_Decision-time scored, every signal logged. Costs are per-side bp._
