import pytest
import json
from app.config import get_config
from app.netris_client import NetrisClient
from app.telemetry_dispatch import register_telemetry
from app.charting import register_charting
from fastmcp import FastMCP

@pytest.fixture
def test_client():
    cfg = get_config()
    return NetrisClient(base_url=cfg.netris_url, username=cfg.netris_username, password=cfg.netris_password)

@pytest.mark.asyncio
async def test_live_fabric_telemetry_utilisation(test_client):
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live test")

    mcp = FastMCP("TestTelemetry")
    register_telemetry(mcp, test_client)

    tool = await mcp.get_tool("fabric_telemetry")
    raw_res = await tool.fn(intent="interface_utilisation", top_n=5)
    res = json.loads(raw_res)

    assert res["intent"] == "interface_utilisation"
    assert "records" in res
    assert len(res["records"]) <= 5

@pytest.mark.asyncio
async def test_generate_telemetry_chart():
    mcp = FastMCP("TestCharting")
    register_charting(mcp)

    tool = await mcp.get_tool("generate_telemetry_chart")
    res = await tool.fn(
        chart_type="bar",
        title="Top 3 Utilised Links",
        labels=["swp1s0", "swp2s0", "swp3s0"],
        values=[85.4, 62.1, 41.8],
        y_axis_label="Utilisation %"
    )

    assert res.startswith("![Top 3 Utilised Links](data:image/png;base64,")
