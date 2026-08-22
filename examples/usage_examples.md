# Netris MCP Server — Usage Examples

These examples show how a user interacts with Claude when the Netris MCP server is connected. Each example shows the user's natural language prompt, which tools Claude calls (in order), and what the user sees as a result.

---

## Example 1: List all sites

**User prompt**
> "What sites do I have in Netris?"

**What Claude does**

1. Calls `list_sites` (no parameters required).
2. Receives the raw JSON response from the Netris API.
3. Formats the site list into a readable summary.

**Result**

Claude responds with something like:

> You have 3 sites configured in Netris:
>
> | ID | Name | ASN | Location |
> |----|------|-----|----------|
> | 1 | DC-East | 65001 | New York, NY |
> | 2 | DC-West | 65002 | Los Angeles, CA |
> | 3 | HQ | 65000 | Austin, TX |
>
> Would you like details on any of these sites, or do you want to see the devices registered at each one?

---

## Example 2: Create a new site and verify it

**User prompt**
> "Create a new site called 'EU-Frankfurt' with ASN 65010. The location is Frankfurt, Germany."

**What Claude does**

1. Calls `list_sites` to verify that a site with this name does not already exist.
2. Calls `create_site` with `name="EU-Frankfurt"`, `asn=65010`, `location="Frankfurt, Germany"`.
3. Notes the returned site ID (e.g. `7`).
4. Calls `get_site` with `site_id=7` to confirm the details are correct.

**Result**

> I created the new site successfully. Here are the details:
>
> - **Name**: EU-Frankfurt
> - **ID**: 7
> - **ASN**: 65010
> - **Location**: Frankfurt, Germany
>
> The site is ready. Would you like to register a SoftGate at this site, or add subnets to it?

---

## Example 3: Provision a VPC with subnets (using the guide)

**User prompt**
> "I need to provision a new VPC called 'prod-vpc' for the tenant 'acme'. Use subnet 10.100.0.0/16 as the allocation, with a /24 workload subnet at 10.100.1.0/24. The site is DC-East. Use the VPC provisioning guide."

**What Claude does**

1. Invokes the `provision_vpc` guide (prompt) with `vpc_name="prod-vpc"`, `tenant="acme"`, `subnet_prefix="10.100.0.0/16"`, `site="DC-East"`.
2. The guide returns a structured set of step-by-step instructions. Claude reads and follows them:
   - Calls `list_vpcs` to verify `prod-vpc` doesn't already exist.
   - Calls `list_tenants` to confirm `acme` exists.
   - Calls `create_vpc` with `name="prod-vpc"`, `tenant="acme"`. Notes the returned ID.
   - Calls `create_allocation` with `name="prod-vpc-pool"`, `prefix="10.100.0.0/16"`, `tenant="acme"`.
   - Calls `create_subnet` with `prefix="10.100.1.0/24"`, `tenant="acme"`, `purpose="common"`, `site="DC-East"`.
   - Calls `create_vnet` with `name="prod-vpc-vnet1"`, `sites=["DC-East"]`, `tenant="acme"`.
   - Calls `list_subnets` and `list_vnets` to verify everything was created.

**Result**

> The VPC provisioning is complete. Here's a summary of what was created:
>
> - **VPC**: prod-vpc (ID: 12), owned by tenant `acme`
> - **Allocation**: prod-vpc-pool — `10.100.0.0/16` (top-level IP block)
> - **Subnet**: `10.100.1.0/24` (purpose: common, site: DC-East)
> - **VNet**: prod-vpc-vnet1, attached to site DC-East
>
> Workloads at DC-East can now be placed in the `10.100.1.0/24` subnet. Would you like to set up BGP peering or NAT rules for this VPC?

---

## Example 4: List and inspect BGP sessions

**User prompt**
> "Show me all BGP sessions and give me the full details on the one peering with AS 64512."

**What Claude does**

1. Calls `list_bgp_sessions` to retrieve all eBGP session objects.
2. Scans the results for the session where `neighborAs == 64512`.
3. Notes that session's ID (e.g. `3`).
4. Calls `get_bgp_session` with `bgp_id=3` to retrieve full details.

**Result**

