"""FastAPI/Starlette Webserver exposing /api/health and Streamable HTTP MCP endpoint.

Contract:
- GET /api/health returns HTTP 200 with JSON status, or HTTP 503 if controller is unreachable.
- Streamable MCP endpoint mounted for remote demo portal integration.
"""

from __future__ import annotations

import argparse
import logging
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.config import get_config
from app.netris_client import NetrisClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("netris-mcp.webserver")

# Global client reference for health checks
_netris_client: NetrisClient | None = None


@asynccontextmanager
async def lifespan(app: Starlette):
    global _netris_client
    cfg = get_config()
    logger.info("Initialising Netris MCP Webserver with Controller: %s (Mode: %s)", cfg.netris_url, cfg.mode)
    _netris_client = NetrisClient(
        base_url=cfg.netris_url,
        username=cfg.netris_username,
        password=cfg.netris_password,
        verify_ssl=cfg.netris_verify_ssl,
    )
    try:
        await _netris_client.login()
    except Exception as e:
        logger.warning("Initial controller login failed during startup: %s", e)
    
    yield
    
    if _netris_client:
        await _netris_client.close()


async def health_endpoint(request) -> JSONResponse:
    """Demo Portal Health Contract: returns 200 OK or 503 Service Unavailable."""
    cfg = get_config()
    is_authenticated = False
    controller_reachable = False
    details = {}

    if _netris_client:
        try:
            # Query quick summary endpoint
            res = await _netris_client.get("/api/v2/sites")
            controller_reachable = True
            is_authenticated = True
            details["sites_count"] = len(res) if isinstance(res, list) else 0
        except Exception as e:
            logger.debug("Health probe check failed: %s", e)
            controller_reachable = False
            details["error"] = str(e)

    status_code = 200 if controller_reachable else 503
    payload = {
        "status": "healthy" if controller_reachable else "degraded",
        "service": "netris-mcp",
        "version": "0.2.0",
        "mode": cfg.mode,
        "tool_surface": cfg.tool_surface,
        "controller": {
            "url": cfg.netris_url,
            "reachable": controller_reachable,
            "authenticated": is_authenticated,
        },
        "details": details,
    }
    return JSONResponse(payload, status_code=status_code)


routes = [
    Route("/api/health", health_endpoint, methods=["GET"]),
]

app = Starlette(debug=False, routes=routes, lifespan=lifespan)


def main():
    parser = argparse.ArgumentParser(description="Netris MCP Server")
    parser.add_argument("--port", type=int, default=None, help="Listen port")
    parser.add_argument("--host", type=str, default=None, help="Listen host")
    args = parser.parse_args()

    cfg = get_config()
    port = args.port or cfg.port
    host = args.host or cfg.host

    logger.info("Starting Netris Demo Tool on http://%s:%d", host, port)
    logger.info("Health Endpoint: http://%s:%d/api/health", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
