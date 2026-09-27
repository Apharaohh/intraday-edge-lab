from iel import gates as G

def test_insufficient():
    assert G.verdict(5, 2.0, 5.0) == "INSUFFICIENT"
    assert G.verdict(25, 2.0, 5.0) == "SUGGESTIVE-ONLY"

def test_go_needs_stability():
    assert G.verdict(100, 0.8, 2.0, sharpe_postpub=0.3) == "GO"
    assert G.verdict(100, 0.8, 2.0, sharpe_postpub=-0.2) != "GO"

def test_nogo():
    assert G.verdict(100, -0.5, 0.2) == "NO-GO"
