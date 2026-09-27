"""Count-only screen for 06-liquidity-shock-reversal. SIGNAL FREQUENCY ONLY.

Reads free 1-min TRADE bars (or --synthetic) and counts how often the
shock/volume/QQQ-relative proxies fire. Uses CLOSE-to-CLOSE returns as a
stand-in for midquote returns because free bars have no NBBO.

This script MUST NOT establish fills or edge:
  - no forward returns, no expectancy, no Sharpe, no GO/NO-GO verdict
  - no spread / tradability / entry-timing / stop-target simulation
  - output is labeled INFEASIBLE_FOR_PNL by construction

Use: does the proxy signal even occur often enough to justify buying TAQ?
If the naive proxy is rare or already ugly, reject without spending.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd


BANNER = (
    "COUNT-ONLY — INFEASIBLE_FOR_PNL. Trade-bar closes proxy midquote; "
    "no spreads, no NBBO, no fills, no expectancy. Do not trade on this."
)


def _to_et(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    if getattr(idx, "tz", None) is not None:
        try:
            idx = idx.tz_convert("America/New_York")
        except Exception:
            pass
        df = df.copy()
        df.index = idx.tz_localize(None)
    return df.sort_index()


def _clock_parts(index: pd.DatetimeIndex):
    mins = index.hour * 60 + index.minute
    days = index.date
    return mins, days


def load_symbol(symbol: str, synthetic: bool) -> pd.DataFrame:
    from iel.data import load_bars, synthetic as make_synth

    if synthetic:
        return _to_et(make_synth(symbol))
    df = load_bars(symbol)
    # load_bars in this repo returns a bare DataFrame (see src/iel/data.py)
    if isinstance(df, tuple):
        df = df[0]
    return _to_et(df)


def prior_day_eligibility(df: pd.DataFrame) -> pd.Series:
    """Eligible minute = prior close >= $20 and prior-20d median daily $vol >= $100M.

    Computed causally per calendar day. Days lacking 20d history -> ineligible.
    """
    closes = df["close"]
    dvol = closes * df["volume"]
    day = pd.Series(df.index.date, index=df.index)
    daily_close = closes.groupby(day).last()
    daily_dvol = dvol.groupby(day).sum()
    days = list(daily_close.index)
    elig_day: dict = {}
    for k, d in enumerate(days):
        if k == 0:
            elig_day[d] = False
            continue
        window = days[max(0, k - 20):k]
        med = daily_dvol.loc[window].median() if len(window) else 0.0
        elig_day[d] = bool(daily_close.iloc[k - 1] >= 20.0 and med >= 100_000_000)
    return day.map(elig_day)


def count_signals(df: pd.DataFrame, qqq: pd.DataFrame | None) -> pd.DataFrame:
    df = _to_et(df)
    if qqq is not None:
        qqq = _to_et(qqq)
    close = df["close"].to_numpy()
    vol = df["volume"].to_numpy()
    idx = df.index
    clock_min, _ = _clock_parts(idx)

    ret = np.full(len(df), np.nan)
    ret[1:] = close[1:] / close[:-1] - 1.0

    # QQQ same-bar return aligned on exact timestamps (proxy for same-minute).
    if qqq is not None and len(qqq):
        qc = qqq["close"]
        # map by timestamp; missing -> NaN (no signal)
        qmap = pd.Series(qc.values, index=qqq.index)
        q_aligned = qmap.reindex(idx)
        q_prev = q_aligned.shift(1)
        qret = (q_aligned / q_prev - 1.0).to_numpy()
    else:
        qret = np.full(len(df), np.nan)

    elig = prior_day_eligibility(df).to_numpy()
    in_window = (clock_min >= 10 * 60) & (clock_min <= 14 * 60 + 30)

    # Per (clock-minute, rolling 20-session) volume median and return std.
    # Build day list for causal windows.
    days = np.array([d.toordinal() for d in idx.date])
    uniq_days = sorted(set(idx.date))
    pos = {d: k for k, d in enumerate(uniq_days)}
    day_idx = np.array([pos[d] for d in idx.date])

    # Pre-group row indices by (day_pos, clock_min).
    from collections import defaultdict

    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i in range(len(df)):
        buckets[(day_idx[i], int(clock_min[i]))].append(i)

    vol_med = np.full(len(df), np.nan)
    ret_std = np.full(len(df), np.nan)
    for i in range(len(df)):
        cm = int(clock_min[i])
        dp = int(day_idx[i])
        if dp < 1:
            continue
        past_vol, past_ret = [], []
        for back in range(1, 21):
            rows = buckets.get((dp - back, cm))
            if not rows:
                continue
            for r in rows:
                past_vol.append(vol[r])
                if not np.isnan(ret[r]):
                    past_ret.append(ret[r])
        if len(past_vol) >= 10:
            vol_med[i] = float(np.median(past_vol))
        if len(past_ret) >= 10:
            sd = float(np.std(past_ret, ddof=1))
            ret_std[i] = sd if sd > 0 else np.nan

    raw = (ret <= -0.006) & in_window & elig
    sig = (~np.isnan(ret_std)) & (ret <= -3.0 * ret_std)
    volok = (~np.isnan(vol_med)) & (vol_med > 0) & (vol >= 3.0 * vol_med)
    rel = (~np.isnan(qret)) & ((ret - qret) <= -0.004) & (qret > -0.003)

    out = pd.DataFrame(
        {
            "ret_1m": ret,
            "qqq_ret_1m": qret,
            "vol_med_20d": vol_med,
            "ret_std_20d": ret_std,
            "eligible": elig,
            "in_window": in_window,
            "raw_shock": pd.Series(raw, index=idx).fillna(False).to_numpy(),
            "pass_sigma": pd.Series(raw & sig, index=idx).fillna(False).to_numpy(),
            "pass_volume": pd.Series(raw & sig & volok, index=idx).fillna(False).to_numpy(),
            "pass_all": pd.Series(raw & sig & volok & rel, index=idx).fillna(False).to_numpy(),
        },
        index=idx,
    )
    out["vol_mult"] = np.where(
        out["vol_med_20d"].to_numpy() > 0,
        vol / np.where(out["vol_med_20d"].to_numpy() > 0, out["vol_med_20d"].to_numpy(), np.nan),
        np.nan,
    )
    return out


def summarize(symbol: str, flags: pd.DataFrame) -> dict:
    n_days = flags.index.date
    ndays = len(set(n_days)) if len(flags) else 0
    elig_cov = float(flags["eligible"].mean()) if len(flags) else 0.0
    rows = {
        "symbol": symbol,
        "bars": int(len(flags)),
        "days": int(ndays),
        "eligible_bar_share": round(elig_cov, 4),
        "raw_shocks": int(flags["raw_shock"].sum()),
        "pass_sigma": int(flags["pass_sigma"].sum()),
        "pass_volume": int(flags["pass_volume"].sum()),
        "pass_all_proxy": int(flags["pass_all"].sum()),
    }
    rows["per_day_all_proxy"] = round(rows["pass_all_proxy"] / ndays, 3) if ndays else 0.0
    sub = flags[flags["pass_all"].to_numpy()]
    rows["median_vol_mult_at_signal"] = round(float(sub["vol_mult"].median()), 2) if len(sub) else None
    rows["median_ret_bp_at_signal"] = round(float(sub["ret_1m"].median()) * 1e4, 1) if len(sub) else None
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="COUNT-ONLY shock proxy frequency. No P&L.")
    ap.add_argument("--symbols", default="SPY,QQQ", help="comma list; QQQ used as reference by default")
    ap.add_argument("--qqq", default="QQQ", help="reference symbol for idiosyncratic proxy")
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args(argv)

    print(BANNER)
    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    try:
        qqq_df = load_symbol(args.qqq, args.synthetic)
    except Exception as e:
        print(f"reference {args.qqq} unavailable ({e}); idiosyncratic stage will be 0")
        qqq_df = None

    print("symbol | bars | days | elig_share | raw | +sigma | +vol | +qqq_proxy | per_day | med_volx | med_ret_bp")
    for s in syms:
        if s == args.qqq:
            qref = qqq_df
        else:
            qref = qqq_df
        try:
            df = load_symbol(s, args.synthetic)
        except Exception as e:
            print(f"{s}: no data ({e})")
            continue
        if df.empty or "close" not in df.columns:
            print(f"{s}: empty")
            continue
        flags = count_signals(df, qref)
        r = summarize(s, flags)
        print(
            f"{r['symbol']} | {r['bars']} | {r['days']} | {r['eligible_bar_share']} | "
            f"{r['raw_shocks']} | {r['pass_sigma']} | {r['pass_volume']} | {r['pass_all_proxy']} | "
            f"{r['per_day_all_proxy']} | {r['median_vol_mult_at_signal']} | {r['median_ret_bp_at_signal']}"
        )
    print("END " + BANNER)
    print("Refusing P&L: no expectancy / Sharpe / verdict computed. For TAQ verdict spec see hypotheses/06-*.yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
