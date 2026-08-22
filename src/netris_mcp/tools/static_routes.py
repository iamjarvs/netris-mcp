import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_static_routes(ctx: Context) -> str:
    """List all static routes across all VPCs in Netris.

    Returns a string representation of all static route objects from the
    Netris API. Static routes provide simple routing without BGP and are
    useful for directing traffic to specific subnets via a known next hop.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/static-route/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "static-route"))
    return str(data)


@mcp.tool()
async def get_static_route(ctx: Context, route_id: int) -> str:
    """Get a single static route by ID.

    Args:
        route_id: The numeric ID of the static route to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/static-route/{id}
    data = await get(nc.client, api_url(nc.base_url, "static-route", route_id))
    return str(data)


@mcp.tool()
async def create_static_route(
    ctx: Context,
    prefix: str,
    next_hop: str,
    vpc: str,
    site: str,
    description: Optional[str] = None,
) -> str:
    """Create a new static route in Netris.

    Static routes provide simple routing without BGP. They are useful for
    directing traffic to specific subnets through a known gateway when dynamic
    routing protocols are not available or not needed.

    Args:
        prefix: The destination network in CIDR notation (e.g. '10.0.0.0/8').
                Traffic destined for this prefix will be forwarded to next_hop.
        next_hop: The gateway IP address that traffic matching the prefix should
                  be forwarded to. Must be reachable within the specified VPC.
        vpc: The name of the VPC this static route belongs to. The route will
             only be active within the routing context of this VPC.
        site: The name of the site where this static route is installed on the
              underlying network hardware.
        description: Optional human-readable description for this route.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/static-route/
    payload: dict = {
        "prefix": prefix,
        "nextHop": next_hop,
        "vpc": {"name": vpc},
        "site": {"name": site},
    }
    if description is not None:
        payload["description"] = description
    data = await post(nc.client, api_url(nc.base_url, "static-route"), payload)
    return f"Created static route with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def delete_static_route(ctx: Context, route_id: int) -> str:
    """Delete a static route by ID.

    Args:
        route_id: The numeric ID of the static route to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/static-route/{id}
    data = await delete(nc.client, api_url(nc.base_url, "static-route", route_id))
    return f"Deleted static route {route_id}: {data}"
