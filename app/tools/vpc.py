import logging

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_vpcs(ctx: Context) -> str:
    """List all VPCs in Netris.

    Returns a string representation of all VPC objects from the Netris API.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "vpc"))
    return str(data)


@mcp.tool()
async def get_vpc(ctx: Context, vpc_id: int) -> str:
    """Get a single VPC by ID.

    Args:
        vpc_id: The numeric ID of the VPC to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc/{id}
    data = await get(nc.client, api_url(nc.base_url, "vpc", vpc_id))
    return str(data)


@mcp.tool()
async def create_vpc(ctx: Context, name: str, tenant: str) -> str:
    """Create a new VPC in Netris.

    Args:
        name: The name of the new VPC.
        tenant: The name of the tenant that will own this VPC.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc/
    payload = {"name": name, "tenant": {"name": tenant}}
    data = await post(nc.client, api_url(nc.base_url, "vpc"), payload)
    return f"Created VPC with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def delete_vpc(ctx: Context, vpc_id: int) -> str:
    """Delete a VPC by ID.

    Args:
        vpc_id: The numeric ID of the VPC to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc/{id}
    data = await delete(nc.client, api_url(nc.base_url, "vpc", vpc_id))
    return f"Deleted VPC {vpc_id}: {data}"


@mcp.tool()
async def set_default_vpc(ctx: Context, vpc_id: int) -> str:
    """Set a VPC as the default VPC in Netris.

    Args:
        vpc_id: The numeric ID of the VPC to make the default.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc/{id}/make-default — verify against netrisai/swagger-sources if needed
    url = f"{api_url(nc.base_url, 'vpc', vpc_id)}/make-default"
    data = await post(nc.client, url, {})
    return f"Set VPC {vpc_id} as default: {data}"
