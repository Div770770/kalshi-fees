from decimal import Decimal as D

from polymarket_us import account_rate, combo_fee, compare, rate, taker_fee


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


def test_new_account():
    # days 1 to 7 pay the top tier's rate whatever the volume
    assert account_rate(1) == account_rate(7, 0, 0) == D("0.0695")
    # day 8 to 30: first week x 30/7 against trailing, whichever is higher. $2,400 x 30/7 = $10,285.71
    assert account_rate(8, 2400, 2400) == D("0.085")
    assert account_rate(8, 2300, 2300) == D("0.095")
    assert account_rate(30, 60000, 2400) == D("0.075")
    # from day 31 the first week no longer counts
    assert account_rate(31, 2400, 2400) == D("0.095")


def test_combo():
    vols = (0, 10000, 50000, 250000)
    # 1,000 combo contracts, before the November 11 change and in each tier after it
    table = {
        5: ("6.76", "6.96", "6.48", "6.01", "5.74"),
        10: ("11.83", "12.49", "11.59", "10.69", "10.19"),
        15: ("15.52", "16.81", "15.54", "14.26", "13.56"),
        25: ("19.75", "22.56", "20.68", "18.81", "17.78"),
        50: ("20.03", "25.62", "23.12", "20.62", "19.25"),
    }
    for cents, (before, *after) in table.items():
        assert combo_fee(1000, cents, tiered=False) == D(before)
        assert [combo_fee(1000, cents, v) for v in vols] == [D(x) for x in after]
    # before the change the volume does not matter
    assert combo_fee(1000, 25, 250000, tiered=False) == combo_fee(1000, 25, 0, tiered=False)
