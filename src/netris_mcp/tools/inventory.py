import logging

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_inventory(ctx: Context) -> str:
    """List all inventory items in Netris (switches, softgates, servers, controllers).

    Returns a string representation of all device inventory objects from the Netris API.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/ — general hardware listing
    data = await get(nc.client, api_url(nc.base_url, "hw"))
    return str(data)


@mcp.tool()
async def get_inventory_item(ctx: Context, item_id: int) -> str:
    """Get a single inventory item by ID.

    Args:
        item_id: The numeric ID of the inventory item to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/{id}
    data = await get(nc.client, api_url(nc.base_url, "hw", item_id))
    return str(data)


@mcp.tool()
async def list_controllers(ctx: Context) -> str:
    """List all Netris controllers.

    Returns a string representation of all controller objects from the Netris API.
    Controllers are the central management components of the Netris platform.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/controller/
    data = await get(nc.client, api_url(nc.base_url, "hw/controller"))
    return str(data)


@mcp.tool()
async def list_softgates(ctx: Context) -> str:
    """List all SoftGate nodes in Netris.

    Returns a string representation of all SoftGate objects. SoftGates are
    software-based network gateways that provide L3 routing and services.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/softgate/
    data = await get(nc.client, api_url(nc.base_url, "hw/softgate"))
    return str(data)


@mcp.tool()
async def get_softgate(ctx: Context, sg_id: int) -> str:
    """Get a single SoftGate node by ID.

    Args:
        sg_id: The numeric ID of the SoftGate to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/softgate/{id}
    data = await get(nc.client, api_url(nc.base_url, "hw/softgate", sg_id))
    return str(data)


@mcp.tool()
async def create_softgate(
    ctx: Context,
    name: str,
    site: str,
    tenant: str,
    main_ip: str,
    mgmt_ip: str,
) -> str:
    """Create a new SoftGate node in Netris.

    Args:
        name: The name to assign to the new SoftGate.
        site: The name of the site where this SoftGate will be located.
        tenant: The name of the tenant that will own this SoftGate.
        main_ip: The primary IP address of the SoftGate (used for data-plane traffic).
        mgmt_ip: The management IP address of the SoftGate (used for out-of-band access).
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/softgate/
    payload = {
        "name": name,
        "site": {"name": site},
        "tenant": {"name": tenant},
        "mainIp": main_ip,
        "mgmtIp": mgmt_ip,
    }
    data = await post(nc.client, api_url(nc.base_url, "hw/softgate"), payload)
    return f"Created SoftGate with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def update_softgate(ctx: Context, sg_id: int, main_ip: str | None = None, mgmt_ip: str | None = None) -> str:
    """Update a softgate's IP configuration.
    Args:
        sg_id: The numeric ID of the softgate to update.
        main_ip: New main IP address (optional).
        mgmt_ip: New management IP address (optional).
    """
    nc = ctx.request_context.lifespan_context
    existing = await get(nc.client, api_url(nc.base_url, "hw/softgate", sg_id))
    # TODO(api-access): verify which fields PUT /hw/softgate/{id} accepts — replace
    # dict(existing) with an allowlist (name, site, tenant, mainIp, mgmtIp) if Netris
    # rejects server-managed fields (agentVersion, heartbeat, syncState, nos, etc.).
    payload = dict(existing)
    if main_ip is not None:
        payload["mainIp"] = main_ip
    if mgmt_ip is not None:
        payload["mgmtIp"] = mgmt_ip
    data = await put(nc.client, api_url(nc.base_url, "hw/softgate", sg_id), payload)
    return f"Updated softgate {sg_id}: {data}"

@mcp.tool()
async def delete_softgate(ctx: Context, sg_id: int) -> str:
    """Delete a softgate from inventory.
    Args:
        sg_id: The numeric ID of the softgate to delete.
    """
    nc = ctx.request_context.lifespan_context
    data = await delete(nc.client, api_url(nc.base_url, "hw/softgate", sg_id))
    return f"Deleted softgate {sg_id}: {data}"


@mcp.tool()
async def list_switches(ctx: Context) -> str:
    """List all switches in the Netris inventory.

    Returns a string representation of all switch objects managed by Netris.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/switch/
    data = await get(nc.client, api_url(nc.base_url, "hw/switch"))
    return str(data)


@mcp.tool()
async def get_switch(ctx: Context, switch_id: int) -> str:
    """Get a single switch by ID.

    Args:
        switch_id: The numeric ID of the switch to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/hw/switch/{id}
    data = await get(nc.client, api_url(nc.base_url, "hw/switch", switch_id))
    return str(data)
