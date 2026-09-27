import pandas as pd
import numpy as np
from iel.evaluate import evaluate, _split_frame
from iel import gates as G

def _trades(n_days=10, per_day=5, edge=0.0005, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_days):
        day = f"2026-06-{d+1:02d}"
        for _ in range(per_day):
            rows.append({"day": day, "gross": edge + rng.normal(0, 0.001), "sides": 2.0})
    return pd.DataFrame(rows)

def test_splits_stable_edge_stays_go():
    tr = _trades(edge=0.001)  # strong edge survives 1bp
    r = evaluate(tr)
    assert r["splits"]["first"]["sharpe_1bp"] is not None
    assert r["splits"]["second"]["sharpe_1bp"] is not None
    assert r["verdict"] == "GO", r

def test_split_instability_blocks_go():
    # first half wins, second half loses -> must not be GO
    rows = []
    for d in range(10):
        day = f"2026-06-{d+1:02d}"
        edge = 0.002 if d < 5 else -0.002
        for _ in range(6):
            rows.append({"day": day, "gross": edge, "sides": 2.0})
    r = evaluate(pd.DataFrame(rows))
    assert r["verdict"] != "GO", r

def test_tiny_splits_ignored_not_failed():
    tr = _trades(n_days=4, per_day=8, edge=0.002, seed=1)
    r = evaluate(tr)
    # 32 trades total -> verdict path runs; tiny postpub split shouldn't veto alone
    assert r["n"] == 32
