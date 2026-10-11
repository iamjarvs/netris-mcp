"""
Netris MCP server entry point.

Responsibilities
----------------
1. Load configuration from the environment via ``get_config()``.
2. Authenticate to the Netris controller once at startup and obtain the
   session cookie.
3. Create a long-lived ``httpx.AsyncClient`` with the session cookie baked in
   and expose it to all tool handlers through the FastMCP lifespan context.
4. Run a background asyncio task that periodically refreshes the session so
   the cookie doesn't expire during a long-running server process.
5. Register all tool and guide modules by importing them (their ``@mcp.tool``
   and ``@mcp.prompt`` decorators register themselves against ``mcp`` at import
   time).

Transport: STDIO only.  All logging goes to stderr; stdout is reserved
exclusively for MCP protocol messages.
"""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from mcp.server.mcpserver import MCPServer

from .auth import login, refresh_session
from .config import get_config

# ---------------------------------------------------------------------------
# Logging — must write to stderr; stdout is the MCP wire protocol
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan context dataclass
# ---------------------------------------------------------------------------


@dataclass
class NetrisContext:
    """
    Holds the authenticated HTTP client and base URL for the Netris controller.

    Injected into every tool handler via ``ctx.request_context.lifespan_context``.
    """

    client: httpx.AsyncClient
    base_url: str


# ---------------------------------------------------------------------------
# Lifespan — auth, client creation, background refresh, teardown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[NetrisContext]:
    """
    FastMCP lifespan context manager.

    Sequence
    --------
    startup:
        1. Read config from env.
        2. Authenticate (POST /api/v2/auth/login) → obtain connect.sid cookie.
        3. Open a persistent ``httpx.AsyncClient`` pre-loaded with the cookie.
        4. Start a background task that GETs /api/v2/auth/profile every
           ``session_refresh_seconds`` to prevent session expiry.
        5. Yield ``NetrisContext`` to all tool handlers.

    shutdown (finally block):
        6. Cancel the background refresh task.
        7. Log shutdown.
        (The ``async with httpx.AsyncClient`` block closes the client cleanly.)
    """
    config = get_config()
    base_url = f"https://{config.host}"

    logger.info("Authenticating to Netris controller at %s", base_url)
    cookies = await login(
        config.host,
        config.username,
        config.password,
        config.ssl_verify,
    )

    async with httpx.AsyncClient(
        cookies=cookies,
        verify=config.ssl_verify,
        timeout=config.timeout,
        headers={"Content-Type": "application/json"},
    ) as client:

        async def _refresh_loop() -> None:
            """Background coroutine — keeps the Netris session alive."""
            while True:
                await asyncio.sleep(config.session_refresh_seconds)
                await refresh_session(client, config.host)

        refresh_task = asyncio.create_task(_refresh_loop())
        logger.info(
            "Netris MCP server ready (session refresh every %d s)",
            config.session_refresh_seconds,
        )

        try:
            yield NetrisContext(client=client, base_url=base_url)
        finally:
            refresh_task.cancel()
            # Swallow CancelledError from the task itself
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
            logger.info("Netris MCP server shutting down")


# ---------------------------------------------------------------------------
# FastMCP application instance
# ---------------------------------------------------------------------------

mcp = MCPServer("Netris", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Register tools and guides
#
# Importing each sub-module is sufficient — the @mcp.tool() / @mcp.prompt()
# decorators in each file register themselves against the ``mcp`` instance
# above at import time.  This block must come AFTER ``mcp`` is defined to
# avoid circular-import issues (each sub-module imports ``mcp`` from here).
# ---------------------------------------------------------------------------

# Tools
from .tools import vpc  # noqa: E402, F401
from .tools import vnet  # noqa: E402, F401
from .tools import bgp  # noqa: E402, F401
from .tools import sites  # noqa: E402, F401
from .tools import inventory  # noqa: E402, F401
from .tools import ipam  # noqa: E402, F401
from .tools import nat  # noqa: E402, F401
from .tools import l4lb  # noqa: E402, F401
from .tools import tenants  # noqa: E402, F401
from .tools import vpc_peering  # noqa: E402, F401
from .tools import static_routes  # noqa: E402, F401
from .tools import acl  # noqa: E402, F401

# Guides (MCP prompts)
from .guides import site_onboarding  # noqa: E402, F401
from .guides import vpc_provisioning  # noqa: E402, F401
from .guides import bgp_setup  # noqa: E402, F401
from .guides import l4lb_setup  # noqa: E402, F401
from .guides import network_bootstrap  # noqa: E402, F401
from .guides import vpc_peering_guide  # noqa: E402, F401
from .guides import acl_guide  # noqa: E402, F401
from .guides import troubleshooting_guide  # noqa: E402, F401
from .guides import multi_site_guide  # noqa: E402, F401
from .guides import gpu_cluster_guide  # noqa: E402, F401


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server over STDIO."""
    mcp.run()


if __name__ == "__main__":
    main()
