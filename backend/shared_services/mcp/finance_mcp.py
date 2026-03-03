"""
Finance MCP — market data with provider fallback.

Implements the Model Context Protocol pattern for financial data: each
capability is expressed both as a callable async function (for direct use
in LangGraph nodes) and as an Anthropic tool definition (so the same
capability can be invoked via LLM tool-use when needed).

Provider fallback hierarchy
----------------------------
Real-time price
  1. Finnhub  /api/v1/quote          (FINNHUB_API_KEY)
  2. Alpha Vantage  GLOBAL_QUOTE     (ALPHA_VANTAGE_API_KEY)
  3. MarketSnapshot.price = None, source = "unavailable"

Historical OHLCV
  1. Alpha Vantage  TIME_SERIES_DAILY (ALPHA_VANTAGE_API_KEY)
  2. Returns empty list on failure

News headlines (always attempted, independent of price fallback)
  1. NewsAPI /v2/everything           (NEWSAPI_KEY)
  2. Returns empty list on failure

News sentiment
  Classifies each headline as bullish / bearish / neutral using keyword
  matching and aggregates into a consolidated string for LLM injection.

Usage
-----
    import httpx
    from mcp.finance_mcp import get_market_context, get_news_sentiment

    async with httpx.AsyncClient(timeout=8.0) as http:
        snap = await get_market_context("AAPL", http=http)
        print(snap.price, snap.source, snap.headlines[:3])

        sentiment = await get_news_sentiment("AAPL", http=http)
        print(sentiment.mood, sentiment.consolidated)
"""

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# ── Provider base URLs ───────────────────────────────────────────────────────
_FINNHUB_BASE = "https://finnhub.io/api/v1"
_AV_BASE = "https://www.alphavantage.co/query"
_NEWSAPI_BASE = "https://newsapi.org/v2/everything"


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class OHLCVBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class MarketSnapshot:
    symbol: str
    price: float | None
    source: str                       # "finnhub" | "alpha_vantage" | "unavailable"
    change_pct: float | None          # % change vs previous close
    historicals: list[OHLCVBar] = field(default_factory=list)  # last 30 daily bars
    headlines: list[str] = field(default_factory=list)         # last 10 headlines


# ── Private fetch functions ───────────────────────────────────────────────────

async def _finnhub_quote(symbol: str, http: httpx.AsyncClient) -> dict | None:
    """Return raw Finnhub /quote JSON or None on any failure."""
    key = settings.finnhub_api_key
    if not key:
        return None
    try:
        r = await http.get(
            f"{_FINNHUB_BASE}/quote",
            params={"symbol": symbol, "token": key},
        )
        r.raise_for_status()
        data = r.json()
        # Finnhub returns {"c": 0, ...} with c==0 when symbol not found
        if data.get("c", 0) == 0:
            return None
        return data
    except Exception as exc:
        logger.warning("finnhub_quote %s failed: %s", symbol, exc)
        return None


async def _av_global_quote(symbol: str, http: httpx.AsyncClient) -> dict | None:
    """Return raw Alpha Vantage GLOBAL_QUOTE dict or None on any failure."""
    key = settings.alpha_vantage_api_key
    if not key:
        return None
    try:
        r = await http.get(
            _AV_BASE,
            params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": key},
        )
        r.raise_for_status()
        data = r.json()
        gq = data.get("Global Quote", {})
        return gq if gq.get("05. price") else None
    except Exception as exc:
        logger.warning("av_global_quote %s failed: %s", symbol, exc)
        return None


async def _av_daily_history(symbol: str, http: httpx.AsyncClient) -> list[OHLCVBar]:
    """Return up to 30 recent daily OHLCV bars from Alpha Vantage."""
    key = settings.alpha_vantage_api_key
    if not key:
        return []
    try:
        r = await http.get(
            _AV_BASE,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": key,
            },
        )
        r.raise_for_status()
        ts = r.json().get("Time Series (Daily)", {})
        bars: list[OHLCVBar] = []
        for date, vals in sorted(ts.items(), reverse=True)[:30]:
            bars.append(
                OHLCVBar(
                    date=date,
                    open=float(vals["1. open"]),
                    high=float(vals["2. high"]),
                    low=float(vals["3. low"]),
                    close=float(vals["4. close"]),
                    volume=int(vals["5. volume"]),
                )
            )
        return bars
    except Exception as exc:
        logger.warning("av_daily_history %s failed: %s", symbol, exc)
        return []


