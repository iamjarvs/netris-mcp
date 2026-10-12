import pytest
import json
from app.config import get_config
from app.netris_client import NetrisClient
from app.diagnostics_dispatch import register_diagnostics
from fastmcp import FastMCP

@pytest.fixture
def test_client():
    cfg = get_config()
    client = NetrisClient(
        base_url=cfg.netris_url,
        username=cfg.netris_username,
        password=cfg.netris_password,
        verify_ssl=False,
    )
    return client

@pytest.mark.asyncio
async def test_diagnostics_registration(test_client):
    mcp = FastMCP("TestNetris")
    register_diagnostics(mcp, test_client)

    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "fabric_health" in tool_names
    assert "fabric_audit" in tool_names
    assert "triage" in tool_names
    assert "looking_glass" in tool_names

@pytest.mark.asyncio
async def test_live_fabric_health_overview(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")

    mcp = FastMCP("TestNetris")
    register_diagnostics(mcp, test_client)

    tool = await mcp.get_tool("fabric_health")
    raw_res = await tool.fn(scope="overview")
    res = json.loads(raw_res)

    assert "overall_status" in res
    assert "summary" in res
    assert res["summary"]["ebgp_established"] == 4

@pytest.mark.asyncio
async def test_live_triage_playbook(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")

    mcp = FastMCP("TestNetris")
    register_diagnostics(mcp, test_client)

    tool = await mcp.get_tool("triage")
    raw_res = await tool.fn(symptom="fabric_health_check")
    res = json.loads(raw_res)

    assert "verdict" in res
    assert res["active_vnets"] >= 1
    assert len(res["unestablished_bgp"]) == 0

@pytest.mark.asyncio
async def test_live_looking_glass_peers(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")

    mcp = FastMCP("TestNetris")
    register_diagnostics(mcp, test_client)

    tool = await mcp.get_tool("looking_glass")
    raw_res = await tool.fn(query="peers_list")
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] == 4


@pytest.mark.asyncio
async def test_live_fabric_audit_categories(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")

    mcp = FastMCP("TestNetris")
    register_diagnostics(mcp, test_client)

    tool = await mcp.get_tool("fabric_audit")

    # 1. API audit trail
    res_api = json.loads(await tool.fn(category="api_logs", limit=3))
    assert "items" in res_api
    assert len(res_api["items"]) > 0

    # 2. Monitoring checks threshold rules
    res_checks = json.loads(await tool.fn(category="monitoring_checks", limit=5))
    assert "items" in res_checks
    assert len(res_checks["items"]) > 0

    # 3. Events query (gracefully handles uninitialised 500 by falling back to mutation audit events)
    res_events = json.loads(await tool.fn(category="events", limit=3))
    assert "notice" in res_events or "items" in res_events


@pytest.mark.asyncio
async def test_architecture_reference_ai_fabrics(test_client):
    from app.switch_exec import register_switch_exec

    mcp = FastMCP("TestNetris")
    register_switch_exec(mcp, test_client)

    tool = await mcp.get_tool("architecture_reference")

    # AI Fabric domain overview
    res_ai = json.loads(await tool.fn(platform="ai_fabric"))
    assert "frontend_network" in res_ai
    assert "backend_network" in res_ai
    assert "scale_up_fabric" in res_ai
    assert "on_host_networking" in res_ai

    # NVIDIA UFM
    res_ufm = json.loads(await tool.fn(platform="nvidia_ufm"))
    assert "netris_integration" in res_ufm
    assert "UFM" in res_ufm["technology"]

    # NVIDIA NVLink NVL72
    res_nvl = json.loads(await tool.fn(platform="nvidia_nvlink_nvl72"))
    assert "NVL72" in res_nvl["technology"]

