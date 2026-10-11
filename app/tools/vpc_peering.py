import logging

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_vpc_peerings(ctx: Context) -> str:
    """List all VPC peerings in Netris.

    Returns a string representation of all VPC peering objects from the
    Netris API. VPC peerings connect two VPCs so traffic can flow between
    them without hairpinning through an external gateway.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc-peering/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "vpc-peering"))
    return str(data)


@mcp.tool()
async def get_vpc_peering(ctx: Context, peering_id: int) -> str:
    """Get a single VPC peering by ID.

    Args:
        peering_id: The numeric ID of the VPC peering to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc-peering/{id}
    data = await get(nc.client, api_url(nc.base_url, "vpc-peering", peering_id))
    return str(data)


@mcp.tool()
async def create_vpc_peering(ctx: Context, vpc1: str, vpc2: str, tenant: str) -> str:
    """Create a new VPC peering between two Netris VPCs.

    VPC peering establishes bidirectional cross-VPC routing rules so that
    workloads in each VPC can reach each other directly. A common use case
    is peering a tenant VPC with the System VPC (or Default VPC) to enable
    internet access via NAT or L4LB resources that live in the System VPC.
    At least one of vpc1 or vpc2 must be the System VPC or Default VPC when
    internet access is required.

    Args:
        vpc1: The name of the first VPC in the peering pair.
        vpc2: The name of the second VPC in the peering pair. At least one of
              vpc1/vpc2 must be the System VPC or Default VPC to enable
              internet access (NAT/L4LB) for workloads in the tenant VPC.
        tenant: The name of the tenant that owns this peering relationship.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc-peering/
    payload = {
        "vpc1": {"name": vpc1},
        "vpc2": {"name": vpc2},
        "tenant": {"name": tenant},
    }
    data = await post(nc.client, api_url(nc.base_url, "vpc-peering"), payload)
    return f"Created VPC peering with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def delete_vpc_peering(ctx: Context, peering_id: int) -> str:
    """Delete a VPC peering by ID.

    Args:
        peering_id: The numeric ID of the VPC peering to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/vpc-peering/{id}
    data = await delete(nc.client, api_url(nc.base_url, "vpc-peering", peering_id))
    return f"Deleted VPC peering {peering_id}: {data}"
