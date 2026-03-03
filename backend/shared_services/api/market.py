"""
Market Data API — hub-level, venture-agnostic.

GET /market/prices?symbols=AAPL,GOOGL,MSFT
    Returns real-time quotes for up to 20 symbols via Finnhub.
    Falls back to Alpha Vantage if Finnhub fails, then returns
    partial results (symbols that succeeded).  Never raises 5xx
    so the ticker widget always has something to display.

Auth: requires valid X-Venture-ID + X-API-Key (any venture).
      No path-scope restriction (no slug in URL).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["market"])

_MAX_SYMBOLS = 20
_TIMEOUT = 4.0  # seconds per Finnhub call


class StockQuote(BaseModel):
    symbol: str
    price: float
    change: float
    changePercent: float
    high: float
    low: float
    volume: int


class MarketPricesResponse(BaseModel):
    quotes: list[StockQuote]
    source: str  # "finnhub" | "alpha_vantage" | "partial" | "unavailable"


async def _fetch_finnhub(client: httpx.AsyncClient, symbol: str) -> StockQuote | None:
    """Fetch a single quote from Finnhub /quote endpoint."""
    try:
        resp = await client.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": settings.finnhub_api_key},
            timeout=_TIMEOUT,
        )
        data = resp.json()
        price = float(data.get("c") or 0)
        if price <= 0:
            return None
        return StockQuote(
            symbol=symbol,
            price=price,
            change=float(data.get("d") or 0),
            changePercent=float(data.get("dp") or 0),
            high=float(data.get("h") or price),
            low=float(data.get("l") or price),
            volume=int(data.get("v") or 0),
        )
    except Exception as exc:
        logger.debug("finnhub %s: %s", symbol, exc)
        return None


async def _fetch_alpha_vantage(client: httpx.AsyncClient, symbol: str) -> StockQuote | None:
    """Fetch a single global quote from Alpha Vantage as fallback."""
    try:
        resp = await client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": settings.alpha_vantage_api_key,
            },
            timeout=_TIMEOUT,
        )
        gq: dict[str, Any] = resp.json().get("Global Quote", {})
        price = float(gq.get("05. price") or 0)
        if price <= 0:
            return None
        change = float(gq.get("09. change") or 0)
        pct = float((gq.get("10. change percent") or "0%").rstrip("%"))
        return StockQuote(
            symbol=symbol,
            price=price,
            change=change,
            changePercent=pct,
            high=float(gq.get("03. high") or price),
            low=float(gq.get("04. low") or price),
            volume=int(gq.get("06. volume") or 0),
        )
    except Exception as exc:
        logger.debug("alpha_vantage %s: %s", symbol, exc)
        return None


@router.get(
    "/prices",
    response_model=MarketPricesResponse,
    summary="Real-time stock quotes",
    description=(
        "Returns real-time OHLCV quotes for up to 20 comma-separated symbols. "
        "Tries Finnhub first, falls back to Alpha Vantage per symbol. "
        "Returns partial results — never blocks on missing symbols."
    ),
)
async def market_prices(
    symbols: str = Query(..., description="Comma-separated ticker symbols, e.g. AAPL,GOOGL,MSFT"),
) -> MarketPricesResponse:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:_MAX_SYMBOLS]

    quotes: list[StockQuote] = []
    sources_used: set[str] = set()

    async with httpx.AsyncClient() as client:
        for symbol in symbol_list:
            quote = None
            if settings.finnhub_api_key:
                quote = await _fetch_finnhub(client, symbol)
                if quote:
                    sources_used.add("finnhub")

            if quote is None and settings.alpha_vantage_api_key:
                quote = await _fetch_alpha_vantage(client, symbol)
                if quote:
                    sources_used.add("alpha_vantage")

            if quote:
                quotes.append(quote)

    if not sources_used:
        source = "unavailable"
    elif len(sources_used) > 1:
        source = "partial"
    else:
        source = next(iter(sources_used))

    return MarketPricesResponse(quotes=quotes, source=source)
