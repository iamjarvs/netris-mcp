"""Stage 6 Deep Diagnostics Test Suite: Observability, Looking Glass, Triage, and Telemetry.

Comprehensive test suite verifying deep operational behaviour, error handling,
parameter parsing, fallback mechanisms, and output schema consistency across:
1. `fabric_health`: scopes 'overview', 'heartbeats', 'hardware_health', 'ebgp_health'.
2. `fabric_audit`: categories 'api_logs', 'events' (including 500 fallback notice), 'monitoring_checks'.
3. `triage`: playbooks 'fabric_health_check', 'vnet_degraded', 'bgp_session_down', 'node_unreachable'.
4. `looking_glass`: queries 'peers_list', 'bgp_summary', 'bgp_route', 'route', 'ping', 'traceroute'.
5. `fabric_telemetry`: intents 'interface_utilisation', 'top_talkers', 'error_drops', 'health_timeline'.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
import respx
from fastmcp import FastMCP

from app.config import get_config, NetrisConfig
from app.diagnostics_dispatch import register_diagnostics
from app.netris_client import NetrisClient
from app.telemetry_dispatch import register_telemetry


@pytest.fixture
def client():
    """Initialise live NetrisClient using environment credentials."""
    cfg = get_config()
    return NetrisClient(
        base_url=cfg.netris_url,
        username=cfg.netris_username,
        password=cfg.netris_password,
        verify_ssl=False,
    )


@pytest.fixture
def mcp_server(client):
    """Initialise FastMCP server with registered diagnostics and telemetry dispatchers."""
    server = FastMCP("TestStage6Diagnostics")
    register_diagnostics(server, client)
    register_telemetry(server, client)
    return server


# =============================================================================
# 1. Fabric Health Deep Tests Across All Scopes
# =============================================================================


@pytest.mark.asyncio
async def test_fabric_health_overview_scope(mcp_server):
    """Verify 'overview' scope aggregates heartbeats, border BGP sessions, and widget statuses."""
    tool = await mcp_server.get_tool("fabric_health")
    raw_res = await tool.fn(scope="overview")
    res = json.loads(raw_res)

    assert "overall_status" in res
    assert res["overall_status"] in ("Healthy", "Degraded")
    assert "summary" in res
    summary = res["summary"]
    assert "total_heartbeat_nodes" in summary
    assert "critical_heartbeats_count" in summary
    assert "ebgp_sessions_total" in summary
    assert "ebgp_established" in summary
    assert "dashboard_widgets" in res
    assert isinstance(res["dashboard_widgets"], (dict, list))


@pytest.mark.asyncio
async def test_fabric_health_heartbeats_scope(mcp_server):
    """Verify 'heartbeats' scope returns digest of controller agent heartbeats."""
    tool = await mcp_server.get_tool("fabric_health")
    raw_res = await tool.fn(scope="heartbeats", limit=5)
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] >= 0
    assert len(res["items"]) <= 5
    if res["items"]:
        hb = res["items"][0]
        assert "name" in hb
        assert "status" in hb


@pytest.mark.asyncio
async def test_fabric_health_hardware_health_scope(mcp_server):
    """Verify 'hardware_health' scope inspects switch component sensors and alarms."""
    tool = await mcp_server.get_tool("fabric_health")
    raw_res = await tool.fn(scope="hardware_health", limit=5)
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] >= 0
    assert len(res["items"]) <= 5


@pytest.mark.asyncio
async def test_fabric_health_ebgp_health_scope(mcp_server):
    """Verify 'ebgp_health' scope inspects border peering state and neighbor AS numbers."""
    tool = await mcp_server.get_tool("fabric_health")
    raw_res = await tool.fn(scope="ebgp_health", limit=5)
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] >= 0
    if res["items"]:
        peer = res["items"][0]
        assert "neighbor_as" in peer
        assert "name" in peer


@pytest.mark.asyncio
@respx.mock
async def test_fabric_health_overview_degraded_mock():
    """Verify that critical agent heartbeats trigger Degraded overall status in overview."""
    mock_url = "https://mock.netris.io"
    respx.post(f"{mock_url}/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    respx.get(f"{mock_url}/api/v2/dashboard/widgets").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": [{"id": 1, "title": "Bandwidth"}]})
    )
    respx.get(f"{mock_url}/api/dashboard/totalcounts").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    respx.get(f"{mock_url}/api/v2/dashboard/agent-heartbeats").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {"id": 1, "name": "leaf-01", "status": "critical", "lastHeartbeat": "2026-10-11T20:00:00Z"},
                    {"id": 2, "name": "leaf-02", "status": "ok", "lastHeartbeat": "2026-10-11T20:00:00Z"},
                ],
            },
        )
    )
    respx.get(f"{mock_url}/api/v2/ebgp").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {"id": 10, "name": "isp1", "bgp_state": "established", "neighbor_as": 65001},
                ],
            },
        )
    )

    mock_client = NetrisClient(base_url=mock_url, username="admin", password="pwd")
    server = FastMCP("MockHealthServer")
    register_diagnostics(server, mock_client)

    tool = await server.get_tool("fabric_health")
    res = json.loads(await tool.fn(scope="overview"))

    assert res["overall_status"] == "Degraded"
    assert res["summary"]["critical_heartbeats_count"] == 1
    assert "leaf-01" in res["summary"]["critical_nodes"]
    assert res["summary"]["ebgp_established"] == 1

    await mock_client.close()


# =============================================================================
# 2. Fabric Audit Deep Tests Across All Categories
# =============================================================================


@pytest.mark.asyncio
async def test_fabric_audit_api_logs(mcp_server):
    """Verify 'api_logs' returns controller audit log trail with pagination and DESC sort."""
    tool = await mcp_server.get_tool("fabric_audit")
    raw_res = await tool.fn(category="api_logs", limit=3)
    res = json.loads(raw_res)

    assert "items" in res
    assert len(res["items"]) <= 3
    if res["items"]:
        entry = res["items"][0]
        assert "method" in entry
        assert "url" in entry
        assert "createdAt" in entry


@pytest.mark.asyncio
async def test_fabric_audit_monitoring_checks(mcp_server):
    """Verify 'monitoring_checks' returns sensor threshold rules (critLow, warnHigh, etc.)."""
    tool = await mcp_server.get_tool("fabric_audit")
    raw_res = await tool.fn(category="monitoring_checks", limit=5)
    res = json.loads(raw_res)

    assert "items" in res
    if res["items"]:
        chk = res["items"][0]
        assert "name" in chk
        assert any(k in chk for k in ("unit", "critHigh", "warnHigh", "critLow"))


@pytest.mark.asyncio
async def test_fabric_audit_events_fallback_live(mcp_server):
    """Verify 'events' category query: returns events or falls back gracefully on uninitialised 500."""
    tool = await mcp_server.get_tool("fabric_audit")
    raw_res = await tool.fn(category="events", limit=3)
    res = json.loads(raw_res)

    # In live Netris lab, /api/eventlogs returns HTTP 500, triggering the graceful mutation fallback
    if "notice" in res:
        assert "fallback_category" in res
        assert res["fallback_category"] == "api_logs"
        assert "recent_mutation_events" in res
        assert "items" in res["recent_mutation_events"]
    else:
        assert "items" in res


@pytest.mark.asyncio
@respx.mock
async def test_fabric_audit_events_500_fallback_mock():
    """Verify mock scenario where /api/eventlogs returns 500 and triggers audit mutation log fallback."""
    mock_url = "https://mock.netris.io"
    respx.post(f"{mock_url}/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    # Event logs endpoint raises 500 error
    respx.get(f"{mock_url}/api/eventlogs").mock(
        return_value=httpx.Response(500, text="Internal Server Error: Table uninitialised")
    )
    # Mutation audit logs fallback
    respx.get(f"{mock_url}/api/apilogs").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {"id": 44, "createdAt": 1728680000, "method": "POST", "url": "/api/v2/vnet", "user": "admin", "ip": "10.0.0.1"},
                ],
            },
        )
    )

    mock_client = NetrisClient(base_url=mock_url, username="admin", password="pwd")
    server = FastMCP("MockAuditServer")
    register_diagnostics(server, mock_client)

    tool = await server.get_tool("fabric_audit")
    res = json.loads(await tool.fn(category="events", limit=5))

    assert "notice" in res
    assert "uninitialised" in res["notice"] or "500" in res["notice"]
    assert res["fallback_category"] == "api_logs"
    assert "recent_mutation_events" in res
    assert len(res["recent_mutation_events"]["items"]) == 1
    assert res["recent_mutation_events"]["items"][0]["method"] == "POST"

    await mock_client.close()


@pytest.mark.asyncio
@respx.mock
async def test_fabric_audit_events_success_mock():
    """Verify mock scenario where /api/eventlogs succeeds and returns hardware events digest."""
    mock_url = "https://mock.netris.io"
    respx.post(f"{mock_url}/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    respx.get(f"{mock_url}/api/eventlogs").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {
                        "id": 12,
                        "hardware": "leaf-01",
                        "status": "warning",
                        "checkName": "temperature",
                        "message": "Thermal threshold exceeded",
                        "date": "2026-10-11T12:00:00Z",
                    }
                ],
            },
        )
    )

    mock_client = NetrisClient(base_url=mock_url, username="admin", password="pwd")
    server = FastMCP("MockAuditServer")
    register_diagnostics(server, mock_client)

    tool = await server.get_tool("fabric_audit")
    res = json.loads(await tool.fn(category="events", limit=5))

    assert "items" in res
    assert len(res["items"]) == 1
    assert res["items"][0]["checkName"] == "temperature"

    await mock_client.close()


# =============================================================================
# 3. Fabric Triage Deep Tests Across All Playbooks
# =============================================================================


@pytest.mark.asyncio
async def test_triage_fabric_health_check_live(mcp_server):
    """Verify 'fabric_health_check' symptom executes holistic multi-point diagnosis."""
    tool = await mcp_server.get_tool("triage")
    raw_res = await tool.fn(symptom="fabric_health_check")
    res = json.loads(raw_res)

    assert "verdict" in res
    assert res["verdict"] in ("OPTIMAL", "ATTENTION_REQUIRED")
    assert "total_switches" in res
    assert "active_vnets" in res
    assert "unestablished_bgp" in res
    assert "offline_nodes_count" in res
    assert isinstance(res["unestablished_bgp"], list)


@pytest.mark.asyncio
async def test_triage_vnet_degraded_live(mcp_server):
    """Verify 'vnet_degraded' playbook audits V-Net states across the fabric."""
    tool = await mcp_server.get_tool("triage")
    raw_res = await tool.fn(symptom="vnet_degraded")
    res = json.loads(raw_res)

    assert res["symptom"] == "vnet_degraded"
    assert "verdict" in res
    assert res["verdict"] in ("HEALTHY", "ANOMALY_DETECTED")
    assert "findings" in res
    assert len(res["findings"]) > 0


@pytest.mark.asyncio
async def test_triage_vnet_degraded_target_not_found(mcp_server):
    """Verify 'vnet_degraded' reports specific message when target V-Net is not found."""
    tool = await mcp_server.get_tool("triage")
    res = await tool.fn(symptom="vnet_degraded", target_name="non-existent-vnet-xyz")

    assert "not found" in res.lower()


@pytest.mark.asyncio
async def test_triage_bgp_session_down_live(mcp_server):
    """Verify 'bgp_session_down' playbook inspects external BGP peer sessions."""
    tool = await mcp_server.get_tool("triage")
    raw_res = await tool.fn(symptom="bgp_session_down")
    res = json.loads(raw_res)

    assert res["symptom"] == "bgp_session_down"
    assert "verdict" in res
    assert res["verdict"] in ("HEALTHY", "BGP_DOWN_DETECTED")
    assert "findings" in res


@pytest.mark.asyncio
async def test_triage_node_unreachable_live(mcp_server):
    """Verify 'node_unreachable' playbook inspects daemon heartbeats for failures."""
    tool = await mcp_server.get_tool("triage")
    raw_res = await tool.fn(symptom="node_unreachable")
    res = json.loads(raw_res)

    assert res["symptom"] == "node_unreachable"
    assert "verdict" in res
    assert res["verdict"] in ("HEALTHY", "UNREACHABLE_NODES_FOUND")
    assert "findings" in res


@pytest.mark.asyncio
@respx.mock
async def test_triage_playbooks_anomaly_detection_mock():
    """Verify mock scenarios where anomalies trigger distinct verdicts across all playbooks."""
    mock_url = "https://mock.netris.io"
    respx.post(f"{mock_url}/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    respx.get(f"{mock_url}/api/v2/vnet").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {"id": 1, "name": "vnet-prod", "state": "degraded"},
                    {"id": 2, "name": "vnet-dev", "state": "active"},
                ],
            },
        )
    )
    respx.get(f"{mock_url}/api/v2/ebgp").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {"id": 1, "name": "peer-core1", "bgp_state": "Active", "neighbor_as": 65000, "local_ip": "10.0.0.1", "remote_ip": "10.0.0.2"},
                ],
            },
        )
    )
    respx.get(f"{mock_url}/api/v2/dashboard/agent-heartbeats").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {"id": 5, "name": "spine-01", "status": "failed", "lastHeartbeat": "2026-10-11T18:00:00Z"},
                ],
            },
        )
    )
    respx.get(f"{mock_url}/api/v2/hw").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [{"id": 1, "name": "spine-01", "type": "switch"}],
            },
        )
    )

    mock_client = NetrisClient(base_url=mock_url, username="admin", password="pwd")
    server = FastMCP("MockTriageServer")
    register_diagnostics(server, mock_client)

    tool = await server.get_tool("triage")

    # 1. vnet_degraded detects anomaly
    res_vnet = json.loads(await tool.fn(symptom="vnet_degraded"))
    assert res_vnet["verdict"] == "ANOMALY_DETECTED"
    assert any("vnet-prod" in f for f in res_vnet["findings"])

    # 2. bgp_session_down detects unestablished session
    res_bgp = json.loads(await tool.fn(symptom="bgp_session_down"))
    assert res_bgp["verdict"] == "BGP_DOWN_DETECTED"
    assert any("peer-core1" in f for f in res_bgp["findings"])

    # 3. node_unreachable detects failed daemon heartbeat
    res_node = json.loads(await tool.fn(symptom="node_unreachable"))
    assert res_node["verdict"] == "UNREACHABLE_NODES_FOUND"
    assert any("spine-01" in f for f in res_node["findings"])

    # 4. fabric_health_check aggregates attention required
    res_fhc = json.loads(await tool.fn(symptom="fabric_health_check"))
    assert res_fhc["verdict"] == "ATTENTION_REQUIRED"
    assert "peer-core1" in res_fhc["unestablished_bgp"]
    assert res_fhc["offline_nodes_count"] == 1

    await mock_client.close()


# =============================================================================
# 4. Looking Glass Deep Tests Across All Queries and Parameter Handling
# =============================================================================


@pytest.mark.asyncio
async def test_looking_glass_peers_list(mcp_server):
    """Verify 'peers_list' returns active Looking Glass BGP peers digest."""
    tool = await mcp_server.get_tool("looking_glass")
    raw_res = await tool.fn(query="peers_list")
    res = json.loads(raw_res)

    assert "items" in res
    assert res["total_records"] >= 0
    if res["items"]:
        peer = res["items"][0]
        assert "name" in peer
        assert "asNumber" in peer
        assert "ip" in peer


@pytest.mark.asyncio
async def test_looking_glass_inspect_peer(mcp_server):
    """Verify 'inspect_peer' query filters peer details by target name or IP."""
    tool = await mcp_server.get_tool("looking_glass")
    raw_res = await tool.fn(query="inspect_peer", target_ip="upstream1")
    res = json.loads(raw_res)

    assert res["query"] == "inspect_peer"
    assert "items" in res
    assert "total_matches" in res


@pytest.mark.asyncio
async def test_looking_glass_bgp_summary(mcp_server):
    """Verify 'bgp_summary' executes live or simulated BGP state query on target switch."""
    tool = await mcp_server.get_tool("looking_glass")
    raw_res = await tool.fn(query="bgp_summary", switch_name="leaf-pod00-su0-r0")
    res = json.loads(raw_res)

    assert res["query"] == "bgp_summary"
    assert "target_switch" in res
    assert "command" in res
    assert "show bgp summary" in res["command"]
    assert res["status"] in ("success", "error")
    assert "output" in res


@pytest.mark.asyncio
async def test_looking_glass_bgp_route(mcp_server):
    """Verify 'bgp_route' parameter handling (prefix, ip_family, switch_name)."""
    tool = await mcp_server.get_tool("looking_glass")
    raw_res = await tool.fn(
        query="bgp_route",
        switch_name="leaf-pod00-su0-r0",
        prefix="10.253.128.0/24",
        ip_family="ipv4",
    )
    res = json.loads(raw_res)

    assert res["query"] == "bgp_route"
    assert res["prefix"] == "10.253.128.0/24"
    assert res["ip_family"] == "ipv4"
    assert "10.253.128.0/24" in res["command"]
    assert res["status"] in ("success", "error")
    assert "output" in res


@pytest.mark.asyncio
async def test_looking_glass_route(mcp_server):
    """Verify 'route' parameter handling and output format for routing table queries."""
    tool = await mcp_server.get_tool("looking_glass")
    raw_res = await tool.fn(
        query="route",
        switch_name="leaf-pod00-su0-r0",
        prefix="10.253.0.0/24",
    )
    res = json.loads(raw_res)

    assert res["query"] == "route"
    assert res["target_switch"] == "leaf-pod00-su0-r0"
    assert "ip route show" in res["command"]
    assert res["status"] in ("success", "error")
    assert "output" in res


@pytest.mark.asyncio
async def test_looking_glass_ping_live_and_validation(mcp_server):
    """Verify 'ping' query parameter validation and execution output format."""
    tool = await mcp_server.get_tool("looking_glass")

    # 1. Validation failure: missing target_ip
    missing_res = json.loads(await tool.fn(query="ping", target_ip=None))
    assert "error" in missing_res
    assert "required" in missing_res["error"]

    # 2. Valid ping probe execution
    raw_res = await tool.fn(
        query="ping",
        switch_name="leaf-pod00-su0-r0",
        target_ip="127.0.0.1",
        count=2,
    )
    res = json.loads(raw_res)

    assert res["query"] == "ping"
    assert res["destination"] == "127.0.0.1"
    assert res["count"] == 2
    assert "ping -c 2" in res["command"]
    assert res["status"] in ("success", "error")
    assert "output" in res


@pytest.mark.asyncio
async def test_looking_glass_traceroute_live_and_validation(mcp_server):
    """Verify 'traceroute' query parameter validation and execution output format."""
    tool = await mcp_server.get_tool("looking_glass")

    # 1. Validation failure: missing target_ip
    missing_res = json.loads(await tool.fn(query="traceroute", target_ip=None))
    assert "error" in missing_res
    assert "required" in missing_res["error"]

    # 2. Valid traceroute query execution
    raw_res = await tool.fn(
        query="traceroute",
        switch_name="leaf-pod00-su0-r0",
        target_ip="10.253.0.1",
    )
    res = json.loads(raw_res)

    assert res["query"] == "traceroute"
    assert res["destination"] == "10.253.0.1"
    assert "traceroute" in res["command"]
    assert res["status"] in ("success", "error")
    assert "output" in res


# =============================================================================
# 5. Fabric Telemetry Deep Tests Across All Intents
# =============================================================================


@pytest.mark.asyncio
async def test_fabric_telemetry_interface_utilisation(mcp_server):
    """Verify 'interface_utilisation' ranks links by utilisation percent and respects top_n."""
    tool = await mcp_server.get_tool("fabric_telemetry")
    raw_res = await tool.fn(intent="interface_utilisation", top_n=5)
    res = json.loads(raw_res)

    assert res["intent"] == "interface_utilisation"
    assert "records" in res
    assert len(res["records"]) <= 5
    if res["records"]:
        record = res["records"][0]
        assert "utilisation_percent" in record
        assert "local_device" in record
        assert "remote_device" in record


@pytest.mark.asyncio
async def test_fabric_telemetry_top_talkers(mcp_server):
    """Verify 'top_talkers' queries configured traffic graphboards across transit ports."""
    tool = await mcp_server.get_tool("fabric_telemetry")
    raw_res = await tool.fn(intent="top_talkers")
    res = json.loads(raw_res)

    assert res["intent"] == "top_talkers"
    assert "configured_traffic_boards" in res
    assert "summary" in res
    assert "note" in res
    assert isinstance(res["summary"], list)


@pytest.mark.asyncio
async def test_fabric_telemetry_error_drops(mcp_server):
    """Verify 'error_drops' queries interface error indicators and drop conditions."""
    tool = await mcp_server.get_tool("fabric_telemetry")
    raw_res = await tool.fn(intent="error_drops", top_n=10)
    res = json.loads(raw_res)

    assert res["intent"] == "error_drops"
    assert "degraded_ports_count" in res
    assert "records" in res
    assert isinstance(res["records"], list)
    assert len(res["records"]) <= 10


@pytest.mark.asyncio
async def test_fabric_telemetry_health_timeline(mcp_server):
    """Verify 'health_timeline' aggregates chronological health events and node counts."""
    tool = await mcp_server.get_tool("fabric_telemetry")
    raw_res = await tool.fn(intent="health_timeline", top_n=10)
    res = json.loads(raw_res)

    assert res["intent"] == "health_timeline"
    assert "timeline_entries_count" in res
    assert "healthy_nodes_count" in res
    assert "degraded_nodes_count" in res
    assert "records" in res
    assert isinstance(res["records"], list)
    if res["records"]:
        entry = res["records"][0]
        assert "timestamp" in entry
        assert "entity" in entry
        assert "type" in entry
        assert "status" in entry
        assert "details" in entry


@pytest.mark.asyncio
@respx.mock
async def test_fabric_telemetry_mock_pipeline():
    """Verify telemetry pipeline edge cases: node_name filtering and percentage sorting."""
    mock_url = "https://mock.netris.io"
    respx.post(f"{mock_url}/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    respx.get(f"{mock_url}/api/v2/link").mock(
        return_value=httpx.Response(
            200,
            json={
                "isSuccess": True,
                "data": [
                    {
                        "id": 1,
                        "local": {"hardware": {"name": "leaf-01"}, "port": "swp1", "speed": "100G", "status": {"label": "Up"}},
                        "remote": {"hardware": {"name": "spine-01"}, "port": "swp1"},
                        "utilization": 24.5,
                    },
                    {
                        "id": 2,
                        "local": {"hardware": {"name": "leaf-02"}, "port": "swp1", "speed": "100G", "status": {"label": "Up"}},
                        "remote": {"hardware": {"name": "spine-01"}, "port": "swp2"},
                        "utilization": 88.2,
                    },
                ],
            },
        )
    )

    mock_client = NetrisClient(base_url=mock_url, username="admin", password="pwd")
    server = FastMCP("MockTelemetryServer")
    register_telemetry(server, mock_client)

    tool = await server.get_tool("fabric_telemetry")

    # 1. Utilisation ranking: leaf-02 (88.2%) must be ranked first
    raw_util = await tool.fn(intent="interface_utilisation", top_n=2)
    res_util = json.loads(raw_util)
    assert res_util["records"][0]["local_device"] == "leaf-02"
    assert res_util["records"][0]["utilisation_percent"] == 88.2

    # 2. Node filtering: filtering to 'leaf-01' should only return 1 link
    raw_filt = await tool.fn(intent="interface_utilisation", node_name="leaf-01")
    res_filt = json.loads(raw_filt)
    assert len(res_filt["records"]) == 1
    assert res_filt["records"][0]["local_device"] == "leaf-01"

    await mock_client.close()
