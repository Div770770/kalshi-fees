"""MCP server for Kalshi and Polymarket US trading fees, over stdio, no dependencies.

    python3 mcp_server.py

Claude Code:     claude mcp add kalshi-fees -- python3 /path/to/kalshi-fees/mcp_server.py
Claude Desktop:  {"mcpServers": {"kalshi-fees": {"command": "python3", "args": ["/path/to/kalshi-fees/mcp_server.py"]}}}

Every tool is plain arithmetic from kalshi_fees.py and polymarket_us.py, except
kalshi_series_fee_type, which reads one series from Kalshi's public API (no key).
"""
from __future__ import annotations
import json, sys, urllib.parse, urllib.request
from decimal import Decimal
from fractions import Fraction

from kalshi_fees import fill, breakeven, kelly, american_odds, fee_per_contract_cents
import polymarket_us

SERVER = {"name": "kalshi-fees", "version": "0.1.0"}
PROTOCOL = "2025-06-18"
SERIES_API = "https://api.elections.kalshi.com/trade-api/v2/series/"

PRICE = {"type": "number", "description": "Price per contract in cents, 1 to 99 (two decimals allowed)"}
CONTRACTS = {"type": "number", "description": "Number of contracts (Kalshi allows steps of 0.01)"}
MAKER = {"type": "boolean", "description": "True if your resting order is taken (maker). Kalshi charges makers only on series whose fee_type has maker fees; check with kalshi_series_fee_type", "default": False}
MULT = {"type": "number", "description": "The series fee multiplier (1 on most series; kalshi_series_fee_type reads it)", "default": 1}
VOLUME = {"type": "number", "description": "Your Polymarket US taker volume over the last 30 days, in dollars", "default": 0}

TOOLS = [
    {"name": "kalshi_fee",
     "description": "Kalshi trading fee for one fill: cost, fee and total in dollars, using Kalshi's general schedule (taker 0.07, maker 0.0175, times contracts x P x (1 - P)) and its documented rounding.",
     "inputSchema": {"type": "object", "required": ["contracts", "price_cents"], "properties": {
         "contracts": CONTRACTS, "price_cents": PRICE, "maker": MAKER, "multiplier": MULT,
         "grid": {"type": "string", "enum": ["0.0001", "0.01"], "default": "0.0001",
                  "description": "Balance grid: 0.0001 for direct members, 0.01 through a broker (FCM)"}}}},
    {"name": "kalshi_breakeven",
     "description": "The win probability a Kalshi contract needs to break even after the fee, and the price as American odds before and after the fee.",
     "inputSchema": {"type": "object", "required": ["price_cents"], "properties": {
         "price_cents": PRICE, "maker": MAKER, "multiplier": MULT}}},
    {"name": "kalshi_kelly",
     "description": "Kelly stake as a share of bankroll for buying a Kalshi contract at a price, given your own probability, with the fee included. Returns 0 when the probability does not clear the break-even.",
     "inputSchema": {"type": "object", "required": ["probability", "price_cents"], "properties": {
         "probability": {"type": "number", "description": "Your probability that the side you buy wins, 0 to 1"},
         "price_cents": PRICE, "maker": MAKER, "multiplier": MULT,
         "fraction": {"type": "number", "description": "Kelly fraction, e.g. 0.25 for quarter Kelly", "default": 1}}}},
    {"name": "kalshi_series_fee_type",
     "description": "Reads one series from Kalshi's public API and says whether resting (maker) orders pay a fee there, and the fee multiplier.",
     "inputSchema": {"type": "object", "required": ["series_ticker"], "properties": {
         "series_ticker": {"type": "string", "description": "Kalshi series ticker, e.g. KXNFLGAME or KXCPI"}}}},
    {"name": "polymarket_us_fee",
     "description": "Polymarket US taker fee for one fill at your 30 day volume tier (0.095, 0.085, 0.075 or 0.0695 since Nov 6, 2026), next to the Kalshi taker fee on the same order.",
     "inputSchema": {"type": "object", "required": ["contracts", "price_cents"], "properties": {
         "contracts": CONTRACTS, "price_cents": PRICE, "volume_30d": VOLUME}}},
    {"name": "polymarket_us_combo_fee",
     "description": "Polymarket US taker fee on a combo fill, under the formula before 1:00 PM ET on Nov 11, 2026 and the tiered formula from then on.",
     "inputSchema": {"type": "object", "required": ["contracts", "price_cents"], "properties": {
         "contracts": CONTRACTS, "price_cents": PRICE, "volume_30d": VOLUME}}},
]


