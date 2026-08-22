from ..server import mcp

@mcp.prompt()
def setup_bgp_peering(peer_name: str, neighbor_as: int, neighbor_address: str, local_address: str, site: str) -> str:
    """Guide for configuring a BGP peering session in Netris."""
    return f"""
# Netris BGP Peering Setup Guide: {peer_name}

## Overview
Setting up BGP peering in Netris creates an eBGP session between the Netris fabric and an external router or peer. You can optionally add route maps and prefix lists for filtering.

## Step 1: Verify Site Exists
Use `get_site` or `list_sites` to confirm "{site}" exists and note its ID.

## Step 2: Check Existing BGP Sessions
Use `list_bgp_sessions` to see current sessions and confirm no conflict with {neighbor_address}.

## Step 3: Check Existing BGP Objects (Optional)
If you need prefix filtering or community-based policies, use `list_bgp_objects` to see available prefix lists and community lists. If none exist yet, you may need to create them first (ask which BGP object types you need).

## Step 4: Check Route Maps (Optional)
Use `list_route_maps` to see available route maps if you need to apply routing policy.

## Step 5: Create the BGP Session
Use `create_bgp_session` with:
- name: "{peer_name}"
- site: "{site}"
- neighbor_as: {neighbor_as}
- neighbor_address: "{neighbor_address}"
- local_address: "{local_address}"
- vnet: (optional — specify VNet name if this BGP session should be within a VNet)

## Step 6: Verify BGP Session
Use `get_bgp_session` with the returned ID to confirm the session configuration.

## Notes
- Netris manages eBGP sessions — the peer router must be configured to accept the session from {local_address}
- AS {neighbor_as} is the remote peer's AS number; your local Netris AS is set per-site (configurable in site settings)
- For ECMP / redundancy, create multiple BGP sessions per site
- Route filtering via BGP objects and route maps is applied on the Netris side
"""
