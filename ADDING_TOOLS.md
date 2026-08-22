# Adding Tools and Guides to the Netris MCP Server

This document covers everything you need to extend the server with new tools (direct API calls) or guides (multi-step workflow prompts). Read it before writing any new code.

---

## The two primitive types

| Type | What it is | When to use |
|---|---|---|
| **Tool** (`@mcp.tool()`) | An async function the LLM can call to perform an action or retrieve data | Direct API calls: list, get, create, update, delete a single Netris resource |
| **Guide** (`@mcp.prompt()`) | A function that returns a markdown instruction string | Multi-step workflows that chain several tools in a specific order |

Tools do work. Guides teach the LLM how to do work.

---

## Part 1 — Adding a tool

### Step 1: Find the API endpoint

Look up the resource in the Netris OpenAPI specs at:

```
https://github.com/netrisai/swagger-sources/tree/master/v2/
```

Find the YAML file for your resource (e.g. `vpc.yaml`, `ebgp.yaml`). Note:
- The URL path (e.g. `/api/v2/vpc/`)
- The HTTP method for each operation
- The request body schema (field names and types)
- Which fields are required vs optional
- Which fields the API sets server-side (never send these in PUT/POST)

Some paths don't follow the obvious pattern — check the table:

| Resource | API path | Notes |
|---|---|---|
| VPC | `/api/v2/vpc/` | |
| VNet | `/api/v2/v-net/` | hyphenated |
| eBGP sessions | `/api/v2/ebgp/` | not "bgp" |
| BGP objects | `/api/v2/bgp-object/` | |
| Route maps | `/api/v2/routemap/` | no hyphen |
| IPAM subnets | `/api/v2/ipam/subnet/` | under /ipam/ |
| IPAM allocations | `/api/v2/ipam/allocation/` | under /ipam/ |
| SoftGate | `/api/v2/hw/softgate/` | under /hw/ |
| Switch | `/api/v2/hw/switch/` | under /hw/ |
| Controller | `/api/v2/hw/controller/` | under /hw/ |
| VPC peering | `/api/v2/vpc-peering/` | |
| Static routes | `/api/v2/static-route/` | |
| Sites | `/api/v2/sites/` | |
| NAT | `/api/v2/nat/` | |
| L4LB | `/api/v2/l4lb/` | |
| ACL | `/api/v2/acl/` | |
| Tenants | `/api/v2/tenant/` | |

### Step 2: Create the module file

Create `src/netris_mcp/tools/<resource>.py`. If the resource logically belongs with an existing module (e.g. adding a DHCP tool alongside VNet tools), add it to the existing file instead.

**Full file template:**

```python
import logging
from typing import Optional

from mcp.server.mcpserver import Context

from ..client import api_url, delete, get, post, put
from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_things(ctx: Context) -> str:
    """List all <resource> objects in Netris."""
    nc = ctx.request_context.lifespan_context
    # URL: /api/v2/thing/ — verify against netrisai/swagger-sources
    data = await get(nc.client, api_url(nc.base_url, "thing"))
    return str(data)


@mcp.tool()
async def get_thing(ctx: Context, thing_id: int) -> str:
    """Get a single <resource> by ID.

    Args:
        thing_id: The numeric ID of the <resource> to retrieve.
    """
    nc = ctx.request_context.lifespan_context
    data = await get(nc.client, api_url(nc.base_url, "thing", thing_id))
    return str(data)


@mcp.tool()
async def create_thing(
    ctx: Context,
    name: str,
    site: str,
    tenant: str,
    optional_field: Optional[str] = None,
) -> str:
    """Create a new <resource> in Netris.

    Args:
        name: Name for the new <resource>.
        site: The site name where this <resource> is created.
        tenant: The tenant name that owns this <resource>.
        optional_field: (optional) Description of what this field does.
    """
    nc = ctx.request_context.lifespan_context
    payload: dict = {
        "name": name,
        "site": {"name": site},
        "tenant": {"name": tenant},
    }
    if optional_field is not None:
        payload["optionalField"] = optional_field
    data = await post(nc.client, api_url(nc.base_url, "thing"), payload)
    return f"Created <resource> with ID {data.get('id', 'unknown')}"


@mcp.tool()
async def delete_thing(ctx: Context, thing_id: int) -> str:
    """Delete a <resource> by ID.

    Args:
        thing_id: The numeric ID of the <resource> to delete.
    """
    nc = ctx.request_context.lifespan_context
    data = await delete(nc.client, api_url(nc.base_url, "thing", thing_id))
    return f"Deleted <resource> {thing_id}: {data}"
```

