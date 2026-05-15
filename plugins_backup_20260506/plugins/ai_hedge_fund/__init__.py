import os
import sys
import logging

# 動態添加本插件目錄到 sys.path，以便載入同目錄下的 tools.py
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

# 動態添加 ai-hedge-fund 專案的絕對路徑，使其模組可以被載入
HEDGE_FUND_PATH = "/Users/kennethlin/Github/ai-hedge-fund"
if HEDGE_FUND_PATH not in sys.path:
    sys.path.append(HEDGE_FUND_PATH)

import tools

logger = logging.getLogger(__name__)

def register(ctx):
    """
    註冊 ai_hedge_fund 插件工具。
    當 hermes-agent 啟動時，會自動調用此註冊方法。
    """
    ctx.register_tool(
        name="run_hedge_fund_analysis",
        toolset="finance",
        schema={
            "name": "run_hedge_fund_analysis",
            "description": "呼叫 AI 對沖基金決策系統，匯整多位投資大師（巴菲特、蒙格、情緒面、技術面等）的意見，生成詳細的買賣分析與部位分配建議。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要分析的股票美股代號列表，例如 ['AAPL', 'NVDA']"
                    },
                    "months_back": {
                        "type": "integer",
                        "default": 3,
                        "description": "分析所需的歷史數據回溯月份數，預設為 3 個月"
                    }
                },
                "required": ["tickers"]
            }
        },
        handler=lambda args, **kw: tools.run_hedge_fund_analysis(
            tickers=args.get("tickers"),
            months_back=args.get("months_back", 3)
        )
    )

    logger.info("AI Hedge Fund 插件已成功載入，並註冊 'run_hedge_fund_analysis' 工具。")
