# CLAUDE.md — Netris MCP Server

This file documents the codebase for LLMs working in this repository. Read it before making any changes.

---

## What this project is

This is an **MCP (Model Context Protocol) server** for [Netris](https://netris.io), a network automation platform. MCP is an open standard that lets AI assistants call tools and use workflow guides exposed by external servers. This server exposes Netris's REST API as MCP tools so an AI assistant (e.g. Claude) can manage network infrastructure using natural language — creating sites, VPCs, BGP sessions, load balancers, and more.

The server runs as a local process and communicates with the AI client over **STDIO using JSON-RPC**. It authenticates to a Netris controller once at startup and maintains a live session for the lifetime of the process.

---

## Architecture

### Key files

| File | Role |
|---|---|
| `src/netris_mcp/server.py` | MCPServer instance, lifespan (auth + session refresh), tool/guide module imports |
| `src/netris_mcp/config.py` | `get_config()` reads env vars → `NetrisConfig` dataclass |
| `src/netris_mcp/auth.py` | `login()` and `refresh_session()` — cookie-based auth |
| `src/netris_mcp/client.py` | `get()`, `post()`, `put()`, `delete()`, `api_url()` — HTTP helpers |
| `src/netris_mcp/tools/*.py` | `@mcp.tool()` functions — the callable tools exposed to the LLM |
| `src/netris_mcp/guides/*.py` | `@mcp.prompt()` functions — workflow guides (multi-step instructions) |
| `pyproject.toml` | Project metadata, dependencies, `netris-mcp` CLI entrypoint |

### Registration pattern

`server.py` creates the `MCPServer` instance:

```python
mcp = MCPServer("Netris", lifespan=lifespan)
```

Tool and guide modules are then imported at the bottom of `server.py`. Each module imports `mcp` from `server` and registers its functions at import time via decorators:

```python
# server.py — registration happens via import
from .tools import vpc       # noqa: E402, F401
from .tools import bgp       # noqa: E402, F401
from .guides import site_onboarding  # noqa: E402, F401
```

This works because `@mcp.tool()` and `@mcp.prompt()` register against the module-level `mcp` object the moment the decorator runs (i.e. at import time). The `# noqa: F401` suppresses the "imported but unused" linter warning — these imports are side-effect-only and intentional.

### Lifespan context

The `lifespan` context manager in `server.py` runs at startup and shutdown:

**Startup:**
1. Calls `get_config()` to read environment variables.
2. Calls `login()` to POST credentials to Netris → gets the `connect.sid` session cookie.
3. Creates a long-lived `httpx.AsyncClient` with the cookie baked in.
4. Starts a background `asyncio.Task` that calls `refresh_session()` every `session_refresh_seconds` to prevent session expiry.
5. Yields a `NetrisContext` dataclass to all tool handlers.

**Shutdown:**
6. Cancels the background refresh task (swallows `CancelledError`).
7. Closes the `httpx.AsyncClient` (handled by the `async with` block).

```python
@dataclass
class NetrisContext:
    client: httpx.AsyncClient
    base_url: str
```

Tools access the context through `ctx.request_context.lifespan_context`, which returns the `NetrisContext` instance.

---

## Netris Platform Concepts

This section explains the Netris domain model so an LLM can use the MCP tools correctly. Read this before deciding which tools to call and how to populate their parameters.

### 1. Resource Hierarchy

```
Tenant → VPC → [V-Net, Subnet, BGP session, NAT rule, L4LB, Static Route]
Site   → [SoftGate, Switch, Controller, Links]
```

- A **Tenant** owns resources. Every VPC, subnet, VNet, NAT rule, and L4LB must belong to a tenant.
- A **VPC** is a routing domain (VRF). It spans all sites and provides isolation between tenants.
- A **Site** is a physical or logical location with its own switch fabric and ASN.
- VPCs and Sites are orthogonal: a VPC can have resources at multiple sites.

### 2. VPC vs. V-Net

This is the most important distinction for using the API correctly:

- **VPC** = an isolated routing domain (like a VRF). Controls *who* owns the network and enforces isolation between tenants. A VPC spans all sites.
- **V-Net** = a group of switch ports forming a network segment (like a VLAN or routed subnet). Lives *inside* a VPC. Can span multiple sites. Has ports attached to it.
- One VPC can have many V-Nets; one V-Net belongs to exactly one VPC.
- Creating a VPC does **NOT** create any network connectivity — you still need V-Nets, subnets, and optionally BGP sessions.

### 3. The System VPC

- Every Netris deployment has a special "System VPC" (sometimes called "Default VPC").
- It anchors infrastructure: upstream BGP sessions, NAT IPs, L4LB VIPs.
- To give workloads in a tenant VPC internet access you must: (a) peer the tenant VPC with the System VPC using `create_vpc_peering`, then (b) create SNAT/DNAT rules in the System VPC.
- Use `list_vpcs` to find the System VPC — it is usually the first VPC or named "System VPC".

### 4. SoftGate Role

- A SoftGate is a software-based gateway running on a regular Linux server.
- It provides: NAT, L4LB, BGP termination (SoftGate-mode), and ACL enforcement.
- You **must** have a SoftGate registered at a site before you can use NAT, L4LB, or SoftGate-terminated BGP at that site.
- Register a SoftGate with `create_softgate` — you will also need to install the Netris agent on the server.

### 5. IPAM Subnet Purposes

The `purpose` field on a subnet controls what services can use it. This is critical — using the wrong purpose causes Netris to reject or silently ignore the resource:

| Purpose | Allowed use |
|---|---|
| `"common"` | General workload networks (V-Net gateways, DHCP pools) |
| `"loopback"` | Hardware loopback IPs (switches, SoftGates) |
| `"management"` | Out-of-band management, ZTP |
| `"load-balancer"` | L4LB VIP addresses — L4LB frontend IPs **must** come from a load-balancer subnet |
| `"nat"` | NAT translated addresses — SNAT/DNAT IPs **must** come from a nat subnet |
| `"inactive"` | Reserved, not in use |

If you assign an L4LB a VIP from a `"common"` subnet, Netris will likely reject it or not announce it.

### 6. BGP Termination Modes

Two ways to terminate BGP in Netris:

- **SoftGate BGP**: The SoftGate process runs BGP. Supports NAT/L4LB integration, route-maps, BFD, and multihop. Use `create_bgp_session` with `site` pointing to a site that has a SoftGate.
- **Switch BGP (VPC Connect)**: Line-rate BGP terminated on a switch. No NAT/L4LB integration. For pure routing use cases.

If you do not have a SoftGate at the site, you cannot use SoftGate BGP.

### 7. V-Net Transport Modes

- **L2VPN**: Ports share a Layer 2 broadcast domain (like a VLAN). Optional Layer 3 gateway (SVI/IRB). Use `update_vnet` with `gateway` to add a gateway.
- **L3VPN**: Each port gets a /31 point-to-point routed link. No ARP flooding. Used for GPU clusters and ROH (Routing on Host). Configured by setting the V-Net gateway and attaching ports.

### 8. API Field Names Cheat Sheet

The Netris API uses camelCase field names that differ from the Python parameter names exposed by these tools:

| Resource | Python param | API field name |
|---|---|---|
| Site | `public_asn` | `publicAsn` |
| Site | `roh_asn` | `rohAsn` |
| Site | `vm_asn` | `vmAsn` |
| BGP session | `neighbor_address` | `remoteIP` |
| BGP session | `local_address` | `localIP` |
| BGP session | `neighbor_as` | `neighborAs` |
| L4LB | `frontend_ip` | `ip` |
| L4LB | `frontend_port` | `port` |
| SoftGate | `main_ip` | `mainIp` |
| SoftGate | `mgmt_ip` | `mgmtIp` |
| VNet gateway | `gateway` | `gateways[0].gateway` |
| SNAT | `snat_to_ip` | `translatedAddress` |

### 9. Hardware Endpoint Paths

Hardware inventory uses the `/api/v2/hw/` prefix:

| Resource | API path |
|---|---|
| SoftGate | `/api/v2/hw/softgate` |
| Switch | `/api/v2/hw/switch` |
| Controller | `/api/v2/hw/controller` |
| General inventory | `/api/v2/hw/` |

IPAM uses the `/api/v2/ipam/` prefix:

| Resource | API path |
|---|---|
| Subnets | `/api/v2/ipam/subnet` |
| Allocations | `/api/v2/ipam/allocation` |

---

## Critical rules

- **NEVER use `print()`**. The server runs over STDIO; stdout is reserved for the MCP JSON-RPC wire protocol. Any stray `print()` call will corrupt the protocol stream and crash the client. Always use `logging.getLogger(__name__)` and write to stderr. The logging config in `server.py` points the root logger at `sys.stderr`.

- **All tools must be `async def`**. MCPServer runs an asyncio event loop. Synchronous tools will block it.

- **Tools get the HTTP client from the lifespan context.** Always start a tool with:
  ```python
  nc = ctx.request_context.lifespan_context
  ```
  Then use `nc.client` for the httpx client and `nc.base_url` for the controller URL.

- **Return strings from tools**. The MCP framework transmits the return value to the LLM as a text result. Return a descriptive string — not a dict, not `None`.

- **NO classes**. This codebase is functional Python. Use `@dataclass` for data containers (like `NetrisContext`, `NetrisConfig`), but do not define classes with methods. All logic is in plain functions.

- **Type annotations on tool parameters are required**. MCPServer generates the MCP JSON Schema for each tool from the Python type annotations. A parameter with no annotation will not appear in the schema and the LLM will not know to pass it.

- **`Optional[T]` makes a parameter optional in the MCP schema**. Parameters without `Optional` are required — the LLM must always supply them.

- **Docstrings on tools become the tool description shown to the LLM**. Write clear, accurate docstrings. The first line is the short description; `Args:` block describes each parameter. The LLM reads these to decide which tool to call and how to populate parameters.

---

## Adding a new tool

1. Create `src/netris_mcp/tools/myresource.py`.
2. Write the module following this exact pattern:

```python
# src/netris_mcp/tools/myresource.py
import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..server import mcp
from ..client import get, post, put, delete, api_url

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_myresources(ctx: Context) -> str:
    """List all myresources in Netris.

    Returns a string representation of all myresource objects from the Netris API.
    """
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/myresource/ — verify against netrisai/swagger-sources
    data = await get(nc.client, api_url(nc.base_url, "myresource"))
    return str(data)


@mcp.tool()
async def create_myresource(ctx: Context, name: str, site: str, optional_field: Optional[str] = None) -> str:
    """Create a new myresource in Netris.

    Args:
        name: The name for the new resource.
        site: The site name where this resource is created.
        optional_field: An optional description or tag.
    """
    nc = ctx.request_context.lifespan_context
    payload: dict = {"name": name, "site": {"name": site}}
    if optional_field is not None:
        payload["optionalField"] = optional_field
    data = await post(nc.client, api_url(nc.base_url, "myresource"), payload)
    return f"Created myresource with ID {data.get('id', 'unknown')}"
```

3. Add a registration import to the bottom of `src/netris_mcp/server.py`, after the existing tool imports:

```python
from .tools import myresource  # noqa: E402, F401
```

That is all. The decorator handles registration.

---

## Adding a new guide

Guides are MCP prompts — they return a formatted string of instructions that tell the LLM which tools to call and in what order. They do not call tools themselves.

```python
# src/netris_mcp/guides/myworkflow.py
from ..server import mcp


@mcp.prompt()
def my_workflow(param_one: str, param_two: int) -> str:
    """Guide for doing something complex in Netris."""
    return f"""
# My Workflow Guide: {param_one}

## Step 1
Use `list_sites` to ...

## Step 2
Use `create_vpc` with:
- name: "{param_one}"
- ...
"""
```

Then register it in `server.py`:

```python
from .guides import myworkflow  # noqa: E402, F401
```

Note: guide functions are **not** `async def` — `@mcp.prompt()` functions are synchronous string builders, not coroutines.

---

## Auth

Netris uses **cookie-based session authentication exclusively** — no API keys, no Bearer tokens. The session cookie is named `connect.sid`.

- `auth.login()` opens a short-lived `httpx.AsyncClient`, POSTs to `/api/v2/auth/login` with `{"login": username, "password": password}`, extracts the cookie jar, and closes the client. The caller stores the cookies on the long-lived client.
- `auth.refresh_session()` GETs `/api/v2/auth/profile` using the long-lived client. This is called by the background task in `server.py`. Failures are logged as warnings and swallowed — the next real API call will surface a 401 if the session has genuinely expired.
- Session expiry: if you see `HTTP 401` errors from tool calls (not from the refresh loop), the session has expired. Restart the server to re-authenticate. The root cause is usually `NETRIS_SESSION_REFRESH` set too high, or a network interruption during a gap between refreshes.

---

## URL patterns

Use `api_url()` from `client.py` to build all URLs. Never construct URL strings manually.

```python
api_url(base_url, "resource")        # → https://host/api/v2/resource/   (collection)
api_url(base_url, "resource", 42)    # → https://host/api/v2/resource/42  (single item)
```

**Important exceptions** — some Netris resource names differ from their logical names:

| Logical name | Actual API path segment |
|---|---|
| BGP sessions | `ebgp` |
| VNet | `v-net` |
| BGP objects | `bgp-object` |
| Route maps | `routemap` |

Always verify the path against the Netris OpenAPI spec at [netrisai/swagger-sources](https://github.com/netrisai/swagger-sources) when adding new endpoints. The existing tool files include inline comments like `# URL: /api/v2/ebgp/ — verify against netrisai/swagger-sources` as a reminder.

---

## Error handling

`client.py` raises `RuntimeError` on:
- Non-2xx HTTP status (with the status code and response body in the message)
- Non-JSON response body
- Network errors (`httpx.RequestError`)

**Do not catch `RuntimeError` in tool code unless you have a specific recovery action.** Let it propagate to the MCPServer framework, which converts unhandled exceptions into MCP error responses that the LLM can read and relay to the user.

Do not catch-and-swallow errors in tools. If something goes wrong, the LLM needs to see it.

The one exception to this rule is in `auth.refresh_session()`, where network errors are intentionally swallowed so the background refresh loop continues running. That is documented in the function's docstring.

---

## Testing

Run the test suite with:

```bash
uv run pytest
```

Dev dependencies (`pytest`, `pytest-asyncio`, `respx`) are declared in `pyproject.toml` under `[tool.uv] dev-dependencies`. `respx` is an httpx mock library suitable for testing async HTTP calls without a live Netris controller.

Tests live in `tests/`. The `tests/__init__.py` file is currently empty — add test modules alongside it.

---

## Key files map

| Path | Purpose |
|---|---|
| `pyproject.toml` | Project metadata, dependencies, `netris-mcp` CLI entry point (`netris_mcp.server:main`) |
| `.env.example` | Template for environment variable configuration |
| `src/netris_mcp/server.py` | MCPServer (mcp) instance, lifespan, `NetrisContext` dataclass, tool/guide import block |
| `src/netris_mcp/config.py` | `NetrisConfig` dataclass, `get_config()` — reads and validates all env vars |
| `src/netris_mcp/auth.py` | `login()` → cookie dict, `refresh_session()` → keep-alive ping |
| `src/netris_mcp/client.py` | `api_url()`, `get()`, `post()`, `put()`, `delete()` — all HTTP I/O lives here |
| `src/netris_mcp/tools/vpc.py` | VPC tools: list, get, create, delete, set-default |
| `src/netris_mcp/tools/vnet.py` | VNet tools: list, get, create, delete |
| `src/netris_mcp/tools/bgp.py` | BGP tools: list/get/create/delete sessions, list BGP objects, list route maps |
| `src/netris_mcp/tools/sites.py` | Site tools: list, get, create, delete |
| `src/netris_mcp/tools/inventory.py` | Inventory tools: list/get items, controllers, softgates, switches |
| `src/netris_mcp/tools/ipam.py` | IPAM tools: subnets (list/get/create/delete) and allocations (list/create) |
| `src/netris_mcp/tools/nat.py` | NAT tools: list/get/delete rules, create SNAT, create DNAT |
| `src/netris_mcp/tools/l4lb.py` | L4LB tools: list, get, create, update backends, delete |
| `src/netris_mcp/tools/tenants.py` | Tenant tools: list, get, create, update, delete |
| `src/netris_mcp/tools/vpc_peering.py` | VPC peering tools |
| `src/netris_mcp/tools/static_routes.py` | Static routing tools |
| `src/netris_mcp/tools/acl.py` | ACL tools |
| `src/netris_mcp/guides/site_onboarding.py` | `onboard_new_site` prompt — site creation through softgate registration |
| `src/netris_mcp/guides/vpc_provisioning.py` | `provision_vpc` prompt — VPC, allocation, subnet, VNet |
| `src/netris_mcp/guides/bgp_setup.py` | `setup_bgp_peering` prompt — eBGP session with optional route policy |
| `src/netris_mcp/guides/l4lb_setup.py` | `setup_load_balancer` prompt — L4LB creation with backend pool |
| `src/netris_mcp/guides/network_bootstrap.py` | `bootstrap_network` prompt — end-to-end first-time Netris setup |
| `src/netris_mcp/guides/vpc_peering_guide.py` | VPC peering workflow |
| `src/netris_mcp/guides/acl_guide.py` | ACL configuration workflow |
| `src/netris_mcp/guides/troubleshooting_guide.py` | Network troubleshooting |
| `src/netris_mcp/guides/multi_site_guide.py` | Multi-site setup |
| `src/netris_mcp/guides/gpu_cluster_guide.py` | GPU cluster networking |
| `examples/claude_desktop_config.json` | Ready-to-copy Claude Desktop MCP config |
| `examples/usage_examples.md` | Annotated usage examples showing tool call sequences |
