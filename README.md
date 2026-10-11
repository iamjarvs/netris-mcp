# Netris MCP Server

A Model Context Protocol (MCP) server for [Netris](https://netris.io) cloud networking and AI fabric automation.

Compatible with **Claude Desktop**, **Anti-gravity IDE**, **Cursor**, **VS Code**, and the **Netris Proof of Concept Demo Portal**.

---

## 1. Features

- **Compact Umbrella Dispatchers:** Grouped into high-signal tools (`fabric_inventory`, `virtual_networks`, `routing_and_policy`, `fabric_links`, `fabric_health`, `triage`, `looking_glass`) to maintain a lean LLM token context.
- **Demo Portal Contract:** Includes `./start.sh`, `./stop.sh`, and a live `/api/health` endpoint for plug-and-play portal integration.
- **Switch Shell Execution via Controller:** Secure, allow-listed read-only show commands directly on Cumulus switches via the controller jump host.
- **Multi-Vendor Architecture Guidance:** Built-in operational reference hints for NVIDIA Cumulus Linux, SONiC (Broadcom, NextHop, Dell), Juniper Junos, Nokia SR Linux, and Arista EOS.
- **Safety by Default:** Enforces strict read-only operation unless explicitly overridden with `NETRIS_MCP_MODE=read-write`. All mutating actions default to `dry_run=True`.

---

## 2. Quickstart

### Prerequisites
- Python 3.10+ (tested through Python 3.14)
- Target Netris Controller credentials (e.g., `https://adam-ctl.netris.io`)

### Installation & Interactive Setup
```bash
git clone https://github.com/iamjarvs/netris-mcp.git
cd netris-mcp

python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python setup_cli.py
```

The setup wizard will prompt for your Netris Controller details, verify authentication against the live controller, and automatically configure:
- `.env` configuration file
- `.vscode/mcp.json` for Anti-gravity IDE / Cursor / VS Code
- `claude_desktop_config.example.json`

---

## 3. Running the Server

### Standalone Webserver (Demo Portal Mode)
```bash
./start.sh
# Check health:
curl http://localhost:8750/api/health
# Stop service:
./stop.sh
```

### STDIO Mode (Direct CLI / MCP Client)
```bash
./start.sh --stdio
```

---

## 4. Repository Structure

```text
├── start.sh              # Standard executable entrypoint (creates .venv, starts server)
├── stop.sh               # Standard teardown script (graceful termination)
├── setup_cli.py          # Interactive configuration wizard
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Hatchling project configuration
├── instructions.md       # AI agent guidance and tool conventions
├── app/                  # Application package
│   ├── config.py         # Root-aware configuration loader
│   ├── netris_client.py  # Async v1 & v2 Netris API client with cookie auth
│   ├── webserver.py      # Starlette webserver exposing /api/health
│   ├── server.py         # FastMCP server instance (STDIO & Streamable HTTP)
│   ├── tools_dispatch.py # Compact umbrella tools (Inventory, VNet, Policy, Links)
│   ├── diagnostics_dispatch.py # Health, Audit, Triage, and Looking Glass
│   ├── switch_exec.py    # Allow-listed switch show commands via SSH jump host
│   └── architecture_hints.py # Multi-vendor NOS troubleshooting hints
├── lab-guide/            # Full documentation & integration guide
│   ├── 01-introduction.md
│   ├── 02-prerequisites-and-install.md
│   ├── 03-connect-clients.md
│   ├── 04-tools-reference.md
│   └── 05-troubleshooting.md
└── tests/                # Automated pytest suite (respx + live integration)
```

---

## 5. Tool Catalog

| Tool Name | Domain / Actions | Description |
|---|---|---|
| `fabric_inventory` | `summary`, `sites`, `tenants`, `vpcs`, `hardware`, `controllers`, `profiles` | Unified inventory across physical hardware and logical tenants. |
| `virtual_networks` | `list_vnets`, `vnet_detail`, `ipam_tree`, `vpc_peerings` | EVPN V-Nets, hierarchical IPAM subnets, and VPC peerings. |
| `routing_and_policy`| `ebgp_sessions`, `ebgp_routemaps`, `acls`, `static_routes`, `nat_rules`, `l4lb_services` | Border BGP sessions, route maps, security ACLs, and L4 load balancers. |
| `fabric_links` | `links_summary`, `links_list`, `interfaces_list` | Dual-ended physical link cabling, optical telemetry, and switch ports. |
| `fabric_health` | `overview`, `heartbeats`, `hardware_health`, `ebgp_health` | Holistic fabric health evaluation across agent heartbeats and hardware alarms. |
| `fabric_audit` | `events`, `monitoring_checks` | Audits system events and sensor threshold configurations. |
| `triage` | `vnet_degraded`, `bgp_session_down`, `node_unreachable`, `fabric_health_check` | Automated root-cause troubleshooting playbook. |
| `looking_glass` | `peers_list`, `inspect_peer` | Live routing daemon telemetry directly from fabric switches. |
| `run_switch_command` | Target IP/Name + Read-only show command | Executes allow-listed show commands (`nv show`, `sudo vtysh`, `ip route`) on switches via the controller jump host. |
| `architecture_reference` | `cumulus`, `sonic`, `junos`, `nokia_sr_linux`, `arista_eos` | Retrieves operational architecture guidance, troubleshooting hints, and recommended show commands. |
| `mutate_vnet` | `create`, `delete` (Gated: requires `read-write` mode) | Provisions or deletes tenant V-Nets with dry-run preview diffs and audit logging. |

---

## 6. Testing

Run the automated test suite:
```bash
./.venv/bin/pytest -v
```
