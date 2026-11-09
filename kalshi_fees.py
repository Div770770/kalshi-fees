"""Kalshi trading fee, break-even and Kelly sizing, in exact integer arithmetic.

Kalshi's general fee schedule charges, per fill of n contracts at price P (in dollars):
    taker fee = ceil(0.07   * n * P * (1 - P))   on the fee grid
    maker fee = ceil(0.0175 * n * P * (1 - P))
Some markets carry a different multiplier; pass it as `multiplier`. Amounts are computed
in micro dollars (1e-6 $) so nothing drifts, the fee is rounded up, and cost plus fee is then
aligned up to the account grid ($0.0001 by default, or $0.01).

Free calculators that use the same math, no sign-up:
    https://evdesk.ai/tools/kalshi-fee-calculator
    https://evdesk.ai/tools/kalshi-odds-converter
    https://evdesk.ai/tools/kelly-ev-calculator
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction

__all__ = ["Fill", "fill", "fee_per_contract_cents", "breakeven", "kelly", "american_odds"]


def _ceil_div(a, b) -> int:
    """Ceiling of a / b for integers or Fractions."""
    q = Fraction(a) / Fraction(b)
    return -(-q.numerator // q.denominator)


@dataclass(frozen=True)
class Fill:
    contracts: Fraction
    price_cents: Fraction
    cost: Fraction      # dollars, before the fee
    fee: Fraction       # dollars, after grid alignment
    total: Fraction     # dollars, cost + fee

    def __str__(self) -> str:
        return "%s @ %sc: cost $%.4f, fee $%.4f, total $%.4f" % (
            float(self.contracts) if self.contracts.denominator != 1 else self.contracts,
            self.price_cents, self.cost, self.fee, self.total)


def fill(contracts, price_cents, maker: bool = False, multiplier=1, grid_dollars="0.0001") -> Fill:
    """Cost, fee and total for one fill of `contracts` (fractional to 0.01 allowed) at `price_cents`
    (1 to 99, two decimals allowed)."""
    contracts = Fraction(str(contracts))
    if contracts <= 0 or (contracts * 100).denominator != 1:
        raise ValueError("contracts must be positive, in steps of 0.01")
    k = Fraction(str(price_cents)) * 100          # hundredths of a cent
    if k.denominator != 1 or not 100 <= k <= 9900:
        raise ValueError("price must be between 1c and 99c with at most two decimals")
    k = int(k)
    mh = Fraction(str(multiplier)) * 2            # multiplier in halves, as Kalshi's schedule states it
    if mh.denominator != 1 or mh < 0:
        raise ValueError("multiplier must be a non-negative multiple of 0.5")
    mh = int(mh)
    grid = int(Fraction(grid_dollars) * 1_000_000)
    cost = int(contracts * k * 100)               # micro dollars (exact: contracts step 0.01)
    raw = _ceil_div(contracts * 7 * mh * k * (10000 - k), 80000 if maker else 20000) if mh else 0
    total = _ceil_div(cost + raw, grid) * grid
    to_usd = lambda micro: Fraction(micro, 1_000_000)
    return Fill(contracts, Fraction(k, 100), to_usd(cost), to_usd(total - cost), to_usd(total))


def fee_per_contract_cents(price_cents, maker: bool = False, multiplier=1) -> Fraction:
    """The unrounded fee for one contract, in cents (1.75 at 50c taker)."""
    p = Fraction(str(price_cents)) / 100
    rate = Fraction(7, 400) if maker else Fraction(7, 100)
    return rate * Fraction(str(multiplier)) * p * (1 - p) * 100


def breakeven(price_cents, maker: bool = False, multiplier=1) -> Fraction:
    """The win probability (0 to 1) at which buying at `price_cents` breaks even after the fee."""
    return (Fraction(str(price_cents)) + fee_per_contract_cents(price_cents, maker, multiplier)) / 100


def kelly(probability, price_cents, maker: bool = False, multiplier=1, fraction=1) -> Fraction:
    """Share of bankroll Kelly stakes on a $1 contract: (p - k) / (1 - k), k = all-in cost; 0 if no edge."""
    p = Fraction(str(probability))
    k = breakeven(price_cents, maker, multiplier)
    return max(Fraction(0), (p - k) / (1 - k)) * Fraction(str(fraction))


def american_odds(price_cents) -> Fraction:
    """A Kalshi price as American odds: 40c is +150, 75c is -300."""
    p = Fraction(str(price_cents))
    return (100 - p) / p * 100 if p < 50 else -(p / (100 - p)) * 100


if __name__ == "__main__":
    for n, c, m in ((100, 50, False), (100, 50, True), (500, 85, False)):
        print(fill(n, c, maker=m), "(maker)" if m else "(taker)")
    print("break-even at 40c: %.2f%%" % (breakeven(40) * 100))
    print("full Kelly at 62%% and 55c: %.2f%%" % (kelly("0.62", 55) * 100))
