import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_nat_rules(ctx: Context) -> str:
    """List all NAT rules in Netris.

    Returns a string representation of all NAT rule objects (SNAT and DNAT)
    from the Netris API.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/nat/ — verify against netrisai/swagger-sources if needed
    data = await get(nc.client, api_url(nc.base_url, "nat"))
    return str(data)


@mcp.tool()
async def get_nat_rule(ctx: Context, nat_id: int) -> str:
    """Get a single NAT rule by ID.

    Args:
        nat_id: The numeric ID of the NAT rule to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/nat/{id}
    data = await get(nc.client, api_url(nc.base_url, "nat", nat_id))
    return str(data)


@mcp.tool()
async def create_snat_rule(
    ctx: Context,
    name: str,
    site: str,
    source_prefix: str,
    snat_to_ip: str,
    destination_address: Optional[str] = None,
) -> str:
    """Create a new SNAT (Source NAT) rule in Netris.

    SNAT rewrites the source IP of outbound packets, typically used to provide
    internet access to internal hosts using a shared public IP.

    Args:
        name: A descriptive name for this SNAT rule.
        site: The name of the site where this NAT rule is applied.
        source_prefix: The source IP prefix to match in CIDR notation
                       (e.g., "192.168.1.0/24"). Traffic from this prefix
                       will be SNATted.
        snat_to_ip: The public IP address that source traffic will be translated to.
        destination_address: Optional destination IP/prefix to match. If omitted,
                             the rule applies to all destinations.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/nat/
    payload: dict = {
        "name": name,
        "site": {"name": site},
        "type": "SNAT",
        "sourcePrefix": source_prefix,
        "translatedAddress": snat_to_ip,
    }
    if destination_address is not None:
        payload["destinationAddress"] = destination_address
    data = await post(nc.client, api_url(nc.base_url, "nat"), payload)
    return f"Created SNAT rule with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def create_dnat_rule(
    ctx: Context,
    name: str,
    site: str,
    destination_address: str,
    translated_address: str,
    protocol: str = "tcp",
    port: Optional[int] = None,
) -> str:
    """Create a new DNAT (Destination NAT) rule in Netris.

    DNAT rewrites the destination IP of inbound packets, typically used to
    forward traffic arriving at a public IP to an internal host (port forwarding).

    Args:
        name: A descriptive name for this DNAT rule.
        site: The name of the site where this NAT rule is applied.
        destination_address: The public destination IP address to match for
                             incoming traffic.
        translated_address: The internal IP address to translate the destination
                            to (the real backend host).
        protocol: The protocol to match — "tcp" or "udp". Defaults to "tcp".
        port: Optional destination port number to match. If omitted, the rule
              applies to all ports.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/nat/
    payload: dict = {
        "name": name,
        "site": {"name": site},
        "type": "DNAT",
        "destinationAddress": destination_address,
        "translatedAddress": translated_address,
        "protocol": protocol,
    }
    if port is not None:
        payload["port"] = port
    data = await post(nc.client, api_url(nc.base_url, "nat"), payload)
    return f"Created DNAT rule with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def update_nat_rule(ctx: Context, nat_id: int, enabled: bool) -> str:
    """Enable or disable a NAT rule.
    Args:
        nat_id: The numeric ID of the NAT rule.
        enabled: True to enable, False to disable.
    """
    nc = ctx.request_context.lifespan_context
    existing = await get(nc.client, api_url(nc.base_url, "nat", nat_id))
    payload = dict(existing)
    payload["state"] = "enabled" if enabled else "disabled"
    data = await put(nc.client, api_url(nc.base_url, "nat", nat_id), payload)
    return f"NAT rule {nat_id} {'enabled' if enabled else 'disabled'}: {data}"


@mcp.tool()
async def delete_nat_rule(ctx: Context, nat_id: int) -> str:
    """Delete a NAT rule by ID.

    Args:
        nat_id: The numeric ID of the NAT rule to delete.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/nat/{id}
    data = await delete(nc.client, api_url(nc.base_url, "nat", nat_id))
    return f"Deleted NAT rule {nat_id}: {data}"
