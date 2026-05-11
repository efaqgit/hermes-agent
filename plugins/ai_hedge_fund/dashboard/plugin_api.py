"""AI Hedge Fund & Moomoo Quant Dashboard Plugin — Backend API.

Mounted at /api/plugins/ai_hedge_fund/ by the dashboard plugin system.
Integrates:
1. Moomoo Quant: Positions, account info, and active order lists.
2. Finance Pro: Dynamic technical chart compiler with OpenD fail-safe connection checks.
3. AI Hedge Fund: LangGraph master advisor multi-agent consensus flows.
"""

import sys
import os
import json
import logging
import socket
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional

# Set path resolution
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.moomoo_tools import moomoo_get_positions, moomoo_get_account_info, moomoo_get_orders
from plugins.ai_hedge_fund.tools import run_hedge_fund_analysis

router = APIRouter()
logger = logging.getLogger(__name__)

class AnalysisRequest(BaseModel):
    tickers: List[str]
    months_back: Optional[int] = 3

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

@router.get("/positions")
async def get_moomoo_positions():
    """Retrieve live Moomoo positions for the Dashboard."""
    try:
        if not _is_futu_opend_running():
            return {
                "success": False,
                "error": "Moomoo FutuOpenD is not running. Please start Futu OpenD locally to see live assets.",
                "data": []
            }
            
        res_str = moomoo_get_positions(env="SIMULATE")
        res = json.loads(res_str)
        return res
    except Exception as e:
        logger.exception("Failed to get positions in dashboard API")
        return {"success": False, "error": str(e), "data": []}

@router.get("/account")
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
        return res
    except Exception as e:
        logger.exception("Failed to get account info in dashboard API")
        return {"success": False, "error": str(e), "data": {}}

@router.get("/orders")
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
        logger.exception("Failed to get orders list in dashboard API")
        return {"success": False, "error": str(e), "data": []}

@router.post("/run-analysis")
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
        logger.exception("Failed to run hedge fund analysis in dashboard API")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chart", response_class=HTMLResponse)
async def get_chart_html(
    ticker: str = Query(..., description="The ticker symbol, e.g. TSLA, NVDA"),
    period: str = "1y",
    interval: str = "1d",
    indicators: str = "ma,macd,rsi,bb,vol"
):
    """Generates an interactive HTML Technical chart using Lightweight Charts.
    
    Directly returns the HTML so it can be seamlessly rendered inside an iframe on the dashboard.
    """
    try:
        import numpy as np
        import pandas as pd
        import talib
    except ImportError as e:
        return f"<html><body style='background:#0a0a0f;color:#e0e0e0;padding:20px;font-family:sans-serif;'><h3>Missing system dependencies: {e}</h3><p>Please make sure numpy, pandas, and ta-lib are installed in your Hermes environment.</p></body></html>"

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
        color = "#26A69A" if row["Close"] >= row["Open"] else "#EF5350"
        vol_data.append({"time": t, "value": int(row["Volume"]), "color": color})

    ma20_data, ma81_data = [], []
    if "ma" in indicator_set:
        if len(close) >= 20:
            ma20 = talib.SMA(close, timeperiod=20)
            ma20_data = [{"time": ts(df.index[i]), "value": round(float(ma20[i]), 2)}
                         for i in range(len(df)) if not np.isnan(ma20[i])]
        if len(close) >= 81:
            ma81 = talib.SMA(close, timeperiod=81)
            ma81_data = [{"time": ts(df.index[i]), "value": round(float(ma81[i]), 2)}
                         for i in range(len(df)) if not np.isnan(ma81[i])]

    bb_upper_data, bb_lower_data = [], []
    if "bb" in indicator_set and len(close) >= 20:
        bb_upper, _, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        for i in range(len(df)):
            if not np.isnan(bb_upper[i]):
                t = ts(df.index[i])
                bb_upper_data.append({"time": t, "value": round(float(bb_upper[i]), 2)})
                bb_lower_data.append({"time": t, "value": round(float(bb_lower[i]), 2)})

    macd_data, signal_data, hist_data = [], [], []
    if "macd" in indicator_set and len(close) >= 26:
        macd_line, signal_line, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        for i in range(len(df)):
            if not np.isnan(macd_line[i]):
                t = ts(df.index[i])
                macd_data.append({"time": t, "value": round(float(macd_line[i]), 4)})
                signal_data.append({"time": t, "value": round(float(signal_line[i]), 4)})
                color = "#26A69A" if macd_hist[i] >= 0 else "#EF5350"
                hist_data.append({"time": t, "value": round(float(macd_hist[i]), 4), "color": color})

    rsi_data = []
    if "rsi" in indicator_set and len(close) >= 14:
        rsi = talib.RSI(close, timeperiod=14)
        rsi_data = [{"time": ts(df.index[i]), "value": round(float(rsi[i]), 2)}
                    for i in range(len(df)) if not np.isnan(rsi[i])]

    display_ticker = ticker.replace("US.", "").replace("HK.", "") if "." in ticker else ticker
    last_price = float(df["Close"].iloc[-1])
    change_pct = (df["Close"].iloc[-1] / df["Close"].iloc[-2] - 1) * 100 if len(df) >= 2 else 0
    change_color = "#EF5350" if change_pct >= 0 else "#26A69A" # Asian convention: Up is RED, Down is GREEN (Futu-style)

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
    
    except Exception as e:
        logger.exception("Error in chart generation")
        return f"<html><body style='background:#0a0a0f;color:#e0e0e0;padding:20px;'><h3>Chart generation failed: {e}</h3></body></html>"