> You have 2 BGP sessions configured:
>
> | ID | Name | Site | Neighbor AS | Neighbor Address | Status |
> |----|------|------|-------------|------------------|--------|
> | 2 | dc-east-transit | DC-East | 65100 | 192.0.2.1 | Established |
> | 3 | dc-east-isp2 | DC-East | 64512 | 198.51.100.1 | Established |
>
> Full details for **dc-east-isp2** (AS 64512):
> - **Local address**: 198.51.100.2
> - **Site**: DC-East
> - **VNet**: (none)
> - **Status**: Established
> - **Prefixes received**: 14
> - **Uptime**: 4d 7h 12m
>
> Is there anything you'd like to change about this session, or would you like to add route filtering?

---

## Example 5: Full network bootstrap for a new tenant (using the bootstrap guide)

**User prompt**
> "I've just installed a fresh Netris controller. Bootstrap the whole deployment for organisation 'CloudCo'. First site is 'Primary-DC' with ASN 65000. Management block is 10.0.0.0/24, loopback block is 10.0.255.0/29, public block is 203.0.113.0/26."

**What Claude does**

1. Invokes the `bootstrap_network` guide with `org_name="CloudCo"`, `first_site_name="Primary-DC"`, `site_asn=65000`, `mgmt_prefix="10.0.0.0/24"`, `loopback_prefix="10.0.255.0/29"`, `public_prefix="203.0.113.0/26"`.
2. The guide returns an 8-phase workflow. Claude executes each phase:
   - **Phase 1** (Tenant): Calls `list_tenants` → not found → calls `create_tenant` with `name="CloudCo"`.
   - **Phase 2** (Site): Calls `create_site` with `name="Primary-DC"`, `asn=65000`. Verifies with `get_site`.
   - **Phase 3** (Allocations): Calls `create_allocation` three times — management, loopback, and public pools.
   - **Phase 4** (Subnets): Calls `create_subnet` for management and loopback subnets with appropriate `purpose` values.
   - **Phase 5** (Infrastructure): Asks the user for the SoftGate's main IP and management IP, then calls `create_softgate`.
   - **Phase 6** (VPC/VNet): Calls `create_vpc`, `create_subnet` (workload), and `create_vnet`.
   - **Phase 7** (BGP): Asks the user for the upstream provider's ASN and peering IPs, then calls `create_bgp_session`.
   - **Phase 8** (Verification): Calls `list_sites`, `list_inventory`, `list_subnets`, `list_vpcs`, `list_vnets`, `list_bgp_sessions` and reports the status of each.

**Result**

> Bootstrap complete. Here's what was created for **CloudCo / Primary-DC**:
>
> **Tenant**: CloudCo (ID: 1)
> **Site**: Primary-DC, ASN 65000 (ID: 1)
>
> **IP Allocations**:
> - Primary-DC-mgmt-pool: `10.0.0.0/24`
> - Primary-DC-loopback-pool: `10.0.255.0/29`
> - Primary-DC-public-pool: `203.0.113.0/26`
>
> **Subnets**: management `10.0.0.0/25`, loopback `10.0.255.0/29`
> **SoftGate**: Primary-DC-sg1, main IP `10.0.0.1`, mgmt IP `10.0.0.100`
> **VPC**: CloudCo-vpc1 (ID: 1)
> **VNet**: CloudCo-vnet1 (ID: 1), attached to Primary-DC
> **BGP Session**: Primary-DC-upstream → AS 64496 at 203.0.113.1 (local 203.0.113.2)
>
> All verification checks passed. The SoftGate must be online and the upstream peer must be configured before the BGP session will establish. Would you like to add NAT rules or a load balancer?

---

## Example 6: Troubleshoot — list all inventory

**User prompt**
> "Something seems wrong with one of my switches. Show me all inventory and then give me the full details on any device at site DC-West."

**What Claude does**

1. Calls `list_inventory` to retrieve all inventory items.
2. Filters the results for items associated with site `DC-West`.
3. For each DC-West device, calls `get_inventory_item` with its ID to retrieve full details.
4. Also calls `list_softgates` and `list_switches` to get type-specific status fields.

