#!/usr/bin/env python3
"""
Finance Plugin Tools

A comprehensive set of financial analysis tools:
- DCF Valuation
- Company Health Check (Financial Metrics)
- Insider Trades
- SEC Filings
- Earnings Estimates
- Financial News
- X (Twitter) Sentiment Search
"""

import json
import os
import re
import time
import logging
import socket
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# =============================================================================
# Data Fetching Helpers (Moomoo Priority, yfinance Fallback) with Fail-Fast Check
# =============================================================================

def _is_futu_opend_running(host: str = "127.0.0.1", port: int = 11111) -> bool:
    """Check if Moomoo's Futu OpenD is actively running on the target port."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False

def _get_moomoo_code(ticker: str) -> str:
    """Standardize ticker for Moomoo (e.g. US.AAPL, HK.00700)."""
    if "." in ticker:
        return ticker.upper()
    if ticker.isdigit():
        return f"HK.{ticker.zfill(5)}"
    return f"US.{ticker.upper()}"

def _get_ticker_info(ticker: str, host: str = '127.0.0.1', port: int = 11111) -> Dict[str, Any]:
    """Fetch combined info from Moomoo (Snapshot) or yfinance."""
    info = {}
    source = "Unknown"
    
    # 1. Try Moomoo Snapshot (only if OpenD is running to prevent hang)
    if _is_futu_opend_running(host, port):
        try:
            from moomoo import OpenQuoteContext
            moo_code = _get_moomoo_code(ticker)
            quote_ctx = OpenQuoteContext(host=host, port=port)
            ret, data = quote_ctx.get_market_snapshot([moo_code])
            quote_ctx.close()
            
            if ret == 0 and not data.empty:
                row = data.iloc[0].to_dict()
                info = {
                    "currentPrice": row.get("last_price"),
                    "regularMarketPrice": row.get("last_price"),
                    "sharesOutstanding": row.get("issued_shares"),
                    "totalDebt": None,
                    "totalCash": None,
                    "trailingPE": row.get("pe_ratio"),
                    "dividendYield": row.get("dividend_yield"),
                    "marketCap": row.get("market_val"),
                    "high": row.get("high_price"),
                    "low": row.get("low_price"),
                    "volume": row.get("volume"),
                    "shortName": row.get("name"),
                    "sector": None,
                }
                source = "Moomoo"
                logger.info(f"Fetched snapshot for {ticker} from Moomoo")
        except Exception as e:
            logger.debug(f"Moomoo snapshot failed for {ticker}: {e}")
    else:
        logger.info(f"Moomoo FutuOpenD not running. Skipping Moomoo snapshot for {ticker}.")

    # 2. Try yfinance for missing/fallback
    try:
        import yfinance as yf
        yf_ticker = ticker.split(".")[-1] if "." in ticker else ticker
        stock = yf.Ticker(yf_ticker)
        yf_info = stock.info
        
        if yf_info:
            if not info:
                info = yf_info
                source = "Yahoo Finance"
            else:
                for k, v in yf_info.items():
                    if info.get(k) is None:
                        info[k] = v
                logger.info(f"Augmented Moomoo info with yfinance data for {ticker}")
    except Exception as e:
        logger.warning(f"yfinance fallback failed for {ticker}: {e}")
        
    return {"info": info, "source": source}

def _get_stock_news(ticker: str, host: str = '127.0.0.1', port: int = 11111) -> List[Dict[str, Any]]:
    """Fetch news from Moomoo or yfinance."""
    all_news = []
    
    # Try Moomoo News (only if OpenD is running)
    if _is_futu_opend_running(host, port):
        try:
            from moomoo import OpenQuoteContext
            moo_code = _get_moomoo_code(ticker)
            quote_ctx = OpenQuoteContext(host=host, port=port)
            ret, data = quote_ctx.get_market_news(moo_code) 
            quote_ctx.close()
            
            if ret == 0 and not data.empty:
                for _, row in data.head(10).iterrows():
                    all_news.append({
                        "title": row.get("title"),
                        "publisher": "Moomoo",
                        "link": row.get("news_url"),
                        "providerPublishTime": row.get("news_time"),
                        "source": "Moomoo"
                    })
        except Exception as e:
            logger.debug(f"Moomoo news failed for {ticker}: {e}")

    # Try yfinance News
    try:
        import yfinance as yf
        yf_ticker = ticker.split(".")[-1] if "." in ticker else ticker
        stock = yf.Ticker(yf_ticker)
        yf_news = stock.news
        if yf_news:
            for n in yf_news[:10]:
                content = n.get("content", {})
                if content:
                    title = content.get("title")
                    provider = content.get("provider", {})
                    publisher = provider.get("displayName") if isinstance(provider, dict) else provider
                    canonical = content.get("canonicalUrl", {})
                    link = canonical.get("url") if isinstance(canonical, dict) else None
                    if not link:
                        clickthrough = content.get("clickThroughUrl", {})
                        link = clickthrough.get("url") if isinstance(clickthrough, dict) else None
                    pub_time = content.get("pubDate") or content.get("displayTime")
                else:
                    title = n.get("title")
                    publisher = n.get("publisher")
                    link = n.get("link")
                    pub_time = n.get("providerPublishTime")

                all_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "providerPublishTime": pub_time,
                    "source": "Yahoo Finance"
                })
    except Exception:
        pass
        
    return all_news

# =============================================================================
# Refactored Tools
# =============================================================================

def calculate_dcf(ticker: str, wacc: Optional[float] = None, terminal_growth_rate: float = 0.025, fcf_growth_rate: Optional[float] = None) -> str:
    try:
        data = _get_ticker_info(ticker)
        info = data["info"]
        if not info:
            return f"Error: Could not retrieve information for {ticker}."
            
        import yfinance as yf
        yf_ticker = ticker.split(".")[-1] if "." in ticker else ticker
        stock = yf.Ticker(yf_ticker)
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        shares_outstanding = info.get("sharesOutstanding")
        total_debt = info.get("totalDebt", 0)
        total_cash = info.get("totalCash", 0)
        net_debt = total_debt - total_cash
        sector = info.get("sector", "Unknown")
        
        cf = stock.cashflow
        if cf.empty:
            return f"Error: Could not retrieve cash flow data for {ticker}."
            
        fcf_series = None
        if "Free Cash Flow" in cf.index:
            fcf_series = cf.loc["Free Cash Flow"]
        elif "Operating Cash Flow" in cf.index and "Capital Expenditure" in cf.index:
            fcf_series = cf.loc["Operating Cash Flow"] + cf.loc["Capital Expenditure"]
            
        if fcf_series is None or fcf_series.empty:
            return f"Error: Could not calculate Free Cash Flow for {ticker}."
            
        fcf_series = fcf_series.dropna().sort_index(ascending=True)
        if len(fcf_series) < 2:
            return f"Error: Not enough historical Free Cash Flow data for {ticker}."
            
        if fcf_growth_rate is None:
            first_fcf = fcf_series.iloc[0]
            last_fcf = fcf_series.iloc[-1]
            years = len(fcf_series) - 1
            fcf_growth_rate = (last_fcf / first_fcf) ** (1 / years) - 1 if first_fcf > 0 and last_fcf > 0 else 0.05
            fcf_growth_rate = min(max(fcf_growth_rate, 0.0), 0.15)
        else:
            last_fcf = fcf_series.iloc[-1]
        
        if wacc is None:
            wacc_map = {"Technology": 0.09, "Healthcare": 0.08, "Financial Services": 0.09, "Consumer Cyclical": 0.085, "Industrials": 0.08, "Energy": 0.085, "Consumer Defensive": 0.07, "Utilities": 0.065, "Real Estate": 0.075, "Communication Services": 0.085, "Basic Materials": 0.08}
            wacc = wacc_map.get(sector, 0.085)
            
        projected_fcf = []
        current_fcf = last_fcf
        decay = 0.95
        for i in range(1, 6):
            current_fcf *= (1 + (fcf_growth_rate * (decay ** (i-1))))
            projected_fcf.append(current_fcf)
            
        terminal_value = (projected_fcf[-1] * (1 + terminal_growth_rate)) / (wacc - terminal_growth_rate)
        pv_fcf = sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(projected_fcf))
        pv_terminal_value = terminal_value / ((1 + wacc) ** 5)
        
        enterprise_value = pv_fcf + pv_terminal_value
        equity_value = enterprise_value - net_debt
        fair_value_per_share = equity_value / shares_outstanding
        upside = (fair_value_per_share / current_price) - 1
        
        output = {
            "ticker": ticker.upper(),
            "data_source": data["source"],
            "valuation_summary": {
                "current_price": round(current_price, 2),
                "fair_value_per_share": round(fair_value_per_share, 2),
                "upside_downside_pct": round(upside * 100, 2)
            }
        }
        return json.dumps(output, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error performing DCF: {str(e)}"

def company_health_check(ticker: str) -> str:
    try:
        data = _get_ticker_info(ticker)
        info = data["info"]
        if not info:
            return f"Error: Could not retrieve info for {ticker}."
            
        metrics = {
            "Valuation": {
                "Trailing P/E": info.get("trailingPE"),
                "Forward P/E": info.get("forwardPE"),
                "Price-to-Book (P/B)": info.get("priceToBook"),
                "PEG Ratio": info.get("pegRatio"),
                "Enterprise Value / EBITDA": info.get("enterpriseToEbitda")
            },
            "Profitability": {
                "Return on Equity (ROE)": info.get("returnOnEquity"),
                "Profit Margin": info.get("profitMargins"),
            },
            "Liquidity_and_Debt": {
                "Current Ratio": info.get("currentRatio"),
                "Debt-to-Equity": info.get("debtToEquity"),
            }
        }
        return json.dumps({"ticker": ticker.upper(), "data_source": data["source"], "metrics": metrics}, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error performing health check: {str(e)}"

def get_insider_trades(ticker: str) -> str:
    """
    Retrieves recent insider transactions using yfinance.
    """
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return "Error: yfinance or pandas is not installed."
        
    try:
        stock = yf.Ticker(ticker)
        trades = stock.insider_transactions
        
        if trades is None or trades.empty:
            return f"No recent insider trades found for {ticker}."
            
        # Limit to the 10 most recent transactions
        recent_trades = trades.head(10).copy()
        
        # Convert date to string if applicable
        if 'Start Date' in recent_trades.columns:
            recent_trades['Start Date'] = recent_trades['Start Date'].dt.strftime('%Y-%m-%d')
            
        # Select important columns if they exist
        cols_to_keep = []
        for col in ['Start Date', 'Insider', 'Position', 'Transaction', 'Shares', 'Value']:
            if col in recent_trades.columns:
                cols_to_keep.append(col)
                
        if cols_to_keep:
            recent_trades = recent_trades[cols_to_keep]
            
        # Convert to dictionary format
        trades_dict = recent_trades.to_dict(orient='records')
        
        # Clean up pandas NaNs
        for row in trades_dict:
            for k, v in row.items():
                if pd.isna(v):
                    row[k] = None
                    
        return json.dumps({
            "ticker": ticker.upper(),
            "recent_insider_trades": trades_dict
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return f"Error retrieving insider trades for {ticker}: {str(e)}"

def get_sec_filings(ticker: str, form_type: str = "10-K") -> str:
    """
    Queries SEC EDGAR API for recent filings of a specific type (e.g. 10-K, 10-Q).
    """
    import requests
    
    # 1. Map ticker to CIK
    headers = {
        "User-Agent": "Hermes-Agent/1.0 (info@example.com)"
    }
    try:
        # SEC provides a ticker to CIK mapping
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(tickers_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return f"Error contacting SEC API: Status code {resp.status_code}"
            
        tickers_data = resp.json()
        cik = None
        for _, data in tickers_data.items():
            if data['ticker'].upper() == ticker.upper():
                cik = data['cik_str']
                break
                
        if not cik:
            return f"Error: Could not find CIK for ticker {ticker} in SEC database."
            
        # Format CIK to 10 digits as required by SEC submissions API
        cik_str = str(cik).zfill(10)
        
        # 2. Get company submissions
        sub_url = f"https://data.sec.gov/submissions/CIK{cik_str}.json"
        sub_resp = requests.get(sub_url, headers=headers, timeout=10)
        
        if sub_resp.status_code != 200:
            return f"Error retrieving SEC submissions for CIK {cik_str}: {sub_resp.status_code}"
            
        sub_data = sub_resp.json()
        filings = sub_data.get("filings", {}).get("recent", {})
        
        if not filings:
            return f"No filings found for {ticker}."
            
        # 3. Filter by form type and get top 5
        results = []
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates = filings.get("filingDate", [])
        docs = filings.get("primaryDocument", [])
        
        for i in range(len(forms)):
            if forms[i].upper() == form_type.upper():
                acc_no = accessions[i].replace("-", "")
                doc_name = docs[i]
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{doc_name}"
                
                results.append({
                    "form": forms[i],
                    "filing_date": dates[i],
                    "url": url,
                    "accession_number": accessions[i]
                })
                
                if len(results) >= 5:
                    break
                    
        if not results:
            return f"No recent {form_type} filings found for {ticker}."
            
        return json.dumps({
            "ticker": ticker.upper(),
            "cik": cik_str,
            "filings": results,
            "note": "Use the provided URLs with the browser tool to read the full document if necessary."
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return f"Error fetching SEC filings for {ticker}: {str(e)}"

def get_earnings_estimates(ticker: str) -> str:
    """
    Retrieves Wall Street consensus earnings estimates and future calendar dates using yfinance.
    """
    try:
        import yfinance as yf
    except ImportError:
        return "Error: yfinance is not installed."
        
    try:
        stock = yf.Ticker(ticker)
        
        # Pull data safely
        calendar = stock.calendar
        
        try:
            earnings_est = stock.earnings_estimate
            if hasattr(earnings_est, 'to_dict'):
                earnings_est = earnings_est.to_dict()
        except Exception:
            earnings_est = None
            
        try:
            eps_trend = stock.eps_trend
            if hasattr(eps_trend, 'to_dict'):
                eps_trend = eps_trend.to_dict()
        except Exception:
            eps_trend = None
            
        output = {
            "ticker": ticker.upper(),
            "next_earnings_calendar": calendar.to_dict() if hasattr(calendar, 'to_dict') else str(calendar),
            "earnings_estimate": earnings_est,
            "eps_trend": eps_trend
        }
        
        return json.dumps(output, indent=2, default=str, ensure_ascii=False)
        
    except Exception as e:
        return f"Error fetching earnings estimates for {ticker}: {str(e)}"

def get_financial_news(ticker: str) -> str:
    """
    Retrieves the latest financial news headlines and links for the ticker.
    """
    try:
        import yfinance as yf
    except ImportError:
        return "Error: yfinance is not installed."
        
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            return f"No recent news found for {ticker}."
            
        # Clean up the output to include only relevant fields
        cleaned_news = []
        for article in news[:10]:  # Limit to top 10
            content = article.get("content", {})
            if content:
                title = content.get("title")
                provider = content.get("provider", {})
                publisher = provider.get("displayName") if isinstance(provider, dict) else provider
                canonical = content.get("canonicalUrl", {})
                link = canonical.get("url") if isinstance(canonical, dict) else None
                if not link:
                    clickthrough = content.get("clickThroughUrl", {})
                    link = clickthrough.get("url") if isinstance(clickthrough, dict) else None
                pub_time = content.get("pubDate") or content.get("displayTime")
                related = content.get("relatedTickers", [])
            else:
                title = article.get("title")
                publisher = article.get("publisher")
                link = article.get("link")
                pub_time = article.get("providerPublishTime")
                related = article.get("relatedTickers", [])

            cleaned_news.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "providerPublishTime": pub_time,
                "relatedTickers": related
            })
            
        return json.dumps({
            "ticker": ticker.upper(),
            "latest_news": cleaned_news
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return f"Error fetching financial news for {ticker}: {str(e)}"

# =============================================================================
# X (Twitter) Search Tool — Ported from Dexter x-search.ts
# =============================================================================

X_API_BASE = "https://api.x.com/2"
RATE_DELAY_S = 0.35  # Delay between pagination requests

TWEET_FIELDS = (
    "tweet.fields=created_at,public_metrics,author_id,conversation_id,entities"
    "&expansions=author_id"
    "&user.fields=username,name,public_metrics"
)


def _get_x_bearer_token() -> str:
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise ValueError(
            "X_BEARER_TOKEN is not set. "
            "Get one at https://developer.x.com and add it to your .env file."
        )
    return token


def _x_api_get(url: str) -> Dict[str, Any]:
    """Make a GET request to the X API v2."""
    import requests

    headers = {"Authorization": f"Bearer {_get_x_bearer_token()}"}
    resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code == 429:
        reset = resp.headers.get("x-rate-limit-reset")
        if reset:
            wait_sec = max(int(reset) - int(time.time()), 1)
        else:
            wait_sec = 60
        raise RuntimeError(f"X API rate limited. Resets in {wait_sec}s")

    if resp.status_code != 200:
        raise RuntimeError(f"X API {resp.status_code}: {resp.text[:300]}")

    return resp.json()


def _parse_tweets(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse raw X API response into clean tweet dicts."""
    data = raw.get("data", [])
    if not data:
        return []

    users: Dict[str, Dict] = {}
    for u in raw.get("includes", {}).get("users", []):
        users[u["id"]] = u

    tweets = []
    for t in data:
        u = users.get(t.get("author_id", ""), {})
        m = t.get("public_metrics", {})
        entities = t.get("entities", {})
        url_entities = entities.get("urls", [])
        username = u.get("username", "?")

        tweets.append({
            "id": t.get("id"),
            "text": t.get("text"),
            "author_id": t.get("author_id"),
            "username": username,
            "name": u.get("name", "?"),
            "created_at": t.get("created_at"),
            "metrics": {
                "likes": m.get("like_count", 0),
                "retweets": m.get("retweet_count", 0),
                "replies": m.get("reply_count", 0),
                "impressions": m.get("impression_count", 0),
            },
            "urls": [e.get("expanded_url") for e in url_entities if e.get("expanded_url")],
            "tweet_url": f"https://x.com/{username}/status/{t.get('id')}",
        })
    return tweets


