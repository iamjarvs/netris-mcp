import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_bgp_sessions(ctx: Context) -> str:
    """List all eBGP peer sessions in Netris.

    Returns a string representation of all eBGP session objects from the Netris API.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/ebgp/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "ebgp"))
    return str(data)


@mcp.tool()
async def get_bgp_session(ctx: Context, bgp_id: int) -> str:
    """Get a single eBGP peer session by ID.

    Args:
        bgp_id: The numeric ID of the BGP session to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/ebgp/{id}
    data = await get(nc.client, api_url(nc.base_url, "ebgp", bgp_id))
    return str(data)


@mcp.tool()
async def create_bgp_session(
    ctx: Context,
    name: str,
    site: str,
    neighbor_as: int,
    neighbor_address: str,
    local_address: str,
    vnet: Optional[str] = None,
    bgp_password: Optional[str] = None,
    multihop: Optional[int] = None,
    bfd: bool = False,
) -> str:
    """Create a new eBGP peer session in Netris.

    Args:
        name: The name to assign to this BGP session.
        site: The name of the site where this BGP session is configured.
        neighbor_as: The AS number of the BGP neighbor (remote ASN).
        neighbor_address: The IP address of the BGP neighbor peer.
        local_address: The local IP address to use as the BGP source.
        vnet: Optional VNet name to associate with this BGP session.
        bgp_password: Optional MD5 password for BGP session authentication.
        multihop: Optional TTL value for multihop BGP sessions.
        bfd: Enable BFD (Bidirectional Forwarding Detection) for fast failure detection.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/ebgp/
    payload: dict = {
        "name": name,
        "site": {"name": site},
        "neighborAs": neighbor_as,
        "remoteIP": neighbor_address,
        "localIP": local_address,
    }
    if vnet is not None:
        payload["vnet"] = {"name": vnet}
    if bgp_password is not None:
        payload["bgpPassword"] = bgp_password
    if multihop is not None:
        payload["multihop"] = multihop
    if bfd:
        payload["bfd"] = bfd
    data = await post(nc.client, api_url(nc.base_url, "ebgp"), payload)
    return f"Created BGP session with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def delete_bgp_session(ctx: Context, bgp_id: int) -> str:
    """Delete an eBGP peer session by ID.

    Args:
        bgp_id: The numeric ID of the BGP session to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/ebgp/{id}
    data = await delete(nc.client, api_url(nc.base_url, "ebgp", bgp_id))
    return f"Deleted BGP session {bgp_id}: {data}"


@mcp.tool()
async def list_bgp_objects(ctx: Context) -> str:
    """List all BGP objects in Netris (prefix lists, community lists, etc.).

    Returns a string representation of all BGP object definitions used in
    route filtering and policy configuration.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/bgp-object/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "bgp-object"))
    return str(data)


@mcp.tool()
async def list_route_maps(ctx: Context) -> str:
    """List all route maps configured in Netris.

    Returns a string representation of all route map objects used for
    BGP policy and route manipulation.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/routemap/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "routemap"))
    return str(data)


@mcp.tool()
async def create_bgp_object(ctx: Context, name: str, type: str, prefixes: list[str]) -> str:
    """Create a BGP prefix list or community list object in Netris.
    Args:
        name: Name for this BGP object.
        type: Object type: 'ipv4' or 'ipv6' for prefix lists, 'community' for community lists.
        prefixes: List of prefix strings (e.g. ['10.0.0.0/8 le 24', '192.168.0.0/16']) or community values.
    """
    nc = ctx.request_context.lifespan_context
    payload = {"name": name, "type": type, "prefixes": [{"prefix": p} for p in prefixes]}
    data = await post(nc.client, api_url(nc.base_url, "bgp-object"), payload)
    return f"Created BGP object with ID {data.get('id', 'unknown')}"

@mcp.tool()
async def delete_bgp_object(ctx: Context, object_id: int) -> str:
    """Delete a BGP object (prefix list or community list) by ID.
    Args:
        object_id: The numeric ID of the BGP object to delete.
    """
    nc = ctx.request_context.lifespan_context
    data = await delete(nc.client, api_url(nc.base_url, "bgp-object", object_id))
    return f"Deleted BGP object {object_id}: {data}"

@mcp.tool()
async def create_route_map(ctx: Context, name: str, rules: list[dict]) -> str:
    """Create a route map for BGP policy in Netris.
    Args:
        name: Name for this route map.
        rules: List of rule dicts. Each rule: {"action": "permit"|"deny", "match": {...}, "set": {...}}
               Example: [{"action": "permit", "match": {"prefixList": "my-list"}, "set": {"localPref": 100}}]
    """
    nc = ctx.request_context.lifespan_context
    payload = {"name": name, "rules": rules}
    data = await post(nc.client, api_url(nc.base_url, "routemap"), payload)
    return f"Created route map with ID {data.get('id', 'unknown')}"

@mcp.tool()
async def delete_route_map(ctx: Context, route_map_id: int) -> str:
    """Delete a route map by ID.
    Args:
        route_map_id: The numeric ID of the route map to delete.
    """
    nc = ctx.request_context.lifespan_context
    data = await delete(nc.client, api_url(nc.base_url, "routemap", route_map_id))
    return f"Deleted route map {route_map_id}: {data}"
