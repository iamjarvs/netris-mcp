from ..server import mcp

@mcp.prompt()
def onboard_new_site(site_name: str, asn: int, location: str = "") -> str:
    """Guide for onboarding a new network site in Netris."""
    return f"""
# Netris Site Onboarding Guide: {site_name}

## Overview
Onboarding a new site in Netris requires creating the site definition, then registering the physical infrastructure (controllers, softgates) that will run at that site.

## Step 1: Check Existing Sites
First, use `list_sites` to see all existing sites and confirm {site_name} doesn't already exist.

## Step 2: Create the Site
Use `create_site` with these parameters:
- name: "{site_name}"
- asn: {asn}
{f'- location: "{location}"' if location else "- location: (optional, can be omitted)"}

Note the `id` returned — you will need it for subsequent steps.

## Step 3: Verify Site Creation
Use `get_site` with the returned ID to confirm the site was created correctly.

## Step 4: Check Available Controllers
Use `list_controllers` to see which controllers are registered and available to associate with this site.

## Step 5: Register Softgates (if needed)
If this site needs a software gateway (for routing, NAT, load balancing), use `create_softgate` with:
- name: "{site_name}-sg1" (suggested naming)
- site: "{site_name}"
- tenant: the appropriate tenant name (use `list_tenants` to find it)
- main_ip: the softgate's main IP address (on the management network)
- mgmt_ip: the softgate's management IP address

## Step 6: Verify Full Setup
Use `list_inventory` to confirm the site appears with its associated devices.

## Notes
- ASN {asn} must be unique across all sites in this Netris deployment
- Softgates require physical or virtual machines pre-configured with the Netris agent
- After creating a site, you may want to add subnets — see the VPC provisioning guide
"""
