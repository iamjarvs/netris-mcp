import pytest
import json
from app.config import get_config
from app.netris_client import NetrisClient
from app.tools_dispatch import register_tools
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
async def test_tools_registration(test_client):
    mcp = FastMCP("TestNetris")
    register_tools(mcp, test_client)
    
    # Verify tools registered
    tool_objects = await mcp.list_tools()
    tool_names = [t.name for t in tool_objects]
    assert "fabric_inventory" in tool_names
    assert "virtual_networks" in tool_names
    assert "routing_and_policy" in tool_names
    assert "fabric_links" in tool_names

@pytest.mark.asyncio
async def test_live_fabric_inventory(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")
        
    mcp = FastMCP("TestNetris")
    register_tools(mcp, test_client)
    
    tool = await mcp.get_tool("fabric_inventory")
    raw_res = await tool.fn(domain="summary")
    res = json.loads(raw_res)
    
    assert res["sites_count"] >= 1
    assert "Datacenter-A" in res["sites"]
    assert res["hardware_total"] > 50
    assert res["vpcs_count"] >= 1

@pytest.mark.asyncio
async def test_live_virtual_networks(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")

    mcp = FastMCP("TestNetris")
    register_tools(mcp, test_client)

    tool = await mcp.get_tool("virtual_networks")
    raw_res = await tool.fn(action="list_vnets")
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] >= 1

@pytest.mark.asyncio
async def test_live_ebgp_sessions(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")

    mcp = FastMCP("TestNetris")
    register_tools(mcp, test_client)

    tool = await mcp.get_tool("routing_and_policy")
    raw_res = await tool.fn(action="ebgp_sessions")
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] >= 1
