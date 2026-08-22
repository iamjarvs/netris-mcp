from ..server import mcp

@mcp.prompt()
def provision_vpc(vpc_name: str, tenant: str, subnet_prefix: str = "", site: str = "") -> str:
    """Guide for provisioning a VPC with subnets and a VNet in Netris."""
    return f"""
# Netris VPC Provisioning Guide: {vpc_name}

## Overview
Provisioning a VPC in Netris sets up an isolated network namespace. After creating the VPC, you'll create IP allocations, subnets, and VNets within it.

## Step 1: Check Existing VPCs
Use `list_vpcs` to confirm {vpc_name} doesn't already exist.

## Step 2: Verify Tenant Exists
Use `list_tenants` to confirm "{tenant}" exists. If not, use `create_tenant` to create it first.

## Step 3: Create the VPC
Use `create_vpc` with:
- name: "{vpc_name}"
- tenant: "{tenant}"

Note the `id` returned.

## Step 4: Create an IP Allocation (if needed)
If you have a large address block to subdivide, use `create_allocation` first:
- name: "{vpc_name}-pool"
- prefix: "{subnet_prefix or 'e.g. 10.100.0.0/16'}"
- tenant: "{tenant}"

## Step 5: Create a Subnet
Use `create_subnet` with:
- prefix: "{subnet_prefix or 'the specific subnet, e.g. 10.100.1.0/24'}"
- tenant: "{tenant}"
- purpose: "common" (or "loopback", "management" as appropriate)
{f'- site: "{site}"' if site else "- site: (specify the site name if subnet is site-specific)"}

## Step 6: Create a VNet
A VNet connects the subnet to the network fabric. Use `create_vnet` with:
- name: "{vpc_name}-vnet1"
- sites: ["{site or 'list of site names where this vnet should be available'}"]
- tenant: "{tenant}"
- vlan: (optional VLAN ID if needed)

## Step 7: Verify the Setup
Use `list_subnets` and `list_vnets` to confirm everything is configured correctly.

## Notes
- VPCs provide network isolation — different tenants can use overlapping IP ranges in different VPCs
- VNets are the attachment points for workloads — each site listed gets the VNet provisioned on its fabric
- Subnets can exist without a VNet, but workloads need a VNet to communicate
"""