**Result**

> Here is the full inventory for site **DC-West**:
>
> **SoftGates**:
> - dc-west-sg1 (ID: 3) — Status: **Active**, main IP: 10.1.0.1, mgmt IP: 10.1.0.100
>
> **Switches**:
> - spine-01 (ID: 8) — Status: **Active**, management IP: 10.1.0.10
> - leaf-01 (ID: 9) — Status: **Offline** ⚠ — last seen: 2 hours ago
> - leaf-02 (ID: 10) — Status: **Active**, management IP: 10.1.0.12
>
> It looks like **leaf-01** (ID: 9) is offline. Would you like me to pull the full detail record for it, or check if there are any associated BGP sessions or VNets that might be affected?

---

## Example 7: Set up a load balancer

**User prompt**
> "Set up an L4 TCP load balancer called 'web-lb' at site DC-East for tenant acme. Frontend IP is 203.0.113.20, port 80. Backends are 10.0.1.10:80, 10.0.1.11:80, and 10.0.1.12:80."

**What Claude does**

1. Calls `list_sites` to verify `DC-East` exists.
2. Calls `list_tenants` to verify `acme` exists.
3. Calls `list_l4lb` to check whether `203.0.113.20:80` is already in use.
4. Calls `list_allocations` to confirm `203.0.113.20` is within a Netris-managed IP block.
5. Calls `create_l4lb` with:
   - `name="web-lb"`, `site="DC-East"`, `tenant="acme"`
   - `frontend_ip="203.0.113.20"`, `frontend_port=80`, `protocol="tcp"`
   - `backends=[{"ip": "10.0.1.10", "port": 80}, {"ip": "10.0.1.11", "port": 80}, {"ip": "10.0.1.12", "port": 80}]`
6. Notes the returned ID (e.g. `5`).
7. Calls `get_l4lb` with `lb_id=5` to verify the configuration.

**Result**

> The load balancer **web-lb** has been created successfully:
>
> - **Frontend**: 203.0.113.20:80 (TCP)
> - **Site**: DC-East
> - **Tenant**: acme
> - **Backends**:
>   - 10.0.1.10:80
>   - 10.0.1.11:80
>   - 10.0.1.12:80
>
> Netris will program the fabric to distribute port 80 traffic across all three backends. Health checks will begin automatically. Would you like to add HTTPS (port 443) or set up a DNAT rule alongside this?

---

## Example 8: Check and manage NAT rules

**User prompt**
> "What NAT rules do I have? I want to add port forwarding for SSH (TCP port 22) from 203.0.113.5 to the internal host 10.0.1.50."

**What Claude does**

1. Calls `list_nat_rules` to retrieve and display all existing SNAT and DNAT rules.
2. Checks whether a conflicting rule for `203.0.113.5:22` already exists.
3. Since the user wants inbound port forwarding (public → internal), this is a DNAT rule.
4. Calls `create_dnat_rule` with:
   - `name="ssh-forward-10.0.1.50"`, `site="DC-East"`
   - `destination_address="203.0.113.5"`, `translated_address="10.0.1.50"`
   - `protocol="tcp"`, `port=22`

**Result**

> You currently have 3 NAT rules:
>
> | ID | Name | Type | Site | Source / Destination |
> |----|------|------|------|----------------------|
> | 1 | outbound-snat | SNAT | DC-East | 10.0.0.0/24 → any |
> | 2 | web-dnat | DNAT | DC-East | 203.0.113.20:80 → 10.0.1.10:80 |
> | 3 | api-dnat | DNAT | DC-East | 203.0.113.20:8080 → 10.0.1.20:8080 |
>
> No conflicting rule found for `203.0.113.5:22`. I've created the new DNAT rule:
>
> - **Name**: ssh-forward-10.0.1.50
> - **Type**: DNAT
> - **Public address**: 203.0.113.5 (any source)
> - **Port**: TCP 22
> - **Translates to**: 10.0.1.50:22
>
> SSH traffic arriving at 203.0.113.5:22 will now be forwarded to 10.0.1.50 by the Netris fabric. Make sure the host at 10.0.1.50 has an SSH server running and its local firewall allows the connection.
