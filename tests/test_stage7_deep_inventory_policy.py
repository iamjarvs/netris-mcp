"""Stage 7 Deep Test Suite: Fabric Inventory, Links, Policy, and Mutation Safety.

Verifies comprehensive functionality, parameter validation, and safety safeguards across:
- `fabric_inventory`: 'summary', 'sites', 'switches', 'softgates', 'servers', 'vpcs', 'tenants'
- `virtual_networks`: 'vnets', 'ipam', 'peering'
- `routing_and_policy`: 'ebgp', 'route_maps', 'acls', 'static_routes', 'nat'
- `fabric_links`: 'summary', 'links', 'interfaces'
- `mutate_vnet`: dry-run preview in read-only mode, parameter validation, and protection safeguards
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx
from fastmcp import FastMCP

from app.config import NetrisConfig, get_config
from app.mutations import register_mutations
from app.netris_client import NetrisClient
from app.tools_dispatch import register_tools


@pytest.fixture
def client():
    """Initialise NetrisClient for testing."""
    cfg = get_config()
    return NetrisClient(
        base_url=cfg.netris_url,
        username=cfg.netris_username,
        password=cfg.netris_password,
        verify_ssl=False,
    )


@pytest.fixture
def mcp_server(client):
    """Initialise FastMCP server with registered tools and mutations."""
    server = FastMCP("TestStage7Server")
    register_tools(server, client)
    register_mutations(server, client)
    return server


# =============================================================================
# 1. Fabric Inventory Deep Tests across all domains
# =============================================================================


@pytest.mark.asyncio
async def test_fabric_inventory_summary(mcp_server):
    """Verify 'summary' domain aggregates sites, VPCs, tenants, and hardware types."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="summary")
    res = json.loads(raw_res)

    assert "sites_count" in res
    assert "vpcs_count" in res
    assert "tenants_count" in res
    assert "hardware_total" in res
    assert "switches" in res
    assert "softgates" in res
    assert "servers" in res
    assert "controllers" in res
    assert isinstance(res["sites"], list)
    assert isinstance(res["tenants"], list)


@pytest.mark.asyncio
async def test_fabric_inventory_sites(mcp_server):
    """Verify 'sites' domain returns digest of sites with public ASN and fabric info."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="sites", limit=5)
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] >= 0
    if res["items"]:
        site = res["items"][0]
        assert "name" in site
        assert "publicAsn" in site


@pytest.mark.asyncio
async def test_fabric_inventory_switches(mcp_server):
    """Verify 'switches' domain returns exclusively switch hardware devices."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="switches", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    for item in res["items"]:
        assert item.get("type") == "switch"


@pytest.mark.asyncio
async def test_fabric_inventory_softgates(mcp_server):
    """Verify 'softgates' domain returns exclusively SoftGate gateway appliances."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="softgates", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    for item in res["items"]:
        assert item.get("type") == "softgate"


@pytest.mark.asyncio
async def test_fabric_inventory_servers(mcp_server):
    """Verify 'servers' domain returns server compute resources."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="servers", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    for item in res["items"]:
        assert item.get("type") == "server"


@pytest.mark.asyncio
async def test_fabric_inventory_vpcs(mcp_server):
    """Verify 'vpcs' domain returns VPC tenant network definitions."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="vpcs", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    if res["items"]:
        vpc = res["items"][0]
        assert "name" in vpc


@pytest.mark.asyncio
async def test_fabric_inventory_tenants(mcp_server):
    """Verify 'tenants' domain returns tenant isolation entities."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="tenants", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    if res["items"]:
        tenant = res["items"][0]
        assert "name" in tenant


@pytest.mark.asyncio
async def test_fabric_inventory_hardware_filtering(mcp_server):
    """Verify filtering hardware inventory by site name."""
    tool = await mcp_server.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="hardware", site_name="Datacenter-A", limit=5)
    res = json.loads(raw_res)

    assert "items" in res
    for item in res["items"]:
        site_info = item.get("site", {})
        if isinstance(site_info, dict) and "name" in site_info:
            assert site_info["name"].lower() == "datacenter-a"


