import os
import sys
import logging
import json

# Add current plugin directory to sys.path to allow local imports
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

import tools

logger = logging.getLogger(__name__)

def register(ctx):
    # Register Account Info
    ctx.register_tool(
        name="moomoo_get_account_info",
        toolset="moomoo",
        schema={
            "name": "moomoo_get_account_info",
            "description": "Get account balance and asset summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "env": {"type": "string", "enum": ["REAL", "SIMULATE"], "default": "SIMULATE"},
                    "market": {"type": "string", "enum": ["US", "HK", "CN"], "default": "US"}
                }
            }
        },
        handler=lambda args, **kw: tools.moomoo_get_account_info(env=args.get("env", "SIMULATE"), market=args.get("market", "US"))
    )

    # Register Positions
    ctx.register_tool(
        name="moomoo_get_positions",
        toolset="moomoo",
        schema={
            "name": "moomoo_get_positions",
            "description": "List all stock positions in your account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "env": {"type": "string", "enum": ["REAL", "SIMULATE"], "default": "SIMULATE"},
                    "market": {"type": "string", "enum": ["US", "HK", "CN"], "default": "US"}
                }
            }
        },
        handler=lambda args, **kw: tools.moomoo_get_positions(env=args.get("env", "SIMULATE"), market=args.get("market", "US"))
    )
    
    logger.info("Moomoo Quant plugin loaded successfully with toolset 'moomoo'.")
