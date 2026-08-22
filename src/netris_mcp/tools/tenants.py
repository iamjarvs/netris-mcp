"""
Tenant tools — Netris multi-tenancy management.

Tenants are the top-level organisational unit in Netris.  All resources
(VPCs, subnets, load balancers, BGP sessions, etc.) are owned by a tenant.
"""

import logging

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_tenants(ctx: Context) -> str:
    """List all tenants configured in Netris.

    Returns a string representation of all tenant objects. Each tenant
    represents an isolated organisational unit that owns network resources.
    """
    nc = ctx.request_context.lifespan_context
    # TODO: confirm exact path against netrisai/swagger-sources — candidate: "tenant"
    data = await get(nc.client, api_url(nc.base_url, "tenant"))
    return str(data)


@mcp.tool()
async def get_tenant(ctx: Context, tenant_id: int) -> str:
    """Get a single tenant by ID.

    Args:
        tenant_id: The numeric ID of the tenant to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    data = await get(nc.client, api_url(nc.base_url, "tenant", tenant_id))
    return str(data)


@mcp.tool()
async def create_tenant(ctx: Context, name: str, description: str = "") -> str:
    """Create a new tenant in Netris.

    After creating a tenant, assign it IP allocations and resources.  The
    tenant name is used as the ownership reference in all resource-creation
    calls (VPCs, subnets, VNets, L4LBs, etc.).

    Args:
        name: The unique name for this tenant.
        description: Optional human-readable description of the tenant.
    """
    nc = ctx.request_context.lifespan_context
    payload: dict = {"name": name}
    if description:
        payload["description"] = description
    data = await post(nc.client, api_url(nc.base_url, "tenant"), payload)
    return f"Created tenant with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def update_tenant(
    ctx: Context,
    tenant_id: int,
    name: str,
    description: str = "",
) -> str:
    """Update an existing tenant's name or description.

    Args:
        tenant_id: The numeric ID of the tenant to update.
        name: The new name for the tenant.
        description: Optional updated description.
    """
    nc = ctx.request_context.lifespan_context
    payload: dict = {"name": name}
    if description:
        payload["description"] = description
    data = await put(nc.client, api_url(nc.base_url, "tenant", tenant_id), payload)
    return f"Updated tenant {tenant_id}: {data}"


@mcp.tool()
async def delete_tenant(ctx: Context, tenant_id: int) -> str:
    """Delete a tenant by ID.

    Warning: the tenant must have no remaining owned resources before it can
    be deleted.  Netris will return an error if owned resources exist.

    Args:
        tenant_id: The numeric ID of the tenant to delete.
    """
    nc = ctx.request_context.lifespan_context
    data = await delete(nc.client, api_url(nc.base_url, "tenant", tenant_id))
    return f"Deleted tenant {tenant_id}: {data}"
