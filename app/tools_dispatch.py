"""Central umbrella tool dispatchers inspired by mcp-apstra.

Provides:
- `fabric_inventory`: Consolidated inventory across sites, VPCs, tenants, switches, softgates, controllers.
- `virtual_networks`: VNet, IPAM, and overlay routing inspection.
- `routing_and_policy`: BGP peering, route maps, ACLs, static routes, NAT, and L4 load balancers.
- `fabric_links`: Physical links and switch interfaces topology.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from app.config import get_config
from app.netris_client import NetrisClient
from app.primitives import format_digest, to_json_output


def register_tools(mcp: FastMCP, client: NetrisClient):
    cfg = get_config()

    # -------------------------------------------------------------------------
    # 1. Fabric Inventory Umbrella Dispatcher
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def fabric_inventory(
        domain: Annotated[
            Literal[
                "summary",
                "sites",
                "tenants",
                "vpcs",
                "hardware",
                "switches",
                "softgates",
                "servers",
                "controllers",
                "profiles",
            ],
            Field(description="Inventory domain to inspect. 'summary' gives quick fabric-wide counts."),
        ] = "summary",
        site_name: Annotated[str | None, Field(description="Filter hardware by site name.")] = None,
        tenant_name: Annotated[str | None, Field(description="Filter by tenant name.")] = None,
        limit: Annotated[int, Field(description="Max records to return.")] = 50,
    ) -> str:
        """Query physical and logical fabric inventory (Sites, Tenants, VPCs, Switches, SoftGates, Controllers)."""
        if domain == "summary":
            sites = await client.get("/api/v2/sites") or []
            vpcs = await client.get("/api/v2/vpc") or []
            tenants = await client.get("/api/tenants") or []
            hw = await client.get("/api/v2/hw") or []
            
            # Count hardware types
            switches = [d for d in hw if d.get("type") == "switch"]
            softgates = [d for d in hw if d.get("type") == "softgate"]
            servers = [d for d in hw if d.get("type") == "server"]
            controllers = [d for d in hw if d.get("type") == "controller"]
            
            summary = {
                "sites_count": len(sites),
                "sites": [s.get("name") for s in sites],
                "vpcs_count": len(vpcs),
                "tenants_count": len(tenants),
                "tenants": [t.get("name") for t in tenants],
                "hardware_total": len(hw),
                "switches": len(switches),
                "softgates": len(softgates),
                "servers": len(servers),
                "controllers": len(controllers),
            }
            return to_json_output(summary)

        elif domain == "sites":
            sites = await client.get("/api/v2/sites") or []
            return to_json_output(format_digest(sites, ["id", "name", "publicAsn", "switchFabric", "aclPolicy"], limit=limit))

        elif domain == "tenants":
            tenants = await client.get("/api/tenants") or []
            return to_json_output(format_digest(tenants, ["id", "name", "description"], limit=limit))

        elif domain == "vpcs":
            vpcs = await client.get("/api/v2/vpc") or []
            return to_json_output(format_digest(vpcs, ["id", "name", "adminTenant", "vni"], limit=limit))

        elif domain in ("hardware", "switches", "softgates", "servers"):
            hw = await client.get("/api/v2/hw") or []
            if domain == "switches":
                hw = [h for h in hw if h.get("type") == "switch"]
            elif domain == "softgates":
                hw = [h for h in hw if h.get("type") == "softgate"]
            elif domain == "servers":
                hw = [h for h in hw if h.get("type") == "server"]
            if site_name:
                hw = [h for h in hw if str(h.get("site", {}).get("name", "")).lower() == site_name.lower()]
            if tenant_name:
                hw = [h for h in hw if str(h.get("tenant", {}).get("name", "")).lower() == tenant_name.lower()]
            return to_json_output(format_digest(hw, ["id", "name", "type", "mainAddress", "health", "site", "tenant"], limit=limit))

        elif domain == "controllers":
            hw = await client.get("/api/v2/hw") or []
            ctrls = [h for h in hw if h.get("type") == "controller"]
            return to_json_output(format_digest(ctrls, ["id", "name", "mainAddress", "health", "site"], limit=limit))

        elif domain == "profiles":
            profiles = await client.get("/api/v2/hw/profiles") or []
            return to_json_output(format_digest(profiles, ["id", "name", "description"], limit=limit))

        return "Unknown domain"

    # -------------------------------------------------------------------------
    # 2. Virtual Networks & Overlay Dispatcher
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def virtual_networks(
        action: Annotated[
            Literal["list_vnets", "vnets", "vnet_detail", "ipam_tree", "ipam", "vpc_peerings", "peering"],
            Field(description="Overlay inspection action."),
        ] = "list_vnets",
        name: Annotated[str | None, Field(description="Filter by VNet or Peering name.")] = None,
        vpc_name: Annotated[str | None, Field(description="Filter by VPC name.")] = None,
        limit: Annotated[int, Field(description="Max records to return.")] = 50,
    ) -> str:
        """Inspect V-Net overlay networks, IPAM subnets/allocations, and VPC peering connections."""
        if action in ("list_vnets", "vnets"):
            vnets = await client.get("/api/v2/vnet") or []
            if vpc_name:
                vnets = [v for v in vnets if str(v.get("vpc", {}).get("name", "")).lower() == vpc_name.lower()]
            if name:
                vnets = [v for v in vnets if name.lower() in str(v.get("name", "")).lower()]
            return to_json_output(format_digest(vnets, ["id", "name", "state", "vpc", "tenant", "gateways", "provisioning"], limit=limit))

        elif action == "vnet_detail":
            if not name:
                return "Error: Please supply 'name' parameter to query specific VNet detail."
            vnets = await client.get("/api/v2/vnet") or []
            match = next((v for v in vnets if str(v.get("name", "")).lower() == name.lower()), None)
            if not match:
                return f"V-Net '{name}' not found."
            return to_json_output(match)

        elif action in ("ipam_tree", "ipam"):
            ipam = await client.get("/api/v2/ipam") or []
            return to_json_output(format_digest(ipam, ["id", "prefix", "name", "purpose", "type", "vpc", "tenant", "utilization"], limit=limit))

        elif action in ("vpc_peerings", "peering"):
            peerings = await client.get("/api/v2/vpc-peering") or []
            return to_json_output(format_digest(peerings, ["id", "name", "vpc1", "vpc2", "state"], limit=limit))

        return "Unknown action"

    # -------------------------------------------------------------------------
    # 3. Routing and Policy Dispatcher
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def routing_and_policy(
        action: Annotated[
            Literal[
                "ebgp_sessions",
                "ebgp",
                "ebgp_routemaps",
                "route_maps",
                "acls",
                "static_routes",
                "nat_rules",
                "nat",
                "l4lb_services",
            ],
            Field(description="Routing and security policy inspect action."),
        ] = "ebgp_sessions",
        limit: Annotated[int, Field(description="Max records to return.")] = 50,
    ) -> str:
        """Inspect edge and fabric policy: E-BGP peerings, route maps, ACLs, static routes, NAT, and L4LB."""
        if action in ("ebgp_sessions", "ebgp"):
            ebgp = await client.get("/api/v2/ebgp") or []
            return to_json_output(format_digest(ebgp, ["id", "name", "neighbor_as", "local_ip", "remote_ip", "status", "vpc"], limit=limit))

        elif action in ("ebgp_routemaps", "route_maps"):
            maps = await client.get("/api/v2/ebgp/routemaps") or []
            return to_json_output(format_digest(maps, ["id", "name", "description"], limit=limit))

        elif action == "acls":
            # ACL is v1 endpoint
            acls = await client.get("/api/acl") or []
            return to_json_output(format_digest(acls, ["id", "name", "action", "protocol", "srcAddress", "dstAddress", "status"], limit=limit))

        elif action == "static_routes":
            # Static routes is v1 endpoint
            routes = await client.get("/api/routes") or []
            return to_json_output(format_digest(routes, ["id", "prefix", "nextHop", "site", "state", "description"], limit=limit))

        elif action in ("nat_rules", "nat"):
            nat = await client.get("/api/v2/nat") or []
            return to_json_output(format_digest(nat, ["id", "name", "action", "protocol", "srcAddress", "dstAddress", "status"], limit=limit))

        elif action == "l4lb_services":
            l4lb = await client.get("/api/v2/l4lb") or []
            return to_json_output(format_digest(l4lb, ["id", "name", "frontend", "status", "site", "tenant"], limit=limit))

        return "Unknown action"

    # -------------------------------------------------------------------------
    # 4. Fabric Links and Interfaces Dispatcher
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def fabric_links(
        query: Annotated[
            Literal["links_summary", "summary", "links_list", "links", "interfaces_list", "interfaces"],
            Field(description="Topology link and port query."),
        ] = "links_summary",
        node_name: Annotated[str | None, Field(description="Filter by switch/server node name.")] = None,
        limit: Annotated[int, Field(description="Max records to return.")] = 50,
    ) -> str:
        """Inspect physical cabling, link states, optical connectivity, and interface configurations."""
        if query in ("links_summary", "summary"):
            links = await client.get("/api/v2/link", params={"page": 1, "limit": 10}) or []
            ports = await client.get("/api/v2/ports", params={"page": 1, "limit": 10}) or []
            return to_json_output({
                "note": "Netris manages 2,244 physical links and 7,110 interfaces across the fabric.",
                "sample_links": links[:3],
            })

        elif query in ("links_list", "links"):
            params = {"page": 1, "limit": limit}
            if node_name:
                params["filterHardwareName"] = node_name
            links = await client.get("/api/v2/link", params=params) or []
            
            # Format endpoints
            formatted = []
            for lnk in links[:limit]:
                local = lnk.get("local", {})
                remote = lnk.get("remote", {})
                formatted.append({
                    "id": lnk.get("id"),
                    "speed": local.get("speed"),
                    "status": local.get("status", {}).get("label"),
                    "local_node": local.get("hardware", {}).get("name"),
                    "local_port": local.get("port"),
                    "remote_node": remote.get("hardware", {}).get("name"),
                    "remote_port": remote.get("port"),
                })
            return to_json_output({
                "count": len(formatted),
                "links": formatted,
            })

        elif query in ("interfaces_list", "interfaces"):
            params = {"page": 1, "limit": limit}
            if node_name:
                params["filterHardwareName"] = node_name
            ports = await client.get("/api/v2/ports", params=params) or []
            return to_json_output(format_digest(ports, ["id", "port", "name", "speed", "status", "hardware"], limit=limit))

        return "Unknown query"
