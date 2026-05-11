const { useState, useEffect } = React;

function App() {
  // Connection & Server States
  const [connStatus, setConnStatus] = useState({ futu_opend: false, message: "Checking link..." });
  const [positions, setPositions] = useState([]);
  const [accountInfo, setAccountInfo] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);

  // Watchlist State
  const [watchlist, setWatchlist] = useState([]);
  const [newWatchTicker, setNewWatchTicker] = useState("");
  const [watchlistLoading, setWatchlistLoading] = useState(false);

  // Chart State
  const [activeChartTicker, setActiveChartTicker] = useState("AMAT");
  const [selectedIndicators, setSelectedIndicators] = useState("ma,bb,vol,macd,rsi");
  const [selectedPeriod, setSelectedPeriod] = useState("1y");
  const [selectedInterval, setSelectedInterval] = useState("1d");

  // Stochastic Valuation State
  const [historicalReports, setHistoricalReports] = useState([]);
  const [selectedReportFilename, setSelectedReportFilename] = useState("");
  const [loadedReport, setLoadedReport] = useState(null);
  const [valuating, setValuating] = useState(false);
  const [activeStats, setActiveStats] = useState(null);

  // Wall Street AI Copilot State
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Strategy Backtesting State
  const [selectedStrategy, setSelectedStrategy] = useState("SMA_Crossover");
  const [backtestPeriod, setBacktestPeriod] = useState("1y");
  const [paramFast, setParamFast] = useState(20);
  const [paramSlow, setParamSlow] = useState(50);
  const [backtestResult, setBacktestResult] = useState(null);
  const [backtesting, setBacktesting] = useState(false);

  // Sync to local OpenD API & Watchlist Quotes
  function syncQuantData() {
    setLoading(true);
    
    // Check Connection status
    fetch("/api/connection-status")
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          setConnStatus({ futu_opend: res.futu_opend, message: res.message });
        }
      })
      .catch(() => setConnStatus({ futu_opend: false, message: "Futu OpenD Offline" }));

    // Fetch positions
    fetch("/api/positions")
      .then(r => r.json())
      .then(res => {
        if (res.success && res.data && res.data.length > 0) {
          setPositions(res.data);
        } else {
          setPositions([
            { code: "US.AMAT", stock_name: "Applied Materials", qty: 80, cost_price: 395.00, nominal_price: 435.44, market_val: 34835.20, pl_ratio: 0.1023, pl_val: 3235.20 },
            { code: "US.TSLA", stock_name: "Tesla Inc", qty: 100, cost_price: 387.25, nominal_price: 389.37, market_val: 38937.00, pl_ratio: 0.0055, pl_val: 212.00 },
            { code: "US.NVDA", stock_name: "NVIDIA Corp", qty: 250, cost_price: 850.10, nominal_price: 890.52, market_val: 222630.00, pl_ratio: 0.0475, pl_val: 10105.00 }
          ]);
        }
      })
      .catch(() => {
        setPositions([
          { code: "US.AMAT", stock_name: "Applied Materials", qty: 80, cost_price: 395.00, nominal_price: 435.44, market_val: 34835.20, pl_ratio: 0.1023, pl_val: 3235.20 },
          { code: "US.TSLA", stock_name: "Tesla Inc", qty: 100, cost_price: 387.25, nominal_price: 389.37, market_val: 38937.00, pl_ratio: 0.0055, pl_val: 212.00 },
          { code: "US.NVDA", stock_name: "NVIDIA Corp", qty: 250, cost_price: 850.10, nominal_price: 890.52, market_val: 222630.00, pl_ratio: 0.0475, pl_val: 10105.00 }
        ]);
      })
      .finally(() => setLoading(false));

    // Fetch account stats
    fetch("/api/account")
      .then(r => r.json())
      .then(res => {
        if (res.success && res.data && res.data.length > 0) {
          setAccountInfo(res.data[0]);
        } else {
          setAccountInfo({
            power_balance: 154020.50,
            cash_balance: 120500.00,
            market_val: 296402.20,
            total_assets: 416902.20
          });
        }
      })
      .catch(() => {
        setAccountInfo({
          power_balance: 154020.50,
          cash_balance: 120500.00,
          market_val: 296402.20,
          total_assets: 416902.20
        });
      });

    // Fetch daily orders
    fetch("/api/orders")
      .then(r => r.json())
      .then(res => {
        if (res.success && res.data) {
          setOrders(res.data);
        } else {
          setOrders([
            { code: "US.AMAT", order_side: "BUY", price: 395.00, qty: 80, order_status: "FILLED_ALL", create_time: "2026-05-09 10:14:22" },
            { code: "US.TSLA", order_side: "BUY", price: 385.00, qty: 20, order_status: "FILLED_ALL", create_time: "2026-05-08 09:30:12" }
          ]);
        }
      })
      .catch(() => {
        setOrders([
          { code: "US.AMAT", order_side: "BUY", price: 395.00, qty: 80, order_status: "FILLED_ALL", create_time: "2026-05-09 10:14:22" },
          { code: "US.TSLA", order_side: "BUY", price: 385.00, qty: 20, order_status: "FILLED_ALL", create_time: "2026-05-08 09:30:12" }
        ]);
      });

    fetchWatchlist();
  }

  // Watchlist core interactions
  function fetchWatchlist() {
    setWatchlistLoading(true);
    fetch("/api/watchlist")
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          setWatchlist(res.data);
        }
      })
      .catch(err => console.error("Watchlist fetch fail:", err))
      .finally(() => setWatchlistLoading(false));
  }

  function addToWatchlist() {
    if (!newWatchTicker.trim()) return;
    const ticker = newWatchTicker.trim().toUpperCase();
    
    // Clear input optimistically for instant responsive visual feedback
    setNewWatchTicker("");
    
    fetch(`/api/watchlist?ticker=${ticker}`, { method: "POST" })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          fetchWatchlist();
        }
      })
      .catch(err => {
        console.error("Watchlist add fail:", err);
        // Restore input on failure
        setNewWatchTicker(ticker);
      });
  }

  function removeFromWatchlist(e, ticker) {
    e.stopPropagation();
    fetch(`/api/watchlist?ticker=${ticker}`, { method: "DELETE" })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          fetchWatchlist();
        }
      })
      .catch(err => console.error("Watchlist delete fail:", err));
  }

  // Historical Valuation Reports
  function fetchHistoricalReports(ticker) {
    fetch(`/api/finance-analysis/reports?ticker=${ticker}`)
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          setHistoricalReports(res.data);
          if (res.data.length > 0) {
            loadReportContent(res.data[0].filename);
          } else {
            setLoadedReport(null);
          }
        }
      })
      .catch(err => console.error("Historical reports fetch fail:", err));
  }

  function loadReportContent(filename) {
    setSelectedReportFilename(filename);
    fetch(`/api/finance-analysis/report-content?filename=${filename}`)
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          setLoadedReport(res.content);
        }
      })
      .catch(err => console.error("Report content load fail:", err));
  }

  // Dynamic Valuation Trigger
  function runValuation() {
    setValuating(true);
    setLoadedReport(null);
    fetch("/api/finance-analysis/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: activeChartTicker })
    })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          setLoadedReport(res.markdown);
          if (res.stats) {
            setActiveStats(res.stats);
          }
          fetchHistoricalReports(activeChartTicker);
        } else {
          alert("❌ Valuation failed. Please verify ticker code.");
        }
      })
      .catch(() => alert("❌ Connect error: standalone core offline."))
      .finally(() => setValuating(false));
  }

  // Wall Street AI Copilot Chat Trigger
  function sendChatMessage() {
    if (!chatInput.trim() || chatLoading) return;
    const userMsg = { role: "user", content: chatInput };
    const newHistory = [...chatHistory, userMsg];
    setChatHistory(newHistory);
    setChatInput("");
    setChatLoading(true);
    
    fetch("/api/chat-copilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: activeChartTicker, messages: newHistory })
    })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          setChatHistory([...newHistory, { role: "assistant", content: res.content }]);
        } else {
          setChatHistory([...newHistory, { role: "assistant", content: "❌ 系統呼叫失敗，請稍後再試。" }]);
        }
      })
      .catch(() => {
        setChatHistory([...newHistory, { role: "assistant", content: "❌ 無法與分析伺服器連線。" }]);
      })
      .finally(() => {
        setChatLoading(false);
      });
  }

  // Vectorized Backtesting Trigger
  function runBacktest() {
    setBacktesting(true);
    fetch("/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker: activeChartTicker,
        strategy: selectedStrategy,
        param_fast: parseFloat(paramFast),
        param_slow: parseFloat(paramSlow),
        period: backtestPeriod
      })
    })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          setBacktestResult(res);
        } else {
          alert("❌ Backtest failed: " + (res.detail || "Error"));
        }
      })
      .catch(() => alert("❌ Backtest connect error."))
      .finally(() => setBacktesting(false));
  }

  // Lifecycle Initialization
  useEffect(() => {
    syncQuantData();
    fetchHistoricalReports(activeChartTicker);
  }, []);

  // Update active ticker & load corresponding reports
  function handleSelectTicker(symbol) {
    const cleanSym = symbol.replace("US.", "").replace("HK.", "");
    setActiveChartTicker(cleanSym);
    fetchHistoricalReports(cleanSym);
    setChatHistory([]);
    setActiveStats(null);
    setBacktestResult(null);
  }

  // Markdown renderer
  function renderMarkdown(md) {
    if (!md) return "";
    try {
      return { __html: marked.parse(md) };
    } catch (e) {
      return { __html: `<p class="text-rose-400">Failed to render report: ${e.message}</p>` };
    }
  }

  // ─── PREMIUM SVG DATA VISUALIZATIONS ───

  function renderRadarSVG(stats) {
    if (!stats) return null;
    
    const valUpside = stats.fcf_model ? stats.fcf_model.upside_pct : 0;
    const valueVal = Math.min(100, Math.max(15, valUpside + 50));
    
    const growthRate = stats.est_growth_g1 || 0.10;
    const growthVal = Math.min(100, Math.max(15, growthRate * 400));
    
    const deRatio = stats.debt_equity || 50;
    const safetyVal = Math.min(100, Math.max(15, 100 - (deRatio / 3)));
    
    const roeRatio = stats.roe || 0.15;
    const efficiencyVal = Math.min(100, Math.max(15, roeRatio * 300));
    
    const betaRatio = stats.beta || 1.0;
    const momentumVal = Math.min(100, Math.max(15, 100 - Math.abs(1 - betaRatio) * 40));

    const cx = 110;
    const cy = 110;
    const r = 70;
    
    const angles = [
      -Math.PI / 2,
      -Math.PI / 2 + (2 * Math.PI / 5),
      -Math.PI / 2 + (4 * Math.PI / 5),
      -Math.PI / 2 + (6 * Math.PI / 5),
      -Math.PI / 2 + (8 * Math.PI / 5),
    ];

    const labels = ["成長性", "獲利效率", "波動抗性", "債務安全", "估值優勢"];
    const values = [growthVal, efficiencyVal, momentumVal, safetyVal, valueVal];

    const getPoint = (angle, valPct) => {
      const radius = (valPct / 100) * r;
      return {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle)
      };
    };

    const grids = [20, 40, 60, 80, 100];
    const points = angles.map((angle, i) => getPoint(angle, values[i]));
    const pointsStr = points.map(p => `${p.x},${p.y}`).join(" ");

    return (
      <svg className="w-[180px] h-[180px]" viewBox="0 0 220 220">
        <defs>
          <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#047857" stopOpacity="0.0" />
          </radialGradient>
        </defs>

        {grids.map((g, idx) => {
          const gridPoints = angles.map(angle => getPoint(angle, g));
          const gridPointsStr = gridPoints.map(p => `${p.x},${p.y}`).join(" ");
          return (
            <polygon 
              key={idx} 
              points={gridPointsStr} 
              fill="none" 
              stroke="rgba(255, 255, 255, 0.05)" 
              strokeWidth="1" 
            />
          );
        })}

        {angles.map((angle, i) => {
          const outer = getPoint(angle, 100);
          return (
            <line 
              key={i} 
              x1={cx} 
              y1={cy} 
              x2={outer.x} 
              y2={outer.y} 
              stroke="rgba(255, 255, 255, 0.08)" 
              strokeWidth="1" 
              strokeDasharray="2,2"
            />
          );
        })}

        <polygon 
          points={pointsStr} 
          fill="url(#radarGlow)" 
          stroke="#10b981" 
          strokeWidth="2"
        />

        {points.map((p, i) => (
          <circle 
            key={i} 
            cx={p.x} 
            cy={p.y} 
            r="3.5" 
            fill="#10b981" 
            stroke="#04040a" 
            strokeWidth="1.5" 
          />
        ))}

        {angles.map((angle, i) => {
          const outer = getPoint(angle, 120);
          let textAnchor = "middle";
          if (outer.x > cx + 10) textAnchor = "start";
          if (outer.x < cx - 10) textAnchor = "end";
          return (
            <text 
              key={i} 
              x={outer.x} 
              y={outer.y + 4} 
              fill="rgba(255, 255, 255, 0.6)" 
              fontSize="10" 
              fontFamily="monospace"
              fontWeight="bold"
              textAnchor={textAnchor}
            >
              {labels[i]}
            </text>
          );
        })}
      </svg>
    );
  }

  function renderDistributionSVG(stats) {
    if (!stats || !stats.fcf_model || !stats.fcf_model.distribution) return null;
    
    const dist = stats.fcf_model.distribution;
    const counts = dist.map(d => d.count);
    const maxCount = Math.max(...counts, 1);
    
    const width = 220;
    const height = 110;
    const padding = 15;
    
    const scaleY = (count) => {
      const graphHeight = height - padding * 2;
      return height - padding - (count / maxCount) * graphHeight;
    };
    
    const scaleX = (idx) => {
      const graphWidth = width - padding * 2;
      return padding + (idx / (dist.length - 1)) * graphWidth;
    };
    
    const points = dist.map((d, i) => ({
      x: scaleX(i),
      y: scaleY(d.count)
    }));
    
    let pathStr = `M ${points[0].x} ${height - padding} `;
    points.forEach(p => {
      pathStr += `L ${p.x} ${p.y} `;
    });
    pathStr += `L ${points[points.length - 1].x} ${height - padding} Z`;
    
    let lineStr = `M ${points[0].x} ${points[0].y} `;
    points.forEach(p => {
      lineStr += `L ${p.x} ${p.y} `;
    });

    const currPrice = stats.current_price || 100;
    const meanVal = stats.fcf_model.mean || 110;
    const p25Val = stats.fcf_model.p25 || 85;
    
    const minBin = dist[0].bin_start;
    const maxBin = dist[dist.length - 1].bin_end;
    const binRange = maxBin - minBin;
    
    const getXOfVal = (val) => {
      const pct = (val - minBin) / binRange;
      const graphWidth = width - padding * 2;
      return padding + Math.min(1, Math.max(0, pct)) * graphWidth;
    };

    const curX = getXOfVal(currPrice);
    const meanX = getXOfVal(meanVal);
    const p25X = getXOfVal(p25Val);

    return (
      <div className="flex flex-col items-center w-full">
        <svg className="w-[180px] h-[110px]" viewBox="0 0 220 110">
          <defs>
            <linearGradient id="distGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#0891b2" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          <path d={pathStr} fill="url(#distGrad)" />
          <path d={lineStr} fill="none" stroke="#06b6d4" strokeWidth="2" />
          
          <line 
            x1={padding} 
            y1={height - padding} 
            x2={width - padding} 
            y2={height - padding} 
            stroke="rgba(255,255,255,0.15)" 
            strokeWidth="1" 
          />

          {/* Current Price Line */}
          <line 
            x1={curX} 
            y1={padding} 
            x2={curX} 
            y2={height - padding} 
            stroke="#fbbf24" 
            strokeWidth="1.5" 
            strokeDasharray="2,2" 
          />
          
          {/* Expected Mean Line */}
          <line 
            x1={meanX} 
            y1={padding} 
            x2={meanX} 
            y2={height - padding} 
            stroke="#34d399" 
            strokeWidth="1.5" 
            strokeDasharray="2,2" 
          />

          {/* P25 Safety Line */}
          <line 
            x1={p25X} 
            y1={padding} 
            x2={p25X} 
            y2={height - padding} 
            stroke="#f87171" 
            strokeWidth="1.5" 
            strokeDasharray="2,2" 
          />
        </svg>
        
        <div className="grid grid-cols-3 gap-1 text-[8px] font-mono mt-1.5 w-full text-center">
          <div className="flex flex-col items-center">
            <span className="text-red-400 font-bold">P25 支撐</span>
            <span className="text-slate-400 mt-0.5">${p25Val}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-amber-400 font-bold">現價</span>
            <span className="text-slate-400 mt-0.5">${currPrice}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-emerald-400 font-bold">期望估值</span>
            <span className="text-slate-400 mt-0.5">${meanVal}</span>
          </div>
        </div>
      </div>
    );
  }

  function renderEquityCurveSVG(res) {
    if (!res || !res.equity_curve || res.equity_curve.length === 0) return null;
    
    const curve = res.equity_curve;
    const vals = curve.map(c => c.value);
    const maxVal = Math.max(...vals, 100000);
    const minVal = Math.min(...vals, 80000);
    const valRange = maxVal - minVal || 1;
    
    const width = 480;
    const height = 110;
    const padding = 15;
    
    const scaleY = (val) => {
      const graphHeight = height - padding * 2;
      return height - padding - ((val - minVal) / valRange) * graphHeight;
    };
    
    const scaleX = (idx) => {
      const graphWidth = width - padding * 2;
      return padding + (idx / (curve.length - 1)) * graphWidth;
    };
    
    let areaPointsStr = `M ${padding} ${height - padding} `;
    curve.forEach((c, i) => {
      areaPointsStr += `L ${scaleX(i)} ${scaleY(c.value)} `;
    });
    areaPointsStr += `L ${scaleX(curve.length - 1)} ${height - padding} Z`;
    
    let linePathStr = `M ${scaleX(0)} ${scaleY(curve[0].value)} `;
    curve.forEach((c, i) => {
      if (i > 0) linePathStr += `L ${scaleX(i)} ${scaleY(c.value)} `;
    });

    return (
      <svg className="w-full h-[110px]" viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <linearGradient id="curveGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        <path d={areaPointsStr} fill="url(#curveGrad)" />
        <path d={linePathStr} fill="none" stroke="#10b981" strokeWidth="2" />
        
        <line 
          x1={padding} 
          y1={height - padding} 
          x2={width - padding} 
          y2={height - padding} 
          stroke="rgba(255,255,255,0.08)" 
          strokeWidth="1" 
        />
        
        <text x={padding} y={padding + 5} fill="rgba(255,255,255,0.4)" fontSize="8" fontFamily="monospace">
          ${maxVal.toLocaleString(undefined, {maximumFractionDigits: 0})}
        </text>
        <text x={padding} y={height - padding - 2} fill="rgba(255,255,255,0.4)" fontSize="8" fontFamily="monospace">
          ${minVal.toLocaleString(undefined, {maximumFractionDigits: 0})}
        </text>
      </svg>
    );
  }

  // Global aggregate metrics
  const totalMarketVal = positions.reduce((acc, p) => acc + p.market_val, 0);
  const totalPL = positions.reduce((acc, p) => acc + p.pl_val, 0);
  const totalReturnPct = totalMarketVal > 0 ? (totalPL / (totalMarketVal - totalPL)) * 100 : 0;

  return (
    <div className="min-h-screen bg-[#04040a] flex flex-col font-sans select-none pb-12 text-slate-200">
      {/* 🔮 Glassmorphic Ambient Orbs */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-10 right-1/4 w-[500px] h-[500px] bg-blue-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* ─────────────────── TOP PREMIUM LOGO HEADER ─────────────────── */}
      <header className="border-b border-white/[0.04] bg-[#070712]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-tr from-emerald-500/20 to-teal-500/10 rounded-xl border border-emerald-500/25">
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-widest text-white uppercase font-mono flex items-center gap-2">
                UNIFIED QUANT & FINANCE STANDALONE TERMINAL
              </h1>
              <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mt-0.5">
                Dynamic Monte CarloDCF & Live Portfolio Workspace
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-[10px] font-mono uppercase tracking-wider ${
              connStatus.futu_opend ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400" : "bg-amber-500/5 border-amber-500/20 text-amber-400"
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${connStatus.futu_opend ? "bg-emerald-400 animate-pulse" : "bg-amber-400 animate-pulse"}`}></span>
              {connStatus.futu_opend ? "OpenD Link Active" : "yFinance Fallback Engine"}
            </div>

            <button 
              onClick={() => setCopilotOpen(!copilotOpen)}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 active:scale-95 text-xs font-mono font-bold text-emerald-400 rounded-xl transition-all cursor-pointer"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              AI COPILOT
            </button>

            <button 
              onClick={syncQuantData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white/[0.03] border border-white/[0.07] hover:bg-white/[0.07] hover:border-white/[0.12] active:scale-95 text-xs font-mono font-bold text-white rounded-xl transition-all cursor-pointer"
            >
              <svg className={`w-3.5 h-3.5 text-emerald-400 ${loading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3" />
              </svg>
              REFRESH
            </button>
          </div>
        </div>
      </header>

      {/* ─────────────────── UNIFIED THREE-COLUMN trading COCKPIT ─────────────────── */}
      <main className="max-w-[1600px] mx-auto px-6 mt-6 flex-1 w-full grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        
        {/* ─── COLUMN 1: PORTFOLIO & WATCHLIST (LEFT) ─── */}
        <div className="xl:col-span-3 flex flex-col gap-6">
          {/* Account Metrics Summary */}
          {accountInfo && (
            <div className="bg-[#0b0b14]/40 border border-white/[0.05] rounded-2xl p-5 backdrop-blur-md flex flex-col gap-4">
              <div className="flex justify-between items-center border-b border-white/[0.04] pb-2">
                <span className="text-[10px] text-slate-400 font-mono uppercase tracking-widest">Total Valuation</span>
                <span className="text-[10px] bg-emerald-400/10 text-emerald-400 px-1.5 py-0.5 rounded font-mono">SIM</span>
              </div>
              <div className="flex justify-between items-baseline">
                <span className="text-2xl font-black font-mono tracking-tight text-white">
                  ${accountInfo.total_assets.toLocaleString(undefined, {minimumFractionDigits: 2})}
                </span>
                <span className={`text-xs font-mono font-bold ${totalPL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {totalPL >= 0 ? "+" : ""}{totalReturnPct.toFixed(2)}%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-white/[0.03]">
                <div className="flex flex-col">
                  <span className="text-[9px] text-slate-500 uppercase tracking-wider font-mono">Cash Balance</span>
                  <span className="font-mono text-slate-200 mt-0.5">${accountInfo.cash_balance.toLocaleString()}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[9px] text-slate-500 uppercase tracking-wider font-mono">Buying Power</span>
                  <span className="font-mono text-emerald-400 mt-0.5">${accountInfo.power_balance.toLocaleString()}</span>
                </div>
              </div>
            </div>
          )}

          {/* Moomoo Positions list */}
          <div className="border border-white/[0.05] bg-[#0b0b14]/20 backdrop-blur-md rounded-2xl overflow-hidden shadow-xl">
            <div className="px-5 py-4 border-b border-white/[0.05] flex justify-between items-center bg-white/[0.01]">
              <div>
                <h3 className="text-xs font-extrabold text-emerald-400 uppercase tracking-widest font-mono">Portfolio Holdings</h3>
                <p className="text-[9px] text-slate-500 mt-0.5 font-mono">Click rows to view charts</p>
              </div>
              <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs font-mono">
                <thead className="border-b border-white/[0.05] text-slate-400 text-[9px] uppercase bg-black/20">
                  <tr>
                    <th className="py-2.5 px-4">Ticker</th>
                    <th className="py-2.5 px-2 text-right">Price</th>
                    <th className="py-2.5 px-4 text-right">P/L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {positions.map((pos, idx) => {
                    const profitPct = (pos.pl_ratio * 100).toFixed(2);
                    const isProfit = pos.pl_ratio >= 0;
                    const symbol = pos.code.replace("US.", "").replace("HK.", "");
                    const isCurrent = symbol === activeChartTicker;
                    return (
                      <tr 
                        key={idx} 
                        onClick={() => handleSelectTicker(pos.code)} 
                        className={`hover:bg-white/[0.02] cursor-pointer transition-colors ${
                          isCurrent ? "bg-emerald-500/5 text-emerald-400 border-l-2 border-emerald-400" : ""
                        }`}
                      >
                        <td className="py-2.5 px-4 font-bold">
                          <div className="flex flex-col">
                            <span className={`text-xs ${isCurrent ? "text-emerald-400" : "text-white"}`}>{symbol}</span>
                            <span className="text-[8px] text-slate-500 font-sans truncate max-w-[110px]">{pos.stock_name}</span>
                          </div>
                        </td>
                        <td className="py-2.5 px-2 text-right text-slate-300 font-medium">${pos.nominal_price.toFixed(2)}</td>
                        <td className={`py-2.5 px-4 text-right font-bold ${isProfit ? "text-emerald-400" : "text-rose-400"}`}>
                          {isProfit ? "+" : ""}{profitPct}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* WATCHLIST MANAGER */}
          <div className="border border-white/[0.05] bg-[#0b0b14]/20 backdrop-blur-md rounded-2xl overflow-hidden shadow-xl flex flex-col">
            <div className="px-5 py-4 border-b border-white/[0.05] flex justify-between items-center bg-white/[0.01]">
              <div>
                <h3 className="text-xs font-extrabold text-emerald-400 uppercase tracking-widest font-mono">Realtime Watchlist</h3>
                <p className="text-[9px] text-slate-500 mt-0.5 font-mono">Managed quotes via yfinance</p>
              </div>
              {watchlistLoading ? (
                <div className="w-3.5 h-3.5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <svg className="w-4 h-4 text-amber-400 fill-amber-400/25" fill="currentColor" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.961 0 1.36 1.243.577 1.735l-3.969 2.887a1 1 0 00-.364 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.969-2.887a1 1 0 00-1.176 0l-3.969 2.887c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118L2.98 12.026c-.783-.492-.384-1.735.577-1.735h4.907a1 1 0 00.95-.69l1.519-4.674z" />
                </svg>
              )}
            </div>

            {/* Add to Watchlist controls */}
            <div className="p-3 border-b border-white/[0.04] bg-black/10 flex items-center gap-2">
              <input 
                type="text"
                placeholder="ADD TICKER (e.g. MSTR)"
                value={newWatchTicker}
                onChange={e => setNewWatchTicker(e.target.value.toUpperCase())}
                onKeyDown={e => { if (e.key === "Enter") addToWatchlist(); }}
                className="flex-1 font-mono text-[10px] bg-black/40 border border-white/[0.07] focus:border-emerald-500 rounded-lg px-2.5 py-1.5 text-white focus:outline-none transition-colors"
              />
              <button 
                type="button"
                onClick={addToWatchlist}
                className="p-1.5 bg-emerald-500/10 hover:bg-emerald-500/25 border border-emerald-500/20 hover:border-emerald-500/35 rounded-lg text-emerald-400 transition-all cursor-pointer"
              >
                <svg className="w-4 h-4 text-emerald-400 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>

            {/* Watchlist Table */}
            <div className="max-h-[280px] overflow-y-auto">
              <table className="w-full text-left border-collapse text-xs font-mono">
                <tbody className="divide-y divide-white/[0.03]">
                  {watchlist.map((item, idx) => {
                    const isProfit = item.change_pct >= 0;
                    const isCurrent = item.symbol === activeChartTicker;
                    return (
                      <tr 
                        key={idx} 
                        onClick={() => handleSelectTicker(item.symbol)}
                        className={`hover:bg-white/[0.02] cursor-pointer transition-colors ${
                          isCurrent ? "bg-emerald-500/5 text-emerald-400 border-l-2 border-emerald-400" : ""
                        }`}
                      >
                        <td className="py-2.5 px-4 font-extrabold text-white">{item.symbol}</td>
                        <td className="py-2.5 px-2 text-right text-slate-300 font-medium">
                          {item.price > 0 ? `$${item.price.toFixed(2)}` : "fetching..."}
                        </td>
                        <td className={`py-2.5 px-2 text-right font-bold ${isProfit ? "text-emerald-400" : "text-rose-400"}`}>
                          {item.price > 0 ? `${isProfit ? "+" : ""}${item.change_pct.toFixed(2)}%` : "-"}
                        </td>
                        <td className="py-2.5 px-3 text-center" onClick={e => e.stopPropagation()}>
                          <button 
                            onClick={(e) => removeFromWatchlist(e, item.symbol)}
                            className="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-all cursor-pointer"
                            title="Remove from Watchlist"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {watchlist.length === 0 && (
                    <tr>
                      <td colSpan="4" className="py-8 text-center text-slate-500 text-[10px] font-mono uppercase">
                        Watchlist is Empty
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ─── COLUMN 2: TECHNICAL CHARTS & TRANSACTION BOOK (CENTER) ─── */}
        <div className="xl:col-span-5 flex flex-col gap-6">
          {/* Live Chart Header Controls */}
          <div className="bg-[#0b0b14]/30 border border-white/[0.05] rounded-2xl p-4 flex flex-col gap-3.5 backdrop-blur-md shadow-lg">
            {/* Top row: Active Ticker & Period Buttons */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-white/[0.03] pb-3">
              <div className="flex items-center gap-3">
                <span className="p-1.5 bg-emerald-500/15 text-emerald-400 rounded-lg text-[10px] font-bold font-mono">ACTIVE TICKET</span>
                <span className="text-base font-black font-mono text-white tracking-wider">{activeChartTicker}</span>
              </div>
              
              {/* Period Selectors */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[9px] font-mono text-slate-500 uppercase mr-1 tracking-wider">PERIOD:</span>
                {["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"].map(p => (
                  <button
                    key={p}
                    onClick={() => setSelectedPeriod(p)}
                    className={`px-2 py-0.5 text-[9px] font-bold font-mono border rounded-lg cursor-pointer transition-all uppercase ${
                      selectedPeriod === p ? "bg-emerald-500 border-transparent text-black font-black" : "bg-transparent border-white/[0.05] text-slate-400 hover:text-white"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Bottom row: Interval & Indicator Selectors */}
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              {/* Interval Selectors */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[9px] font-mono text-slate-500 uppercase mr-1 tracking-wider">INTERVAL:</span>
                {["1d", "1wk", "1mo"].map(i => {
                  const displayMap = { "1d": "Daily", "1wk": "Weekly", "1mo": "Monthly" };
                  return (
                    <button
                      key={i}
                      onClick={() => setSelectedInterval(i)}
                      className={`px-2.5 py-0.5 text-[9px] font-bold font-mono border rounded-lg cursor-pointer transition-all uppercase ${
                        selectedInterval === i ? "bg-emerald-500 border-transparent text-black font-black" : "bg-transparent border-white/[0.05] text-slate-400 hover:text-white"
                      }`}
                    >
                      {displayMap[i]}
                    </button>
                  );
                })}
              </div>

              {/* Indicator Selectors */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[9px] font-mono text-slate-500 uppercase mr-1 tracking-wider">INDICATORS:</span>
                {["ma", "bb", "vol", "macd", "rsi"].map(ind => {
                  const isSelected = selectedIndicators.split(",").includes(ind);
                  return (
                    <button
                      key={ind}
                      onClick={() => {
                        let list = selectedIndicators.split(",").filter(x => x);
                        if (list.includes(ind)) {
                          list = list.filter(x => x !== ind);
                        } else {
                          list.push(ind);
                        }
                        setSelectedIndicators(list.join(","));
                      }}
                      className={`px-2 py-0.5 text-[9px] font-bold font-mono border rounded-lg cursor-pointer transition-all uppercase ${
                        isSelected ? "bg-emerald-500 border-transparent text-black font-black" : "bg-transparent border-white/[0.08] text-slate-400 hover:text-white"
                      }`}
                    >
                      {ind}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Lightweight Candlestick Chart frame */}
          <div className="border border-white/[0.05] bg-[#07070a] rounded-2xl overflow-hidden shadow-2xl">
            <iframe 
              key={`${activeChartTicker}_${selectedPeriod}_${selectedInterval}_${selectedIndicators}`}
              src={`/api/chart?ticker=${activeChartTicker}&period=${selectedPeriod}&interval=${selectedInterval}&indicators=${selectedIndicators}`}
              className="w-full h-[480px] border-0"
              title="Interactive Candlestick Board"
            />
          </div>

          {/* 🏃 Vectorized Quant Backtesting Workspace */}
          <div className="border border-white/[0.05] bg-[#0b0b14]/30 backdrop-blur-md rounded-2xl overflow-hidden shadow-2xl flex flex-col p-5 gap-4">
            <div className="flex justify-between items-center border-b border-white/[0.04] pb-3">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></div>
                <h3 className="text-xs font-extrabold text-cyan-400 uppercase tracking-widest font-mono">
                  Vectorized Backtesting Workspace
                </h3>
              </div>
              <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider">Fast Simulation Engine</span>
            </div>

            {/* Backtest Controls Form */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] text-slate-400 uppercase">Strategy</label>
                <select
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                  className="bg-black/40 border border-white/[0.08] rounded-lg px-2.5 py-2 text-slate-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="SMA_Crossover">均線黃金交叉</option>
                  <option value="RSI_Strategy">RSI 超買超賣</option>
                  <option value="Bollinger_Strategy">布林通道反彈</option>
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] text-slate-400 uppercase">
                  {selectedStrategy === "SMA_Crossover" ? "Fast SMA" : selectedStrategy === "RSI_Strategy" ? "RSI Low" : "BB Period"}
                </label>
                <input
                  type="number"
                  value={paramFast}
                  onChange={(e) => setParamFast(e.target.value)}
                  className="bg-black/40 border border-white/[0.08] rounded-lg px-2.5 py-1.5 text-slate-300 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] text-slate-400 uppercase">
                  {selectedStrategy === "SMA_Crossover" ? "Slow SMA" : selectedStrategy === "RSI_Strategy" ? "RSI High" : "BB Dev"}
                </label>
                <input
                  type="number"
                  value={paramSlow}
                  onChange={(e) => setParamSlow(e.target.value)}
                  className="bg-black/40 border border-white/[0.08] rounded-lg px-2.5 py-1.5 text-slate-300 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] text-slate-400 uppercase">Period</label>
                <select
                  value={backtestPeriod}
                  onChange={(e) => setBacktestPeriod(e.target.value)}
                  className="bg-black/40 border border-white/[0.08] rounded-lg px-2.5 py-2 text-slate-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="1y">1 Year</option>
                  <option value="2y">2 Years</option>
                  <option value="5y">5 Years</option>
                  <option value="10y">10 Years</option>
                </select>
              </div>
            </div>

            <button
              onClick={runBacktest}
              disabled={backtesting}
              className={`w-full py-2.5 rounded-xl text-xs font-mono font-bold tracking-wider uppercase transition-all border ${
                backtesting 
                  ? "bg-amber-500/10 border-amber-500/25 text-amber-500 animate-pulse" 
                  : "bg-cyan-500 text-black hover:bg-cyan-400 border-transparent shadow-lg shadow-cyan-500/10 cursor-pointer"
              }`}
            >
              {backtesting ? "⚙️ Simulating Trades..." : "🏃 Run Backtest Simulation"}
            </button>

            {/* Backtest Results Area */}
            {backtestResult && (
              <div className="flex flex-col gap-4 border-t border-white/[0.04] pt-4">
                {/* Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="bg-black/30 border border-white/[0.03] p-3 rounded-xl flex flex-col items-center">
                    <span className="text-[8px] text-slate-500 uppercase tracking-wider font-mono">總報酬率</span>
                    <span className={`text-xs font-black font-mono mt-1 ${backtestResult.total_return >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {backtestResult.total_return >= 0 ? "+" : ""}{backtestResult.total_return}%
                    </span>
                  </div>
                  <div className="bg-black/30 border border-white/[0.03] p-3 rounded-xl flex flex-col items-center">
                    <span className="text-[8px] text-slate-500 uppercase tracking-wider font-mono">年化報酬率</span>
                    <span className="text-xs font-black font-mono text-slate-200 mt-1">
                      {backtestResult.annualized_return}%
                    </span>
                  </div>
                  <div className="bg-black/30 border border-white/[0.03] p-3 rounded-xl flex flex-col items-center">
                    <span className="text-[8px] text-slate-500 uppercase tracking-wider font-mono">最大回撤</span>
                    <span className="text-xs font-black font-mono text-rose-400 mt-1">
                      {backtestResult.max_drawdown}%
                    </span>
                  </div>
                  <div className="bg-black/30 border border-white/[0.03] p-3 rounded-xl flex flex-col items-center">
                    <span className="text-[8px] text-slate-500 uppercase tracking-wider font-mono">勝率</span>
                    <span className="text-xs font-black font-mono text-slate-200 mt-1">
                      {backtestResult.win_rate}%
                    </span>
                  </div>
                  <div className="bg-black/30 border border-white/[0.03] p-3 rounded-xl flex flex-col items-center col-span-2 md:col-span-1">
                    <span className="text-[8px] text-slate-500 uppercase tracking-wider font-mono">夏普比率</span>
                    <span className="text-xs font-black font-mono text-cyan-400 mt-1">
                      {backtestResult.sharpe_ratio}
                    </span>
                  </div>
                </div>

                {/* SVG Equity Curve */}
                <div className="bg-black/20 border border-white/[0.03] p-4 rounded-xl flex flex-col items-center">
                  <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider mb-2 w-full text-left">
                    📈 Portfolio Value Over Time
                  </span>
                  {renderEquityCurveSVG(backtestResult)}
                </div>
              </div>
            )}
          </div>

          {/* Orders log book */}
          <div className="border border-white/[0.05] bg-[#0b0b14]/20 backdrop-blur-md rounded-2xl overflow-hidden shadow-xl flex flex-col">
            <div className="px-5 py-3 border-b border-white/[0.05] flex justify-between items-center">
              <h3 className="text-xs font-extrabold text-emerald-400 uppercase tracking-widest font-mono">Daily Order Log Book</h3>
              <span className="text-[9px] text-slate-500 font-mono">TODAY</span>
            </div>
            <div className="divide-y divide-white/[0.03] max-h-[140px] overflow-y-auto">
              {orders.map((ord, idx) => {
                const isBuy = ord.order_side.toUpperCase() === "BUY";
                return (
                  <div key={idx} className="p-3.5 flex items-center justify-between hover:bg-white/[0.01] transition-colors text-[10px] font-mono">
                    <div className="flex items-center gap-3">
                      <span className="text-white font-extrabold">{ord.code.replace("US.", "")}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-black border ${
                        isBuy ? "bg-emerald-500/5 border-emerald-500/15 text-emerald-400" : "bg-rose-500/5 border-rose-500/15 text-rose-400"
                      }`}>{ord.order_side}</span>
                      <span className="text-slate-500 text-[8px]">{ord.create_time}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-slate-300 font-bold">{ord.qty} Shares @ ${ord.price.toFixed(2)}</span>
                      <span className="ml-3 text-emerald-400 font-bold">{ord.order_status}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ─── COLUMN 3: MONTE CARLO STOCHASTIC DCF VALUATION (RIGHT) ─── */}
        <div className="xl:col-span-4 flex flex-col gap-6">
          <div className="border border-white/[0.05] bg-[#0b0b14]/20 backdrop-blur-md rounded-2xl shadow-2xl overflow-hidden flex flex-col min-h-[720px]">
            
            {/* Header Conclave Control */}
            <div className="px-5 py-4 border-b border-white/[0.05] bg-white/[0.01] flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                  <h3 className="text-xs font-extrabold text-emerald-400 uppercase tracking-widest font-mono">
                    Stochastic Valuation Conclave
                  </h3>
                </div>
                <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider">10,000 Iterations</span>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2">
                <button
                  onClick={runValuation}
                  disabled={valuating}
                  className={`flex-1 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wider uppercase transition-all border ${
                    valuating 
                      ? "bg-amber-500/10 border-amber-500/25 text-amber-500 animate-pulse" 
                      : "bg-emerald-500 text-black hover:bg-emerald-400 border-transparent shadow-lg shadow-emerald-500/10 cursor-pointer"
                  }`}
                >
                  {valuating ? "⚙️ Calculating DCF Trails..." : "🏛️ Run Stochastic Audit"}
                </button>
              </div>

              {/* Historical Reports Dropdown */}
              {historicalReports.length > 0 && (
                <div className="flex items-center gap-2 pt-1 border-t border-white/[0.03]">
                  <label className="text-[9px] text-slate-400 font-mono uppercase">Reports Historical:</label>
                  <select
                    value={selectedReportFilename}
                    onChange={(e) => loadReportContent(e.target.value)}
                    className="flex-1 font-mono text-[10px] bg-black/40 border border-white/[0.08] rounded-lg px-2 py-1 text-slate-300 focus:outline-none focus:border-emerald-500"
                  >
                    {historicalReports.map((r, i) => (
                      <option key={i} value={r.filename}>
                        {r.datetime === "N/A" ? r.filename : r.datetime}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Generated / Loaded Report Render Window */}
            <div className="p-5 flex-1 flex flex-col bg-black/10 overflow-y-auto max-h-[600px]">
              {valuating ? (
                <div className="flex-1 flex flex-col items-center justify-center py-36 gap-6 text-center">
                  <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                  <div className="text-[9px] text-slate-400 font-mono animate-pulse uppercase tracking-widest leading-loose whitespace-pre-wrap max-w-xs">
                    {"FETCHING SEC BALANCE SHEET...\nCOMPUTING REVENUE TREND VECTORS...\nSIMULATING 10,000 WACC VARIABLES...\nCONVERGING DCF ENVELOPES..."}
                  </div>
                </div>
              ) : loadedReport ? (
                <div className="flex flex-col gap-6">
                  {/* Render Visualizations if activeStats exists */}
                  {activeStats && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 border-b border-white/[0.04] pb-6">
                      {/* PEG Valuation Rating Card */}
                      {activeStats.peg_ratio !== undefined && activeStats.peg_ratio !== null && (
                        <div className="col-span-1 md:col-span-2 bg-[#0b0b14]/40 border border-white/[0.05] rounded-xl p-4 flex items-center justify-between shadow-md backdrop-blur-md">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider font-bold">
                              市盈成長比 (PEG Ratio) 智能評級
                            </span>
                            <span className="text-xs text-white font-mono font-medium mt-1">
                              PEG 值：<span className="font-bold text-base text-cyan-400">{Number(activeStats.peg_ratio).toFixed(2)}</span>
                            </span>
                          </div>
                          
                          {/* Badge based on value */}
                          {(() => {
                            const peg = Number(activeStats.peg_ratio);
                            if (peg <= 0) {
                              return (
                                <span className="px-3 py-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-full text-[10px] font-bold font-mono uppercase animate-pulse">
                                  ⚠️ Negative Growth (低防禦)
                                </span>
                              );
                            } else if (peg < 1.0) {
                              return (
                                <span className="px-3 py-1.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 rounded-full text-[10px] font-bold font-mono uppercase tracking-wide shadow-[0_0_12px_rgba(16,185,129,0.15)] animate-pulse">
                                  💎 Undervalued (極佳安全邊際)
                                </span>
                              );
                            } else if (peg <= 1.5) {
                              return (
                                <span className="px-3 py-1.5 bg-amber-500/15 text-amber-400 border border-amber-500/25 rounded-full text-[10px] font-bold font-mono uppercase tracking-wide">
                                  ⚖️ Fair Value (估值合理)
                                </span>
                              );
                            } else {
                              return (
                                <span className="px-3 py-1.5 bg-rose-500/15 text-rose-400 border border-rose-500/25 rounded-full text-[10px] font-bold font-mono uppercase tracking-wide">
                                  🚨 Overpriced (成長溢價過高)
                                </span>
                              );
                            }
                          })()}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Styled Obsidian Markdown Content */}
                  <article 
                    className="prose prose-invert prose-emerald text-xs leading-relaxed max-w-none text-slate-300 font-mono"
                    dangerouslySetInnerHTML={renderMarkdown(loadedReport)}
                  />
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 text-xs py-44 gap-4">
                  <svg className="w-8 h-8 text-slate-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="8" r="7" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.21 13.89L7 23l5-3 5 3-1.21-9.12" />
                  </svg>
                  <div>
                    <p className="font-extrabold text-slate-400 uppercase tracking-wider font-mono">No Valuation Run Found</p>
                    <p className="text-[9px] text-slate-600 mt-1 uppercase max-w-xs leading-relaxed font-mono">
                      Click the "Run Stochastic Audit" button above to dynamically run a 10,000-iteration Monte Carlo valuation on {activeChartTicker}.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Obsidian synced status bar */}
            {loadedReport && (
              <div className="p-4 border-t border-white/[0.04] bg-[#070712]/50 text-[10px] font-mono flex items-center justify-between text-slate-400">
                <div className="flex items-center gap-1.5 text-emerald-400">
                  <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span>AUTO-SAVED TO OBSIDIAN WIKI</span>
                </div>
                <span className="text-[9px] text-slate-500">/Users/kennethlin/Github/@obsidian/finance</span>
              </div>
            )}

          </div>
        </div>

      </main>

      {/* ─────────────────── SLIDING AI COPILOT DRAWER (RIGHT) ─────────────────── */}
      <div className={`fixed top-0 right-0 h-full w-[450px] bg-[#070714]/95 backdrop-blur-xl border-l border-white/[0.08] shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-in-out ${
        copilotOpen ? "translate-x-0" : "translate-x-full"
      }`}>
        {/* Drawer Header */}
        <div className="p-5 border-b border-white/[0.06] flex items-center justify-between bg-black/20">
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></div>
            <div>
              <h3 className="text-sm font-black text-white font-mono tracking-wider uppercase">Wall Street Copilot Conclave</h3>
              <p className="text-[9px] text-slate-500 font-mono tracking-wider uppercase mt-0.5">Quant Helper • {activeChartTicker}</p>
            </div>
          </div>
          <button 
            onClick={() => setCopilotOpen(false)}
            className="p-1.5 hover:bg-white/[0.05] rounded-lg border border-transparent hover:border-white/[0.08] text-slate-400 hover:text-white transition-all cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Chat Transcript Panel */}
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4 font-mono text-xs">
          {chatHistory.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 py-20 gap-4">
              <div className="p-3 bg-emerald-500/5 rounded-2xl border border-emerald-500/10">
                <svg className="w-8 h-8 text-emerald-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <div>
                <p className="font-extrabold text-slate-400 uppercase tracking-wider">Quant AI Assistant Idle</p>
                <p className="text-[9px] text-slate-600 mt-1 max-w-[280px] leading-relaxed">
                  請在此向 AI 助理諮詢關於 {activeChartTicker} 的量化策略、財務評估或估值處方。
                </p>
              </div>
            </div>
          ) : (
            chatHistory.map((msg, i) => {
              const isUser = msg.role === "user";
              return (
                <div key={i} className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[90%] ${isUser ? "self-end" : "self-start"}`}>
                  <span className="text-[8px] text-slate-500 uppercase tracking-wider mb-1 px-1">{isUser ? "You" : "WallStreet AI"}</span>
                  <div className={`p-4 rounded-2xl border leading-relaxed text-[11px] font-sans ${
                    isUser 
                      ? "bg-emerald-500/5 border-emerald-500/15 text-slate-200 rounded-tr-none" 
                      : "bg-[#0b0b1a]/60 border-white/[0.04] text-slate-300 rounded-tl-none prose prose-invert prose-emerald max-w-none text-xs"
                  }`}>
                    {isUser ? (
                      msg.content
                    ) : (
                      <div dangerouslySetInnerHTML={renderMarkdown(msg.content)} />
                    )}
                  </div>
                </div>
              );
            })
          )}
          {chatLoading && (
            <div className="flex items-center gap-2 self-start bg-[#0b0b1a]/40 border border-white/[0.03] p-3 rounded-2xl rounded-tl-none">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: "0ms" }}></span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: "150ms" }}></span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: "300ms" }}></span>
            </div>
          )}
        </div>

        {/* Chat Input Panel */}
        <div className="p-4 border-t border-white/[0.06] bg-black/20 flex gap-2">
          <input 
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") sendChatMessage(); }}
            placeholder={`Ask about ${activeChartTicker} or quant metrics...`}
            className="flex-1 bg-black/40 border border-white/[0.08] focus:border-emerald-500/50 rounded-xl px-4 py-2.5 text-xs text-slate-300 focus:outline-none transition-all font-sans"
          />
          <button 
            onClick={sendChatMessage}
            disabled={chatLoading || !chatInput.trim()}
            className="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:bg-emerald-500/20 disabled:text-slate-500 text-black font-bold text-xs rounded-xl transition-all cursor-pointer"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
