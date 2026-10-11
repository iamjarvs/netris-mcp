from ..server import mcp


@mcp.prompt()
def provision_gpu_cluster(cluster_name: str, site: str, tenant: str, node_count: int = 8) -> str:
    """Guide for provisioning GPU cluster networking in Netris with L3VPN east-west connectivity."""
    return f"""
# GPU Cluster Networking Guide: {cluster_name}

## Overview
This guide provisions the network fabric for a {node_count}-node GPU cluster at {site}.
Netris uses L3VPN mode for GPU east-west traffic — each node gets a dedicated routed /31 link
rather than a shared Layer 2 broadcast domain, giving line-rate loop-free connectivity ideal
for distributed AI training workloads.

## Architecture
- **L3VPN V-Net**: Each server port gets a /31 IPv4 point-to-point link
- **VPC isolation**: Cluster traffic stays in a dedicated VPC
- **ROH (Routing on Host)**: Each GPU server runs its own BGP speaker (vmAsn must be set on site)

## Phase 1: Verify Prerequisites

### 1.1 Confirm Site
Use `list_sites` / `get_site` to confirm "{site}" exists.
Check that `vmAsn` is set if using ROH — use `update_site` if it is missing.

### 1.2 Check Switch Capacity
Use `list_switches` — need {node_count * 2}+ ports for {node_count} nodes (2 per node).

## Phase 2: Create Dedicated VPC

Use `create_vpc` with:
- name: "{cluster_name}-vpc"
- tenant: "{tenant}"

## Phase 3: IP Allocation

### 3.1 Create Allocation (top-level block)
Use `create_allocation` with:
- name: "{cluster_name}-pool"
- prefix: e.g. "10.200.0.0/24" (holds {node_count * 2}+ /31 links comfortably)
- tenant: "{tenant}"

### 3.2 Create Subnet
Use `create_subnet` with:
- prefix: e.g. "10.200.0.0/24"
- tenant: "{tenant}"
- purpose: "common"
- site: "{site}"

## Phase 4: L3VPN V-Net

### 4.1 Create V-Net
Use `create_vnet` with:
- name: "{cluster_name}-l3vpn"
- sites: ["{site}"]
- tenant: "{tenant}"

### 4.2 Set Gateway (activates L3VPN mode)
Use `update_vnet` with:
- vnet_id: (returned from 4.1)
- gateway: e.g. "10.200.0.1/24"

With a gateway and server ports attached, Netris assigns /31 point-to-point links.

## Phase 5: BGP Sessions Per Server (ROH)

For each of the {node_count} GPU nodes, use `create_bgp_session` with:
- name: "{cluster_name}-node-N-bgp"
- site: "{site}"
- neighbor_as: unique private ASN per server (e.g. 64512, 64513, …)
- neighbor_address: server port IP on the /31 link
- local_address: switch-side IP of the /31 link

## Phase 6: Optional — Internet Access

### 6.1 Peer with System VPC
Use `list_vpcs` to find the System VPC name.
Use `create_vpc_peering` with vpc1="{cluster_name}-vpc", vpc2=<System VPC>.

### 6.2 Create SNAT Rule
Use `create_snat_rule` with source_prefix="10.200.0.0/24", snat_to_ip=<public NAT IP from a nat-purpose subnet>.

## Phase 7: Verify

- `list_vpcs` — {cluster_name}-vpc present
- `list_vnets` — {cluster_name}-l3vpn at {site} with gateway set
- `list_subnets` — cluster subnet with purpose=common
- `list_bgp_sessions` — {node_count} server BGP sessions
- `list_vpc_peerings` — System VPC peering (if internet access configured)

## Notes
- vmAsn on the site must be set before ROH BGP sessions will work
- Each server needs a unique private ASN in the range 64512–65534
- For NVIDIA NVLink / Spectrum-X: fabric topology tracked in NVLink Ledger
- Intra-cluster GPU traffic stays within the L3VPN V-Net at line rate
"""
