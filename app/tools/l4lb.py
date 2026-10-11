"""
L4 Load Balancer tools — Netris L4LB management.

L4LB objects define frontend VIPs and their backend server pools.
Netris automatically programs the network fabric to distribute traffic.
"""

import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_l4lb(ctx: Context) -> str:
    """List all L4 load balancers in Netris.

    Returns a string representation of all L4LB objects from the Netris API,
    including their frontend VIP, protocol, and backend pool.
    """
    nc = ctx.request_context.lifespan_context
    # TODO: confirm exact path against netrisai/swagger-sources — candidate: "l4lb"
    data = await get(nc.client, api_url(nc.base_url, "l4lb"))
    return str(data)


@mcp.tool()
async def get_l4lb(ctx: Context, lb_id: int) -> str:
    """Get a single L4 load balancer by ID.

    Args:
        lb_id: The numeric ID of the L4LB to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    data = await get(nc.client, api_url(nc.base_url, "l4lb", lb_id))
    return str(data)


@mcp.tool()
async def create_l4lb(
    ctx: Context,
    name: str,
    site: str,
    tenant: str,
    frontend_ip: str,
    frontend_port: int,
    protocol: str,
    backends: list[dict],
    health_check: Optional[str] = None,
) -> str:
    """Create a new L4 load balancer in Netris.

    Netris programs the network fabric to route traffic arriving at the
    frontend VIP to the specified backend pool using ECMP or weighted
    distribution.

    Args:
        name: A descriptive name for this load balancer.
        site: The name of the site where this load balancer is provisioned.
        tenant: The name of the tenant that owns this load balancer.
        frontend_ip: The public VIP address clients connect to.
        frontend_port: The TCP/UDP port clients connect to on the frontend IP.
        protocol: Transport protocol — "tcp" or "udp".
        backends: List of backend dicts, each with "ip" (str) and "port" (int)
                  keys, e.g. [{"ip": "10.0.1.10", "port": 8080}].
        health_check: Optional health-check type string (e.g. "tcp", "http").
                      Defaults to the protocol if omitted.
    """
    nc = ctx.request_context.lifespan_context
    # TODO: confirm exact path and payload shape against netrisai/swagger-sources
    payload: dict = {
        "name": name,
        "site": {"name": site},
        "tenant": {"name": tenant},
        "ip": frontend_ip,
        "port": frontend_port,
        "protocol": protocol,
        "backends": backends,
        "automatic": True,
    }
    if health_check is not None:
        payload["healthCheck"] = health_check
    data = await post(nc.client, api_url(nc.base_url, "l4lb"), payload)
    return f"Created L4LB with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def update_l4lb_backends(
    ctx: Context,
    lb_id: int,
    backends: list[dict],
) -> str:
    """Update the backend pool of an existing L4 load balancer.

    Replaces the entire backend list.  Pass the complete desired set of
    backends, not just the delta.

    Args:
        lb_id: The numeric ID of the L4LB to update.
        backends: The new complete list of backend dicts, each with "ip" (str)
                  and "port" (int) keys.
    """
    nc = ctx.request_context.lifespan_context
    existing = await get(nc.client, api_url(nc.base_url, "l4lb", lb_id))
    # Only send known-writable fields — sending the full GET response back verbatim
    # would include server-managed read-only fields (status, timestamps) that many
    # REST APIs reject on PUT with a 400/422.
    payload: dict = {
        "name": existing.get("name"),
        "site": existing.get("site"),
        "tenant": existing.get("tenant"),
        "ip": existing.get("ip"),
        "port": existing.get("port"),
        "protocol": existing.get("protocol"),
        "backends": backends,
        "automatic": existing.get("automatic", True),
    }
    if existing.get("healthCheck"):
        payload["healthCheck"] = existing["healthCheck"]
    data = await put(nc.client, api_url(nc.base_url, "l4lb", lb_id), payload)
    return f"Updated L4LB {lb_id} backends: {data}"


@mcp.tool()
async def delete_l4lb(ctx: Context, lb_id: int) -> str:
    """Delete an L4 load balancer by ID.

    Args:
        lb_id: The numeric ID of the L4LB to delete.
    """
    nc = ctx.request_context.lifespan_context
    data = await delete(nc.client, api_url(nc.base_url, "l4lb", lb_id))
    return f"Deleted L4LB {lb_id}: {data}"
