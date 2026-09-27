"""CLI: list / run / scan / sources."""
from __future__ import annotations
import argparse, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
HYP = ROOT / "hypotheses"

def cmd_list(_a):
    for p in sorted(HYP.glob("*.yaml")):
        if p.name.startswith("00-"):
            continue
        print(p.name)

def cmd_sources(_a):
    from .data import available_sources
    import json
    print(json.dumps(available_sources(), indent=1))

def cmd_run(a):
    from .data import load_bars
    from .backtest import run
    from .evaluate import evaluate, findings_md
    cfg = yaml.safe_load(pathlib.Path(a.hyp).read_text())
    syms = a.symbols.split(",") if a.symbols else cfg.get("universe", ["SPY"])
    base_params = dict(cfg.get("params", {}))
    filt = dict(cfg.get("filters", {}))
    # CLI overrides win over YAML filters
    if a.rvol_min is not None:
        filt["rvol_min"] = a.rvol_min
    if a.rvol_max is not None:
        filt["rvol_max"] = a.rvol_max
    if a.price_min is not None:
        filt["price_min"] = a.price_min
    params = {**base_params, **filt}
    per = {}
    for s in syms:
        s = s.strip()
        if a.synthetic:
            from .data import synthetic
            df, src = synthetic(s), "synthetic(forced)"
        else:
            df, src = load_bars(s, source=a.source)
        tr = run(df, cfg["entry"], params)
        r = evaluate(tr, s)
        r["data_source"] = src
        r["bars"] = len(df)
        r["gate"] = tr.attrs.get("rvol_gate", "off")
        r["blocked"] = (tr.attrs.get("blocked_rvol", 0), tr.attrs.get("blocked_price", 0))
        per[s] = r
        print(f"{s}[{src} n_bars={len(df)} gate={r['gate']} blocked_rvol/price={r['blocked']}]:" 
              f" n={r['n']} t_gross={r.get('t_gross',0):.2f} "
              f"breakeven={r.get('breakeven_bp',0):.2f}bp t_1bp={r.get('t_1.0bp',0):.2f} verdict={r['verdict']}")
        sp = r.get("splits", {})
        def _f(k):
            d = sp.get(k)
            return f"{k}={d['sharpe_1bp']:.2f}(n={d['n']})" if d and d["sharpe_1bp"] is not None else f"{k}=–"
        if sp:
            print(f"   splits: {_f('first')} {_f('second')} {_f('odd')} {_f('even')}" +
                  (f" {_f('postpub')}" if "postpub" in sp else ""))
    if a.out:
        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(findings_md(pathlib.Path(a.hyp).stem, cfg, per))
        print(f"wrote {out}")

def cmd_scan(a):
    for p in sorted(HYP.glob("*.yaml")):
        if p.name.startswith("00-"):
            continue
        print(f"=== {p.name} ===")
        cmd_run(type("A", (), {"hyp": str(p), "symbols": a.symbols, "synthetic": a.synthetic,
                               "source": a.source, "out": None, "rvol_min": a.rvol_min,
                               "rvol_max": a.rvol_max, "price_min": a.price_min})())

def main():
    ap = argparse.ArgumentParser(prog="iel")
    sub = ap.add_subparsers(dest="c", required=True)
    sub.add_parser("list")
    sub.add_parser("sources")
    r = sub.add_parser("run"); r.add_argument("hyp"); r.add_argument("--symbols", default=None)
    r.add_argument("--synthetic", action="store_true"); r.add_argument("--out", default=None)
    r.add_argument("--source", default="auto")
    r.add_argument("--rvol-min", type=float, default=None); r.add_argument("--rvol-max", type=float, default=None)
    r.add_argument("--price-min", type=float, default=None)
    s = sub.add_parser("scan"); s.add_argument("--symbols", default=None)
    s.add_argument("--synthetic", action="store_true"); s.add_argument("--source", default="auto")
    s.add_argument("--rvol-min", type=float, default=None); s.add_argument("--rvol-max", type=float, default=None)
    s.add_argument("--price-min", type=float, default=None)
    a = ap.parse_args()
    {"list": cmd_list, "sources": cmd_sources, "run": cmd_run, "scan": cmd_scan}[a.c](a)

if __name__ == "__main__":
    main()
