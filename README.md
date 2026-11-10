# kalshi-fees

Kalshi's trading fee, the break-even chance after the fee, and Kelly sizing, in exact integer arithmetic. One small file, no dependencies, MIT licensed. Also: Polymarket US taker fees by volume tier, for comparing the same order on both.

```python
from kalshi_fees import fill, breakeven, kelly

fill(100, 50)                  # 100 @ 50c: cost $50.0000, fee $1.7500, total $51.7500 (taker)
fill(100, 50, maker=True)      # fee $0.4375: a resting limit order pays a quarter
fill("388.19", 76)             # fee $4.9565: fractional contracts are supported
breakeven(40)                  # 0.4168: a 40c contract needs better than 41.68% after the taker fee
kelly("0.62", 55)              # 0.1217: full Kelly at 62% with a 55c ask, fee included
```

## The formula

Kalshi's general schedule, per fill of `n` contracts at price `P` in dollars:

| Route | Fee |
|---|---|
| Taker (you take a resting order) | `ceil(0.07 * n * P * (1 - P))` |
| Maker (your resting order is taken), only on series with maker fees | `ceil(0.0175 * n * P * (1 - P))` |

The fee is largest at 50c (1.75c a contract to take) and shrinks toward the edges (0.63c at 10c or 90c). Maker fees apply only on series whose `fee_type` is `quadratic_with_maker_fees` (about 160 of roughly 16,000 series in November 2026, mostly major sports games such as NFL, NBA and college football games); on other series a resting order pays no fee. Some markets use a different multiplier; pass `multiplier=`. Amounts are kept in micro dollars, the fee rounds up once per fill (not per contract), and cost plus fee aligns up to the account grid (`grid_dollars="0.0001"` by default, or `"0.01"`). Fractional contracts in steps of 0.01 are supported. Checked against a real fill: 388.19 contracts at 76c had a recorded `fee_cost` of $4.9564; the raw fee is $4.95640992 and this package returns $4.9565 on the $0.0001 grid. Rounding to the whole cent gives $4.96, and rounding per contract gives $7.76.

This follows Kalshi's documented [fee rounding](https://docs.kalshi.com/getting_started/fee_rounding): the trade fee is rounded up to $0.000001, then the balance change is aligned to $0.0001 for direct members or $0.01 for members clearing through a broker (`grid_dollars="0.01"`). Across the fills of one order, Kalshi's fee accumulator rebates rounding overpayment, so an order's total converges to what a single equivalent fill costs; `fill()` models that single fill.

Selling before settlement pays the fee again on the way out, and the formula is symmetric: 40c in and 60c out cost $1.68 each on 100 contracts.

## Which markets charge a maker fee

`fee_types.py` reads Kalshi's public series endpoint and lists every series that charges resting orders:

```sh
python3 fee_types.py                  # counts by category
python3 fee_types.py --csv out.csv    # the full list
```

On November 9, 2026: 163 of 15,967 series charged a maker fee. 107 were sports (mostly NFL, NBA, NHL, college football and Champions League game markets), 21 science and technology (mostly GPU rental prices), 13 financials, 10 economics (including CPI and the Fed funds rate), 7 entertainment, 3 exotics and 2 crypto. None of the 4,901 politics and elections series did. The full list is in [`data/maker-fee-series-2026-11-09.csv`](data/maker-fee-series-2026-11-09.csv).

## Kalshi against Polymarket US

Polymarket US uses the same curve with its own rate. Since November 6, 2026 that rate depends on your taker volume over the last 30 days: 0.095 below $10,000, 0.085 below $50,000, 0.075 below $250,000 and 0.0695 from $250,000 up. Kalshi's general rate is 0.07 at any volume. `polymarket_us.py` has the tiers and the fee, rounded the way Polymarket's schedule says (nearest cent, halves to even):

```python
from polymarket_us import rate, taker_fee, compare

rate(4000)                     # Decimal('0.095')
taker_fee(1000, 50, 4000)      # Decimal('23.75'); the same order on Kalshi is $17.50
compare(18000, 50, 9000)       # $9,000 of volume at 50c: Kalshi 315.00, Polymarket US 427.50
```

A new account pays 0.0695 for its first seven days, then until day 30 its tier uses the higher of its first week scaled by 30/7 and its trailing volume. `account_rate(day, trailing_volume, first_week_volume)` returns the rate for that day:

```python
from polymarket_us import account_rate

account_rate(3)                # Decimal('0.0695'), days 1 to 7
account_rate(8, 2400, 2400)    # Decimal('0.085'): $2,400 x 30/7 is $10,285.71
account_rate(31, 2400, 2400)   # Decimal('0.095')
```

