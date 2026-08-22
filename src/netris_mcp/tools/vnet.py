import copy
import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_vnets(ctx: Context) -> str:
    """List all VNets (virtual networks) in Netris.

    Returns a string representation of all VNet objects from the Netris API.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/v-net/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "v-net"))
    return str(data)


@mcp.tool()
async def get_vnet(ctx: Context, vnet_id: int) -> str:
    """Get a single VNet (virtual network) by ID.

    Args:
        vnet_id: The numeric ID of the VNet to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/v-net/{id}
    data = await get(nc.client, api_url(nc.base_url, "v-net", vnet_id))
    return str(data)


@mcp.tool()
async def create_vnet(
    ctx: Context,
    name: str,
    sites: list[str],
    tenant: str,
    vlan: Optional[int] = None,
) -> str:
    """Create a new VNet (virtual network) in Netris.

    Args:
        name: The name of the new VNet.
        sites: List of site names to associate with this VNet.
        tenant: The name of the tenant that will own this VNet.
        vlan: Optional VLAN ID to assign to this VNet.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/v-net/
    payload: dict = {
        "name": name,
        "sites": [{"name": s} for s in sites],
        "tenant": {"name": tenant},
    }
    if vlan is not None:
        payload["vlan"] = vlan
    data = await post(nc.client, api_url(nc.base_url, "v-net"), payload)
    return f"Created VNet with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def update_vnet(
    ctx: Context,
    vnet_id: int,
    gateway: str | None = None,
    dhcp_enabled: bool | None = None,
    vlan: int | None = None,
) -> str:
    """Update a VNet's gateway, DHCP, or VLAN configuration.
    Args:
        vnet_id: The numeric ID of the VNet to update.
        gateway: Gateway IP address in CIDR notation (e.g. '10.0.1.1/24'). Sets the Layer 3 gateway for this VNet.
        dhcp_enabled: Enable (True) or disable (False) DHCP on this VNet.
        vlan: New VLAN ID to assign (optional).
    """
    nc = ctx.request_context.lifespan_context
    existing = await get(nc.client, api_url(nc.base_url, "v-net", vnet_id))
    payload = copy.deepcopy(existing)
    if gateway is not None:
        payload["gateways"] = [{"gateway": gateway}]
    if dhcp_enabled is not None:
        if "dhcp" not in payload:
            payload["dhcp"] = {}
        payload["dhcp"]["enabled"] = dhcp_enabled
    if vlan is not None:
        payload["vlan"] = vlan
    data = await put(nc.client, api_url(nc.base_url, "v-net", vnet_id), payload)
    return f"Updated VNet {vnet_id}: {data}"


@mcp.tool()
async def delete_vnet(ctx: Context, vnet_id: int) -> str:
    """Delete a VNet (virtual network) by ID.

    Args:
        vnet_id: The numeric ID of the VNet to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/v-net/{id}
    data = await delete(nc.client, api_url(nc.base_url, "v-net", vnet_id))
    return f"Deleted VNet {vnet_id}: {data}"
