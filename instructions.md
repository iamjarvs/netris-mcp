# Instructions for LLMs using Netris MCP Server

This server provides tools to inspect and operate the Netris Network Controller (v4.15+).

## General Guidance
- Always explore fabric state prior to diagnosing issues or performing changes.
- Start with high-level umbrella tools before querying granular tables:
  1. `fabric_inventory(domain='summary')` to understand site, hardware, VPC, and tenant counts.
  2. `fabric_health(scope='overview')` to evaluate alarms, critical heartbeats, and border BGP states.
  3. `triage(symptom=...)` to execute targeted diagnostic playbooks (e.g. `vnet_degraded`, `bgp_session_down`).

## Resource Scoping Conventions
- By default, Netris API queries for IPAM and services resolve to the **Default VPC** unless specified.
- Hardware names in Netris correspond to switch hostnames (e.g. `leaf-pod00-su0-r0`, `ns-leaf-0`, `ns-softgate-0`).

## Safety and Mutations
- The server runs in **read-only** mode by default.
- Any mutating tool requires `dry_run=False` and `NETRIS_MCP_MODE=read-write` configured on the host. Always inspect the returned dry-run diff preview before advising commit operations.
