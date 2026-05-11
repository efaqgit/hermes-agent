"""Standalone Financial & Quant Dashboard Server.

An independent FastAPI server running on port 9200.
Connects directly to:
1. Moomoo Live Trading API (Positions, Balance, Orders)
2. Interactive Technical Charts (TradingView)
3. AI Hedge Fund Master Consensus Flows
"""

import sys
import os
import json
import logging
import socket
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Path resolution to import local modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.moomoo_tools import moomoo_get_positions, moomoo_get_account_info, moomoo_get_orders
from plugins.ai_hedge_fund.tools import run_hedge_fund_analysis

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StandaloneFinanceDashboard")

app = FastAPI(
    title="Unified Quant & Finance Standalone Terminal",
    description="Independent Financial Dashboard serving Moomoo, Charting, and AI Hedge Fund operations.",
    version="1.0.0"
)

# Enable CORS for local development freedom
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    tickers: List[str]
    months_back: Optional[int] = 3

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

def _is_futu_opend_running(host: str = "127.0.0.1", port: int = 11111) -> bool:
    """Check if Moomoo's Futu OpenD is actively running on the target port."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False

def _get_moomoo_code(ticker: str) -> str:
    """Standardize ticker for Moomoo (e.g. US.TSLA)."""
    ticker = ticker.strip().upper()
    if "." in ticker:
        return ticker
    if ticker.isdigit():
        return f"HK.{ticker.zfill(5)}"
    return f"US.{ticker}"

# ─── FRONTEND STATIC ROUTING ──────────────────────────────────────────

@app.get("/")
async def get_index():
    """Serve the single-page application dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Frontend static/index.html is missing. Please make sure the static files are generated.</h2>")

@app.get("/app.js")
async def get_js():
    """Serve the React application code."""
    js_path = os.path.join(STATIC_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path)
    return HTMLResponse("// Frontend static/app.js is missing.", media_type="application/javascript")

# ─── API ENDPOINTS ───────────────────────────────────────────────────

@app.get("/api/connection-status")
async def check_connection():
    """Check connection status to Futu OpenD."""
    opend_ok = _is_futu_opend_running()
    return {
        "success": True,
        "futu_opend": opend_ok,
        "yfinance": True,
        "message": "Futu OpenD is LIVE" if opend_ok else "Futu OpenD Offline (yfinance Fallback active)"
    }

@app.get("/api/positions")
async def get_moomoo_positions():
    """Retrieve live Moomoo positions."""
    try:
        if not _is_futu_opend_running():
            return {
                "success": False,
                "error": "Moomoo FutuOpenD is not running. Live portfolio disabled.",
                "data": []
            }
            
        res_str = moomoo_get_positions(env="SIMULATE")
        res = json.loads(res_str)
        if res.get("success") and res.get("data"):
            for row in res["data"]:
                # Convert pl_ratio from percentage (Moomoo API) to fraction (expected by frontend)
                ratio = row.get("pl_ratio")
                if ratio is not None:
                    row["pl_ratio"] = float(ratio) / 100.0
                else:
                    row["pl_ratio"] = 0.0
                
                # Standardize price key
                row["nominal_price"] = float(row.get("nominal_price") or row.get("cost_price") or 0.0)
        return res
    except Exception as e:
        logger.exception("Failed to get positions")
        return {"success": False, "error": str(e), "data": []}

@app.get("/api/account")
async def get_moomoo_account():
    """Retrieve live Moomoo account equity, balances and buying power."""
    try:
        if not _is_futu_opend_running():
            return {
                "success": False,
                "error": "Moomoo FutuOpenD is not running.",
                "data": {}
            }
            
        res_str = moomoo_get_account_info(env="SIMULATE")
        res = json.loads(res_str)
        if res.get("success") and res.get("data"):
            # Map Futu keys to what frontend expects to prevent TypeError crashes
            for row in res["data"]:
                row["cash_balance"] = float(row.get("cash") or 0.0)
                row["power_balance"] = float(row.get("power") or 0.0)
                row["total_assets"] = float(row.get("total_assets") or 0.0)
                row["market_val"] = float(row.get("market_val") or 0.0)
        return res
    except Exception as e:
        logger.exception("Failed to get account info")
        return {"success": False, "error": str(e), "data": {}}

@app.get("/api/orders")
async def get_moomoo_orders():
    """Retrieve Moomoo daily trading orders list."""
    try:
        if not _is_futu_opend_running():
            return {
                "success": False,
                "error": "Moomoo FutuOpenD is not running.",
                "data": []
            }
            
        res_str = moomoo_get_orders(env="SIMULATE")
        res = json.loads(res_str)
        return res
    except Exception as e:
        logger.exception("Failed to get orders list")
        return {"success": False, "error": str(e), "data": []}

WATCHLIST_FILE = os.path.join(os.path.expanduser("~"), ".hermes", "finance_watchlist.json")

def _load_watchlist() -> list:
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default watchlist
    return ["AMAT", "MSTR", "NVDA", "TSLA"]

def _save_watchlist(tickers: list):
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(tickers, f, indent=2)