async def _newsapi_headlines(symbol: str, http: httpx.AsyncClient) -> list[str]:
    """Return up to 10 recent headline strings for *symbol* from NewsAPI."""
    key = settings.newsapi_key
    if not key:
        return []
    try:
        r = await http.get(
            _NEWSAPI_BASE,
            params={
                "q": symbol,
                "pageSize": 10,
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": key,
            },
        )
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [a["title"] for a in articles if a.get("title")]
    except Exception as exc:
        logger.warning("newsapi_headlines %s failed: %s", symbol, exc)
        return []


# ── Fallback price resolution ─────────────────────────────────────────────────

async def _resolve_price(
    symbol: str,
    http: httpx.AsyncClient,
) -> tuple[float | None, float | None, str]:
    """
    Try Finnhub → Alpha Vantage for current price.

    Returns (price, change_pct, source_name).
    """
    # Gate 1 — Finnhub real-time
    fh = await _finnhub_quote(symbol, http)
    if fh is not None:
        price = float(fh["c"])
        prev = float(fh.get("pc", 0))
        change_pct = ((price - prev) / prev * 100) if prev else None
        logger.debug("price %s via finnhub: %.4f", symbol, price)
        return price, change_pct, "finnhub"

    # Gate 2 — Alpha Vantage fallback
    av = await _av_global_quote(symbol, http)
    if av is not None:
        price = float(av["05. price"])
        change_pct_raw = av.get("10. change percent", "0%").replace("%", "")
        try:
            change_pct = float(change_pct_raw)
        except ValueError:
            change_pct = None
        logger.debug("price %s via alpha_vantage: %.4f", symbol, price)
        return price, change_pct, "alpha_vantage"

    logger.warning("price unavailable for %s — both providers failed", symbol)
    return None, None, "unavailable"


# ── Public API ────────────────────────────────────────────────────────────────

async def get_market_context(
    symbol: str,
    *,
    http: httpx.AsyncClient,
    fetch_history: bool = True,
) -> MarketSnapshot:
    """
    Fetch a complete market snapshot for *symbol* with provider fallback.

    Price:       Finnhub  →  Alpha Vantage  →  None
    Historicals: Alpha Vantage TIME_SERIES_DAILY (30 bars)
    Headlines:   NewsAPI /v2/everything (10 articles)

    All three data streams are fetched concurrently.  Individual failures
    are swallowed and logged — the caller always receives a MarketSnapshot,
    possibly with None price or empty lists.

    Parameters
    ----------
    symbol:
        Ticker symbol (e.g. "AAPL", "BTC").  Crypto pairs may not be
        supported by all providers.
    http:
        A shared httpx.AsyncClient (connection-pool reuse).
    fetch_history:
        Set False to skip the historical bars call (saves one API credit).
    """
    sym = symbol.upper().strip()

    price_task = asyncio.create_task(_resolve_price(sym, http))
    news_task = asyncio.create_task(_newsapi_headlines(sym, http))
    hist_task = (
        asyncio.create_task(_av_daily_history(sym, http))
        if fetch_history
        else asyncio.create_task(asyncio.coroutine(lambda: [])())
    )

    (price, change_pct, source), headlines, historicals = await asyncio.gather(
        price_task, news_task, hist_task
    )

    return MarketSnapshot(
        symbol=sym,
        price=price,
        source=source,
        change_pct=change_pct,
        historicals=historicals,
        headlines=headlines,
    )


