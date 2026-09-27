# intraday-edge-lab

Hypothesis-driven search for **intraday** edges. Built because the rest of
`~/Projects` proved what *doesn't* work — this lab enforces those lessons
by construction.

## Why this exists (distilled from prior repos)

| Lesson | Source | Rule enforced here |
|---|---|---|
| Costs kill everything (break-even 0.24–1.8bp/side) | `strategy-lab/basket.py`, `INTRADAY_RESULTS.txt` | Every run scored on a **cost ladder** 0 / 0.5 / 1 / 2 bp/side + break-even reported |
| Outcome-selection lies (~0.8 ATR phantom edge) | `quant-platform` move forensics | **Decision-time scoring**: every gate-clearing bar logged, gross mean vs cost reported separately |
| QQQ-only ≠ general edge | `strategy-lab` ETF basket 0/8, XLK overlap | **Cross-ETF gate**: must hold on ≥2 of SPY/QQQ/IWM or be labeled regime-specific |
| Post-publication decay | noise-momentum SPY post-pub Sharpe -0.66 | **Time-split gate**: full + post-2024 + odd/even years |
| n<30 is noise | `schwab-scalper`, `Option-Flow` n≥20 rule | **n≥30** for verdict, n≥20 suggestive-only |
| GEX predicts vol, not direction | `strategy-lab` H1 PASS / H3 reversal | GEX/vol used for **sizing only**, never entry (see H4) |
| No lookahead, ever | `tickforge` BarWindow, `quant-platform` StrategyContext | Backtest passes only past bars; test asserts this |

## Quickstart

```bash
cd ~/Projects/intraday-edge-lab
python3 -m venv .venv && source .venv/bin/activate  # or: uv sync
pip install -e .
python -m iel.cli list
python -m iel.cli run hypotheses/01-orb-breakout.yaml --synthetic
python -m iel.cli scan --synthetic   # cost-ladder table for all hypotheses
pytest -q
```

## Bring your own bars

No 1-min data is vendored (too big, gitignored). Adapters, in priority order:

1. `strategy-lab` Alpaca SIP pickles (`data/SPY_1min.pkl` layout) — put them in `./data/`
2. `tickforge` store (`./store`, `tickforge collect` output)
3. `quant-platform` `data/market.db` daily + `intraday_bars`
4. Schwab 50-day window via `tickforge.data` (short windows only)

`src/iel/data.py::load_bars()` auto-detects whatever is present; `--synthetic`
generates a seeded random-walk fixture so the harness runs with zero data.

## Adding a hypothesis

1. Copy `hypotheses/00-template.yaml`, fill entry/exit/costs/splits.
2. Implement `entry()` in `src/iel/library.py` (pure function of past bars).
3. Pre-register: `git add hypotheses/XX-*.yaml && git commit`.
4. Run + commit `findings/XX-*/FINDINGS.md`.

Verdict scale: **GO / FRAGILE / NO-GO** (see `src/iel/gates.py`).
