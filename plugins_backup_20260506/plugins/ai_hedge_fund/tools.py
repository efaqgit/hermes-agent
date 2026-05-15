import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def run_hedge_fund_analysis(tickers: list[str], months_back: int = 3) -> str:
    """
    呼叫 ai-hedge-fund 決策大腦，分析指定股票代號。
    
    Args:
        tickers: 股票代號清單。
        months_back: 分析歷史回溯月數。
        
    Returns:
        str: 格式化後的 Markdown 報告。
    """
    # 確保 Tickers 均為大寫
    tickers = [t.upper().strip() for t in tickers if t.strip()]
    if not tickers:
        return "❌ 錯誤：未提供有效的股票代號。"

    # 計算歷史開始與結束時間
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=months_back * 30)).strftime("%Y-%m-%d")

    # 構造虛擬投資組合數據結構
    portfolio = {
        "cash": 100000.0,  # 預設虛擬資本十萬美元
        "margin_requirement": 0.0,
        "margin_used": 0.0,
        "positions": {
            ticker: {
                "long": 0,
                "short": 0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
            for ticker in tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,
                "short": 0.0,
            }
            for ticker in tickers
        },
    }

    try:
        # 從 ai-hedge-fund 專案動態引入執行進入點
        from src.main import run_hedge_fund
    except ImportError as e:
        logger.error("無法匯入 run_hedge_fund，請確認路徑或 Poetry 環境依賴: %s", e)
        return "❌ 導入錯誤：無法尋找到 `ai-hedge-fund` 專案核心，請檢查路徑設定。"

    try:
        # 執行決策流 (LangGraph)
        logger.info("啟動 AI Hedge Fund 決策流，分析標的: %s，區間: %s 至 %s", tickers, start_date, end_date)
        result = run_hedge_fund(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            show_reasoning=True,
            model_name="gpt-4o-mini",
            model_provider="OpenAI"
        )
        
        # 提取結果
        decisions = result.get("decisions", {})
        analyst_signals = result.get("analyst_signals", {})

        if not decisions:
            return f"⚠ 分析完成，但未對 {', '.join(tickers)} 產生任何交易決策。"

        # Markdown 美化與排版
        output = []
        output.append("🏛️ **【AI 對沖基金決策報告】**")
        output.append(f"📅 **數據分析區間**：`{start_date}` 至 `{end_date}` (`-{months_back}M` 歷史回溯)")
        output.append("=" * 30 + "\n")

        for ticker in tickers:
            ticker_decision = decisions.get(ticker)
            if not ticker_decision:
                output.append(f"🔍 **股票**: `{ticker}` ── *（本輪未產出交易決策）*\n")
                continue

            action = ticker_decision.get("action", "HOLD").upper()
            quantity = ticker_decision.get("quantity", 0)
            reason = ticker_decision.get("reason", "無特定原因說明")

            # 決策動作 Emoji 視覺化
            if action == "BUY":
                action_str = "🟢 **買入 (BUY)**"
            elif action == "SELL":
                action_str = "🔴 **賣出 (SELL)**"
            else:
                action_str = "🟡 **觀望 (HOLD)**"

            output.append(f"📈 **分析標的**：`{ticker}`")
            output.append(f"📢 **最終決策**：{action_str}")
            if action in ["BUY", "SELL"]:
                output.append(f"💼 **建議數量**：`{quantity}` 股")
            output.append(f"💡 **決策原因**：\n> {reason}\n")

            # 整合各大師與分析模組的細部訊號
            output.append("🧑‍⚖️ **各大投資流派意見分佈**：")
            ticker_signals = analyst_signals.get(ticker, {})
            
            if ticker_signals:
                for analyst_name, signal_data in ticker_signals.items():
                    signal = signal_data.get("signal", "HOLD").upper()
                    analyst_reason = signal_data.get("reason", "無原因說明")
                    
                    # 簡化分析師名稱（美化）
                    clean_name = analyst_name.replace("_agent", "").replace("_", " ").title()
                    
                    # 分析師訊號標籤
                    sig_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
                    output.append(f"• {sig_emoji} **{clean_name}**: `{signal}`\n  *\"{analyst_reason}\"*")
            else:
                output.append("• *暫無細部分析師意見數據。*")
                
            output.append("\n" + "-" * 20 + "\n")

        # 加入專業投資免責聲明
        output.append("⚠️ **投資免責聲明**：")
        output.append("本報告由 AI 代理人模擬生成，僅作教育與學術研究用途，不構成任何真實投資建議。股市有風險，投資需謹慎。")

        return "\n".join(output)

    except Exception as e:
        logger.exception("執行 run_hedge_fund 失敗")
        return f"❌ 系統錯誤：在執行 AI 對沖基金分析時發生未預期的異常。\n詳細錯誤：`{str(e)}`"
