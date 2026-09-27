"""CLI: list / run / scan."""
from __future__ import annotations
import argparse, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
HYP = ROOT / "hypotheses"

def _load(name: str) -> dict:
    import yaml as y
    return y.safe_load((HYP / name).read_text())

def cmd_list(_a):
    for p in sorted(HYP.glob("*.yaml")):
        if p.name.startswith("00-"):
            continue
        print(p.name)

def cmd_run(a):
    from .data import load_bars, DATA
    from .backtest import run
    from .evaluate import evaluate, findings_md
    cfg = yaml.safe_load(pathlib.Path(a.hyp).read_text())
    syms = a.symbols.split(",") if a.symbols else cfg.get("universe", ["SPY"])
    per = {}
    for s in syms:
        s = s.strip()
        df = load_bars(s) if not a.synthetic else __import__("iel.data", fromlist=["synthetic"]).synthetic(s)
        tr = run(df, cfg["entry"], cfg.get("params", {}))
        r = evaluate(tr, s)
        per[s] = r
        print(f"{s}: n={r['n']} t_gross={r.get('t_gross',0):.2f} breakeven={r.get('breakeven_bp',0):.2f}bp "
              f"t_1bp={r.get('t_1.0bp',0):.2f} verdict={r['verdict']}")
    if a.out:
        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(findings_md(pathlib.Path(a.hyp).stem, cfg, per))
        print(f"wrote {out}")

def cmd_scan(a):
    import subprocess
    for p in sorted(HYP.glob("*.yaml")):
        if p.name.startswith("00-"):
            continue
        print(f"=== {p.name} ===")
        cmd_run(type("A", (), {"hyp": str(p), "symbols": a.symbols, "synthetic": a.synthetic, "out": None})())

def main():
    ap = argparse.ArgumentParser(prog="iel")
    sub = ap.add_subparsers(dest="c", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run"); r.add_argument("hyp"); r.add_argument("--symbols", default=None)
    r.add_argument("--synthetic", action="store_true"); r.add_argument("--out", default=None)
    s = sub.add_parser("scan"); s.add_argument("--symbols", default=None); s.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    {"list": cmd_list, "run": cmd_run, "scan": cmd_scan}[a.c](a)

if __name__ == "__main__":
    main()
