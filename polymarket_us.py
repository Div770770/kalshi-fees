"""Polymarket US taker fee by volume tier, next to Kalshi's, in exact decimal arithmetic.

Polymarket US charges the order that takes liquidity:
    fee = rate * contracts * P * (1 - P)       rounded to the nearest cent, halves to even
Since 1:00 PM ET on November 6, 2026 the rate depends on your taker volume over the last 30 days:
    below $10,000           0.095
    $10,000 to < $50,000    0.085
    $50,000 to < $250,000   0.075
    $250,000 or more        0.0695   (the rate everyone paid before November 6)
Volume is what you paid for the side you received (contracts x price), not face value. A resting
order that fills pays no fee. New accounts pay 0.0695 for their first seven days. Combos use a
separate curve and are not covered here.

Source: https://docs.polymarket.us/fees (read November 9, 2026). Check it before you rely on this.
"""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_EVEN

from kalshi_fees import fill

__all__ = ["TIERS", "rate", "account_rate", "taker_fee", "compare"]

# (30 day taker volume floor in dollars, rate), highest floor first
TIERS = (
    (Decimal("250000"), Decimal("0.0695")),
    (Decimal("50000"), Decimal("0.075")),
    (Decimal("10000"), Decimal("0.085")),
    (Decimal("0"), Decimal("0.095")),
)


def rate(volume_30d=0) -> Decimal:
    """The taker rate for an account with `volume_30d` dollars of taker volume in the last 30 days."""
    v = Decimal(str(volume_30d))
    if v < 0:
        raise ValueError("volume must not be negative")
    return next(r for floor, r in TIERS if v >= floor)


def account_rate(day, trailing_volume=0, first_week_volume=0) -> Decimal:
    """The taker rate on `day` of an account's life, for accounts whose first fill is on or after
    November 6, 2026. Day 1 is the Eastern calendar day of the first filled order.

    Days 1 to 7 pay 0.0695 whatever the volume. Days 8 to 30 use the higher of the first seven
    days' taker volume scaled by 30/7 and the trailing 30 day volume. From day 31 it is the trailing
    volume alone. Not covered: the November 2026 rule for older accounts (the better of the trailing
    tier and the October tier) and manual overrides.
    """
    if day < 1:
        raise ValueError("day counts from 1")
    if day <= 7:
        return TIERS[0][1]
    if day <= 30:
        return rate(max(Decimal(str(first_week_volume)) * 30 / 7, Decimal(str(trailing_volume))))
    return rate(trailing_volume)


def taker_fee(contracts, price_cents, volume_30d=0) -> Decimal:
    """Polymarket US taker fee in dollars for one fill, rounded to the cent (halves to even)."""
    n, p = Decimal(str(contracts)), Decimal(str(price_cents)) / 100
    if n <= 0 or not Decimal("0") < p < Decimal("1"):
        raise ValueError("contracts must be positive and the price between 0c and 100c")
    return (rate(volume_30d) * n * p * (1 - p)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def compare(contracts, price_cents, volume_30d=0) -> dict:
    """Taker fee on the same order at both exchanges, in dollars."""
    f = fill(contracts, price_cents).fee
    k = (Decimal(f.numerator) / Decimal(f.denominator)).quantize(Decimal("0.0001"))
    pm = taker_fee(contracts, price_cents, volume_30d)
    return {"kalshi": k, "polymarket_us": pm, "polymarket_us_rate": rate(volume_30d), "difference": pm - k}


if __name__ == "__main__":
    print("Taker fee on 1,000 contracts, Kalshi then Polymarket US by 30 day volume tier")
    print("%5s %9s %9s %9s %9s %9s" % ("price", "Kalshi", "<$10K", "<$50K", "<$250K", "$250K+"))
    for c in (10, 30, 50, 70, 90):
        row = [fill(1000, c).fee] + [taker_fee(1000, c, v) for v in (0, 10000, 50000, 250000)]
        print("%4dc %9.2f %9.2f %9.2f %9.2f %9.2f" % (c, *[float(x) for x in row]))