@app.get("/api/watchlist")
async def get_watchlist():
    """Retrieve dynamic stock watchlist with live quotes."""
    tickers = _load_watchlist()
    data = []
    import yfinance as yf
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d", interval="1d")
            if hist is not None and len(hist) >= 1:
                last_price = float(hist["Close"].iloc[-1])
                prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else last_price
                change_pct = ((last_price / prev_close) - 1) * 100 if prev_close > 0 else 0
                high = float(hist["High"].iloc[-1])
                low = float(hist["Low"].iloc[-1])
            else:
                last_price, prev_close, change_pct, high, low = 0.0, 0.0, 0.0, 0.0, 0.0
            data.append({
                "symbol": ticker,
                "price": round(last_price, 2),
                "prev_close": round(prev_close, 2),
                "change_pct": round(change_pct, 2),
                "high": round(high, 2),
                "low": round(low, 2)
            })
        except Exception as e:
            logger.error(f"Failed to fetch watchlist quote for {ticker}: {e}")
            data.append({
                "symbol": ticker,
                "price": 0.0,
                "prev_close": 0.0,
                "change_pct": 0.0,
                "high": 0.0,
                "low": 0.0,
                "error": str(e)
            })
    return {"success": True, "data": data}

@app.post("/api/watchlist")
async def add_to_watchlist(ticker: str):
    """Add a ticker to the watchlist."""
    tickers = _load_watchlist()
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker")
    if ticker not in tickers:
        tickers.append(ticker)
        _save_watchlist(tickers)
    return {"success": True, "message": f"Added {ticker} to watchlist", "data": tickers}

@app.delete("/api/watchlist")
async def delete_from_watchlist(ticker: str):
    """Remove a ticker from the watchlist."""
    tickers = _load_watchlist()
    ticker = ticker.upper().strip()
    if ticker in tickers:
        tickers.remove(ticker)
        _save_watchlist(tickers)
    return {"success": True, "message": f"Removed {ticker} from watchlist", "data": tickers}

@app.post("/api/run-analysis")
async def run_analysis(req: AnalysisRequest):
    """Run Multi-Agent analysis on specified tickers."""
    try:
        tickers = [t.upper().strip() for t in req.tickers if t.strip()]
        if not tickers:
            raise HTTPException(status_code=400, detail="No valid tickers provided")
            
        markdown_report = run_hedge_fund_analysis(tickers, months_back=req.months_back)
        return {
            "success": True,
            "markdown": markdown_report
        }
    except Exception as e:
        logger.exception("Failed to run hedge fund analysis")
        raise HTTPException(status_code=500, detail=str(e))

OBSIDIAN_DIR = "/Users/kennethlin/Github/@obsidian/finance"

