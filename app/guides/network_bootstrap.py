"""
Network bootstrap guide — end-to-end first-time Netris setup prompt.

This guide walks an operator through the complete sequence of steps required
to go from a fresh Netris controller to a functional multi-tenant network with
at least one site, one VPC, IP allocations, and BGP peering.
"""

from ..server import mcp


@mcp.prompt()
def bootstrap_network(
    org_name: str,
    first_site_name: str,
    site_asn: int,
    mgmt_prefix: str,
    loopback_prefix: str,
    public_prefix: str,
) -> str:
    """End-to-end guide for bootstrapping a brand-new Netris deployment.

    Walks through: tenant creation → site creation → IP allocations →
    subnets → softgate registration → VPC → VNet → BGP peering.

    Args:
        org_name: The name of the primary (admin) tenant / organisation.
        first_site_name: The name of the first network site to create.
        site_asn: The BGP ASN to assign to the first site.
        mgmt_prefix: The management IP block in CIDR notation (e.g. "10.0.0.0/24").
        loopback_prefix: The loopback IP block in CIDR notation (e.g. "10.0.255.0/29").
        public_prefix: The public / internet-facing IP block in CIDR notation.
    """
    return f"""
# Netris Network Bootstrap Guide for {org_name}

## Overview
This guide covers the full first-time setup of a Netris deployment, from a
freshly installed controller to a functional multi-tenant fabric with BGP
peering.  Follow the steps in order — each builds on the last.

---

## Phase 1: Tenant Setup

### Step 1.1 — Verify the admin tenant
Use `list_tenants` to check whether "{org_name}" already exists as the
primary admin tenant.  If not, use `create_tenant` with:
- name: "{org_name}"
- description: "Primary admin tenant"

Note the tenant ID — it will be referenced throughout this guide.

---

## Phase 2: Site Creation

### Step 2.1 — Create the first site
Use `create_site` with:
- name: "{first_site_name}"
- asn: {site_asn}

Verify with `get_site` using the returned ID.

---

## Phase 3: IP Allocations

IP allocations are top-level IP blocks.  Create one allocation per major
address block, then carve subnets from each.

### Step 3.1 — Management allocation
Use `create_allocation` with:
- name: "{first_site_name}-mgmt-pool"
- prefix: "{mgmt_prefix}"
- tenant: "{org_name}"

### Step 3.2 — Loopback allocation
Use `create_allocation` with:
- name: "{first_site_name}-loopback-pool"
- prefix: "{loopback_prefix}"
- tenant: "{org_name}"

### Step 3.3 — Public / internet allocation
Use `create_allocation` with:
- name: "{first_site_name}-public-pool"
- prefix: "{public_prefix}"
- tenant: "{org_name}"

---

## Phase 4: Subnets

Carve subnets from the allocations for specific purposes.

### Step 4.1 — Management subnet
Use `create_subnet` with:
- prefix: (a subnet within {mgmt_prefix})
- tenant: "{org_name}"
- purpose: "management"
- site: "{first_site_name}"

### Step 4.2 — Loopback subnet
Use `create_subnet` with:
- prefix: (a subnet within {loopback_prefix})
- tenant: "{org_name}"
- purpose: "loopback"
- site: "{first_site_name}"

---

## Phase 5: Infrastructure Registration

### Step 5.1 — Register a SoftGate
Use `create_softgate` with:
- name: "{first_site_name}-sg1"
- site: "{first_site_name}"
- tenant: "{org_name}"
- main_ip: (a free IP from the management subnet)
- mgmt_ip: (the SoftGate's out-of-band management IP)

Verify with `list_inventory` — the SoftGate should appear.

---

## Phase 6: VPC and VNet

### Step 6.1 — Create the primary VPC
Use `create_vpc` with:
- name: "{org_name}-vpc1"
- tenant: "{org_name}"

### Step 6.2 — Create a workload subnet
Use `create_subnet` with:
- prefix: (a workload block, e.g. a /24 within {public_prefix})
- tenant: "{org_name}"
- purpose: "common"
- site: "{first_site_name}"

### Step 6.3 — Create a VNet
Use `create_vnet` with:
- name: "{org_name}-vnet1"
- sites: ["{first_site_name}"]
- tenant: "{org_name}"

---

## Phase 7: BGP Peering

### Step 7.1 — Create an upstream BGP session
Use `create_bgp_session` with:
- name: "{first_site_name}-upstream"
- site: "{first_site_name}"
- neighbor_as: (your upstream provider's ASN)
- neighbor_address: (provider's peering IP)
- local_address: (SoftGate's IP facing the provider)

Verify with `list_bgp_sessions`.

---

## Phase 8: Verification

Run these checks to confirm the full stack is healthy:
1. `list_sites`      — "{first_site_name}" present and active
2. `list_inventory`  — SoftGate registered and status OK
3. `list_subnets`    — all expected prefixes present
4. `list_vpcs`       — VPC present
5. `list_vnets`      — VNet present and attached to site
6. `list_bgp_sessions` — BGP session in Established or Idle state

---

## Notes
- ASN {site_asn} must be unique across all Netris sites
- The SoftGate host must have the Netris agent installed and reachable on
  its management IP before registration will succeed
- BGP sessions will not establish until the SoftGate is online and the
  upstream peer is configured to accept the session from the local address
- For multi-site deployments, repeat Phases 2–7 per additional site
"""
