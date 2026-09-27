"""Evaluate trades -> cost ladder + time splits + verdict. Writes FINDINGS.md."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import costs as C, metrics as M, gates as G

POSTPUB = "2024-05-01"

def _t(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) < 2 or float(np.std(x)) == 0:
        return 0.0
    return float(np.mean(x) / np.std(x) * np.sqrt(len(x)))

def _sharpe_equiv(x: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    return _t(x) / np.sqrt(len(x)) * np.sqrt(252)

def _split_frame(trades: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """First/second half, odd/even sessions, post-pub. Needs 'day' col."""
    if trades.empty or "day" not in trades.columns:
        return {}
    days = sorted(trades["day"].unique())
    if len(days) < 4:
        return {}
    pos = {d: k for k, d in enumerate(days)}
    half = len(days) // 2
    first_days = set(days[:half])
    second_days = set(days[half:])
    odd_days = {d for d in days if pos[d] % 2 == 1}
    even_days = {d for d in days if pos[d] % 2 == 0}
    out = {
        "first": trades[trades["day"].isin(first_days)],
        "second": trades[trades["day"].isin(second_days)],
        "odd": trades[trades["day"].isin(odd_days)],
        "even": trades[trades["day"].isin(even_days)],
    }
    post = trades[trades["day"] >= POSTPUB]
    if len(post) >= G.MIN_N_SPLIT:
        out["postpub"] = post
    return out

def evaluate(trades: pd.DataFrame, symbol: str = "SYN") -> dict:
    out: dict = {"symbol": symbol, "n": int(len(trades))}
    if trades.empty:
        out.update({f"sharpe_{bp}bp": 0.0 for bp in C.COST_LADDER_BP})
        out.update({"breakeven_bp": 0.0, "verdict": "INSUFFICIENT", "splits": {}})
        return out
    gross = trades["gross"].to_numpy()
    sides = trades["sides"].to_numpy()
    mean_gross = float(np.mean(gross))
    mean_sides = float(np.mean(sides))
    out["mean_gross_bp"] = mean_gross * 1e4
    out["mean_sides"] = mean_sides
    out["breakeven_bp"] = C.breakeven_bp(mean_gross, mean_sides)
    out["t_gross"] = _t(gross)
    for bp in C.COST_LADDER_BP:
        net = gross - sides * bp / 1e4
        out[f"sharpe_{bp}bp_proxy"] = _sharpe_equiv(net)
        out[f"t_{bp}bp"] = _t(net)
        out[f"win_{bp}bp"] = float(np.mean(net > 0))
        out[f"mean_net_bp_{bp}"] = float(np.mean(net) * 1e4)
    # time splits on 1bp net
    splits: dict = {}
    net1 = gross - sides * 1.0 / 1e4
    trades1 = trades.assign(_net1=net1)
    for name, sub in _split_frame(trades1).items():
        x = sub["_net1"].to_numpy()
        splits[name] = {"n": int(len(sub)), "sharpe_1bp": _sharpe_equiv(x), "t_1bp": _t(x)} \
            if len(sub) >= G.MIN_N_SPLIT else {"n": int(len(sub)), "sharpe_1bp": None, "t_1bp": None}
    out["splits"] = splits

    def _sh(name):
        s = splits.get(name)
        return None if s is None or s["sharpe_1bp"] is None else s["sharpe_1bp"]

    out["verdict"] = G.verdict(len(trades), out.get("sharpe_1.0bp_proxy", 0.0), out["breakeven_bp"],
                               sharpe_postpub=_sh("postpub"), sharpe_odd=_sh("odd"),
                               sharpe_even=_sh("even"), sharpe_first=_sh("first"),
                               sharpe_second=_sh("second"))
    return out

def _split_str(r: dict) -> str:
    parts = []
    for name in ("first", "second", "odd", "even", "postpub"):
        s = r.get("splits", {}).get(name)
        if not s:
            continue
        v = s["sharpe_1bp"]
        parts.append(f"{name}ᴺ={s['n']}/S={v:.2f}" if v is not None else f"{name}ᴺ={s['n']}/S=–")
    return " ".join(parts) if parts else "–"

def findings_md(name: str, cfg: dict, per_symbol: dict) -> str:
    lines = [f"# {name}", "", f"entry={cfg.get('entry')} params={cfg.get('params')}", "",
             "_Splits are Sharpe-proxy @1bp/side on first/second half, odd/even sessions, post-2024-05. "
             "Splits with n<15 shown as – and ignored._", ""]
    lines.append("| sym | n | t_gross | breakeven_bp | t_1bp | mean_net_1bp | splits | verdict |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for sym, r in per_symbol.items():
        lines.append(f"| {sym} | {r['n']} | {r.get('t_gross',0):.2f} | {r.get('breakeven_bp',0):.2f} | "
                     f"{r.get('t_1.0bp',0):.2f} | {r.get('mean_net_bp_1.0',0):.1f} | "
                     f"{_split_str(r)} | {r.get('verdict','')} |")
    lines += ["", "_Decision-time scored, every signal logged. Costs are per-side bp._"]
    return "\n".join(lines) + "\n"
