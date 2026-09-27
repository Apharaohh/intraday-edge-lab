from iel import costs as C

def test_ladder_math():
    assert C.apply_costs(0.001, 2.0, 1.0) == 0.001 - 2 * 1.0 / 1e4
    assert abs(C.breakeven_bp(0.0004, 2.0) - 2.0) < 1e-9

def test_zero_turnover_inf():
    import math
    assert math.isinf(C.breakeven_bp(0.001, 0.0))
