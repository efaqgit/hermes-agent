import json
import logging
import os
from typing import Optional, Dict, Any

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
        
        if ret == 0:
            return json.dumps({"success": True, "data": data.to_dict(orient="records")})
        return json.dumps({"success": False, "error": str(data)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

def moomoo_get_positions(env: str = "SIMULATE", market: str = "US", host: str = '127.0.0.1', port: int = 11111) -> str:
    """List all stock positions in the account."""
    try:
        from moomoo import OpenSecTradeContext, TrdEnv, TrdMarket
        trd_env = TrdEnv.SIMULATE if env.upper() == "SIMULATE" else TrdEnv.REAL
        trd_mkt = getattr(TrdMarket, market.upper(), TrdMarket.US)
        
        trd_ctx = OpenSecTradeContext(filter_trdmarket=trd_mkt, host=host, port=port)
        ret, data = trd_ctx.position_list_query(trd_env=trd_env)
        trd_ctx.close()
        
        if ret == 0:
            return json.dumps({"success": True, "data": data.to_dict(orient="records")})
        return json.dumps({"success": False, "error": str(data)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

def moomoo_get_orders(env: str = "SIMULATE", market: str = "US", host: str = '127.0.0.1', port: int = 11111) -> str:
    """List today's orders."""
    try:
        from moomoo import OpenSecTradeContext, TrdEnv, TrdMarket
        trd_env = TrdEnv.SIMULATE if env.upper() == "SIMULATE" else TrdEnv.REAL
        trd_mkt = getattr(TrdMarket, market.upper(), TrdMarket.US)
        
        trd_ctx = OpenSecTradeContext(filter_trdmarket=trd_mkt, host=host, port=port)
        ret, data = trd_ctx.order_list_query(trd_env=trd_env)
        trd_ctx.close()
        
        if ret == 0:
            return json.dumps({"success": True, "data": data.to_dict(orient="records")})
        return json.dumps({"success": False, "error": str(data)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
