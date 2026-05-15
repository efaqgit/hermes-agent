from __future__ import annotations

import logging
from plugins.finance.tools import (
    calculate_dcf,
    company_health_check,
    get_insider_trades,
    get_sec_filings,
    get_earnings_estimates,
    get_financial_news,
    x_search,
    check_x_bearer_token,
    generate_tech_chart,
)
from plugins.finance.interactive_chart import view_tech_chart

logger = logging.getLogger(__name__)

# Define schemas here so they are isolated from core code
DCF_VALUATION_SCHEMA = {
    "name": "dcf_valuation",
    "description": (
        "Performs a Discounted Cash Flow (DCF) valuation for a given stock ticker.\n"
        "Automatically fetches financial data, calculates FCF growth, estimates WACC,\n"
        "and projects future cash flows to determine the intrinsic fair value per share.\n"
        "Use this tool when the user asks for a company's valuation, intrinsic value,\n"
        "price target, or DCF analysis."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol (e.g., AAPL, MSFT, TSLA)."
            },
            "wacc": {
                "type": "number",
                "description": "Optional custom Weighted Average Cost of Capital (e.g., 0.085 for 8.5%). If omitted, a sector-based default is used."
            },
            "terminal_growth_rate": {
                "type": "number",
                "description": "Optional custom Terminal Growth Rate (default is 0.025 for 2.5%).",
                "default": 0.025
            },
            "fcf_growth_rate": {
                "type": "number",
                "description": "Optional custom Free Cash Flow growth rate for the next 5 years (e.g., 0.10 for 10%). If omitted, historical CAGR is used."
            }
        },
        "required": ["ticker"]
    }
}

COMPANY_HEALTH_CHECK_SCHEMA = {
    "name": "company_health_check",
    "description": (
        "Retrieves deep financial metrics and ratios for fundamental analysis.\n"
        "Provides Valuation (P/E, P/B, PEG), Profitability (ROE, ROA, Margins),\n"
        "Liquidity (Current Ratio), and Growth metrics."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol."
            }
        },
        "required": ["ticker"]
    }
}

INSIDER_TRADES_SCHEMA = {
    "name": "get_insider_trades",
    "description": (
        "Fetches recent buying and selling activity by company insiders (executives, directors).\n"
        "Returns the top 10 most recent transactions including the person, position, type (buy/sell), and value."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol."
            }
        },
        "required": ["ticker"]
    }
}

SEC_FILINGS_SCHEMA = {
    "name": "get_sec_filings",
    "description": (
        "Queries the official SEC EDGAR database to get the latest regulatory filings (10-K, 10-Q, 8-K).\n"
        "Returns direct URLs to the HTML documents. You can use the browser tool to read these URLs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol."
            },
            "form_type": {
                "type": "string",
                "description": "The form type to retrieve, typically '10-K' for annual reports, '10-Q' for quarterly, or '8-K' for current events.",
                "default": "10-K"
            }
        },
        "required": ["ticker"]
    }
}

EARNINGS_ESTIMATES_SCHEMA = {
    "name": "get_earnings_estimates",
    "description": (
        "Retrieves Wall Street consensus earnings estimates (EPS and Revenue), next expected "
        "earnings date, and recent analyst revisions for a given stock."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol."
            }
        },
        "required": ["ticker"]
    }
}

FINANCIAL_NEWS_SCHEMA = {
    "name": "get_financial_news",
    "description": (
        "Fetches the top 10 latest financial news headlines and links for a specific company."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol."
            }
        },
        "required": ["ticker"]
    }
}

X_SEARCH_SCHEMA = {
    "name": "x_search",
    "description": (
        "Search X/Twitter for real-time public sentiment, market opinions, breaking news, "
        "and expert takes. Uses the official X API v2 (read-only, last 7 days).\n"
        "Commands:\n"
        "- search: Search recent tweets. Supports X operators like from:, -is:reply, OR, $TICKER.\n"
        "- profile: Get recent tweets from a specific user (excludes retweets/replies).\n"
        "- thread: Fetch a full conversation thread by root tweet ID."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["search", "profile", "thread"],
                "description": "The command to execute."
            },
            "query": {
                "type": "string",
                "description": "For search: the search query (supports X operators). For thread: the root tweet ID."
            },
            "username": {
                "type": "string",
                "description": "For profile: the X/Twitter username (without @)."
            },
            "sort": {
                "type": "string",
                "enum": ["likes", "impressions", "retweets", "recent"],
                "description": "Sort order for results (default: likes).",
                "default": "likes"
            },
            "since": {
                "type": "string",
                "description": "Time filter: '1h', '3h', '12h', '1d', '7d' or ISO 8601 timestamp."
            },
            "min_likes": {
                "type": "integer",
                "description": "Filter results to tweets with at least this many likes.",
                "default": 0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 15).",
                "default": 15
            },
            "pages": {
                "type": "integer",
                "description": "Number of pages to fetch (1 page ≈ 100 tweets, default: 1).",
                "default": 1
            }
        },
        "required": ["command"]
    }
}

