import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def session(*calls):
    """Start the server, run initialize plus the given tools/call messages over stdio, return the replies by id."""
    msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}]
    for i, (name, args) in enumerate(calls, start=2):
        msgs.append({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}})
    out = subprocess.run([sys.executable, os.path.join(HERE, "mcp_server.py")], cwd=HERE, capture_output=True, text=True,
                         input="".join(json.dumps(m) + "\n" for m in msgs), timeout=30).stdout
    return {r["id"]: r for r in map(json.loads, out.splitlines())}


def test_handshake_and_tools():
    r = session()
    assert r[0]["result"]["serverInfo"]["name"] == "kalshi-fees"
    assert r[0]["result"]["protocolVersion"] == "2025-06-18"
    names = [t["name"] for t in r[1]["result"]["tools"]]
    assert names == ["kalshi_fee", "kalshi_breakeven", "kalshi_kelly", "kalshi_series_fee_type",
                     "polymarket_us_fee", "polymarket_us_combo_fee"]
    assert len(r) == 2   # the initialized notification gets no reply


def test_tool_results():
    r = session(("kalshi_fee", {"contracts": 100, "price_cents": 50}),
                ("kalshi_fee", {"contracts": 100, "price_cents": 50, "maker": True}),
                ("kalshi_fee", {"contracts": 388.19, "price_cents": 76}),
                ("kalshi_breakeven", {"price_cents": 40}),
                ("kalshi_kelly", {"probability": 0.62, "price_cents": 55}),
                ("polymarket_us_fee", {"contracts": 1000, "price_cents": 50}),
                ("polymarket_us_combo_fee", {"contracts": 1000, "price_cents": 25, "volume_30d": 250000}))
    s = {i: r[i]["result"]["structuredContent"] for i in range(2, 9)}
    assert s[2] == {"route": "taker", "cost_usd": "50.0000", "fee_usd": "1.7500", "total_usd": "51.7500", "fee_per_contract_cents": "1.7500"}
    assert s[3]["fee_usd"] == "0.4375" and s[3]["route"] == "maker"
    assert s[4]["fee_usd"] == "4.9565"
    assert s[5]["breakeven_probability"] == "41.68%" and s[5]["american_odds"] == "+150"
    assert s[6]["stake_share_of_bankroll"] == "12.17%"
    assert s[7] == {"polymarket_us_fee_usd": "23.75", "polymarket_us_rate": "0.095", "kalshi_taker_fee_usd": "17.5000", "difference_usd": "6.2500"}
    assert s[8] == {"before_nov_11_2026_usd": "19.75", "from_nov_11_2026_usd": "17.78", "tier_rate": "0.0695"}
    assert json.loads(r[2]["result"]["content"][0]["text"]) == s[2]


def test_errors():
    r = session(("kalshi_fee", {"contracts": 10, "price_cents": 100}), ("no_such_tool", {}))
    assert r[2]["result"]["isError"] is True and "price" in r[2]["result"]["content"][0]["text"]
    assert r[3]["error"]["code"] == -32602


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
