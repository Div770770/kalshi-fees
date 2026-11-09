from decimal import Decimal as D

from polymarket_us import compare, rate, taker_fee


def test_tiers():
    assert rate(0) == D("0.095")
    assert rate("9999.99") == D("0.095")
    assert rate(10000) == D("0.085")
    assert rate(49999) == D("0.085")
    assert rate(50000) == D("0.075")
    assert rate(250000) == D("0.0695")


def test_fee_on_1000_contracts():
    # 1,000 contracts at 50c: $23.75, $21.25, $18.75 and $17.38 (17.375 rounds to the even cent)
    assert [taker_fee(1000, 50, v) for v in (0, 10000, 50000, 250000)] == [D("23.75"), D("21.25"), D("18.75"), D("17.38")]
    assert taker_fee(1000, 10, 0) == taker_fee(1000, 90, 0) == D("8.55")
    assert taker_fee(1000, 30, 250000) == D("14.60")


def test_month_at_50c():
    # $9,000 of volume at 50c is 18,000 contracts: $315.00 on Kalshi, $427.50 on Polymarket US below $10,000
    c = compare(18000, 50, 9000)
    assert c["kalshi"] == D("315.0000") and c["polymarket_us"] == D("427.50") and c["difference"] == D("112.5000")