def _translate_news_titles(news_list: list) -> list:
    """Batch-translates headlines to Taiwan Chinese (Traditional) using auxiliary LLM."""
    if not news_list:
        return news_list
        
    titles = [item.get("title", "") for item in news_list if item.get("title")]
    if not titles:
        return news_list
        
    prompt = f"""You are an elite financial translator. Translate the following English stock news headlines into natural, professional Taiwan Chinese (繁體中文).
Always use proper local Taiwanese terminology (e.g., use '晶片' for chips, '特斯拉' for Tesla, '輝達' for NVIDIA, '台積電' for TSMC, '營收' for revenue, '半導體' for semiconductors, etc.).

Return ONLY a raw JSON array of translated strings in the exact same order. Do NOT wrap in markdown code blocks like ```json. Do NOT include any explanations or conversational preambles.

Input headlines:
{json.dumps(titles, ensure_ascii=False, indent=2)}
"""
    try:
        from agent.auxiliary_client import call_llm, extract_content_or_reasoning
        response = call_llm(
            task="translation",
            messages=[
                {"role": "system", "content": "You are a professional financial translator specialized in Taiwan Chinese."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        ans = extract_content_or_reasoning(response)
        
        # Strip potential markdown formatting
        import re
        ans_cleaned = re.sub(r"```[a-zA-Z]*", "", ans).strip()
        ans_cleaned = ans_cleaned.strip("`").strip()
        
        translated_titles = json.loads(ans_cleaned)
        if isinstance(translated_titles, list) and len(translated_titles) == len(titles):
            title_map = dict(zip(titles, translated_titles))
            for item in news_list:
                t = item.get("title")
                if t in title_map:
                    item["title_translated"] = str(title_map[t])
                else:
                    item["title_translated"] = t
        else:
            for item in news_list:
                item["title_translated"] = item.get("title", "")
    except Exception as e:
        logger.error(f"Failed to batch translate news: {e}")
        for item in news_list:
            item["title_translated"] = item.get("title", "")
            
    return news_list

def _run_monte_carlo(ticker: str) -> dict:
    import numpy as np
    import yfinance as yf
    
    ticker = ticker.upper().strip()
    t = yf.Ticker(ticker)
    info = t.info
    
    current_price = float(info.get("currentPrice") or info.get("previousClose") or 100.0)
    shares_outstanding = int(info.get("sharesOutstanding") or 10000000)
    total_cash = float(info.get("totalCash") or 0.0)
    total_debt = float(info.get("totalDebt") or 0.0)
    net_debt = total_debt - total_cash
    
    # Base amounts (fallback to net income if FCF is negative or missing)
    fcf_base = float(info.get("freeCashflow") or info.get("operatingCashflow") or 0.0)
    earnings_base = float(info.get("netIncomeToCommon") or info.get("netIncome") or 0.0)
    
    if fcf_base <= 0 and earnings_base > 0:
        fcf_base = earnings_base * 0.6
    if earnings_base <= 0 and fcf_base > 0:
        earnings_base = fcf_base * 1.5
    if fcf_base <= 0 and earnings_base <= 0:
        fcf_base = current_price * shares_outstanding * 0.04
        earnings_base = current_price * shares_outstanding * 0.06

    trials = 10000
    np.random.seed(42)
    
    # Stochastic variables dynamically estimated based on yfinance parameters
    beta = info.get("beta")
    if beta is None or beta <= 0:
        beta = 1.0
    
    # Risk-free rate (4.2%) + Beta * Equity Risk Premium (5.0%)
    wacc_mean = 0.042 + (beta * 0.05)
    debt_equity = info.get("debtToEquity")
    if debt_equity:
        # High leverage increases required return rate (WACC risk)
        wacc_mean += min(0.02, (debt_equity / 100.0) * 0.005)
    wacc_mean = min(max(wacc_mean, 0.065), 0.125)

    rev_growth = info.get("revenueGrowth")
    earn_growth = info.get("earningsGrowth")
    growth_est = 0.10
    if earn_growth is not None and earn_growth != 0:
        growth_est = earn_growth
    elif rev_growth is not None and rev_growth != 0:
        growth_est = rev_growth
    
    growth_stage1_mean = min(max(growth_est, 0.05), 0.25)
    growth_stage2_mean = min(max(growth_stage1_mean * 0.6, 0.03), 0.12)
    perp_mean = 0.025

    wacc_trials = np.random.normal(wacc_mean, 0.006, trials)
    wacc_trials = np.clip(wacc_trials, 0.06, 0.14)
    
    growth_stage1_trials = np.random.normal(growth_stage1_mean, 0.02, trials)
    growth_stage2_trials = np.random.normal(growth_stage2_mean, 0.012, trials)
    
    perpetual_growth_trials = np.random.normal(perp_mean, 0.003, trials)
    perpetual_growth_trials = np.minimum(perpetual_growth_trials, wacc_trials - 0.01)
    
    def run_dcf(base_amount):
        results = []
        for i in range(trials):
            wacc = wacc_trials[i]
            g1 = growth_stage1_trials[i]
            g2 = growth_stage2_trials[i]
            g_perp = perpetual_growth_trials[i]
            
            projected = []
            current = base_amount
            for year in range(1, 6):
                current = current * (1 + g1)
                projected.append(current)
            for year in range(6, 11):
                current = current * (1 + g2)
                projected.append(current)
                
            pv = 0
            for year in range(1, 11):
                pv += projected[year - 1] / ((1 + wacc) ** year)
                
            tv = (projected[-1] * (1 + g_perp)) / (wacc - g_perp)
            pv_tv = tv / ((1 + wacc) ** 10)
            
            ev = pv + pv_tv
            eq = ev - net_debt
            results.append(eq / shares_outstanding)
        return np.array(results)
        
    fcf_results = run_dcf(fcf_base)
    earnings_results = run_dcf(earnings_base)
    
    fcf_mean = float(np.mean(fcf_results))
    earnings_mean = float(np.mean(earnings_results))
    
    # Fetch Insider Trades
    insider_data = []
    try:
        df = t.insider_transactions
        if df is not None and not df.empty:
            for _, row in df.head(6).iterrows():
                insider_data.append({
                    "insider": str(row.get("Insider") or "N/A"),
                    "position": str(row.get("Position") or "N/A"),
                    "transaction": str(row.get("Transaction") or "N/A"),
                    "shares": int(row.get("Shares") or 0),
                    "value": float(row.get("Value") or 0.0),
                    "date": str(row.get("Start Date") or "N/A")
                })
    except Exception as e:
        logger.error(f"Failed to fetch insider transactions for {ticker}: {e}")

    # Fetch SEC Filings
    sec_data = []
    try:
        sec = t.sec_filings
        if sec:
            for f in sec[:6]:
                sec_data.append({
                    "date": str(f.get("date") or "N/A"),
                    "type": str(f.get("type") or "N/A"),
                    "title": str(f.get("title") or "N/A"),
                    "url": str(f.get("edgarUrl") or "")
                })
    except Exception as e:
        logger.error(f"Failed to fetch SEC filings for {ticker}: {e}")

    # Fetch News
    news_data = []
    try:
        raw_news = t.news
        if raw_news:
            for item in raw_news[:6]:
                title = ""
                publisher = ""
                link = ""
                pub_date = ""
                if "content" in item:
                    content = item["content"]
                    title = content.get("title") or ""
                    pub_date = content.get("pubDate") or content.get("displayTime") or ""
                    if "provider" in content:
                        publisher = content["provider"].get("displayName") or ""
                    if "canonicalUrl" in content:
                        link = content["canonicalUrl"].get("url") or ""
                else:
                    title = item.get("title") or ""
                    pub_date = item.get("pubDate") or item.get("providerPublishTime") or ""
                    publisher = item.get("publisher") or ""
                    link = item.get("link") or ""
                
                if pub_date and "T" in pub_date:
                    pub_date = pub_date.split("T")[0]
                
                news_data.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "date": pub_date
                })
    except Exception as e:
        logger.error(f"Failed to fetch news for {ticker}: {e}")

    # Batch-translate news titles to Taiwan Chinese
    news_data = _translate_news_titles(news_data)

    return {
        "ticker": ticker,
        "current_price": current_price,
        "shares": shares_outstanding,
        "cash": total_cash,
        "debt": total_debt,
        "net_debt": net_debt,
        "fcf_base": fcf_base,
        "earnings_base": earnings_base,
        "pe_trailing": info.get("trailingPE"),
        "pe_forward": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "peg_ratio": info.get("pegRatio"),
        "profit_margin": info.get("profitMargins"),
        "roe": info.get("returnOnEquity"),
        "current_ratio": info.get("currentRatio"),
        "debt_equity": info.get("debtToEquity"),
        "beta": beta,
        "est_wacc": wacc_mean,
        "est_growth_g1": growth_stage1_mean,
        "est_growth_g2": growth_stage2_mean,
        "est_growth_perp": perp_mean,
        "insider_trades": insider_data,
        "sec_filings": sec_data,
        "news_summary": news_data,
        "fcf_model": {
            "mean": round(fcf_mean, 2),
            "median": round(float(np.median(fcf_results)), 2),
            "p10": round(float(np.percentile(fcf_results, 10)), 2),
            "p25": round(float(np.percentile(fcf_results, 25)), 2),
            "p75": round(float(np.percentile(fcf_results, 75)), 2),
            "p90": round(float(np.percentile(fcf_results, 90)), 2),
            "upside_pct": round(((fcf_mean / current_price) - 1) * 100, 2)
        },
        "earnings_model": {
            "mean": round(earnings_mean, 2),
            "median": round(float(np.median(earnings_results)), 2),
            "p10": round(float(np.percentile(earnings_results, 10)), 2),
            "p25": round(float(np.percentile(earnings_results, 25)), 2),
            "p75": round(float(np.percentile(earnings_results, 75)), 2),
            "p90": round(float(np.percentile(earnings_results, 90)), 2),
            "upside_pct": round(((earnings_mean / current_price) - 1) * 100, 2)
        }
    }

def _generate_markdown_report(stats: dict) -> str:
    from datetime import datetime
    ticker = stats["ticker"]
    
    roe_pct = f"{stats['roe'] * 100:.2f}%" if stats["roe"] is not None else "N/A"
    margin_pct = f"{stats['profit_margin'] * 100:.2f}%" if stats["profit_margin"] is not None else "N/A"
    debt_eq_val = f"{stats['debt_equity']:.2f}%" if stats["debt_equity"] is not None else "N/A"
    pe_trailing = f"{stats['pe_trailing']:.2f}" if stats["pe_trailing"] is not None else "N/A"
    pe_forward = f"{stats['pe_forward']:.2f}" if stats["pe_forward"] is not None else "N/A"
    pb_ratio = f"{stats['pb_ratio']:.2f}" if stats["pb_ratio"] is not None else "N/A"
    peg_ratio = f"{stats['peg_ratio']:.2f}" if stats["peg_ratio"] is not None else "N/A"
    curr_ratio = f"{stats['current_ratio']:.2f}" if stats["current_ratio"] is not None else "N/A"
    
    upside = stats["earnings_model"]["upside_pct"]
    if upside >= 15:
        rating = "強力買入 (Strong Buy)"
    elif upside >= 5:
        rating = "逢低買入 (Buy on Dips / Accumulate)"
    elif upside >= -5:
        rating = "中性持有 (Hold / Neutral)"
    else:
        rating = "高估避險 (Reduce / Avoid)"

    report_date = datetime.now().strftime("%Y-%m-%d")

    # Section IV: SEC Filings Table
    sec_rows = ""
    if stats.get("sec_filings"):
        for f in stats["sec_filings"]:
            url_markdown = f"[閱讀 Edgar 檔案]({f['url']})" if f['url'] else "無連結"
            sec_rows += f"| {f['date']} | **{f['type']}** | {f['title']} | {url_markdown} |\n"
    else:
        sec_rows = "| - | - | 暫無最新 SEC 申報檔案 | - |\n"

    # Section V: Insider Trades Table
    insider_rows = ""
    if stats.get("insider_trades"):
        for t in stats["insider_trades"]:
            val_str = f"${t['value']:,.0f}" if t['value'] > 0 else "-"
            shares_str = f"{t['shares']:,}" if t['shares'] > 0 else "-"
            insider_rows += f"| {t['date']} | **{t['insider']}** | {t['position']} | {t['transaction']} | {shares_str} | {val_str} |\n"
    else:
        insider_rows = "| - | - | - | 暫無最新內部人交易紀錄 | - | - |\n"

    # Section VI: News Summary List
    news_list = ""
    if stats.get("news_summary"):
        for n in stats["news_summary"]:
            translated = n.get("title_translated") or n.get("title", "")
            original = n.get("title", "")
            
            if translated and translated != original:
                display_text = f"**{translated}** ( *{original}* )"
            else:
                display_text = f"**{original}**"
                
            title_link = f"[{display_text}]({n['link']})" if n['link'] else display_text
            pub_info = f"*{n['publisher']}* ({n['date']})" if n['publisher'] else f"({n['date']})"
            news_list += f"* 📰 {title_link} — {pub_info}\n"
    else:
        news_list = "* 暫無最新市場新聞報導。"

    md = f"""---
ticker: {ticker}
type: finance_analysis
date: {report_date}
current_price: {stats['current_price']}
valuation_fcf: {stats['fcf_model']['mean']}
valuation_earnings: {stats['earnings_model']['mean']}
recommendation: {rating}
---

# {ticker} 深度研究與雙軌蒙地卡羅估值報告

> **報告發布時間**：{report_date}
> **分析標的**：{ticker}
> **當前市場收盤價**：${stats['current_price']:.2f}
> **研究框架**：不確定性雙軌隨機模擬估值（Stochastic Hybrid Valuation）

---

## 一、 執行摘要與投資論點 (Executive Summary & Investment Thesis)

本報告針對 {ticker} 進行了全方位的財務審計與 10,000 次蒙地卡羅隨機估值模擬。藉由結合其資本開支特徵與真實營運收益能力，確立其價值中樞與安全邊際。

### 📌 關鍵投資事實與指標摘要 (Key Investment Facts & Metrics Bulletin)：
* **🎯 綜合投資評等**：**{rating}**
* **💎 雙軌價值中樞 (Consensus Fair Value Range)**：
  - 🏦 **自由現金流折現地板 (FCF Model Mean)**：**${stats['fcf_model']['mean']}** (期望空間: {stats['fcf_model']['upside_pct']:+.2f}%) —— 代表極端保守、扣除全額資本支出下的資產價值地板。
  - 📈 **常態獲利貼現中樞 (Earnings Model Mean)**：**${stats['earnings_model']['mean']}** (期望空間: {stats['earnings_model']['upside_pct']:+.2f}%) —— 更加貼近常態商業營運的權益回報。
* **💰 核心營運與資產實力 (Annual Run-Rate & Balance Sheet)**：
  - **年化自由現金流 (Annual FCF Base)**：**${stats['fcf_base']/1e6:.1f}M**
  - **年化淨利潤 (Annual Net Income Base)**：**${stats['earnings_base']/1e6:.1f}M**
  - **淨債務狀況 (Net Debt Position)**：**${stats['net_debt']/1e6:.1f}M** (帳上現金 `${stats['cash']/1e6:.1f}M` vs 總債務 `${stats['debt']/1e6:.1f}M`)
* **⚡ 經營效率與市場波動度 (Operational Efficiency & Beta)**：
  - **股東權益報酬率 (ROE)**：**{roe_pct}** (衡量資金回報效率的核心指標)
  - **核心業務淨利率 (Profit Margin)**：**{margin_pct}**
  - **市場風險係數 (Beta)**：**{stats.get('beta', 1.0):.2f}** (代表股價相較大盤的波動與風險特徵)
* **🛡️ 建議安全邊際吸收價位 (Safety Margin Target - P25)**：
  - 建議於 FCF 折現模型的 P25 分位價位 **${stats['fcf_model']['p25']}** 以下逢低分批吸納，此價位具備極高的中長期抗跌防守價值。

---

## 二、 財務健康狀況審計 (Fundamental Financial Health Audit)

根據最新的市場基礎數據，{ticker} 的財務指標摘要如下：

| 財務維度 | 關鍵指標 | 數值 | 診斷與評估 |
| :--- | :--- | :--- | :--- |
| **估值比率** | Trailing P/E | **{pe_trailing}** | 歷史本益比倍數。 |
| | Forward P/E | **{pe_forward}** | 預期本益比。 |
| | Price-to-Book (P/B)| **{pb_ratio}** | 股價淨值比。 |
| | PEG Ratio | **{peg_ratio}** | 市盈成長比。 |
| **獲利能力** | **ROE (股東權益報酬率)** | **{roe_pct}** | 資金回報率表現。 |
| | **Profit Margin (淨利率)**| **{margin_pct}** | 核心業務盈利溢價能力。 |
| **流動性與債務** | Current Ratio (流動比率)| **{curr_ratio}** | 短期償債防守指標。 |
| | Debt-to-Equity (債務權益比)| **{debt_eq_val}** | 長期財務槓桿健康度。 |
| | **淨債務狀況** | **${stats['net_debt']/1e6:.1f}M** | 總負債減去現金餘額。 |

---

## 三、 雙軌蒙地卡羅隨機模擬估值 (Double-Track Monte Carlo Valuation)

為避免傳統單一 DCF 模型因重資本開支（Deposition CapEx）或研發再投資（R&D Reinvestment）而扭曲價值，本系統特別對其進行了雙軌 10,000 次隨機估值推演。

### 📊 估值模型動態隨機變數假設 (Stochastic Model Assumptions)：
本報告的蒙地卡羅模擬參數並非採用固定死板的硬編碼，而是**根據個股最新的實際市場風險波動度 (Beta) 與成長動能 (Historical Growth Rates) 進行動態智能估算**：
* 🏦 **動態加權平均資本成本 (Estimated WACC)**：期望值為 **{stats.get('est_wacc', 0.085)*100:.2f}%** (基於市場系統性風險係數 Beta = **{stats.get('beta', 1.0):.2f}** 與 CAPM 資本定價模型動態推算)
* 📈 **第一階段高增長率 (Stage 1 Growth, 1-5年)**：期望值為 **{stats.get('est_growth_g1', 0.14)*100:.2f}%** (基於最新歷史營收/盈餘增長動能動態推算)
* 📉 **第二階段過渡增長率 (Stage 2 Growth, 6-10年)**：期望值為 **{stats.get('est_growth_g2', 0.08)*100:.2f}%** (動態衰退)
* 🌐 **終值永續增長率 (Perpetual Growth Rate)**：期望值為 **{stats.get('est_growth_perp', 0.025)*100:.2f}%**

### 10,000 次隨機模擬估值統計結果：

| 統計分位數 | FCF 折現模型 (保守現金流地板) | Earnings 折現模型 (常態盈利天花板) |
| :--- | :---: | :---: |
| **P10 (極度保守熊市)** | ${stats['fcf_model']['p10']} | ${stats['earnings_model']['p10']} |
| **P25 (保守安全邊際)** | ${stats['fcf_model']['p25']} | ${stats['earnings_model']['p25']} |
| **P50 (中位數估值)** | ${stats['fcf_model']['median']} | ${stats['earnings_model']['median']} |
| **Mean (期望內在價值)** | **${stats['fcf_model']['mean']}** | **${stats['earnings_model']['mean']}** |
| **P75 (溫和牛市目標)** | ${stats['fcf_model']['p75']} | ${stats['earnings_model']['p75']} |
| **P90 (樂觀牛市目標)** | ${stats['fcf_model']['p90']} | ${stats['earnings_model']['p90']} |
| **當前收盤價 ${stats['current_price']:.2f} 期望空間** | **{stats['fcf_model']['upside_pct']:+.2f}%** | **{stats['earnings_model']['upside_pct']:+.2f}%** |

### 估值結論與操作建議：
* **保守現金流地板 (FCF Model)**：展示了在最壞、全額核銷資本支出且不轉換為盈利的條件下，公司最低的清算/現金流價值支撐。
* **常態獲利天花板 (Earnings Model)**：更能代表其結構性收益回報，是中長期合理目標價的指引中樞。
* **操作策略**：建議於安全邊際 P25 以下分批吸納，並以 Mean 作為第一中線目標。

---

## 四、 最新 SEC 重要申報檔案 (Latest SEC Filings)

以下是近期該公司向美國證券交易委員會 (SEC) 申報的最新 6 筆檔案明細：

| 申報日期 | 檔案類型 | 檔案主題與摘要描述 | 線上閱讀連結 |
| :--- | :--- | :--- | :--- |
{sec_rows}
---

## 五、 最新內部人交易紀錄 (Insider Transactions)

以下是近期公司內部大股東、董事與高階經理人 (Insiders) 的持股交易與變動明細：

| 交易日期 | 內部人姓名 | 職位 | 交易類型 | 交易股數 | 交易價值 |
| :--- | :--- | :--- | :--- | :--- | :--- |
{insider_rows}
---

## 六、 最新新聞動態與輿情摘要 (Latest News & Media Coverage)

以下是該股在各大財經媒體與市場所關注的最新重要動向與評論：

{news_list}
"""
    return md

@app.get("/api/finance-analysis/reports")
async def get_reports_list(ticker: str):
    """Scan and list all Obsidian reports for a specific ticker."""
    ticker = ticker.upper().strip()
    reports = []
    if os.path.exists(OBSIDIAN_DIR):
        for f in os.listdir(OBSIDIAN_DIR):
            if f.startswith(f"{ticker}_finance_analysis_report_") and f.endswith(".md"):
                # Extract datetime from name like TSLA_finance_analysis_report_20260509_125500.md
                parts = f.replace(".md", "").split("_")
                dt_str = "N/A"
                if len(parts) >= 6:
                    date_part, time_part = parts[-2], parts[-1]
                    if len(date_part) == 8 and len(time_part) == 6:
                        dt_str = f"{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}"
                reports.append({
                    "filename": f,
                    "datetime": dt_str,
                    "path": os.path.join(OBSIDIAN_DIR, f)
                })
    # Sort descending by filename / date
    reports.sort(key=lambda x: x["filename"], reverse=True)
    return {"success": True, "data": reports}

@app.get("/api/finance-analysis/report-content")
async def get_report_content(filename: str):
    """Read and return content of a specific Obsidian report."""
    safe_name = os.path.basename(filename)
    path = os.path.join(OBSIDIAN_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {e}")

class GenerateReportRequest(BaseModel):
    ticker: str

@app.post("/api/finance-analysis/generate")
async def generate_report(req: GenerateReportRequest):
    """Run generalized Monte Carlo simulation and compile premium report to Obsidian."""
    ticker = req.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker provided")
    try:
        # Run 10k simulations
        stats = _run_monte_carlo(ticker)
        # Build markdown content
        md_content = _generate_markdown_report(stats)
        
        # Save to Obsidian folder
        from datetime import datetime
        dt_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(OBSIDIAN_DIR, exist_ok=True)
        filename = f"{ticker}_finance_analysis_report_{dt_str}.md"
        path = os.path.join(OBSIDIAN_DIR, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        return {
            "success": True,
            "filename": filename,
            "path": path,
            "markdown": md_content
        }
    except Exception as e:
        logger.exception(f"Failed to generate Monte Carlo report for {ticker}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chart", response_class=HTMLResponse)
async def get_chart_html(
    ticker: str = Query(..., description="The ticker symbol, e.g. TSLA, NVDA"),
    period: str = "1y",
    interval: str = "1d",
    indicators: str = "ma,macd,rsi,bb,vol"
):
    """Generates an interactive HTML Technical chart using Lightweight Charts."""
    try:
        import numpy as np
        import pandas as pd
    except ImportError as e:
        return f"<html><body style='background:#0a0a0f;color:#e0e0e0;padding:20px;font-family:sans-serif;'><h3>Missing system dependencies: {e}</h3><p>Please make sure numpy and pandas are installed in your environment.</p></body></html>"

    try:
        import talib
        has_talib = True
    except ImportError:
        has_talib = False

    indicator_set = set(i.strip().lower() for i in indicators.split(","))
    df = None
    data_source = None
    host = "127.0.0.1"
    port = 11111

    # 1. Fetch data
    if _is_futu_opend_running(host, port):
        try:
            from moomoo import OpenQuoteContext, KLType
            period_days_map = {"3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
            days = period_days_map.get(period, 365)
            start_date = (pd.Timestamp.now() - pd.DateOffset(days=days)).strftime("%Y-%m-%d")
            moo_code = _get_moomoo_code(ticker)
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
        except Exception as e:
            logger.info(f"Moomoo chart data fetch failed, falling back: {e}")

    if df is None:
        try:
            import yfinance as yf
            clean_ticker = ticker.replace("US.", "").replace("HK.", "") if "." in ticker else ticker
            raw = yf.download(clean_ticker, period=period, interval=interval, progress=False)
            if raw is not None and not raw.empty:
                df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data_source = "Yahoo Finance"
        except Exception as e:
            return f"<html><body style='background:#0a0a0f;color:#e0e0e0;padding:20px;font-family:sans-serif;'><h3>Failed to load chart data for {ticker}</h3><p>{e}</p></body></html>"

    if df is None or df.empty:
        return f"<html><body style='background:#0a0a0f;color:#e0e0e0;padding:20px;font-family:sans-serif;'><h3>No data available for ticker: {ticker}</h3></body></html>"

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(inplace=True)

    if len(df) < 20:
        return f"<html><body style='background:#0a0a0f;color:#e0e0e0;padding:20px;font-family:sans-serif;'><h3>Not enough K-line data available ({len(df)} bars found, minimum 20 needed)</h3></body></html>"

    # 2. Indicators Calculation
    close = np.array(df["Close"], dtype="float64")
    def ts(dt):
        return int(dt.timestamp())

    candle_data = []
    vol_data = []
    for idx, row in df.iterrows():
        t = ts(idx)
        candle_data.append({"time": t, "open": round(row["Open"], 2),
                            "high": round(row["High"], 2), "low": round(row["Low"], 2),
                            "close": round(row["Close"], 2)})
        color = "#EF5350" if row["Close"] >= row["Open"] else "#26A69A"
        vol_data.append({"time": t, "value": int(row["Volume"]), "color": color})

    ma20_data, ma81_data = [], []
    if "ma" in indicator_set:
        if len(close) >= 20:
            if has_talib:
                ma20 = talib.SMA(close, timeperiod=20)
            else:
                ma20 = df["Close"].rolling(window=20).mean().values
            ma20_data = [{"time": ts(df.index[i]), "value": round(float(ma20[i]), 2)}
                         for i in range(len(df)) if not np.isnan(ma20[i])]
        if len(close) >= 81:
            if has_talib:
                ma81 = talib.SMA(close, timeperiod=81)
            else:
                ma81 = df["Close"].rolling(window=81).mean().values
            ma81_data = [{"time": ts(df.index[i]), "value": round(float(ma81[i]), 2)}
                         for i in range(len(df)) if not np.isnan(ma81[i])]

    bb_upper_data, bb_lower_data = [], []
    if "bb" in indicator_set and len(close) >= 20:
        if has_talib:
            bb_upper, _, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        else:
            mid = df["Close"].rolling(window=20).mean()
            std = df["Close"].rolling(window=20).std()
            bb_upper = (mid + 2 * std).values
            bb_lower = (mid - 2 * std).values
        for i in range(len(df)):
            if not np.isnan(bb_upper[i]):
                t = ts(df.index[i])
                bb_upper_data.append({"time": t, "value": round(float(bb_upper[i]), 2)})
                bb_lower_data.append({"time": t, "value": round(float(bb_lower[i]), 2)})

    macd_data, signal_data, hist_data = [], [], []
    if "macd" in indicator_set and len(close) >= 26:
        if has_talib:
            macd_line, signal_line, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        else:
            ema12 = df["Close"].ewm(span=12, adjust=False).mean()
            ema26 = df["Close"].ewm(span=26, adjust=False).mean()
            macd_line = (ema12 - ema26).values
            signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
            macd_hist = macd_line - signal_line
        for i in range(len(df)):
            if not np.isnan(macd_line[i]):
                t = ts(df.index[i])
                macd_data.append({"time": t, "value": round(float(macd_line[i]), 4)})
                signal_data.append({"time": t, "value": round(float(signal_line[i]), 4)})
                color = "#EF5350" if macd_hist[i] >= 0 else "#26A69A"
                hist_data.append({"time": t, "value": round(float(macd_hist[i]), 4), "color": color})

    rsi_data = []
    if "rsi" in indicator_set and len(close) >= 14:
        if has_talib:
            rsi = talib.RSI(close, timeperiod=14)
        else:
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).values
        rsi_data = [{"time": ts(df.index[i]), "value": round(float(rsi[i]), 2)}
                    for i in range(len(df)) if not np.isnan(rsi[i])]

    display_ticker = ticker.replace("US.", "").replace("HK.", "") if "." in ticker else ticker
    last_price = float(df["Close"].iloc[-1])
    change_pct = (df["Close"].iloc[-1] / df["Close"].iloc[-2] - 1) * 100 if len(df) >= 2 else 0
    change_color = "#EF5350" if change_pct >= 0 else "#26A69A"

    # 3. Formulate HTML Output
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{display_ticker} — Interactive Chart</title>
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#07070a; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,'SF Pro','Inter',sans-serif; overflow-x:hidden; }}
.hdr {{
  padding:10px 18px; display:flex; align-items:baseline; gap:12px;
  background:linear-gradient(135deg,#0d0d14,#121220); border-bottom:1px solid #1f1f2e;
}}
.hdr h1 {{ font-size:18px; font-weight:700; color:#fff; }}
.hdr .px {{ font-size:17px; font-weight:600; color:{change_color}; }}
.hdr .ch {{ font-size:13px; color:{change_color}; }}
.hdr .src {{ font-size:11px; color:#555; margin-left:auto; }}
.lbl {{
  padding:2px 18px; font-size:9px; color:#555; background:#07070a;
  border-top:1px solid #1a1a2e; text-transform:uppercase; letter-spacing:1px;
}}
.legend {{
  position:absolute; top:6px; left:12px; z-index:10; font-size:10px; color:#666; pointer-events:none;
}}
.legend span {{ margin-right:10px; }}
</style>
</head>
<body>
<div class="hdr">
  <h1>{display_ticker}</h1>
  <span class="px">${last_price:.2f}</span>
  <span class="ch">({change_pct:+.2f}%)</span>
  <span class="src">{data_source} · {period.upper()} · {interval}</span>
</div>

<div style="position:relative">
  <div class="legend">
    {('<span style="color:#2196F3">━ MA20</span>' if ma20_data else '')}
    {('<span style="color:#FF9800">━ MA81</span>' if ma81_data else '')}
    {('<span style="color:#9E9E9E">┈ BB(20,2)</span>' if bb_upper_data else '')}
  </div>
  <div id="main"></div>
</div>
{"<div class='lbl'>Volume</div><div id='vol'></div>" if "vol" in indicator_set else ""}
{"<div class='lbl'>MACD (12, 26, 9)</div><div id='macd'></div>" if macd_data else ""}
{"<div class='lbl'>RSI (14)</div><div id='rsi'></div>" if rsi_data else ""}

<script>
const D = {{
  candle: {json.dumps(candle_data)},
  vol: {json.dumps(vol_data)},
  ma20: {json.dumps(ma20_data)},
  ma81: {json.dumps(ma81_data)},
  bbU: {json.dumps(bb_upper_data)},
  bbL: {json.dumps(bb_lower_data)},
  macd: {json.dumps(macd_data)},
  sig: {json.dumps(signal_data)},
  hist: {json.dumps(hist_data)},
  rsi: {json.dumps(rsi_data)},
}};

const base = {{
  layout:{{ background:{{ type:'solid', color:'#07070a' }}, textColor:'#888' }},
  grid:{{ vertLines:{{ color:'#121220' }}, horzLines:{{ color:'#121220' }} }},
  crosshair:{{ mode: LightweightCharts.CrosshairMode.Normal }},
  timeScale:{{ borderColor:'#1f1f2e', timeVisible:false }},
  rightPriceScale:{{ borderColor:'#1f1f2e' }},
}};

function mk(id, h) {{
  const el = document.getElementById(id);
  if (!el) return null;
  el.style.height = h + 'px';
  return LightweightCharts.createChart(el, {{ ...base, height: h }});
}}

const charts = [];

// Main Candlestick Chart (Asian Style: Red-Up, Green-Down)
const mainH = Math.max(window.innerHeight * 0.42, 260);
const mc = mk('main', mainH);
if (mc) {{
  const cs = mc.addCandlestickSeries({{
    upColor:'#EF5350', downColor:'#26A69A',
    borderUpColor:'#EF5350', borderDownColor:'#26A69A',
    wickUpColor:'#EF5350', wickDownColor:'#26A69A',
  }});
  cs.setData(D.candle);
  if (D.ma20.length) {{ const s=mc.addLineSeries({{color:'#2196F3',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}); s.setData(D.ma20); }}
  if (D.ma81.length) {{ const s=mc.addLineSeries({{color:'#FF9800',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false}}); s.setData(D.ma81); }}
  if (D.bbU.length) {{
    const u=mc.addLineSeries({{color:'#9E9E9E',lineWidth:0.6,lineStyle:2,priceLineVisible:false,lastValueVisible:false}}); u.setData(D.bbU);
    const l=mc.addLineSeries({{color:'#9E9E9E',lineWidth:0.6,lineStyle:2,priceLineVisible:false,lastValueVisible:false}}); l.setData(D.bbL);
  }}
  mc.timeScale().fitContent();
  charts.push(mc);
}}

// Volume Chart
if (D.vol.length) {{
  const vc = mk('vol', 65);
  if (vc) {{
    const vs = vc.addHistogramSeries({{priceFormat:{{type:'volume'}},priceLineVisible:false,lastValueVisible:false}});
    vs.setData(D.vol);
    vc.timeScale().fitContent();
    charts.push(vc);
  }}
}}

// MACD Chart
if (D.macd.length) {{
  const mcc = mk('macd', 95);
  if (mcc) {{
    const ml=mcc.addLineSeries({{color:'#2196F3',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}); ml.setData(D.macd);
    const sl=mcc.addLineSeries({{color:'#FF9800',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}); sl.setData(D.sig);
    const hs=mcc.addHistogramSeries({{priceLineVisible:false,lastValueVisible:false}}); hs.setData(D.hist);
    const zl=mcc.addLineSeries({{color:'#333',lineWidth:0.5,lineStyle:2,priceLineVisible:false,lastValueVisible:false}});
    zl.setData(D.macd.map(d=>({{time:d.time,value:0}})));
    mcc.timeScale().fitContent();
    charts.push(mcc);
  }}
}}

// RSI Chart
if (D.rsi.length) {{
  const rc = mk('rsi', 80);
  if (rc) {{
    const rl=rc.addLineSeries({{color:'#AB47BC',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}); rl.setData(D.rsi);
    const ob=rc.addLineSeries({{color:'#EF5350',lineWidth:0.5,lineStyle:2,priceLineVisible:false,lastValueVisible:false}});
    ob.setData(D.rsi.map(d=>({{time:d.time,value:70}})));
    const os=rc.addLineSeries({{color:'#26A69A',lineWidth:0.5,lineStyle:2,priceLineVisible:false,lastValueVisible:false}});
    os.setData(D.rsi.map(d=>({{time:d.time,value:30}})));
    rc.timeScale().fitContent();
    charts.push(rc);
  }}
}}

// Sync Logic
let syncing = false;
charts.forEach(c => {{
  c.timeScale().subscribeVisibleLogicalRangeChange(r => {{
    if (syncing || !r) return;
    syncing = true;
    charts.forEach(o => {{ if (o !== c) o.timeScale().setVisibleLogicalRange(r); }});
    syncing = false;
  }});
}});

window.addEventListener('resize', () => {{
  const w = window.innerWidth;
  charts.forEach(c => c.applyOptions({{ width: w }}));
}});
</script>
</body>
</html>"""
    return html

if __name__ == "__main__":
    logger.info("Starting Standalone Unified Finance Terminal on http://127.0.0.1:9200")
    uvicorn.run(app, host="127.0.0.1", port=9200)
