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

from . import tools

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
                    },
                    "model_name": {
                        "type": "string",
                        "default": "gemma-4-26B-A4B-it-MLX-4bit",
                        "description": "使用的模型名稱，預設為 'gemma-4-26B-A4B-it-MLX-4bit'。也可以是 'gpt-oss:120b' 等本地註冊模型"
                    },
                    "model_provider": {
                        "type": "string",
                        "default": "OpenAI",
                        "description": "模型提供商，預設為 'OpenAI'（支援自訂的本地 API 轉接器）"
                    }
                },
                "required": ["tickers"]
            }
        },
        handler=lambda args, **kw: tools.run_hedge_fund_analysis(
            tickers=args.get("tickers"),
            months_back=args.get("months_back", 3),
            model_name=args.get("model_name", "gemma-4-26B-A4B-it-MLX-4bit"),
            model_provider=args.get("model_provider", "OpenAI")
        )
    )

    logger.info("AI Hedge Fund 插件已成功載入，並註冊 'run_hedge_fund_analysis' 工具。")