TECH_CHART_SCHEMA = {
    "name": "generate_tech_chart",
    "description": (
        "Generate a professional candlestick (K-line) chart with technical indicators for a stock.\n"
        "Produces a PNG image with: K-line candles, MA20/MA81 moving averages, Bollinger Bands, "
        "MACD histogram, RSI oscillator, and Volume bars.\n"
        "Data source: Moomoo API (primary), Yahoo Finance (fallback).\n"
        "Use this when the user asks to see a chart, K-line, technical analysis picture, or 技術線圖."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker, e.g. 'TSLA', 'AAPL', or Moomoo format 'US.TSLA', 'HK.00700'."
            },
            "period": {
                "type": "string",
                "enum": ["3mo", "6mo", "1y", "2y", "5y"],
                "description": "Data period. Default '1y'."
            },
            "interval": {
                "type": "string",
                "enum": ["1d", "1wk", "1mo"],
                "description": "Candle interval. Default '1d' (daily)."
            },
            "indicators": {
                "type": "string",
                "description": "Comma-separated indicators to show: ma, macd, rsi, bb, vol. Default 'ma,macd,rsi,bb,vol' (all)."
            },
            "style": {
                "type": "string",
                "enum": ["dark", "classic", "nightclouds", "yahoo"],
                "description": "Chart color theme. Default 'dark'."
            }
        },
        "required": ["ticker"]
    }
}

_TOOLS = (
    (
        "dcf_valuation",
        DCF_VALUATION_SCHEMA,
        lambda args, **kw: calculate_dcf(
            ticker=args.get("ticker"),
            wacc=args.get("wacc"),
            terminal_growth_rate=args.get("terminal_growth_rate", 0.025),
            fcf_growth_rate=args.get("fcf_growth_rate")
        )
    ),
    (
        "company_health_check",
        COMPANY_HEALTH_CHECK_SCHEMA,
        lambda args, **kw: company_health_check(
            ticker=args.get("ticker")
        )
    ),
    (
        "get_insider_trades",
        INSIDER_TRADES_SCHEMA,
        lambda args, **kw: get_insider_trades(
            ticker=args.get("ticker")
        )
    ),
    (
        "get_sec_filings",
        SEC_FILINGS_SCHEMA,
        lambda args, **kw: get_sec_filings(
            ticker=args.get("ticker"),
            form_type=args.get("form_type", "10-K")
        )
    ),
    (
        "get_earnings_estimates",
        EARNINGS_ESTIMATES_SCHEMA,
        lambda args, **kw: get_earnings_estimates(
            ticker=args.get("ticker")
        )
    ),
    (
        "get_financial_news",
        FINANCIAL_NEWS_SCHEMA,
        lambda args, **kw: get_financial_news(
            ticker=args.get("ticker")
        )
    ),
    (
        "x_search",
        X_SEARCH_SCHEMA,
        lambda args, **kw: x_search(
            command=args.get("command"),
            query=args.get("query"),
            username=args.get("username"),
            sort=args.get("sort", "likes"),
            since=args.get("since"),
            min_likes=args.get("min_likes", 0),
            limit=args.get("limit", 15),
            pages=args.get("pages", 1)
        )
    ),
    (
        "generate_tech_chart",
        TECH_CHART_SCHEMA,
        lambda args, **kw: generate_tech_chart(
            ticker=args.get("ticker"),
            period=args.get("period", "1y"),
            interval=args.get("interval", "1d"),
            indicators=args.get("indicators", "ma,macd,rsi,bb,vol"),
            style=args.get("style", "dark"),
        )
    ),
    (
        "view_tech_chart",
        {
            "name": "view_tech_chart",
            "description": (
                "Open an INTERACTIVE technical chart in the user's browser using TradingView engine.\n"
                "Supports zoom (scroll), pan (drag), and crosshair price tracking.\n"
                "Shows: K-line candles, MA20/MA81, Bollinger Bands, Volume, MACD, RSI — all synced.\n"
                "Use this when the user says 'view chart', 'open chart', '看線圖', or wants an interactive experience."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker, e.g. 'TSLA', 'AAPL', or 'US.TSLA', 'HK.00700'."
                    },
                    "period": {
                        "type": "string",
                        "enum": ["3mo", "6mo", "1y", "2y", "5y"],
                        "description": "Data period. Default '1y'."
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["1d", "1wk", "1mo"],
                        "description": "Candle interval. Default '1d'."
                    },
                    "indicators": {
                        "type": "string",
                        "description": "Comma-separated: ma, macd, rsi, bb, vol. Default all."
                    }
                },
                "required": ["ticker"]
            }
        },
        lambda args, **kw: view_tech_chart(
            ticker=args.get("ticker"),
            period=args.get("period", "1y"),
            interval=args.get("interval", "1d"),
            indicators=args.get("indicators", "ma,macd,rsi,bb,vol"),
        )
    ),
)

def register(ctx) -> None:
    """Register all finance tools. Called once by the plugin loader."""
    for name, schema, handler in _TOOLS:
        # x_search requires X_BEARER_TOKEN; other tools are always available
        if name == "x_search":
            chk = check_x_bearer_token
            emoji = "🐦"
        else:
            chk = lambda: True
            emoji = "📈"

        ctx.register_tool(
            name=name,
            toolset="finance",
            schema=schema,
            handler=handler,
            check_fn=chk,
            emoji=emoji
        )
