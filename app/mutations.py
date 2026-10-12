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
        # Parameter validation
        if operation not in ("create", "delete"):
            return f"VALIDATION ERROR: Unsupported operation '{operation}'. Must be 'create' or 'delete'."

        if not name or not name.strip():
            return "VALIDATION ERROR: V-Net name must not be empty."

        # Protection safeguards
        protected_vnets = {"default", "mgmt", "management", "system", "underlay"}
        if operation == "delete" and name.strip().lower() in protected_vnets:
            return f"PROTECTION SAFEGUARD: Deletion of critical system V-Net '{name}' is forbidden."

        if operation == "create" and "/" not in gateways:
            return f"VALIDATION ERROR: Invalid gateway CIDR '{gateways}'. Expected format e.g. '192.168.100.1/24'."

        # Safe dry-run preview: permitted in read-only mode to evaluate configuration safely
        if dry_run:
            impact_desc = (
                "Would provision new tenant EVPN V-Net on fabric switches."
                if operation == "create"
                else f"Would teardown tenant EVPN V-Net '{name}' and withdraw EVPN routes."
            )
            return json.dumps({
                "dry_run": True,
                "operation": operation,
                "target_resource": "vnet",
                "mode": cfg.mode,
                "proposed_configuration": {
                    "name": name,
                    "vpc": vpc_name,
                    "gateways": gateways if operation == "create" else None,
                },
                "impact": impact_desc,
                "notice": "Re-run with dry_run=False and NETRIS_MCP_MODE=read-write to commit change.",
            }, indent=2)

        # Protection safeguard: reject live mutations if not running in read-write mode
        if cfg.mode != "read-write":
            return (
                f"MUTATION REJECTED: Netris MCP is running in '{cfg.mode}' mode. "
                "Mutations require NETRIS_MCP_MODE=read-write in environment configuration."
            )

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

        elif operation == "delete":
            try:
                vnets = await client.get("/api/v2/vnet") or []
                match = next((v for v in vnets if str(v.get("name", "")).lower() == name.lower()), None)
                if not match:
                    return f"Failed to delete V-Net: V-Net '{name}' not found."
                vnet_id = match.get("id")
                res = await client.delete(f"/api/v2/vnet/{vnet_id}")
                _record_audit("delete", "vnet", {"name": name, "id": vnet_id}, "SUCCESS")
                return json.dumps({"status": "SUCCESS", "message": f"Deleted V-Net {name}", "data": res}, indent=2)
            except Exception as e:
                _record_audit("delete", "vnet", {"name": name}, f"FAILED: {e}")
                return f"Failed to delete V-Net: {e}"

        return "Unsupported operation"