def _parse_since(since: str) -> Optional[str]:
    """Parse shorthand time strings like '1h', '3d', '7d' into ISO 8601."""
    match = re.match(r"^(\d+)(m|h|d)$", since)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        delta = {
            "m": timedelta(minutes=num),
            "h": timedelta(hours=num),
            "d": timedelta(days=num),
        }[unit]
        return (datetime.now(timezone.utc) - delta).isoformat()

    if "T" in since or re.match(r"^\d{4}-", since):
        try:
            return datetime.fromisoformat(since).isoformat()
        except ValueError:
            return None
    return None


def _search_tweets(
    query: str,
    pages: int = 1,
    max_results: int = 100,
    sort_order: str = "relevancy",
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search recent tweets with pagination."""
    import requests  # noqa: F811

    pages = min(pages, 5)
    max_results = max(min(max_results, 100), 10)
    encoded = requests.utils.quote(query)

    time_filter = ""
    if since:
        start_time = _parse_since(since)
        if start_time:
            time_filter = f"&start_time={start_time}"

    all_tweets: List[Dict[str, Any]] = []
    next_token = None

    for page in range(pages):
        pagination = f"&pagination_token={next_token}" if next_token else ""
        url = (
            f"{X_API_BASE}/tweets/search/recent?query={encoded}"
            f"&max_results={max_results}&{TWEET_FIELDS}"
            f"&sort_order={sort_order}{time_filter}{pagination}"
        )

        raw = _x_api_get(url)
        all_tweets.extend(_parse_tweets(raw))
        next_token = raw.get("meta", {}).get("next_token")
        if not next_token:
            break
        if page < pages - 1:
            time.sleep(RATE_DELAY_S)

    # Deduplicate
    seen = set()
    unique = []
    for t in all_tweets:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)
    return unique


def _get_x_profile(
    username: str, count: int
) -> Dict[str, Any]:
    """Get a user profile and their recent tweets."""
    user_url = (
        f"{X_API_BASE}/users/by/username/{username}"
        f"?user.fields=public_metrics,description,created_at"
    )
    user_data = _x_api_get(user_url)
    user = user_data.get("data")
    if not user:
        raise RuntimeError(f"User @{username} not found")

    time.sleep(RATE_DELAY_S)

    query = f"from:{username} -is:retweet -is:reply"
    tweets = _search_tweets(query, max_results=min(count, 100), sort_order="recency")

    return {"user": user, "tweets": tweets}


def _get_x_thread(conversation_id: str) -> List[Dict[str, Any]]:
    """Fetch a conversation thread."""
    query = f"conversation_id:{conversation_id}"
    return _search_tweets(query, pages=2, sort_order="recency")


def x_search(
    command: str,
    query: Optional[str] = None,
    username: Optional[str] = None,
    sort: str = "likes",
    since: Optional[str] = None,
    min_likes: int = 0,
    limit: int = 15,
    pages: int = 1,
) -> str:
    """
    Search X/Twitter for real-time public sentiment, news, and expert opinions.
    Supports search, profile, and thread commands.
    """
    try:
        if command == "search":
            if not query:
                return "Error: 'query' is required for the search command."

            # Auto-suppress retweets unless caller explicitly included the operator
            if "is:retweet" not in query:
                query += " -is:retweet"

            sort_order = "recency" if sort == "recent" else "relevancy"
            max_results = max(min(limit, 100), 10)

            tweets = _search_tweets(
                query, pages=pages, max_results=max_results,
                sort_order=sort_order, since=since,
            )

            # Post-hoc filters
            if min_likes > 0:
                tweets = [t for t in tweets if t["metrics"]["likes"] >= min_likes]

            # Sort
            if sort and sort != "recent":
                metric_key = sort  # likes, retweets, impressions
                tweets.sort(key=lambda t: t["metrics"].get(metric_key, 0), reverse=True)

            results = tweets[:limit]
            return json.dumps({
                "command": "search",
                "query": query,
                "total_fetched": len(tweets),
                "results_returned": len(results),
                "tweets": results,
            }, indent=2, ensure_ascii=False)

        elif command == "profile":
            if not username:
                return "Error: 'username' is required for the profile command."

            data = _get_x_profile(username, limit)
            return json.dumps({
                "command": "profile",
                "user": data["user"],
                "tweets": data["tweets"][:limit],
            }, indent=2, ensure_ascii=False)

        elif command == "thread":
            if not query:
                return "Error: 'query' (tweet ID) is required for the thread command."

            tweets = _get_x_thread(query)
            return json.dumps({
                "command": "thread",
                "conversation_id": query,
                "tweets": tweets[:limit],
            }, indent=2, ensure_ascii=False)

        else:
            return f"Error: Unknown command '{command}'. Use 'search', 'profile', or 'thread'."

    except Exception as e:
        return f"Error in x_search: {str(e)}"


def check_x_bearer_token() -> bool:
    """Check if X_BEARER_TOKEN is available."""
    return bool(os.environ.get("X_BEARER_TOKEN"))


# =============================================================================
# Technical Chart Generator
# =============================================================================

def generate_tech_chart(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    indicators: str = "ma,macd,rsi,bb,vol",
    style: str = "dark",
    host: str = "127.0.0.1",
    port: int = 11111,
) -> str:
    """
    Generate a professional candlestick chart with technical indicators.
    Data source priority: Moomoo API → yfinance fallback.
    Returns JSON with the saved image path.
    """
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        plt.switch_backend("Agg")
        import mplfinance as mpf
        import numpy as np
        import pandas as pd
    except ImportError as e:
        return json.dumps({"success": False, "error": f"Missing dependency: {e}. Run: uv pip install mplfinance"})

    # Check for talib, use robust pandas fallbacks if missing
    try:
        import talib
        has_talib = True
    except ImportError:
        has_talib = False

    indicator_set = set(i.strip().lower() for i in indicators.split(","))

    # ------------------------------------------------------------------
    # 1. Fetch data — try Moomoo first, fall back to yfinance
    # ------------------------------------------------------------------
    df = None
    data_source = None

    # --- Moomoo attempt ---
    if _is_futu_opend_running(host, port):
        try:
            from moomoo import OpenQuoteContext, KLType

            period_days_map = {"3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
            days = period_days_map.get(period, 365)
            start_date = (pd.Timestamp.now() - pd.DateOffset(days=days)).strftime("%Y-%m-%d")

            # Moomoo uses codes like "US.TSLA"; yfinance uses "TSLA"
            moo_code = ticker if "." in ticker else f"US.{ticker}"

            ktype_map = {"1d": KLType.K_DAY, "1wk": KLType.K_WEEK, "1mo": KLType.K_MON}
            ktype = ktype_map.get(interval, KLType.K_DAY)

            quote_ctx = OpenQuoteContext(host=host, port=port)
            ret, data, _ = quote_ctx.request_history_kline(moo_code, start=start_date, ktype=ktype)
            quote_ctx.close()

            if ret == 0 and data is not None and not data.empty:
                data["datetime"] = pd.to_datetime(data["time_key"])
                data.set_index("datetime", inplace=True)
                df = data[["open", "high", "low", "close", "volume"]].copy()
                df.columns = ["Open", "High", "Low", "Close", "Volume"]
                data_source = "Moomoo"
                logger.info(f"Chart data for {ticker} fetched from Moomoo ({len(df)} bars)")
        except Exception as e:
            logger.info(f"Moomoo failed for {ticker}: {e}")
    else:
        logger.info(f"Moomoo FutuOpenD not running. Skipping Moomoo chart K-line for {ticker}.")

    # --- yfinance fallback ---
    if df is None:
        try:
            import yfinance as yf
            yf_ticker = ticker.replace("US.", "").replace("HK.", "") if "." in ticker else ticker
            raw = yf.download(yf_ticker, period=period, interval=interval, progress=False)
            if raw is not None and not raw.empty:
                df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
                # Handle multi-level columns from yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data_source = "Yahoo Finance"
                logger.info(f"Chart data for {ticker} fetched from yfinance ({len(df)} bars)")
        except Exception as e2:
            return json.dumps({"success": False, "error": f"Both Moomoo and yfinance failed: {e2}"})

    if df is None or df.empty:
        return json.dumps({"success": False, "error": f"No data available for {ticker}"})

    # Ensure numeric types
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(inplace=True)

    if len(df) < 20:
        return json.dumps({"success": False, "error": f"Not enough data for {ticker} ({len(df)} bars, need ≥20)"})

    # ------------------------------------------------------------------
    # 2. Calculate indicators
    # ------------------------------------------------------------------
    close = np.array(df["Close"], dtype="float64")
    high = np.array(df["High"], dtype="float64")
    low = np.array(df["Low"], dtype="float64")

    addplots = []
    show_volume = "vol" in indicator_set
    # panel 0 = main chart; panel 1 = volume (if enabled by mplfinance)
    panel_count = 2 if show_volume else 1

    # --- Moving Averages (main panel overlay) ---
    if "ma" in indicator_set:
        if len(close) >= 20:
            if has_talib:
                df["MA20"] = talib.SMA(close, timeperiod=20)
            else:
                df["MA20"] = df["Close"].rolling(window=20).mean()
            addplots.append(mpf.make_addplot(df["MA20"], panel=0, color="#2196F3", width=1.2, label="MA20"))
        if len(close) >= 81:
            if has_talib:
                df["MA81"] = talib.SMA(close, timeperiod=81)
            else:
                df["MA81"] = df["Close"].rolling(window=81).mean()
            addplots.append(mpf.make_addplot(df["MA81"], panel=0, color="#FF9800", width=1.5, label="MA81"))

    # --- Bollinger Bands (main panel overlay) ---
    if "bb" in indicator_set and len(close) >= 20:
        if has_talib:
            bb_upper, bb_mid, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            df["BB_Upper"] = bb_upper
            df["BB_Lower"] = bb_lower
        else:
            mid = df["Close"].rolling(window=20).mean()
            std = df["Close"].rolling(window=20).std()
            df["BB_Upper"] = mid + 2 * std
            df["BB_Lower"] = mid - 2 * std
        addplots.append(mpf.make_addplot(df["BB_Upper"], panel=0, color="#9E9E9E", width=0.8, linestyle="dashed"))
        addplots.append(mpf.make_addplot(df["BB_Lower"], panel=0, color="#9E9E9E", width=0.8, linestyle="dashed"))

    # --- MACD (separate panel) ---
    if "macd" in indicator_set and len(close) >= 26:
        if has_talib:
            macd_line, signal_line, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            df["MACD"] = macd_line
            df["Signal"] = signal_line
            df["MACD_Hist"] = macd_hist
        else:
            ema12 = df["Close"].ewm(span=12, adjust=False).mean()
            ema26 = df["Close"].ewm(span=26, adjust=False).mean()
            df["MACD"] = ema12 - ema26
            df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
            df["MACD_Hist"] = df["MACD"] - df["Signal"]

        hist_colors = ["#26A69A" if v >= 0 else "#EF5350" for v in df["MACD_Hist"].fillna(0)]

        addplots.append(mpf.make_addplot(df["MACD"], panel=panel_count, color="#2196F3", width=1.0, ylabel="MACD"))
        addplots.append(mpf.make_addplot(df["Signal"], panel=panel_count, color="#FF9800", width=1.0))
        addplots.append(mpf.make_addplot(df["MACD_Hist"], panel=panel_count, type="bar", color=hist_colors, width=0.7))
        panel_count += 1

    # --- RSI (separate panel) ---
    if "rsi" in indicator_set and len(close) >= 14:
        if has_talib:
            df["RSI"] = talib.RSI(close, timeperiod=14)
        else:
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))

        addplots.append(mpf.make_addplot(df["RSI"], panel=panel_count, color="#AB47BC", width=1.2, ylabel="RSI"))
        # Overbought / Oversold reference lines
        df["RSI_70"] = 70.0
        df["RSI_30"] = 30.0
        addplots.append(mpf.make_addplot(df["RSI_70"], panel=panel_count, color="#EF5350", width=0.5, linestyle="dashed"))
        addplots.append(mpf.make_addplot(df["RSI_30"], panel=panel_count, color="#26A69A", width=0.5, linestyle="dashed"))
        panel_count += 1

    # ------------------------------------------------------------------
    # 3. Render chart with mplfinance
    # ------------------------------------------------------------------
    style_map = {
        "dark": "nightclouds",
        "classic": "charles",
        "nightclouds": "nightclouds",
        "yahoo": "yahoo",
    }
    mpf_style = style_map.get(style, "nightclouds")

    # Custom market colors (red up, green down — Asian market convention)
    mc = mpf.make_marketcolors(
        up="#EF5350", down="#26A69A",
        edge="inherit",
        wick="inherit",
        volume={"up": "#EF5350", "down": "#26A69A"},
    )
    custom_style = mpf.make_mpf_style(base_mpf_style=mpf_style, marketcolors=mc)

    # Build title
    last_price = df["Close"].iloc[-1]
    change_pct = (df["Close"].iloc[-1] / df["Close"].iloc[-2] - 1) * 100 if len(df) >= 2 else 0
    display_ticker = ticker.replace("US.", "").replace("HK.", "") if "." in ticker else ticker
    title = f"{display_ticker}  ${last_price:.2f}  ({change_pct:+.2f}%)  [{data_source}]"

    # Panel ratios — mplfinance auto-creates a volume panel when volume=True,
    # so we must account for it in the ratio list.
    show_volume = "vol" in indicator_set

    # Count actual panels: main chart (always) + volume (if shown) + MACD + RSI
    panel_ratios = [4]  # panel 0: main chart (candlesticks + overlays)
    if show_volume:
        panel_ratios.append(1)  # volume panel (auto-created by mplfinance)
    if "macd" in indicator_set and len(close) >= 26:
        panel_ratios.append(1.5)
    if "rsi" in indicator_set and len(close) >= 14:
        panel_ratios.append(1)

    # Save path
    safe_name = ticker.replace(".", "_")
    chart_path = os.path.join(os.path.expanduser("~"), ".hermes", f"{safe_name}_chart.png")

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=custom_style,
        title=title,
        volume=show_volume,
        addplot=addplots if addplots else None,
        panel_ratios=panel_ratios if len(panel_ratios) > 1 else None,
        figsize=(14, 10),
        tight_layout=True,
        returnfig=True,
        warn_too_much_data=9999,
    )

    fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return json.dumps({
        "success": True,
        "image_path": chart_path,
        "ticker": ticker,
        "data_source": data_source,
        "bars": len(df),
        "period": period,
        "interval": interval,
        "indicators": list(indicator_set),
        "last_price": round(last_price, 2),
        "instruction_for_agent": (
            f"IMPORTANT: A technical chart image has been saved to {chart_path}. "
            f"You MUST include this image in your response using markdown: "
            f"![{display_ticker} Technical Chart]({chart_path})"
        ),
    })