### Step 3: Wire it into the server

Open `src/netris_mcp/server.py` and add one import line in the `# Tools` block at the bottom, after the existing tool imports:

```python
from .tools import thing  # noqa: E402, F401
```

The `# noqa` comments suppress linter warnings about "imported but unused" — the import is purely for its side effect of registering the `@mcp.tool()` decorators.

### Step 4: Verify registration

```bash
NETRIS_HOST=ctrl NETRIS_USERNAME=u NETRIS_PASSWORD=p uv run python -c "
from netris_mcp.server import mcp
tools = sorted(mcp._tool_manager._tools.keys())
print([t for t in tools if 'thing' in t])
"
```

You should see your new tool names in the output.

### Step 5: Write tests

Add a test file at `tests/test_<resource>.py` (or add to `tests/test_new_tools.py`). Minimum coverage:

```python
import pytest
import respx
import httpx
from netris_mcp.client import api_url, get, post, delete


def test_thing_url():
    """Verify the URL path is correct."""
    assert api_url("https://ctrl", "thing") == "https://ctrl/api/v2/thing/"
    assert api_url("https://ctrl", "thing", 5) == "https://ctrl/api/v2/thing/5"


@pytest.mark.asyncio
@respx.mock
async def test_create_thing_payload():
    """Verify the payload shape sent to the API."""
    captured = {}

    def capture(request):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 1})

    respx.post("https://ctrl/api/v2/thing/").mock(side_effect=capture)

    async with httpx.AsyncClient() as client:
        await post(client, api_url("https://ctrl", "thing"),
                   {"name": "test", "site": {"name": "dc1"}, "tenant": {"name": "acme"}})

    assert captured["body"]["name"] == "test"
    assert captured["body"]["site"] == {"name": "dc1"}
```

Run with:

```bash
uv run pytest tests/ -v
```

---

## Part 2 — Adding a guide (prompt)

Guides are `@mcp.prompt()` functions. They take parameters, interpolate them into a markdown instruction string, and return that string. The LLM reads the returned string and uses the available tools to execute the steps.

**Guides do not call tools themselves.** They only describe what tools to call and with what arguments.

### Step 1: Decide what belongs in a guide

A guide is appropriate when:
- The task requires multiple tools called in a specific order
- There are pre-conditions the user might forget to check
- There are common failure modes worth calling out
- The workflow requires decisions based on the output of one step to inform the next

If the user can accomplish the task in one tool call, a guide is unnecessary.

### Step 2: Create the guide file

Create `src/netris_mcp/guides/<workflow>.py`:

```python
from ..server import mcp


@mcp.prompt()
def my_workflow_guide(param_one: str, param_two: str, optional_param: str = "default") -> str:
    """One-line description of what this guide covers."""
    return f"""
# My Workflow Guide: {param_one}

## Overview
Explain in 2-3 sentences what this workflow accomplishes and why the steps
must be done in this order. Mention any prerequisites.

## Prerequisites
- Use `list_sites` to confirm "{param_two}" exists before starting
- Confirm the tenant exists with `list_tenants`

## Step 1: <First action>
Use `list_things` to check whether a <resource> named "{param_one}" already exists.
If it does, skip to Step 3.

## Step 2: Create the resource
Use `create_thing` with:
- name: "{param_one}"
- site: "{param_two}"
- tenant: (the tenant name from your prerequisites check)
- optional_field: "{optional_param}"

Note the `id` returned — you will need it in Step 3.

## Step 3: Verify
Use `get_thing` with the ID from Step 2 to confirm the resource was created
correctly. Check that all fields match what you specified.

## Step 4: (next action that depends on Step 2's result)
...

## Notes
- Explain any gotchas, ordering constraints, or Netris-specific concepts
- Reference related guides if relevant (e.g. "see the VPC peering guide if...")
- Note which fields to verify against netrisai/swagger-sources if uncertain
"""
```

