import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_sites(ctx: Context) -> str:
    """List all sites in Netris.

    Returns a string representation of all site objects from the Netris API.
    Sites represent physical or logical network locations.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/sites/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "sites"))
    return str(data)


@mcp.tool()
async def get_site(ctx: Context, site_id: int) -> str:
    """Get a single site by ID.

    Args:
        site_id: The numeric ID of the site to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/sites/{id}
    data = await get(nc.client, api_url(nc.base_url, "sites", site_id))
    return str(data)


@mcp.tool()
async def create_site(
    ctx: Context,
    name: str,
    asn: int,
    roh_asn: int | None = None,
    vm_asn: int | None = None,
    site_mesh: str | None = None,
    location: Optional[str] = None,
) -> str:
    """Create a new site in Netris.

    Args:
        name: The name of the new site.
        asn: The BGP Autonomous System Number (ASN) assigned to this site.
        roh_asn: Optional ASN for Routing on the Host (RoH) workloads at this site.
        vm_asn: Optional ASN for VM workloads at this site.
        site_mesh: Optional site mesh topology role (e.g. 'hub', 'spoke', 'disabled').
        location: Optional human-readable description of the site's physical location.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/sites/
    payload: dict = {
        "name": name,
        "publicAsn": asn,
    }
    if roh_asn is not None:
        payload["rohAsn"] = roh_asn
    if vm_asn is not None:
        payload["vmAsn"] = vm_asn
    if site_mesh is not None:
        payload["siteMesh"] = site_mesh
    if location is not None:
        payload["location"] = location
    data = await post(nc.client, api_url(nc.base_url, "sites"), payload)
    return f"Created site with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def update_site(ctx: Context, site_id: int, name: str | None = None, public_asn: int | None = None, site_mesh: str | None = None) -> str:
    """Update a site's configuration in Netris.
    Args:
        site_id: The numeric ID of the site to update.
        name: New name for the site (optional).
        public_asn: New BGP ASN for the site (optional).
        site_mesh: Site mesh topology (optional, e.g. 'hub', 'spoke', 'disabled').
    """
    nc = ctx.request_context.lifespan_context
    existing = await get(nc.client, api_url(nc.base_url, "sites", site_id))
    payload = dict(existing)
    if name is not None:
        payload["name"] = name
    if public_asn is not None:
        payload["publicAsn"] = public_asn
    if site_mesh is not None:
        payload["siteMesh"] = site_mesh
    data = await put(nc.client, api_url(nc.base_url, "sites", site_id), payload)
    return f"Updated site {site_id}: {data}"


@mcp.tool()
async def delete_site(ctx: Context, site_id: int) -> str:
    """Delete a site by ID.

    Args:
        site_id: The numeric ID of the site to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/sites/{id}
    data = await delete(nc.client, api_url(nc.base_url, "sites", site_id))
    return f"Deleted site {site_id}: {data}"
