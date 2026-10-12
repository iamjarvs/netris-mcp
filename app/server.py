"""Netris MCP Server entrypoint.

Registers tool dispatchers and workflow prompts using FastMCP.
Supports both STDIO (for Claude Desktop, Cursor, VS Code) and Streamable HTTP (for Demo Portal).
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from app.charting import register_charting
from app.config import get_config
from app.diagnostics_dispatch import register_diagnostics
from app.mutations import register_mutations
from app.netris_client import NetrisClient
from app.switch_exec import register_switch_exec
from app.telemetry_dispatch import register_telemetry
from app.tools_dispatch import register_tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("netris-mcp")

cfg = get_config()

# Initialise FastMCP instance
mcp = FastMCP(
    name="Netris MCP Server",
    instructions="""
You are an AI assistant managing Netris cloud networking and AI fabric infrastructure.
Netris provides unified intent-based orchestration across both Front-End (Ethernet EVPN/VXLAN, VPCs, V-Nets, eBGP, NAT, L4LB SoftGate) and Back-End (NVIDIA UFM for InfiniBand, NVIDIA NVLink NVL72 via NMX-C, and RoCEv2 Spectrum-X) AI network fabrics, as well as on-host networking (ROH).
Always query fabric inventory and network topology before attempting configuration changes.
Use compact umbrella tools (fabric_inventory, virtual_networks, routing_and_policy, fabric_links, fabric_health, fabric_telemetry, triage) to inspect state efficiently without token bloat.
Use run_switch_command to execute read-only show commands on switches via the jump host; target hostnames (e.g. 'leaf-pod00-su1-r1') and routing loopbacks are automatically resolved to out-of-band management IPs (mgmtAddress).
    """,
)

# Shared authenticated client
client = NetrisClient(
    base_url=cfg.netris_url,
    username=cfg.netris_username,
    password=cfg.netris_password,
    verify_ssl=cfg.netris_verify_ssl,
)

# Register Stage 2, 3, 4, 5 & Telemetry tool dispatchers
register_tools(mcp, client)
register_diagnostics(mcp, client)
register_switch_exec(mcp, client)
register_mutations(mcp, client)
register_telemetry(mcp, client)
register_charting(mcp)


def main():
    """Run MCP server in default STDIO mode."""
    logger.info("Starting Netris MCP Server in STDIO mode...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