async def get_market_context_batch(
    symbols: list[str],
    *,
    http: httpx.AsyncClient,
    fetch_history: bool = False,
) -> dict[str, MarketSnapshot]:
    """
    Fetch market snapshots for multiple symbols concurrently.

    Returns a dict keyed by uppercased symbol.  Symbols that fail are
    still present in the dict with price=None.
    """
    tasks = {
        sym.upper(): asyncio.create_task(
            get_market_context(sym, http=http, fetch_history=fetch_history)
        )
        for sym in symbols
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    out: dict[str, MarketSnapshot] = {}
    for sym, res in zip(tasks.keys(), results):
        if isinstance(res, Exception):
            logger.error("get_market_context_batch %s error: %s", sym, res)
            out[sym] = MarketSnapshot(symbol=sym, price=None, source="error", change_pct=None)
        else:
            out[sym] = res
    return out


# ── NewsSentiment ─────────────────────────────────────────────────────────────

_BULLISH_KEYWORDS: frozenset[str] = frozenset(
    {
        "surge", "rally", "beat", "record", "breakout", "upgrade", "profit",
        "growth", "soar", "gain", "bull", "upside", "outperform", "boom",
        "strong", "rise", "jump", "high", "positive", "optimistic",
    }
)
_BEARISH_KEYWORDS: frozenset[str] = frozenset(
    {
        "crash", "plunge", "miss", "loss", "downgrade", "bearish", "sell",
        "decline", "drop", "fall", "weak", "concern", "risk", "warn",
        "cut", "layoff", "deficit", "debt", "negative", "pessimistic",
    }
)


@dataclass
class NewsSentiment:
    symbol: str
    headline_count: int              # number of headlines analysed (≤ 5)
    headlines: list[str]             # raw headline strings
    bullish_count: int
    bearish_count: int
    neutral_count: int
    mood: str                        # "bullish" | "bearish" | "neutral"
    consolidated: str                # single paragraph ready for LLM injection


def _classify_headline(text: str) -> str:
    """Return 'bullish', 'bearish', or 'neutral' based on keyword overlap."""
    lowered = set(text.lower().split())
    b = len(lowered & _BULLISH_KEYWORDS)
    be = len(lowered & _BEARISH_KEYWORDS)
    if b > be:
        return "bullish"
    if be > b:
        return "bearish"
    return "neutral"


async def get_news_sentiment(
    symbol: str,
    *,
    http: httpx.AsyncClient,
) -> NewsSentiment:
    """
    Fetch the latest 5 headlines for *symbol* and classify each as
    bullish / bearish / neutral.  Returns a ``NewsSentiment`` with a
    ``consolidated`` string suitable for injecting into an LLM prompt.

    Falls back gracefully to an empty/neutral result when NewsAPI is
    unavailable or the key is not configured.
    """
    sym = symbol.upper().strip()
    raw_headlines = await _newsapi_headlines(sym, http)
    headlines = raw_headlines[:5]

    bullish = bearish = neutral = 0
    classified: list[tuple[str, str]] = []
    for h in headlines:
        label = _classify_headline(h)
        classified.append((h, label))
        if label == "bullish":
            bullish += 1
        elif label == "bearish":
            bearish += 1
        else:
            neutral += 1

    if bullish > bearish:
        mood = "bullish"
    elif bearish > bullish:
        mood = "bearish"
    else:
        mood = "neutral"

    if classified:
        lines = "\n".join(f"  [{label.upper()}] {h}" for h, label in classified)
        consolidated = (
            f"Recent {sym} news sentiment is {mood.upper()} "
            f"({bullish} bullish, {bearish} bearish, {neutral} neutral).\n"
            f"Headlines:\n{lines}"
        )
    else:
        consolidated = f"No recent news available for {sym}."

    logger.debug(
        "news_sentiment %s: mood=%s (%db/%dbe/%dn)",
        sym, mood, bullish, bearish, neutral,
    )
    return NewsSentiment(
        symbol=sym,
        headline_count=len(headlines),
        headlines=headlines,
        bullish_count=bullish,
        bearish_count=bearish,
        neutral_count=neutral,
        mood=mood,
        consolidated=consolidated,
    )


# ── Anthropic tool definition (for LLM tool-use invocation) ─────────────────

MARKET_DATA_TOOL: dict = {
    "name": "get_market_data",
    "description": (
        "Fetch real-time price (Finnhub → Alpha Vantage fallback), "
        "30-day daily OHLCV history, and the last 10 news headlines "
        "for a given ticker symbol."
    ),
    "input_schema": {
        "type": "object",
        "required": ["symbol"],
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Ticker symbol, e.g. 'AAPL', 'MSFT', 'BTC'.",
            },
            "fetch_history": {
                "type": "boolean",
                "description": "Include 30-day daily OHLCV bars. Default true.",
                "default": True,
            },
        },
    },
}

NEWS_SENTIMENT_TOOL: dict = {
    "name": "get_news_sentiment",
    "description": (
        "Fetch the latest 5 news headlines for a ticker and return a "
        "consolidated sentiment summary (bullish / bearish / neutral) "
        "ready for LLM injection.  Uses NewsAPI with keyword classification."
    ),
    "input_schema": {
        "type": "object",
        "required": ["symbol"],
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Ticker symbol, e.g. 'AAPL', 'MSFT', 'BTC'.",
            },
        },
    },
}
