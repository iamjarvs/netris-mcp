# 04 — Tools Reference Guide

| Tool Name | Domain / Actions | Description |
|---|---|---|
| `fabric_inventory` | `summary`, `sites`, `tenants`, `vpcs`, `hardware`, `controllers`, `profiles` | Unified inventory across physical fabric and logical tenant abstractions. |
| `virtual_networks` | `list_vnets`, `vnet_detail`, `ipam_tree`, `vpc_peerings` | Inspects tenant EVPN overlays, hierarchical IPAM subnets, and peering routes. |
| `routing_and_policy`| `ebgp_sessions`, `ebgp_routemaps`, `acls`, `static_routes`, `nat_rules`, `l4lb_services` | Inspects border BGP peerings, prefix match lists, security ACLs, and L4 load balancers. |
| `fabric_links` | `links_summary`, `links_list`, `interfaces_list` | Inspects dual-ended physical link cabling, optical telemetry, and switch port states. |
| `fabric_health` | `overview`, `heartbeats`, `hardware_health`, `ebgp_health` | Holistic fabric health evaluation across agent heartbeats and hardware alarms. |
| `fabric_audit` | `events`, `monitoring_checks` | Audits system events and sensor threshold configurations. |
| `triage` | `vnet_degraded`, `bgp_session_down`, `node_unreachable`, `fabric_health_check` | Automated root-cause troubleshooting playbook. |
| `looking_glass` | `peers_list`, `inspect_peer` | Live routing daemon telemetry directly from fabric switches. |
| `run_switch_command` | Target IP/Name + Read-only show command | Executes verified, allow-listed show commands (`nv show`, `sudo vtysh`, `ip route`) on switches via the controller jump host. |
| `architecture_reference` | `cumulus`, `sonic`, `junos`, `nokia_sr_linux`, `arista_eos` | Retrieves operational architecture guidance, troubleshooting hints, and recommended show commands. |
| `mutate_vnet` | `create`, `delete` (Gated: requires `read-write` mode) | Provisions or deletes tenant V-Nets with dry-run preview diffs and audit logging. |
