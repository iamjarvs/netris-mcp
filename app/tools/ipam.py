import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_subnets(ctx: Context) -> str:
    """List all subnets in the Netris IPAM.

    Returns a string representation of all subnet objects from the Netris API.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/subnet/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "ipam/subnet"))
    return str(data)


@mcp.tool()
async def get_subnet(ctx: Context, subnet_id: int) -> str:
    """Get a single IPAM subnet by ID.

    Args:
        subnet_id: The numeric ID of the subnet to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/ipam/subnet/{id}
    data = await get(nc.client, api_url(nc.base_url, "ipam/subnet", subnet_id))
    return str(data)


@mcp.tool()
async def create_subnet(
    ctx: Context,
    prefix: str,
    tenant: str,
    purpose: str = "common",
    site: Optional[str] = None,
) -> str:
    """Create a new subnet in the Netris IPAM.

    Args:
        prefix: The IP prefix in CIDR notation (e.g., "10.0.0.0/24").
        tenant: The name of the tenant that will own this subnet.
        purpose: The intended use of this subnet. Common values: "common",
                 "loopback", "management", "load-balancer". Defaults to "common".
        site: Optional name of the site to associate this subnet with.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/subnet/
    payload: dict = {
        "prefix": prefix,
        "tenant": {"name": tenant},
        "purpose": purpose,
    }
    if site is not None:
        payload["site"] = {"name": site}
    data = await post(nc.client, api_url(nc.base_url, "ipam/subnet"), payload)
    return f"Created subnet with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def delete_subnet(ctx: Context, subnet_id: int) -> str:
    """Delete a subnet from the Netris IPAM by ID.

    Args:
        subnet_id: The numeric ID of the subnet to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/ipam/subnet/{id}
    data = await delete(nc.client, api_url(nc.base_url, "ipam/subnet", subnet_id))
    return f"Deleted subnet {subnet_id}: {data}"


@mcp.tool()
async def list_allocations(ctx: Context) -> str:
    """List all IPAM allocations in Netris.

    Returns a string representation of all IP allocation objects. Allocations
    are top-level IP blocks from which subnets are carved out.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/allocation/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "ipam/allocation"))
    return str(data)


@mcp.tool()
async def create_allocation(ctx: Context, name: str, prefix: str, tenant: str) -> str:
    """Create a new IP allocation in the Netris IPAM.

    Allocations are top-level IP blocks that are then further subdivided into
    subnets for assignment to tenants, sites, and services.

    Args:
        name: A descriptive name for this allocation.
        prefix: The IP prefix in CIDR notation (e.g., "10.0.0.0/8").
        tenant: The name of the tenant that will own this allocation.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/allocation/
    payload = {
        "name": name,
        "prefix": prefix,
        "tenant": {"name": tenant},
    }
    data = await post(nc.client, api_url(nc.base_url, "ipam/allocation"), payload)
    return f"Created allocation with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def get_allocation(ctx: Context, allocation_id: int) -> str:
    """Get a single IP allocation by ID.
    Args:
        allocation_id: The numeric ID of the allocation to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    data = await get(nc.client, api_url(nc.base_url, "ipam/allocation", allocation_id))
    return str(data)

@mcp.tool()
async def delete_allocation(ctx: Context, allocation_id: int) -> str:
    """Delete an IP allocation by ID.
    Args:
        allocation_id: The numeric ID of the allocation to delete.
    """
    nc = ctx.request_context.lifespan_context
    data = await delete(nc.client, api_url(nc.base_url, "ipam/allocation", allocation_id))
    return f"Deleted allocation {allocation_id}: {data}"

@mcp.tool()
async def update_subnet(ctx: Context, subnet_id: int, purpose: str | None = None, sites: list[str] | None = None) -> str:
    """Update a subnet's purpose or site assignments.
    Args:
        subnet_id: The numeric ID of the subnet to update.
        purpose: New purpose: 'common', 'loopback', 'management', 'load-balancer', 'nat', 'inactive'.
        sites: New list of site names this subnet is associated with.
    """
    nc = ctx.request_context.lifespan_context
    existing = await get(nc.client, api_url(nc.base_url, "ipam/subnet", subnet_id))
    payload = dict(existing)
    if purpose is not None:
        payload["purpose"] = purpose
    if sites is not None:
        payload["sites"] = [{"name": s} for s in sites]
    data = await put(nc.client, api_url(nc.base_url, "ipam/subnet", subnet_id), payload)
    return f"Updated subnet {subnet_id}: {data}"