### Step 3: Wire it into the server

Add one import to the `# Guides (MCP prompts)` block in `src/netris_mcp/server.py`:

```python
from .guides import my_workflow  # noqa: E402, F401
```

### Step 4: Write tests

Guide tests are simple — verify the function returns a non-empty string containing the expected content:

```python
import os
os.environ.setdefault("NETRIS_HOST", "test.example.com")
os.environ.setdefault("NETRIS_USERNAME", "admin")
os.environ.setdefault("NETRIS_PASSWORD", "secret")

from netris_mcp.guides.my_workflow import my_workflow_guide


def test_guide_returns_string():
    result = my_workflow_guide("prod-resource", "dc1")
    assert isinstance(result, str)
    assert len(result) > 100


def test_guide_interpolates_params():
    result = my_workflow_guide("prod-resource", "dc1")
    assert "prod-resource" in result
    assert "dc1" in result


def test_guide_references_correct_tools():
    result = my_workflow_guide("prod-resource", "dc1")
    assert "create_thing" in result
    assert "get_thing" in result
```

---

## Rules all tools and guides must follow

### No `print()` — ever

The MCP server runs over STDIO. Anything written to stdout corrupts the JSON-RPC protocol and breaks the client. Always use `logging.getLogger(__name__)`:

```python
# WRONG
print(f"Creating {name}")

# RIGHT
logger.info("Creating %s", name)
```

### All tools are `async def`

The server runs an asyncio event loop. Synchronous functions block it:

```python
# WRONG
@mcp.tool()
def list_things(ctx: Context) -> str: ...

# RIGHT
@mcp.tool()
async def list_things(ctx: Context) -> str: ...
```

### Always annotate parameters

The MCP SDK generates the JSON Schema for each tool from Python type hints. Un-annotated parameters are invisible to the LLM:

```python
# WRONG — the LLM doesn't know what to pass
async def create_thing(ctx, name, site):

# RIGHT
async def create_thing(ctx: Context, name: str, site: str) -> str:
```

### Optional parameters use `Optional[T]` or `T | None`

Both forms work. Use `Optional[str] = None` for Python 3.9 compatibility or `str | None = None` for 3.10+. Always include the `= None` default:

```python
from typing import Optional

async def create_thing(
    ctx: Context,
    name: str,                           # required
    description: Optional[str] = None,   # optional
) -> str:
    payload: dict = {"name": name}
    if description is not None:          # only add when provided
        payload["description"] = description
```

Never include an optional field as `None` in a JSON payload — `{"description": null}` can behave differently from omitting the field entirely.

### Access the HTTP client through the context

```python
# WRONG
import httpx
async with httpx.AsyncClient() as client:  # creates an unauthenticated client
    ...

# RIGHT
nc = ctx.request_context.lifespan_context  # authenticated client from lifespan
data = await get(nc.client, api_url(nc.base_url, "thing"))
```

### Return strings from tools

```python
# WRONG — MCP can't transmit a dict
return {"id": 5, "name": "test"}

# RIGHT for list/get
return str(data)

# RIGHT for create/delete
return f"Created thing with ID {data.get('id', 'unknown')}"
return f"Deleted thing {thing_id}: {data}"
```

### Use `api_url()` for all URL construction

