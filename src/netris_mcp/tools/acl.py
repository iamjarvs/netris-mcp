import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_acls(ctx: Context) -> str:
    """List all ACL rules in Netris. ACLs filter network traffic at the site or VPC level.

    Returns a string representation of all ACL rule objects from the Netris
    API, including both permit and deny rules across all sites.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/acl/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "acl"))
    return str(data)


@mcp.tool()
async def get_acl(ctx: Context, acl_id: int) -> str:
    """Get a single ACL rule by ID.

    Args:
        acl_id: The numeric ID of the ACL rule to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/acl/{id}
    data = await get(nc.client, api_url(nc.base_url, "acl", acl_id))
    return str(data)


@mcp.tool()
async def create_acl(
    ctx: Context,
    name: str,
    action: str,
    src_prefix: str,
    dst_prefix: str,
    site: str,
    protocol: Optional[str] = None,
    src_port: Optional[str] = None,
    dst_port: Optional[str] = None,
) -> str:
    """Create a new ACL rule in Netris.

    ACLs filter network traffic at the site or VPC level based on source and
    destination IP, protocol, and port. Rules are evaluated in order and the
    first match determines whether traffic is permitted or denied.

    Args:
        name: A descriptive name for this ACL rule.
        action: Whether to "permit" or "deny" matching traffic.
        src_prefix: Source IP range in CIDR notation (e.g. '192.168.1.0/24').
                    Use '0.0.0.0/0' to match any source.
        dst_prefix: Destination IP range in CIDR notation (e.g. '10.0.0.0/8').
                    Use '0.0.0.0/0' to match any destination.
        site: The name of the site where this ACL rule is enforced.
        protocol: Optional IP protocol to match — "tcp", "udp", "icmp", or
                  None to match all protocols.
        src_port: Optional source port or port range to match, e.g. "80" or
                  "8080-8090". Only applicable when protocol is "tcp" or "udp".
        dst_port: Optional destination port or port range to match, e.g. "443"
                  or "8443-8450". Only applicable when protocol is "tcp" or "udp".
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/acl/
    payload: dict = {
        "name": name,
        "action": action,
        "srcPrefix": src_prefix,
        "dstPrefix": dst_prefix,
        "site": {"name": site},
    }
    if protocol is not None:
        payload["proto"] = protocol
    if src_port is not None:
        payload["srcPort"] = src_port
    if dst_port is not None:
        payload["dstPort"] = dst_port
    data = await post(nc.client, api_url(nc.base_url, "acl"), payload)
    return f"Created ACL rule with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def delete_acl(ctx: Context, acl_id: int) -> str:
    """Delete an ACL rule by ID.

    Args:
        acl_id: The numeric ID of the ACL rule to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/acl/{id}
    data = await delete(nc.client, api_url(nc.base_url, "acl", acl_id))
    return f"Deleted ACL rule {acl_id}: {data}"
