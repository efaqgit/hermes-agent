"""
Interactive Technical Chart — TradingView lightweight-charts (v4)

Generates a self-contained HTML file with:
- Candlestick chart (red-up / green-down, Asian convention)
- MA20 + MA81 moving averages
- Bollinger Bands (20,2)
- Volume histogram
- MACD (12, 26, 9) with signal line + histogram
- RSI (14) with overbought/oversold lines
- Crosshair sync across all panels
- Time-scale zoom/pan sync

Data source: Moomoo API (primary) → yfinance (fallback)
"""

import json
import logging
import os
import socket
from typing import Optional

logger = logging.getLogger(__name__)


def _is_futu_opend_running(host: str = "127.0.0.1", port: int = 11111) -> bool:
    """Check if Moomoo's Futu OpenD is actively running on the target port."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False


def view_tech_chart(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    indicators: str = "ma,macd,rsi,bb,vol",
    host: str = "127.0.0.1",
    port: int = 11111,
) -> str:
    """
    Generate an interactive HTML chart and open it in the default browser.
    """
    try:
        import numpy as np
        import pandas as pd
        import talib
    except ImportError as e:
        return json.dumps({"success": False, "error": f"Missing dependency: {e}"})

    indicator_set = set(i.strip().lower() for i in indicators.split(","))

    # ------------------------------------------------------------------
    # 1. Fetch data — Moomoo first, yfinance fallback
    # ------------------------------------------------------------------
    df = None
    data_source = None

    if _is_futu_opend_running(host, port):
        try:
            from moomoo import OpenQuoteContext, KLType
            period_days_map = {"3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
            days = period_days_map.get(period, 365)
            start_date = (pd.Timestamp.now() - pd.DateOffset(days=days)).strftime("%Y-%m-%d")
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
        except Exception as e:
            logger.info(f"Moomoo failed for {ticker}: {e}")
    else:
        logger.info(f"Moomoo FutuOpenD not running. Skipping Moomoo interactive K-line for {ticker}.")

    if df is None:
        try:
            import yfinance as yf
            yf_ticker = ticker.replace("US.", "").replace("HK.", "") if "." in ticker else ticker
            raw = yf.download(yf_ticker, period=period, interval=interval, progress=False)
            if raw is not None and not raw.empty:
                df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data_source = "Yahoo Finance"
        except Exception as e2:
            return json.dumps({"success": False, "error": f"Both data sources failed: {e2}"})

    if df is None or df.empty:
        return json.dumps({"success": False, "error": f"No data available for {ticker}"})

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(inplace=True)

    if len(df) < 20:
        return json.dumps({"success": False, "error": f"Not enough data ({len(df)} bars)"})

    # ------------------------------------------------------------------
    # 2. Calculate indicators & prepare JSON data
    # ------------------------------------------------------------------
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
    change_color = "#26A69A" if change_pct >= 0 else "#EF5350"

    # ------------------------------------------------------------------
    # 3. Build HTML
    # ------------------------------------------------------------------
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{display_ticker} — Interactive Chart</title>
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0a0f; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,'SF Pro','Inter',sans-serif; }}
.hdr {{
  padding:14px 24px; display:flex; align-items:baseline; gap:14px;
  background:linear-gradient(135deg,#12121a,#1a1a2e); border-bottom:1px solid #2a2a3e;
}}
.hdr h1 {{ font-size:22px; font-weight:700; color:#fff; }}
.hdr .px {{ font-size:20px; font-weight:600; color:{change_color}; }}
.hdr .ch {{ font-size:15px; color:{change_color}; }}
.hdr .src {{ font-size:12px; color:#555; margin-left:auto; }}
.lbl {{
  padding:3px 24px; font-size:10px; color:#444; background:#0d0d14;
  border-top:1px solid #1a1a2e; text-transform:uppercase; letter-spacing:1.2px;
}}
.legend {{
  position:absolute; top:6px; left:12px; z-index:10; font-size:11px; color:#666; pointer-events:none;
}}
.legend span {{ margin-right:12px; }}
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
  layout:{{ background:{{ type:'solid', color:'#0a0a0f' }}, textColor:'#888' }},
  grid:{{ vertLines:{{ color:'#1a1a2e' }}, horzLines:{{ color:'#1a1a2e' }} }},
  crosshair:{{ mode: LightweightCharts.CrosshairMode.Normal }},
  timeScale:{{ borderColor:'#2a2a3e', timeVisible:false }},
  rightPriceScale:{{ borderColor:'#2a2a3e' }},
}};

function mk(id, h) {{
  const el = document.getElementById(id);
  if (!el) return null;
  el.style.height = h + 'px';
  return LightweightCharts.createChart(el, {{ ...base, height: h }});
}}

const charts = [];

// Main
const mainH = Math.max(window.innerHeight * 0.45, 300);
const mc = mk('main', mainH);
if (mc) {{
  const cs = mc.addCandlestickSeries({{
    upColor:'#EF5350', downColor:'#26A69A',
    borderUpColor:'#EF5350', borderDownColor:'#26A69A',
    wickUpColor:'#EF5350', wickDownColor:'#26A69A',
  }});
  cs.setData(D.candle);
  if (D.ma20.length) {{ const s=mc.addLineSeries({{color:'#2196F3',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false}}); s.setData(D.ma20); }}
  if (D.ma81.length) {{ const s=mc.addLineSeries({{color:'#FF9800',lineWidth:2,priceLineVisible:false,lastValueVisible:false}}); s.setData(D.ma81); }}
  if (D.bbU.length) {{
    const u=mc.addLineSeries({{color:'#9E9E9E',lineWidth:0.8,lineStyle:2,priceLineVisible:false,lastValueVisible:false}}); u.setData(D.bbU);
    const l=mc.addLineSeries({{color:'#9E9E9E',lineWidth:0.8,lineStyle:2,priceLineVisible:false,lastValueVisible:false}}); l.setData(D.bbL);
  }}
  mc.timeScale().fitContent();
  charts.push(mc);
}}

// Volume
if (D.vol.length) {{
  const vc = mk('vol', 90);
  if (vc) {{
    const vs = vc.addHistogramSeries({{priceFormat:{{type:'volume'}},priceLineVisible:false,lastValueVisible:false}});
    vs.setData(D.vol);
    vc.timeScale().fitContent();
    charts.push(vc);
  }}
}}

// MACD
if (D.macd.length) {{
  const mcc = mk('macd', 130);
  if (mcc) {{
    const ml=mcc.addLineSeries({{color:'#2196F3',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false}}); ml.setData(D.macd);
    const sl=mcc.addLineSeries({{color:'#FF9800',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false}}); sl.setData(D.sig);
    const hs=mcc.addHistogramSeries({{priceLineVisible:false,lastValueVisible:false}}); hs.setData(D.hist);
    const zl=mcc.addLineSeries({{color:'#333',lineWidth:0.5,lineStyle:2,priceLineVisible:false,lastValueVisible:false}});
    zl.setData(D.macd.map(d=>({{time:d.time,value:0}})));
    mcc.timeScale().fitContent();
    charts.push(mcc);
  }}
}}

// RSI
if (D.rsi.length) {{
  const rc = mk('rsi', 110);
  if (rc) {{
    const rl=rc.addLineSeries({{color:'#AB47BC',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false}}); rl.setData(D.rsi);
    const ob=rc.addLineSeries({{color:'#EF5350',lineWidth:0.5,lineStyle:2,priceLineVisible:false,lastValueVisible:false}});
    ob.setData(D.rsi.map(d=>({{time:d.time,value:70}})));
    const os=rc.addLineSeries({{color:'#26A69A',lineWidth:0.5,lineStyle:2,priceLineVisible:false,lastValueVisible:false}});
    os.setData(D.rsi.map(d=>({{time:d.time,value:30}})));
    rc.timeScale().fitContent();
    charts.push(rc);
  }}
}}

// Sync zoom/pan
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

    # ------------------------------------------------------------------
    # 4. Save & open
    # ------------------------------------------------------------------
    safe_name = ticker.replace(".", "_")
    html_path = os.path.join(os.path.expanduser("~"), ".hermes", f"{safe_name}_chart.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    import webbrowser
    webbrowser.open(f"file://{html_path}")

    return json.dumps({
        "success": True,
        "html_path": html_path,
        "ticker": ticker,
        "data_source": data_source,
        "bars": len(df),
        "last_price": round(last_price, 2),
        "instruction_for_agent": (
            f"An interactive chart for {display_ticker} has been opened in the browser. "
            f"It includes candlesticks, volume, MA20, MA81, Bollinger Bands, MACD, and RSI. "
            f"The user can zoom (scroll), pan (drag), and hover for crosshair tracking. "
            f"All panels are synced."
        ),
    })
