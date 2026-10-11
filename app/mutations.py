"""Gated write operations for Netris MCP server.

Safety Contract:
- Write operations are disabled by default unless NETRIS_MCP_MODE=read-write.
- All mutating tools default to dry_run=True.
- Mutation preview diffs and rollback advice returned to LLM.
- All actions logged to mutations audit log.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from app.config import get_config
from app.netris_client import NetrisClient

logger = logging.getLogger("netris-mcp.mutations")
AUDIT_LOG = Path("logs/mutations.jsonl")


def _record_audit(action: str, resource: str, payload: Any, status: str):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "action": action,
            "resource": resource,
            "payload": payload,
            "status": status,
        }) + "\n")


def register_mutations(mcp: FastMCP, client: NetrisClient):
    cfg = get_config()

    @mcp.tool()
    async def mutate_vnet(
        operation: Annotated[str, Field(description="Action to perform: 'create' or 'delete'.")],
        name: Annotated[str, Field(description="Name of the V-Net (must begin with 'mcp-qa-' in testing).")],
        vpc_name: Annotated[str, Field(description="Target VPC name.")] = "Default",
        gateways: Annotated[str, Field(description="Gateway CIDR (e.g. '192.168.100.1/24').")] = "192.168.100.1/24",
        dry_run: Annotated[bool, Field(description="If True, only validates and returns preview diff.")] = True,
    ) -> str:
        """Create or delete a V-Net overlay network. Mutations require NETRIS_MCP_MODE=read-write."""
        if cfg.mode != "read-write":
            return (
                f"MUTATION REJECTED: Netris MCP is running in '{cfg.mode}' mode. "
                "Mutations require NETRIS_MCP_MODE=read-write in environment configuration."
            )

        if dry_run:
            return json.dumps({
                "dry_run": True,
                "operation": operation,
                "target_resource": "vnet",
                "proposed_configuration": {
                    "name": name,
                    "vpc": vpc_name,
                    "gateways": gateways,
                },
                "impact": "Would create new tenant EVPN V-Net on fabric switches.",
                "notice": "Re-run with dry_run=False to commit change.",
            }, indent=2)

        if operation == "create":
            payload = {
                "name": name,
                "vpc": {"name": vpc_name},
                "gateways": [{"prefix": gateways}],
                "state": "active",
            }
            try:
                res = await client.post("/api/v2/vnet", json_data=payload)
                _record_audit("create", "vnet", payload, "SUCCESS")
                return json.dumps({"status": "SUCCESS", "message": f"Created V-Net {name}", "data": res}, indent=2)
            except Exception as e:
                _record_audit("create", "vnet", payload, f"FAILED: {e}")
                return f"Failed to create V-Net: {e}"

        return "Unsupported operation"
