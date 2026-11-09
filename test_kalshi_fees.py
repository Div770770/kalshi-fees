from fractions import Fraction as F
from kalshi_fees import fill, breakeven, kelly, american_odds, fee_per_contract_cents

def test_taker_50c():
    f = fill(100, 50)
    assert f.fee == F("1.75") and f.total == F("51.75")

def test_maker_50c():
    assert fill(100, 50, maker=True).fee == F("0.4375")

def test_cent_grid_rounds_up():
    assert fill(100, 50, maker=True, grid_dollars="0.01").fee == F("0.44")

def test_ticket_math_500_at_85():
    assert fill(500, 85).fee == F("4.4625")      # 0.07 * 500 * 0.85 * 0.15

def test_breakeven_40c():
    assert breakeven(40) == F("0.4168")

def test_kelly_62_at_55():
    assert round(float(kelly("0.62", 55)) * 100, 2) == 12.17

def test_kelly_no_edge_is_zero():
    assert kelly("0.40", 50) == 0

def test_odds():
    assert american_odds(40) == 150 and american_odds(75) == -300

def test_fee_peaks_at_50():
    assert fee_per_contract_cents(50) == F("1.75") and fee_per_contract_cents(10) == F("0.63")

def test_fractional_fill_close_to_a_real_kalshi_fill():
    # 388.19 contracts at 76c: Kalshi's recorded fee_cost was $4.9564 (cited in a public GitHub issue).
    # Raw fee 4.95640992; this package returns 4.9565 on the $0.0001 grid, within $0.0001.
    f = fill("388.19", 76)
    assert f.fee == F("4.9565")
    assert abs(f.fee - F("4.9564")) <= F("0.0001")