Combos use their own curve, and it changes at 1:00 PM ET on November 11, 2026. Until then every account pays contracts x P x [0.0695 x (1 - P) + 0.085 x (1 - P)^4]. From then it is contracts x P x [your tier's rate x (1 - P) + 0.06 x (1 - P)^4]. `combo_fee` does both:

```python
from polymarket_us import combo_fee

combo_fee(1000, 25, tiered=False)   # Decimal('19.75'), every account until the change
combo_fee(1000, 25)                 # Decimal('22.56'), below $10,000 of 30 day volume
combo_fee(1000, 25, 250000)         # Decimal('17.78'), $250,000 or more
```

Taker fee on 1,000 combo contracts:

| Combo price | Until Nov 11 | Below $10,000 | $10,000 to $50,000 | $50,000 to $250,000 | $250,000 or more |
|---:|---:|---:|---:|---:|---:|
| 5c | $6.76 | $6.96 | $6.48 | $6.01 | $5.74 |
| 10c | $11.83 | $12.49 | $11.59 | $10.69 | $10.19 |
| 15c | $15.52 | $16.81 | $15.54 | $14.26 | $13.56 |
| 25c | $19.75 | $22.56 | $20.68 | $18.81 | $17.78 |
| 50c | $20.03 | $25.62 | $23.12 | $20.62 | $19.25 |

Taker fee on 1,000 contracts (`python3 polymarket_us.py` prints this):

| Price | Kalshi | Polymarket US, below $10,000 | $10,000 to $50,000 | $50,000 to $250,000 | $250,000 or more |
|---|---|---|---|---|---|
| 10c or 90c | $6.30 | $8.55 | $7.65 | $6.75 | $6.26 |
| 30c or 70c | $14.70 | $19.95 | $17.85 | $15.75 | $14.60 |
| 50c | $17.50 | $23.75 | $21.25 | $18.75 | $17.38 |

Resting orders run the other way on some markets: Polymarket US charges them nothing, and Kalshi charges them on the series listed above. New Polymarket US accounts pay 0.0695 for their first seven days, and combos use a separate curve (`combo_fee`). Source: [Polymarket US fee schedule](https://docs.polymarket.us/fees), read November 9, 2026. On the same day Polymarket's public market API (`gateway.polymarket.us/v1/markets`) listed `feeCoefficient` 0.095, the Tier 1 rate, on all 3,000 open markets checked. The full Polymarket US schedule written out (tiers, how volume is counted, the new account window, rebates, combos): [Polymarket US fees](https://evdesk.ai/learn/polymarket-us-fees). The comparison written out, with a worked example: [Kalshi vs Polymarket US fees](https://evdesk.ai/learn/kalshi-vs-polymarket-fees).

## MCP server

`mcp_server.py` puts the same functions in front of an AI assistant over the Model Context Protocol (stdio, no dependencies, Python 3.8+). Ask it what 2,500 contracts at 37c cost to take, which side of a market charges a resting order, or how much a quarter Kelly stake is at your own probability, and it answers from the arithmetic above rather than from memory.

```sh
git clone https://github.com/Div770770/kalshi-fees
claude mcp add kalshi-fees -- python3 /path/to/kalshi-fees/mcp_server.py
```

For Claude Desktop or any other MCP client, add it to the client's config:

```json
{"mcpServers": {"kalshi-fees": {"command": "python3", "args": ["/path/to/kalshi-fees/mcp_server.py"]}}}
```

| Tool | What it returns |
|---|---|
| `kalshi_fee` | cost, fee and total for one fill, taker or maker, direct ($0.0001) or broker ($0.01) grid |
| `kalshi_breakeven` | the win probability needed after the fee, and the price as American odds before and after the fee |
| `kalshi_kelly` | the Kelly stake as a share of bankroll for your probability, fee included, any Kelly fraction |
| `kalshi_series_fee_type` | whether a series charges resting orders, and its fee multiplier, read live from Kalshi's public API |
| `polymarket_us_fee` | the Polymarket US taker fee at your 30 day volume tier, next to Kalshi's fee on the same order |
| `polymarket_us_combo_fee` | the Polymarket US combo taker fee before and after the November 11, 2026 change |

With Docker instead: `docker build -t kalshi-fees .` then `docker run -i --rm kalshi-fees` as the command.

Only `kalshi_series_fee_type` uses the network, and it reads one public endpoint without a key. Nothing places orders or touches an account.

## Calculators in the browser

The same math, free, no sign-up:

- [Kalshi fee calculator](https://evdesk.ai/tools/kalshi-fee-calculator): taker and maker fee, total cost and break-even for any price and size
- [Kalshi odds converter](https://evdesk.ai/tools/kalshi-odds-converter): cents to American, decimal and fractional odds, with the after-fee break-even
- [Kelly and EV calculator](https://evdesk.ai/tools/kelly-ev-calculator): expected value and Kelly stake with the fee included
- [Kalshi vs Polymarket US fee calculator](https://evdesk.ai/tools/kalshi-vs-polymarket-fee-calculator): the taker fee on the same order at both exchanges, by Polymarket US volume tier
- [Polymarket US combo fee calculator](https://evdesk.ai/tools/polymarket-us-combo-fee-calculator): the combo taker fee before and after the November 11, 2026 change, by tier

## Tests

```sh
python -m pytest -q
```

Always check Kalshi's current fee schedule before trading; this package mirrors the general schedule and does not fetch market-specific rates.