def _usd(x) -> str:
    d = Decimal(x.numerator) / Decimal(x.denominator) if isinstance(x, Fraction) else Decimal(x)
    return "%.4f" % d


def _pct(x: Fraction) -> str:
    return "%.2f%%" % (x * 100)


def _odds(x: Fraction) -> str:
    return "%+.0f" % x


def _num(v) -> str:
    """JSON numbers arrive as floats; go through repr so 0.1 stays 0.1, not its binary expansion."""
    return repr(v) if isinstance(v, float) else str(v)


def kalshi_fee(a):
    f = fill(_num(a["contracts"]), _num(a["price_cents"]), bool(a.get("maker", False)),
             _num(a.get("multiplier", 1)), a.get("grid", "0.0001"))
    return {"route": "maker" if a.get("maker") else "taker", "cost_usd": _usd(f.cost), "fee_usd": _usd(f.fee),
            "total_usd": _usd(f.total), "fee_per_contract_cents": "%.4f" % fee_per_contract_cents(
                _num(a["price_cents"]), bool(a.get("maker", False)), _num(a.get("multiplier", 1)))}


def kalshi_breakeven(a):
    p, m, mult = _num(a["price_cents"]), bool(a.get("maker", False)), _num(a.get("multiplier", 1))
    be = breakeven(p, m, mult)
    return {"breakeven_probability": _pct(be), "american_odds": _odds(american_odds(p)),
            "american_odds_after_fee": _odds(american_odds(be * 100))}


def kalshi_kelly(a):
    k = kelly(_num(a["probability"]), _num(a["price_cents"]), bool(a.get("maker", False)),
              _num(a.get("multiplier", 1)), _num(a.get("fraction", 1)))
    return {"stake_share_of_bankroll": _pct(k),
            "breakeven_probability": _pct(breakeven(_num(a["price_cents"]), bool(a.get("maker", False)), _num(a.get("multiplier", 1))))}


def kalshi_series_fee_type(a):
    t = str(a["series_ticker"]).strip().upper()
    if not t or not t.replace("-", "").isalnum():
        raise ValueError("series_ticker must be letters, digits and hyphens")
    req = urllib.request.Request(SERIES_API + urllib.parse.quote(t), headers={"User-Agent": "kalshi-fees"})
    with urllib.request.urlopen(req, timeout=30) as r:
        s = json.load(r)["series"]
    ft = str(s.get("fee_type", ""))
    return {"series_ticker": s.get("ticker", t), "title": s.get("title"), "category": s.get("category"),
            "fee_type": ft, "fee_multiplier": s.get("fee_multiplier"),
            "makers_pay": ft.startswith("quadratic_with"),
            "maker_rate": "0.035" if "combo_maker" in ft else ("0.0175" if ft.startswith("quadratic_with") else "0")}


def polymarket_us_fee(a):
    c = polymarket_us.compare(_num(a["contracts"]), _num(a["price_cents"]), _num(a.get("volume_30d", 0)))
    return {"polymarket_us_fee_usd": str(c["polymarket_us"]), "polymarket_us_rate": str(c["polymarket_us_rate"]),
            "kalshi_taker_fee_usd": str(c["kalshi"]), "difference_usd": str(c["difference"])}


def polymarket_us_combo_fee(a):
    n, p, v = _num(a["contracts"]), _num(a["price_cents"]), _num(a.get("volume_30d", 0))
    return {"before_nov_11_2026_usd": str(polymarket_us.combo_fee(n, p, v, tiered=False)),
            "from_nov_11_2026_usd": str(polymarket_us.combo_fee(n, p, v, tiered=True)),
            "tier_rate": str(polymarket_us.rate(v))}


HANDLERS = {"kalshi_fee": kalshi_fee, "kalshi_breakeven": kalshi_breakeven, "kalshi_kelly": kalshi_kelly,
            "kalshi_series_fee_type": kalshi_series_fee_type, "polymarket_us_fee": polymarket_us_fee,
            "polymarket_us_combo_fee": polymarket_us_combo_fee}


def handle(msg):
    """One JSON-RPC message in, one response out (None for notifications)."""
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": params.get("protocolVersion") or PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        fn = HANDLERS.get(params.get("name"))
        if fn is None:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool: %s" % params.get("name")}}
        try:
            out = fn(params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": json.dumps(out)}], "structuredContent": out, "isError": False}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": "%s: %s" % (type(e).__name__, e)}], "isError": True}}
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found: %s" % method}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            out = handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
