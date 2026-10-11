from ..server import mcp


@mcp.prompt()
def setup_multi_site(site1: str, site2: str, tenant: str, shared_vpc: str) -> str:
    """Guide for connecting two Netris sites with shared VPC resources."""
    return f"""
# Multi-Site Setup Guide: {site1} <-> {site2}

## Overview
This guide provisions network connectivity between two Netris sites under a shared VPC. After completing this guide:
- The same VPC ({shared_vpc}) spans both {site1} and {site2}
- V-Nets can be extended across both sites (VXLAN-encapsulated)
- BGP sessions at each site provide local upstream connectivity
- Workloads at both sites can communicate within the same VPC

## Phase 1: Verify Site Infrastructure

### 1.1 Confirm Sites Exist
Use `list_sites` to confirm both "{site1}" and "{site2}" exist with their correct ASNs.
Use `get_site` with each site ID to inspect full configuration.
If either is missing, use `create_site` to add it — each site must have a unique ASN.

### 1.2 Confirm SoftGates (if using SoftGate-based services)
Use `list_softgates` to confirm each site has at least one registered SoftGate.
Use `get_softgate` with the SoftGate ID to inspect its status.
Without a SoftGate, NAT, L4LB, and SoftGate-terminated BGP are unavailable at that site.

### 1.3 Confirm Switches
Use `list_switches` to confirm switch fabric is registered at each site.
Use `list_inventory` to see a full inventory of hardware across both sites.

## Phase 2: Set Up Shared VPC

### 2.1 Confirm or Create VPC
Use `list_vpcs` to check if "{shared_vpc}" exists.
If not, use `create_vpc`:
- name: "{shared_vpc}"
- tenant: "{tenant}"

Use `get_vpc` with the VPC ID to confirm settings after creation.

## Phase 3: IP Planning

### 3.1 Review Existing Allocations
Use `list_allocations` to see available IP blocks.
Use `get_allocation` with an allocation ID to inspect an individual block.

### 3.2 Create Site-Specific Subnets
Create a subnet for each site in the shared VPC:
- Site {site1} subnet: use `create_subnet` with purpose="common", site="{site1}"
- Site {site2} subnet: use `create_subnet` with purpose="common", site="{site2}"

Use `list_subnets` to confirm both subnets are created and assigned to the correct sites.

## Phase 4: Create Multi-Site V-Net

### 4.1 Create V-Net Spanning Both Sites
Use `create_vnet` with:
- name: "{shared_vpc}-vnet1"
- sites: ["{site1}", "{site2}"]
- tenant: "{tenant}"

Netris automatically creates VXLAN tunnels between sites for this V-Net.
Use `get_vnet` with the new V-Net ID to confirm the configuration.

### 4.2 Configure Gateway (for Layer 3)
If workloads need Layer 3 routing (not just Layer 2 bridging), use `update_vnet` with:
- vnet_id: (the ID from step 4.1)
- gateway: a gateway IP in CIDR notation from the subnet created in Phase 3

## Phase 5: BGP Connectivity (Optional)

### 5.1 Site-Specific BGP
Each site can have its own upstream BGP sessions. Use `create_bgp_session` separately for each site:
- Session at {site1}: site="{site1}", localIP=(IP at {site1}), remoteIP=(peer at {site1})
- Session at {site2}: site="{site2}", localIP=(IP at {site2}), remoteIP=(peer at {site2})

Use `list_bgp_sessions` and `get_bgp_session` to confirm each session comes up.

### 5.2 BGP Objects and Route Maps (Optional)
If upstream peers require prefix filtering or AS-path policies, use `list_bgp_objects` and `list_route_maps` to check for existing policies.
Create policies with `create_bgp_object` and `create_route_map` as needed.

## Phase 6: Static Routes (Optional)

### 6.1 Add Static Routes if BGP is Not Used
If upstream routing is static rather than BGP, use `create_static_route` to point traffic at each site to the correct next-hop.
Use `list_static_routes` to confirm routes are in place and `get_static_route` to inspect individual entries.

## Phase 7: Verify

### 7.1 Check Topology
- `list_sites` — both sites present with correct ASNs
- `list_vnets` + `get_vnet` — V-Net shows both sites
- `list_subnets` — subnets assigned to correct sites
- `list_bgp_sessions` — sessions at each site (if configured)
- `list_softgates` — SoftGates present at each site (if using NAT/L4LB)

### 7.2 Check Controllers
Use `list_controllers` to confirm the Netris controller sees both sites.

## Notes
- VXLAN tunnels between sites are managed automatically by Netris — no manual tunnel config needed
- Each site's switch fabric is independent; only the VPC/VNet overlay spans sites
- VPC peering can optionally be used to connect {shared_vpc} to the System VPC for internet access — see the vpc_peering guide
- Use `delete_site` with caution — removing a site removes all resources registered to it
"""
