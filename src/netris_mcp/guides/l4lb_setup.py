from ..server import mcp

@mcp.prompt()
def setup_load_balancer(lb_name: str, site: str, tenant: str, frontend_ip: str, frontend_port: int, protocol: str = "tcp") -> str:
    """Guide for setting up an L4 load balancer in Netris."""
    return f"""
# Netris L4 Load Balancer Setup Guide: {lb_name}

## Overview
Netris L4 load balancing distributes traffic to backend servers based on IP/port. This guide walks through creating an L4LB with backends.

## Step 1: Verify Prerequisites
- Use `list_sites` to confirm "{site}" exists
- Use `list_tenants` to confirm "{tenant}" exists
- Confirm {frontend_ip} is routable and not already in use (check `list_l4lb`)

## Step 2: Prepare Backend Information
Before creating the LB, gather:
- Backend server IPs and ports (the servers that will receive traffic)
- Health check configuration (Netris uses active health checks)

## Step 3: Create the Load Balancer
Use `create_l4lb` with:
- name: "{lb_name}"
- site: "{site}"
- tenant: "{tenant}"
- frontend_ip: "{frontend_ip}"
- frontend_port: {frontend_port}
- protocol: "{protocol}"
- backends: [
    {{"ip": "10.x.x.1", "port": {frontend_port}}},   ← replace with actual backend IPs
    {{"ip": "10.x.x.2", "port": {frontend_port}}}    ← add as many backends as needed
  ]

## Step 4: Verify the Load Balancer
Use `get_l4lb` with the returned ID to confirm configuration.

## Step 5: Check Health Status
Use `list_l4lb` and examine the status field to verify backends are healthy.

## Notes
- Protocol can be "tcp" or "udp"
- Frontend IP must be within an IP range managed by Netris (check allocations with `list_allocations`)
- Netris automatically programs the network fabric to route {frontend_ip}:{frontend_port} traffic to the backends
- For HTTPS termination, use an application-layer proxy — Netris L4LB is layer 4 only
"""
