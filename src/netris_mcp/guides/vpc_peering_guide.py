from ..server import mcp


@mcp.prompt()
def setup_vpc_peering(tenant_vpc: str, system_vpc: str = "default") -> str:
    """Guide for peering a tenant VPC with the System VPC to enable internet access."""
    return f"""
# VPC Peering Guide: {tenant_vpc} <-> {system_vpc}

## Overview
VPC peering creates cross-VPC routing rules between two isolated VPCs. The most common use case is peering a tenant VPC with the System VPC — this enables workloads in {tenant_vpc} to use internet-facing services: NAT (outbound internet), L4LB (inbound traffic), and upstream BGP routes.

## Key Concepts
- **{system_vpc}** (System VPC): Anchors infrastructure resources — upstream BGP sessions, NAT IPs, L4LB VIPs. This is the internet-facing VPC.
- **{tenant_vpc}**: Your workload VPC. After peering, workloads here can reach the internet via NAT rules in the System VPC.
- Peering is bidirectional — Netris creates routing in both directions.

## Step 1: Verify Both VPCs Exist
Use `list_vpcs` to confirm both "{tenant_vpc}" and "{system_vpc}" exist. Note their IDs.

## Step 2: Check for Existing Peerings
Use `list_vpc_peerings` to confirm these two VPCs are not already peered.

## Step 3: Create the VPC Peering
Use `create_vpc_peering` with:
- vpc1: "{tenant_vpc}"
- vpc2: "{system_vpc}"
- tenant: the admin tenant name for {tenant_vpc} (use `list_tenants` to find it)

## Step 4: Verify the Peering
Use `list_vpc_peerings` to confirm the peering appears and check its status.

## Step 5: Verify Routing
After peering:
- Workloads in {tenant_vpc} should be able to reach destinations via NAT rules in {system_vpc}
- Use `list_nat_rules` to see SNAT rules in {system_vpc} — these provide outbound internet access
- Use `list_bgp_sessions` to see upstream BGP routes available via {system_vpc}

## Common Use Cases After Peering
- **Outbound internet access**: Create an SNAT rule in {system_vpc} with `create_snat_rule` pointing to a subnet in {tenant_vpc}
- **Inbound traffic (L4LB)**: Create an L4LB in {system_vpc} and point backends to IPs in {tenant_vpc}
- **Port forwarding**: Create a DNAT rule in {system_vpc} mapping a public IP to an internal IP in {tenant_vpc}

## Notes
- VPC peering in Netris is not transitive — peering A<->B and B<->C does not enable A<->C traffic
- Deleting a peering immediately removes cross-VPC routing
- Use `delete_vpc_peering` with the peering ID to remove a peering
- Use `get_vpc_peering` with the peering ID to inspect a specific peering in detail
"""
