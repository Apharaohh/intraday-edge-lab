"""Evaluate trades -> cost ladder + splits + verdict. Writes FINDINGS.md."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import costs as C, metrics as M, gates as G

def evaluate(trades: pd.DataFrame, symbol: str = "SYN") -> dict:
    out: dict = {"symbol": symbol, "n": int(len(trades))}
    if trades.empty:
        out.update({f"sharpe_{bp}bp": 0.0 for bp in C.COST_LADDER_BP})
        out.update({"breakeven_bp": 0.0, "verdict": "INSUFFICIENT"})
        return out
    gross = trades["gross"].to_numpy()
    sides = trades["sides"].to_numpy()
    # per-trade -> daily approx: group by trade order into pseudo-days of 1 trade
    # (real daily aggregation happens in CLI when dates present; here trade-level t)
    mean_gross = float(np.mean(gross))
    mean_sides = float(np.mean(sides))
    out["mean_gross_bp"] = mean_gross * 1e4
    out["mean_sides"] = mean_sides
    out["breakeven_bp"] = C.breakeven_bp(mean_gross, mean_sides)
    # trade-level Sharpe annualized by ~252*trades_per_year proxy; report t instead
    t0 = float(np.mean(gross) / np.std(gross) * np.sqrt(len(gross))) if np.std(gross) > 0 else 0.0
    out["t_gross"] = t0
    for bp in C.COST_LADDER_BP:
        net = gross - sides * bp / 1e4
        t = float(np.mean(net) / np.std(net) * np.sqrt(len(net))) if np.std(net) > 0 else 0.0
        out[f"sharpe_{bp}bp_proxy"] = t / np.sqrt(len(net)) * np.sqrt(252)  # Sharpe-equiv
        out[f"t_{bp}bp"] = t
        out[f"win_{bp}bp"] = float(np.mean(net > 0))
        out[f"mean_net_bp_{bp}"] = float(np.mean(net) * 1e4)
    # crude Sharpe proxy via daily bucketing if 'day' col exists
    out["verdict"] = G.verdict(len(trades), out.get("sharpe_1.0bp_proxy", 0.0), out["breakeven_bp"])
    return out

def findings_md(name: str, cfg: dict, per_symbol: dict) -> str:
    lines = [f"# {name}", "", f"entry={cfg.get('entry')} params={cfg.get('params')}", ""]
    lines.append("| sym | n | t_gross | mean_gross_bp | mean_sides | breakeven_bp | t_1bp | mean_net_1bp | verdict |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for sym, r in per_symbol.items():
        lines.append(f"| {sym} | {r['n']} | {r.get('t_gross',0):.2f} | {r.get('mean_gross_bp',0):.1f} | "
                     f"{r.get('mean_sides',0):.2f} | {r.get('breakeven_bp',0):.2f} | "
                     f"{r.get('t_1.0bp',0):.2f} | {r.get('mean_net_bp_1.0',0):.1f} | {r.get('verdict','')} |")
    lines += ["", "_Decision-time scored, every signal logged. Costs are per-side bp._"]
    return "\n".join(lines) + "\n"
