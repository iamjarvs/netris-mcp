from ..server import mcp


@mcp.prompt()
def troubleshoot_network(symptom: str = "general") -> str:
    """Guide for diagnosing common Netris networking issues."""
    return f"""
# Netris Network Troubleshooting Guide

## Reported Symptom: {symptom}

## Diagnostic Approach
Work through the checklist relevant to your symptom. Use the tool calls listed to gather information at each step.

---

## BGP Session Not Coming Up

### Check 1: Verify Session Configuration
Use `list_bgp_sessions` to find the session and `get_bgp_session` with the ID to see full config.
Check: Is the neighbor AS correct? Are localIP and remoteIP correct? Is the site right?

### Check 2: Verify SoftGate is Running
Use `list_softgates` to confirm the SoftGate at the relevant site is present.
Use `get_softgate` with the SoftGate ID to see its full status.
BGP sessions terminate on SoftGates — if no SoftGate is registered for the site, BGP cannot come up.

### Check 3: Check IP Allocation
Use `list_subnets` to confirm the local BGP IP (localIP) is in a subnet that exists in Netris and is assigned to the correct site.
Use `get_subnet` with the subnet ID to confirm site and purpose assignments.

### Check 4: Check BGP Policies
If using route maps or prefix lists, use `list_bgp_objects` and `list_route_maps` to confirm they exist and are correctly named. A missing policy object causes BGP to reject all routes.

---

## VNet Not Reachable

### Check 1: Confirm VNet Exists
Use `list_vnets` to find the VNet and `get_vnet` with the ID to see its full config.
Check: Is it assigned to the correct sites? Is the VLAN ID correct?

### Check 2: Check Gateway Configuration
If expecting Layer 3 routing, use `get_vnet` and verify the gateways field has an IP configured.
No gateway = Layer 2 only — hosts need their own routing or a physical default gateway.

### Check 3: Verify VPC Assignment
Confirm the VNet and its subnets belong to the same VPC. Use `list_vpcs` and `list_subnets`.
Use `get_vpc` with the VPC ID to inspect the VPC in detail.

### Check 4: Check VPC Peering (if cross-VPC)
If traffic needs to cross VPC boundaries, use `list_vpc_peerings` to confirm the relevant VPCs are peered.
Use `get_vpc_peering` with the peering ID to inspect a specific peering.

---

## NAT Not Working (No Internet Access)

### Check 1: Confirm SNAT Rule Exists
Use `list_nat_rules` and find the SNAT rule for the source network.
Use `get_nat_rule` with the rule ID to see its full configuration.
Check: Is the sourcePrefix correct? Is the translatedAddress (NAT IP) set?

### Check 2: Verify NAT IP is Routed
The translatedAddress (NAT IP) must be:
- In a subnet with purpose "nat"
- Routed upstream via a BGP session
Use `list_subnets` and filter for purpose=nat, then `list_bgp_sessions` to confirm upstream connectivity.

### Check 3: Check VPC Peering
If the source workloads are in a tenant VPC and NAT is in the System VPC, use `list_vpc_peerings` to confirm the VPCs are peered.

### Check 4: Confirm SoftGate
NAT is applied on SoftGates. Use `list_softgates` to confirm a SoftGate is present at the site where the NAT rule is defined.

---

## L4LB Traffic Not Reaching Backends

### Check 1: Get L4LB Configuration
Use `list_l4lb` and `get_l4lb` with the ID to confirm:
- Frontend IP and port are correct
- Backend IPs and ports are correct
- Protocol matches (tcp/udp)

### Check 2: Verify Frontend IP is Announced
The L4LB frontend IP must be in a subnet with purpose "load-balancer" that is routed upstream via BGP.
Use `list_subnets` (filter by purpose=load-balancer) and `list_bgp_sessions`.

### Check 3: Backend Reachability
Backends must be reachable from the SoftGate. Use `list_vnets` to confirm the backend IPs are in a VNet attached to the same site as the L4LB.

### Check 4: Check Health Status
Use `get_l4lb` and check the status field. If backends are marked unhealthy, the L4LB will stop forwarding.

---

## IP Address / Subnet Not Available

### Check 1: Review IP Allocations
Use `list_allocations` to see all top-level IP blocks.
Use `get_allocation` with the allocation ID to inspect a specific block.

### Check 2: Review Subnets
Use `list_subnets` to see all subnets and their purposes.
Use `get_subnet` with the subnet ID to inspect a specific subnet.
Ensure the subnet purpose matches the intended service:
- "common" for VNets
- "load-balancer" for L4LB VIPs
- "nat" for NAT IPs
- "loopback" for loopback IPs
- "management" for OOB management

### Check 3: Create Missing Subnet
If the needed prefix does not exist as a subnet, use `create_subnet` with the correct purpose.

---

## ACL Blocking Unexpected Traffic

### Check 1: Review ACL Rules
Use `list_acls` to see all ACL rules currently in effect.
Use `get_acl` with a specific ID to inspect an individual rule.

### Check 2: Check Rule Order
ACLs are processed in order. An early deny rule may be blocking traffic before a permit rule is reached.
Review the order returned by `list_acls` and reorder or adjust rules as needed.

### Check 3: Check Site Default Policy
Use `get_site` for the relevant site and look at the default ACL policy field.
If it is "deny", all unmatched traffic is blocked — you may need to add explicit permit rules.

---

## Static Route Not Working

### Check 1: Confirm Static Route Exists
Use `list_static_routes` to see all static routes.
Use `get_static_route` with the route ID to inspect a specific route.

### Check 2: Verify Next-Hop Reachability
The next-hop IP must be reachable from the site. Confirm the next-hop is in a connected subnet using `list_subnets`.

---

## General Resource Check Sequence
When unsure where the problem is, run this sequence and look for gaps:
1. `list_sites` — confirm site exists; use `get_site` to inspect
2. `list_tenants` — confirm tenant exists; use `get_tenant` to inspect
3. `list_vpcs` — confirm VPC exists; use `get_vpc` to inspect
4. `list_vnets` — confirm VNet exists with correct site; use `get_vnet` to inspect
5. `list_softgates` — confirm SoftGate present at site; use `get_softgate` to inspect
6. `list_allocations` + `list_subnets` — confirm IP space allocated
7. `list_bgp_sessions` — confirm upstream connectivity; use `get_bgp_session` to inspect
8. `list_vpc_peerings` — confirm cross-VPC routing if needed; use `get_vpc_peering` to inspect
9. `list_nat_rules` — confirm NAT rules if internet access is needed; use `get_nat_rule` to inspect
10. `list_acls` — confirm no ACL rules are blocking traffic; use `get_acl` to inspect individual rules
"""