```python
from ..client import api_url

# Collection (list, create)
api_url(nc.base_url, "thing")          # → https://host/api/v2/thing/

# Single item (get, update, delete)
api_url(nc.base_url, "thing", thing_id)  # → https://host/api/v2/thing/42

# Sub-resource action
f"{api_url(nc.base_url, 'vpc', vpc_id)}/make-default"
```

### No classes

All logic lives in plain functions. Use `@dataclass` only for data containers (the existing `NetrisContext` and `NetrisConfig` are the only ones).

### Write a docstring on every tool

The first line becomes the tool's description shown to the LLM in the MCP schema. The `Args:` block documents each parameter. Both directly affect how well the LLM uses the tool:

```python
@mcp.tool()
async def create_bgp_session(ctx: Context, name: str, site: str, neighbor_as: int) -> str:
    """Create a new eBGP peer session in Netris.

    Args:
        name: Descriptive name for this BGP session.
        site: The site name where the BGP session terminates (must have a SoftGate).
        neighbor_as: The AS number of the remote BGP peer.
    """
```

---

## Checklist before pushing

- [ ] Module file is in `src/netris_mcp/tools/` or `src/netris_mcp/guides/`
- [ ] Import added to `server.py` with `# noqa: E402, F401`
- [ ] All functions are `async def`
- [ ] All parameters are type-annotated
- [ ] Optional parameters guard the payload with `if x is not None`
- [ ] All logging uses `logging.getLogger(__name__)`, no `print()`
- [ ] URLs built with `api_url()`, not string concatenation
- [ ] URL paths verified against `netrisai/swagger-sources` (or marked with `# TODO`)
- [ ] API field names match the Netris camelCase convention (see CLAUDE.md cheat sheet)
- [ ] Tests written and passing: `uv run pytest tests/ -v`
- [ ] Server import verified: registration check passes (see Step 4 in Part 1)
- [ ] README updated if adding a significant new module

---

## Finding API field names

Netris uses camelCase for API fields. Python parameters use snake_case. The mapping is usually obvious but some are non-intuitive. Key ones:

| Python parameter | Netris API field |
|---|---|
| `public_asn` | `publicAsn` |
| `roh_asn` | `rohAsn` |
| `neighbor_as` | `neighborAs` |
| `neighbor_address` | `remoteIP` |
| `local_address` | `localIP` |
| `frontend_ip` | `ip` |
| `frontend_port` | `port` |
| `main_ip` | `mainIp` |
| `mgmt_ip` | `mgmtIp` |
| `snat_to_ip` | `translatedAddress` |
| `src_prefix` | `srcPrefix` |
| `dst_prefix` | `dstPrefix` |

When in doubt, check the OpenAPI YAML at `netrisai/swagger-sources/v2/<resource>.yaml` — the `properties` section of the request body schema shows the exact field names.

---

## Update functions: read-modify-write caution

Several `update_*` tools use a read-modify-write pattern:

```python
existing = await get(nc.client, api_url(nc.base_url, "thing", thing_id))
payload = dict(existing)   # ← shallow copy of the GET response
payload["field"] = new_value
await put(nc.client, api_url(nc.base_url, "thing", thing_id), payload)
```

**Risk:** The GET response may include server-managed read-only fields (timestamps, computed status, internal IDs) that the PUT endpoint rejects with a `400/422`. The existing `update_l4lb_backends` function shows the safer pattern — explicitly listing only the known-writable fields:

```python
payload = {
    "name": existing.get("name"),
    "site": existing.get("site"),
    # ... only fields the PUT endpoint accepts
    "myField": new_value,
}
```

When you have API access to test against, prefer the explicit allowlist over `dict(existing)`. Existing functions marked `# TODO(api-access)` need this treatment once the actual PUT response shapes are confirmed.

For nested objects, use `copy.deepcopy(existing)` instead of `dict(existing)` to avoid aliasing nested dicts:

```python
import copy
payload = copy.deepcopy(existing)
payload["nested"]["field"] = new_value  # safe — not aliased
```
