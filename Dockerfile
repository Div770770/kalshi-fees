# The MCP server over stdio: docker build -t kalshi-fees . && docker run -i --rm kalshi-fees
FROM python:3.12-slim
WORKDIR /app
COPY kalshi_fees.py polymarket_us.py mcp_server.py ./
ENTRYPOINT ["python3", "mcp_server.py"]
