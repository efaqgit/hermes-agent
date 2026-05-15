import json
import logging
from tools.registry import registry

logger = logging.getLogger(__name__)

def moomoo_get_account_info(env: str = "SIMULATE", market: str = "US", host: str = '127.0.0.1', port: int = 11111) -> str:
    """Get account info (balance, assets) from Moomoo."""
    try:
        from moomoo import OpenSecTradeContext, TrdEnv, TrdMarket
        trd_env = TrdEnv.SIMULATE if env.upper() == "SIMULATE" else TrdEnv.REAL
        trd_mkt = getattr(TrdMarket, market.upper(), TrdMarket.US)
        trd_ctx = OpenSecTradeContext(filter_trdmarket=trd_mkt, host=host, port=port)
        ret, data = trd_ctx.accinfo_query(trd_env=trd_env)
        trd_ctx.close()
        if ret == 0: return json.dumps({"success": True, "data": data.to_dict(orient="records")})
        return json.dumps({"success": False, "error": str(data)})
    except Exception as e: return json.dumps({"success": False, "error": str(e)})

def moomoo_get_positions(env: str = "SIMULATE", market: str = "US", host: str = '127.0.0.1', port: int = 11111) -> str:
    """List all current stock positions."""
    try:
        from moomoo import OpenSecTradeContext, TrdEnv, TrdMarket
        trd_env = TrdEnv.SIMULATE if env.upper() == "SIMULATE" else TrdEnv.REAL
        trd_mkt = getattr(TrdMarket, market.upper(), TrdMarket.US)
        trd_ctx = OpenSecTradeContext(filter_trdmarket=trd_mkt, host=host, port=port)
        ret, data = trd_ctx.position_list_query(trd_env=trd_env)
        trd_ctx.close()
        if ret == 0: return json.dumps({"success": True, "data": data.to_dict(orient="records")})
        return json.dumps({"success": False, "error": str(data)})
    except Exception as e: return json.dumps({"success": False, "error": str(e)})

def moomoo_get_orders(env: str = "SIMULATE", market: str = "US", host: str = '127.0.0.1', port: int = 11111) -> str:
    """List today's trade orders."""
    try:
        from moomoo import OpenSecTradeContext, TrdEnv, TrdMarket
        trd_env = TrdEnv.SIMULATE if env.upper() == "SIMULATE" else TrdEnv.REAL
        trd_mkt = getattr(TrdMarket, market.upper(), TrdMarket.US)
        trd_ctx = OpenSecTradeContext(filter_trdmarket=trd_mkt, host=host, port=port)
        ret, data = trd_ctx.order_list_query(trd_env=trd_env)
        trd_ctx.close()
        if ret == 0: return json.dumps({"success": True, "data": data.to_dict(orient="records")})
        return json.dumps({"success": False, "error": str(data)})
    except Exception as e: return json.dumps({"success": False, "error": str(e)})

# Core registration
registry.register(
    name="moomoo_get_account_info",
    toolset="finance",
    schema={
        "name": "moomoo_get_account_info",
        "description": "Get account balance and asset summary from Moomoo.",
        "parameters": {
            "type": "object",
            "properties": {
                "env": {"type": "string", "enum": ["REAL", "SIMULATE"], "default": "SIMULATE"},
                "market": {"type": "string", "enum": ["US", "HK", "CN"], "default": "US"}
            }
        }
    },
    handler=lambda args, **kw: moomoo_get_account_info(env=args.get("env", "SIMULATE"), market=args.get("market", "US"))
)

registry.register(
    name="moomoo_get_positions",
    toolset="finance",
    schema={
        "name": "moomoo_get_positions",
        "description": "List all current stock positions in your account.",
        "parameters": {
            "type": "object",
            "properties": {
                "env": {"type": "string", "enum": ["REAL", "SIMULATE"], "default": "SIMULATE"},
                "market": {"type": "string", "enum": ["US", "HK", "CN"], "default": "US"}
            }
        }
    },
    handler=lambda args, **kw: moomoo_get_positions(env=args.get("env", "SIMULATE"), market=args.get("market", "US"))
)

registry.register(
    name="moomoo_get_orders",
    toolset="finance",
    schema={
        "name": "moomoo_get_orders",
        "description": "Get list of today's trade orders from Moomoo.",
        "parameters": {
            "type": "object",
            "properties": {
                "env": {"type": "string", "enum": ["REAL", "SIMULATE"], "default": "SIMULATE"},
                "market": {"type": "string", "enum": ["US", "HK", "CN"], "default": "US"}
            }
        }
    },
    handler=lambda args, **kw: moomoo_get_orders(env=args.get("env", "SIMULATE"), market=args.get("market", "US"))
)