@pytest.mark.asyncio
async def test_fabric_inventory_unknown_domain(mcp_server):
    """Verify error response when querying an unknown inventory domain."""
    tool = await mcp_server.get_tool("fabric_inventory")
    res = await tool.fn(domain="non_existent_domain")  # type: ignore
    assert res == "Unknown domain"


# =============================================================================
# 2. Virtual Networks Deep Tests across all domains
# =============================================================================


@pytest.mark.asyncio
async def test_virtual_networks_vnets_domain(mcp_server):
    """Verify 'vnets' action retrieves overlay network list and digest attributes."""
    tool = await mcp_server.get_tool("virtual_networks")
    raw_res = await tool.fn(action="vnets", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    assert "total_records" in res
    if res["items"]:
        vnet = res["items"][0]
        assert "name" in vnet
        assert "state" in vnet


@pytest.mark.asyncio
async def test_virtual_networks_vnet_detail_found(mcp_server):
    """Verify 'vnet_detail' retrieves full object specification for an existing V-Net."""
    tool = await mcp_server.get_tool("virtual_networks")
    list_raw = await tool.fn(action="vnets", limit=1)
    list_res = json.loads(list_raw)

    if list_res["items"]:
        target_name = list_res["items"][0]["name"]
        raw_detail = await tool.fn(action="vnet_detail", name=target_name)
        detail_res = json.loads(raw_detail)
        assert detail_res["name"] == target_name
        assert "id" in detail_res


@pytest.mark.asyncio
async def test_virtual_networks_vnet_detail_not_found(mcp_server):
    """Verify 'vnet_detail' returns graceful message when V-Net name does not exist."""
    tool = await mcp_server.get_tool("virtual_networks")
    res = await tool.fn(action="vnet_detail", name="non-existent-vnet-xyz")
    assert "not found" in res.lower()


@pytest.mark.asyncio
async def test_virtual_networks_vnet_detail_missing_name(mcp_server):
    """Verify 'vnet_detail' requires name argument."""
    tool = await mcp_server.get_tool("virtual_networks")
    res = await tool.fn(action="vnet_detail")
    assert "error" in res.lower()
    assert "name" in res.lower()


@pytest.mark.asyncio
async def test_virtual_networks_ipam_domain(mcp_server):
    """Verify 'ipam' domain retrieves IP address management prefixes and allocations."""
    tool = await mcp_server.get_tool("virtual_networks")
    raw_res = await tool.fn(action="ipam", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    if res["items"]:
        ipam_entry = res["items"][0]
        assert "prefix" in ipam_entry or "name" in ipam_entry


@pytest.mark.asyncio
async def test_virtual_networks_peering_domain(mcp_server):
    """Verify 'peering' domain retrieves VPC peering interconnections."""
    tool = await mcp_server.get_tool("virtual_networks")
    raw_res = await tool.fn(action="peering", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    assert "total_records" in res


@pytest.mark.asyncio
async def test_virtual_networks_unknown_action(mcp_server):
    """Verify error response for unknown action."""
    tool = await mcp_server.get_tool("virtual_networks")
    res = await tool.fn(action="unknown_action")  # type: ignore
    assert res == "Unknown action"


# =============================================================================
# 3. Routing and Policy Deep Tests across all domains
# =============================================================================


@pytest.mark.asyncio
async def test_routing_and_policy_ebgp(mcp_server):
    """Verify 'ebgp' action inspects external BGP peering sessions."""
    tool = await mcp_server.get_tool("routing_and_policy")
    raw_res = await tool.fn(action="ebgp", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    assert "total_records" in res


@pytest.mark.asyncio
async def test_routing_and_policy_route_maps(mcp_server):
    """Verify 'route_maps' action inspects BGP route-map definitions."""
    tool = await mcp_server.get_tool("routing_and_policy")
    raw_res = await tool.fn(action="route_maps", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    assert "total_records" in res


@pytest.mark.asyncio
async def test_routing_and_policy_acls(mcp_server):
    """Verify 'acls' action inspects access control list rules and policies."""
    tool = await mcp_server.get_tool("routing_and_policy")
    raw_res = await tool.fn(action="acls", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    assert "total_records" in res


@pytest.mark.asyncio
async def test_routing_and_policy_static_routes(mcp_server):
    """Verify 'static_routes' action inspects static routing entries."""
    tool = await mcp_server.get_tool("routing_and_policy")
    raw_res = await tool.fn(action="static_routes", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    assert "total_records" in res


@pytest.mark.asyncio
async def test_routing_and_policy_nat(mcp_server):
    """Verify 'nat' action inspects network address translation rules."""
    tool = await mcp_server.get_tool("routing_and_policy")
    raw_res = await tool.fn(action="nat", limit=10)
    res = json.loads(raw_res)

    assert "items" in res
    assert "total_records" in res


@pytest.mark.asyncio
async def test_routing_and_policy_unknown_action(mcp_server):
    """Verify error response for unknown routing action."""
    tool = await mcp_server.get_tool("routing_and_policy")
    res = await tool.fn(action="unknown_route_action")  # type: ignore
    assert res == "Unknown action"


# =============================================================================
# 4. Fabric Links Deep Tests across all domains
# =============================================================================


@pytest.mark.asyncio
async def test_fabric_links_summary(mcp_server):
    """Verify 'summary' query provides total fabric link and port metrics."""
    tool = await mcp_server.get_tool("fabric_links")
    raw_res = await tool.fn(query="summary")
    res = json.loads(raw_res)

    assert "note" in res
    assert "sample_links" in res
    assert isinstance(res["sample_links"], list)


@pytest.mark.asyncio
async def test_fabric_links_links(mcp_server):
    """Verify 'links' query retrieves link endpoints with local/remote node mappings."""
    tool = await mcp_server.get_tool("fabric_links")
    raw_res = await tool.fn(query="links", limit=5)
    res = json.loads(raw_res)

    assert "count" in res
    assert "links" in res
    if res["links"]:
        lnk = res["links"][0]
        assert "local_node" in lnk
        assert "remote_node" in lnk
        assert "speed" in lnk


@pytest.mark.asyncio
async def test_fabric_links_interfaces(mcp_server):
    """Verify 'interfaces' query retrieves switch and server port interfaces."""
    tool = await mcp_server.get_tool("fabric_links")
    raw_res = await tool.fn(query="interfaces", limit=5)
    res = json.loads(raw_res)

    assert "items" in res
    if res["items"]:
        port = res["items"][0]
        assert "port" in port or "name" in port


@pytest.mark.asyncio
async def test_fabric_links_unknown_query(mcp_server):
    """Verify error response for unknown fabric links query."""
    tool = await mcp_server.get_tool("fabric_links")
    res = await tool.fn(query="unknown_query")  # type: ignore
    assert res == "Unknown query"


# =============================================================================
# 5. Mutate V-Net Safety, Safeguards, and Dry-Run Deep Tests
# =============================================================================


@pytest.mark.asyncio
async def test_mutate_vnet_dry_run_preview_readonly(mcp_server):
    """Verify dry_run=True returns structured preview diff even in read-only mode."""
    tool = await mcp_server.get_tool("mutate_vnet")
    raw_res = await tool.fn(
        operation="create",
        name="mcp-qa-test-vnet",
        vpc_name="Default",
        gateways="192.168.200.1/24",
        dry_run=True,
    )
    res = json.loads(raw_res)

    assert res["dry_run"] is True
    assert res["operation"] == "create"
    assert res["target_resource"] == "vnet"
    assert res["proposed_configuration"]["name"] == "mcp-qa-test-vnet"
    assert res["proposed_configuration"]["gateways"] == "192.168.200.1/24"
    assert "impact" in res
    assert "notice" in res


@pytest.mark.asyncio
async def test_mutate_vnet_dry_run_delete_preview(mcp_server):
    """Verify dry_run=True returns appropriate teardown preview for delete operation."""
    tool = await mcp_server.get_tool("mutate_vnet")
    raw_res = await tool.fn(
        operation="delete",
        name="mcp-qa-old-vnet",
        dry_run=True,
    )
    res = json.loads(raw_res)

    assert res["dry_run"] is True
    assert res["operation"] == "delete"
    assert "teardown" in res["impact"].lower()


@pytest.mark.asyncio
async def test_mutate_vnet_validation_unsupported_operation(mcp_server):
    """Verify parameter validation rejects unsupported operations."""
    tool = await mcp_server.get_tool("mutate_vnet")
    res = await tool.fn(
        operation="restart",
        name="mcp-qa-test-vnet",
        dry_run=True,
    )
    assert "VALIDATION ERROR" in res
    assert "Must be 'create' or 'delete'" in res


@pytest.mark.asyncio
async def test_mutate_vnet_validation_empty_name(mcp_server):
    """Verify parameter validation rejects empty or whitespace V-Net names."""
    tool = await mcp_server.get_tool("mutate_vnet")
    res = await tool.fn(
        operation="create",
        name="   ",
        dry_run=True,
    )
    assert "VALIDATION ERROR" in res
    assert "must not be empty" in res


@pytest.mark.asyncio
async def test_mutate_vnet_validation_invalid_gateway(mcp_server):
    """Verify parameter validation rejects invalid gateway CIDR missing subnet prefix."""
    tool = await mcp_server.get_tool("mutate_vnet")
    res = await tool.fn(
        operation="create",
        name="mcp-qa-test-vnet",
        gateways="192.168.100.1",
        dry_run=True,
    )
    assert "VALIDATION ERROR" in res
    assert "Invalid gateway CIDR" in res


@pytest.mark.asyncio
async def test_mutate_vnet_safeguard_protected_system_vnets(mcp_server):
    """Verify protection safeguard prevents deletion of core system V-Nets."""
    tool = await mcp_server.get_tool("mutate_vnet")
    for protected in ["default", "mgmt", "management", "system", "underlay"]:
        res = await tool.fn(
            operation="delete",
            name=protected,
            dry_run=True,
        )
        assert "PROTECTION SAFEGUARD" in res
        assert "forbidden" in res.lower()


@pytest.mark.asyncio
async def test_mutate_vnet_safeguard_readonly_mode_rejection(mcp_server):
    """Verify live mutations (dry_run=False) are rejected when server is in read-only mode."""
    tool = await mcp_server.get_tool("mutate_vnet")
    res = await tool.fn(
        operation="create",
        name="mcp-qa-test-vnet",
        dry_run=False,
    )
    assert "MUTATION REJECTED" in res
    assert "read-write" in res


@pytest.mark.asyncio
@respx.mock
async def test_mutate_vnet_readwrite_mode_creation_audit(tmp_path):
    """Verify that in read-write mode, live create operations execute and record audit logs."""
    fake_config = NetrisConfig(
        netris_url="https://test.netris.io",
        netris_username="test_admin",
        netris_password="secret_password",
        mode="read-write",
        port=8750,
    )

    client = NetrisClient(base_url="https://test.netris.io", username="test_admin", password="pwd")
    respx.post("https://test.netris.io/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    respx.post("https://test.netris.io/api/v2/vnet").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {"id": 101, "name": "mcp-qa-live"}})
    )

    with patch("app.mutations.get_config", return_value=fake_config):
        server = FastMCP("RWServer")
        register_mutations(server, client)

        tool = await server.get_tool("mutate_vnet")
        raw_res = await tool.fn(
            operation="create",
            name="mcp-qa-live",
            vpc_name="Default",
            gateways="10.50.0.1/24",
            dry_run=False,
        )
        res = json.loads(raw_res)

        assert res["status"] == "SUCCESS"
        assert "Created V-Net mcp-qa-live" in res["message"]

        # Verify audit log was recorded
        audit_file = Path("logs/mutations.jsonl")
        assert audit_file.exists()
        with open(audit_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert any("mcp-qa-live" in line and "SUCCESS" in line for line in lines)

    await client.close()
