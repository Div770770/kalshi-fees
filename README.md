# kalshi-fees

Kalshi's trading fee, the break-even chance after the fee, and Kelly sizing, in exact integer arithmetic. One small file, no dependencies, MIT licensed.

```python
from kalshi_fees import fill, breakeven, kelly

fill(100, 50)                  # 100 @ 50c: cost $50.0000, fee $1.7500, total $51.7500 (taker)
fill(100, 50, maker=True)      # fee $0.4375: a resting limit order pays a quarter
fill("388.19", 76)             # fee $4.9564: fractional contracts, matching Kalshi's recorded fee_cost
breakeven(40)                  # 0.4168: a 40c contract needs better than 41.68% after the taker fee
kelly("0.62", 55)              # 0.1217: full Kelly at 62% with a 55c ask, fee included
```

## The formula

Kalshi's general schedule, per fill of `n` contracts at price `P` in dollars:

| Route | Fee |
|---|---|
| Taker (you take a resting order) | `ceil(0.07 * n * P * (1 - P))` |
| Maker (your resting order is taken) | `ceil(0.0175 * n * P * (1 - P))` |

The fee is largest at 50c (1.75c a contract to take) and shrinks toward the edges (0.63c at 10c or 90c). Some markets use a different multiplier; pass `multiplier=`. Amounts are kept in micro dollars, the fee rounds up once per fill (not per contract), and cost plus fee aligns up to the account grid (`grid_dollars="0.0001"` by default, or `"0.01"`). Fractional contracts in steps of 0.01 are supported. Checked against a real fill: 388.19 contracts at 76c, recorded `fee_cost` $4.9564, and this package returns $4.9564; rounding to the whole cent would give $4.96 and rounding per contract $7.76.

Selling before settlement pays the fee again on the way out, and the formula is symmetric: 40c in and 60c out cost $1.68 each on 100 contracts.

## Calculators in the browser

The same math, free, no sign-up:

- [Kalshi fee calculator](https://evdesk.ai/tools/kalshi-fee-calculator): taker and maker fee, total cost and break-even for any price and size
- [Kalshi odds converter](https://evdesk.ai/tools/kalshi-odds-converter): cents to American, decimal and fractional odds, with the after-fee break-even
- [Kelly and EV calculator](https://evdesk.ai/tools/kelly-ev-calculator): expected value and Kelly stake with the fee included

## Tests

```sh
python -m pytest -q
```

Always check Kalshi's current fee schedule before trading; this package mirrors the general schedule and does not fetch market-specific rates.
