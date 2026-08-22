# Netris MCP Server

**Use natural language to manage your Netris network fabric.**

---

## What it does

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard that lets AI assistants connect to external tools and data sources. This server implements MCP for [Netris](https://netris.io), a network automation platform that manages physical and virtual network infrastructure. Once connected, you can ask Claude (or any MCP-compatible client) to list sites, create VPCs, configure BGP sessions, set up load balancers, manage NAT rules, and more — all in plain English, without logging into the Netris web UI or writing API calls yourself.

The server exposes **72 tools** across 12 modules covering the Netris API surface: VPCs, VPC peering, virtual networks (VNets), eBGP sessions, BGP policy objects, sites, device inventory, IPAM (subnets and allocations), NAT rules, L4 load balancers, ACLs, static routes, and tenants. It also provides **10 workflow guides** (MCP prompts) that walk Claude through multi-step operations — from bootstrapping a new deployment and GPU cluster provisioning to VPC peering, ACL setup, and network troubleshooting.

---

## Requirements

- Python 3.10 or later
- [`uv`](https://github.com/astral-sh/uv) package manager
- A running Netris controller (self-hosted or cloud) with valid credentials

---

## Installation

```bash
git clone <repo-url>
cd netris-mcp
uv sync
```

---

## Configuration

### Environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
NETRIS_HOST=netris.example.com
NETRIS_USERNAME=admin
NETRIS_PASSWORD=your-password-here
```

The full set of environment variables is:

| Variable | Required | Default | Description |
|---|---|---|---|
| `NETRIS_HOST` | Yes | — | Hostname or IP of the Netris controller. No scheme — e.g. `netris.example.com`, not `https://...`. |
| `NETRIS_USERNAME` | Yes | — | Netris login username. |
| `NETRIS_PASSWORD` | Yes | — | Netris login password. |
| `NETRIS_SSL_VERIFY` | No | `true` | Set to `false` or `0` to disable TLS certificate verification. Only do this in trusted lab environments. |
| `NETRIS_SESSION_REFRESH` | No | `1800` | How often (in seconds) the server pings the Netris API to keep the session alive. Minimum 60. |
| `NETRIS_TIMEOUT` | No | `30.0` | Per-request HTTP timeout in seconds. |

Variables can be set in a `.env` file in the project root, or passed directly in the environment (e.g. via the Claude Desktop config below).

---

## Connecting to Claude Desktop

Add the following to your Claude Desktop configuration file. On macOS, the file is at `~/Library/Application Support/Claude/claude_desktop_config.json`.

```json
{
  "mcpServers": {
    "netris": {
      "command": "uv",
      "args": ["--directory", "/path/to/netris-mcp", "run", "netris-mcp"],
      "env": {
        "NETRIS_HOST": "your-netris-controller.example.com",
        "NETRIS_USERNAME": "admin",
        "NETRIS_PASSWORD": "your-password"
      }
    }
  }
}
```

Replace `/path/to/netris-mcp` with the absolute path to where you cloned this repository. Restart Claude Desktop after editing the config. A ready-to-copy example is also available at [`examples/claude_desktop_config.json`](examples/claude_desktop_config.json).

---

## Available Tools

### VPC (`tools/vpc.py`)

| Tool | Description |
|---|---|
| `list_vpcs` | List all VPCs in Netris. |
| `get_vpc` | Get a single VPC by ID. |
| `create_vpc` | Create a new VPC, assigning it to a named tenant. |
| `delete_vpc` | Delete a VPC by ID. |
| `set_default_vpc` | Mark a VPC as the default VPC for the deployment. |

### VNet (`tools/vnet.py`)

| Tool | Description |
|---|---|
| `list_vnets` | List all virtual networks (VNets) in Netris. |
| `get_vnet` | Get a single VNet by ID. |
| `create_vnet` | Create a new VNet, associating it with one or more sites and a tenant. Optionally assigns a VLAN ID. |
| `delete_vnet` | Delete a VNet by ID. |

### BGP (`tools/bgp.py`)

| Tool | Description |
|---|---|
| `list_bgp_sessions` | List all eBGP peer sessions in Netris. |
| `get_bgp_session` | Get a single eBGP session by ID. |
| `create_bgp_session` | Create an eBGP session with neighbor AS, IPs, optional password/BFD/multihop. |
| `delete_bgp_session` | Delete an eBGP session by ID. |
| `list_bgp_objects` | List all BGP objects (prefix lists, community lists). |
| `create_bgp_object` | Create a BGP prefix list or community list for route filtering. |
| `delete_bgp_object` | Delete a BGP object by ID. |
| `list_route_maps` | List all route maps for BGP policy. |
| `create_route_map` | Create a route map with permit/deny rules for BGP policy. |
| `delete_route_map` | Delete a route map by ID. |

### Sites (`tools/sites.py`)

| Tool | Description |
|---|---|
| `list_sites` | List all sites in Netris. |
| `get_site` | Get a single site by ID. |
| `create_site` | Create a site with name, public ASN, and optional ROH/VM ASNs and site mesh. |
| `update_site` | Update a site's name, ASN, or mesh topology. |
| `delete_site` | Delete a site by ID. |

### Inventory (`tools/inventory.py`)

| Tool | Description |
|---|---|
| `list_inventory` | List all hardware inventory (switches, SoftGates, controllers). |
| `get_inventory_item` | Get a single inventory item by ID. |
| `list_controllers` | List all Netris controller nodes. |
| `list_softgates` | List all SoftGate nodes. |
| `get_softgate` | Get a single SoftGate by ID. |
| `create_softgate` | Register a new SoftGate at a site with main and management IPs. |
| `update_softgate` | Update a SoftGate's IP configuration. |
| `delete_softgate` | Remove a SoftGate from inventory. |
| `list_switches` | List all switches managed by Netris. |
| `get_switch` | Get a single switch by ID. |

### IPAM (`tools/ipam.py`)

| Tool | Description |
|---|---|
| `list_subnets` | List all subnets in the Netris IPAM (`/api/v2/ipam/subnet/`). |
| `get_subnet` | Get a single subnet by ID. |
| `create_subnet` | Create a subnet with prefix, tenant, purpose (`common`/`loopback`/`management`/`load-balancer`/`nat`/`inactive`), and optional site. |
| `update_subnet` | Update a subnet's purpose or site assignments. |
| `delete_subnet` | Delete a subnet by ID. |
| `list_allocations` | List all top-level IP allocations. |
| `get_allocation` | Get a single allocation by ID. |
| `create_allocation` | Create a new top-level IP allocation block. |
| `delete_allocation` | Delete an allocation by ID. |

### NAT (`tools/nat.py`)

| Tool | Description |
|---|---|
| `list_nat_rules` | List all NAT rules (SNAT and DNAT). |
| `get_nat_rule` | Get a single NAT rule by ID. |
| `create_snat_rule` | Create a Source NAT rule — rewrites source IP of outbound packets. Requires `snat_to_ip`. |
| `create_dnat_rule` | Create a Destination NAT rule — port-forwards inbound traffic to an internal host. |
| `update_nat_rule` | Enable or disable a NAT rule. |
| `delete_nat_rule` | Delete a NAT rule by ID. |

### L4 Load Balancer (`tools/l4lb.py`)

| Tool | Description |
|---|---|
| `list_l4lb` | List all L4 load balancers. |
| `get_l4lb` | Get a single L4LB by ID. |
| `create_l4lb` | Create an L4LB with frontend VIP/port, protocol, and backend pool. |
| `update_l4lb_backends` | Replace the backend pool of an existing L4LB. |
| `delete_l4lb` | Delete an L4LB by ID. |

### Tenants (`tools/tenants.py`)

| Tool | Description |
|---|---|
| `list_tenants` | List all tenants. |
| `get_tenant` | Get a single tenant by ID. |
| `create_tenant` | Create a tenant with subnet/VNet quotas. |
| `update_tenant` | Update a tenant's name or description. |
| `delete_tenant` | Delete a tenant (requires all owned resources removed first). |

### VPC Peering (`tools/vpc_peering.py`)

| Tool | Description |
|---|---|
| `list_vpc_peerings` | List all VPC peering connections. |
| `get_vpc_peering` | Get a single VPC peering by ID. |
| `create_vpc_peering` | Peer two VPCs to enable cross-VPC routing. Most commonly used to peer a tenant VPC with the System VPC for internet access. |
| `delete_vpc_peering` | Delete a VPC peering by ID. |

### Static Routes (`tools/static_routes.py`)

| Tool | Description |
|---|---|
| `list_static_routes` | List all static routes across all VPCs. |
| `get_static_route` | Get a single static route by ID. |
| `create_static_route` | Create a static route with destination prefix, next-hop, VPC, and site. |
| `delete_static_route` | Delete a static route by ID. |

### ACL (`tools/acl.py`)

| Tool | Description |
|---|---|
| `list_acls` | List all ACL rules in Netris. |
| `get_acl` | Get a single ACL rule by ID. |
| `create_acl` | Create an ACL permit/deny rule with source/destination CIDR, optional protocol and port matching. |
| `delete_acl` | Delete an ACL rule by ID. |

---

## Available Guides (Prompts)

MCP prompts are workflow guides that instruct Claude on the correct sequence of steps and tools to use for multi-step operations. Invoke them by name in Claude Desktop (e.g. "Use the site onboarding guide for site DC-West with ASN 65001").

| Guide | Parameters | What it does |
|---|---|---|
| `onboard_new_site` | `site_name`, `asn`, `location` (optional) | Walks through creating a site, verifying it, checking controllers, and registering SoftGates. |
| `provision_vpc` | `vpc_name`, `tenant`, `subnet_prefix` (optional), `site` (optional) | Guides through creating a VPC, IP allocation, subnet, and VNet in the correct order. |
| `setup_bgp_peering` | `peer_name`, `neighbor_as`, `neighbor_address`, `local_address`, `site` | Steps through verifying prerequisites, checking existing sessions, and creating an eBGP session with optional route policy. |
| `setup_load_balancer` | `lb_name`, `site`, `tenant`, `frontend_ip`, `frontend_port`, `protocol` (default `tcp`) | Covers prerequisite checks, backend preparation, L4LB creation, and health status verification. |
| `bootstrap_network` | `org_name`, `first_site_name`, `site_asn`, `mgmt_prefix`, `loopback_prefix`, `public_prefix` | End-to-end first-time setup: tenant → site → IP allocations → subnets → SoftGate → VPC → VNet → BGP peering, with a final verification checklist. |

---

## Example usage

**List all sites**
> "What sites do I have in Netris?"

Claude calls `list_sites` and presents the results in a readable table.

**Provision a VPC**
> "I need a new VPC called 'prod-vpc' for the 'acme' tenant using subnet 10.100.0.0/24 at site DC-East. Use the VPC provisioning guide."

Claude invokes the `provision_vpc` guide, then calls `list_tenants` (verify tenant), `create_vpc`, `create_allocation`, `create_subnet`, and `create_vnet` in order.

**Set up BGP peering**
> "Configure BGP peering with our upstream ISP at 198.51.100.1 (AS 64512). Our local address is 198.51.100.2 and the site is DC-West."

Claude calls `list_sites` to verify the site, `list_bgp_sessions` to check for conflicts, then `create_bgp_session`.

**Set up a load balancer**
> "Create an L4 load balancer called 'api-lb' on site DC-East for tenant acme. Frontend is 203.0.113.10:443 TCP with backends 10.0.1.10:8443 and 10.0.1.11:8443."

Claude calls `list_sites`, `list_tenants`, `list_l4lb` (conflict check), then `create_l4lb`.

**Bootstrap a new deployment**
> "Bootstrap a fresh Netris deployment for organisation 'AcmeCorp'. First site is 'HQ' with ASN 65000. Use management block 10.0.0.0/24, loopback 10.0.255.0/29, public 203.0.113.0/26."

Claude invokes the `bootstrap_network` guide and executes all 7 phases in sequence.

---

## Authentication

This server uses Netris's cookie-based session authentication. On startup, it posts your credentials to `/api/v2/auth/login` and stores the returned `connect.sid` session cookie in a persistent `httpx.AsyncClient`. A background task re-hits the `/api/v2/auth/profile` endpoint every `NETRIS_SESSION_REFRESH` seconds (default 30 minutes) to prevent the session from expiring during a long-running server process.

Your credentials are read once from the environment at startup and are never transmitted to the AI model or stored outside the running process. They stay on your machine, in your `.env` file or the Claude Desktop config's `env` block.

---

## Adding new tools

1. Create a new file in `src/netris_mcp/tools/`, e.g. `src/netris_mcp/tools/myresource.py`.
2. Import `mcp` from `..server` and define `async def` functions decorated with `@mcp.tool()`.
3. Use `api_url()` from `..client` to build URLs and `get`/`post`/`put`/`delete` to make requests.
4. Add an import line at the bottom of `src/netris_mcp/server.py`:
   ```python
   from .tools import myresource  # noqa: E402, F401
   ```

The decorator registers the tool with the MCP server at import time. See the `CLAUDE.md` file for the exact code pattern and rules to follow.

---

## API endpoint verification

URL paths in the tool source files include inline comments linking to the Netris OpenAPI specification at [netrisai/swagger-sources](https://github.com/netrisai/swagger-sources) for quick cross-referencing. Some resource names differ from the obvious pattern (for example, BGP sessions use `/api/v2/ebgp/`, and VNets use `/api/v2/v-net/`). Always verify against the Swagger source when adding new endpoints.

---

## License

MIT
