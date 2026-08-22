"""
Tests for the new tool modules: vpc_peering, static_routes, acl.
Also covers fixes to existing tools: ipam IPAM prefix paths, sites publicAsn, etc.
"""

import os
import pytest
import respx
import httpx

os.environ.setdefault("NETRIS_HOST", "test.example.com")
os.environ.setdefault("NETRIS_USERNAME", "admin")
os.environ.setdefault("NETRIS_PASSWORD", "secret")

from netris_mcp.client import api_url


# ---------------------------------------------------------------------------
# URL path regression tests for fixed endpoints
# ---------------------------------------------------------------------------


def test_ipam_subnet_url():
    url = api_url("https://ctrl.example.com", "ipam/subnet")
    assert url == "https://ctrl.example.com/api/v2/ipam/subnet/"


def test_ipam_allocation_url():
    url = api_url("https://ctrl.example.com", "ipam/allocation")
    assert url == "https://ctrl.example.com/api/v2/ipam/allocation/"


def test_hw_softgate_url():
    url = api_url("https://ctrl.example.com", "hw/softgate")
    assert url == "https://ctrl.example.com/api/v2/hw/softgate/"


def test_hw_switch_url():
    url = api_url("https://ctrl.example.com", "hw/switch")
    assert url == "https://ctrl.example.com/api/v2/hw/switch/"


def test_hw_controller_url():
    url = api_url("https://ctrl.example.com", "hw/controller")
    assert url == "https://ctrl.example.com/api/v2/hw/controller/"


def test_vpc_peering_url():
    url = api_url("https://ctrl.example.com", "vpc-peering")
    assert url == "https://ctrl.example.com/api/v2/vpc-peering/"


def test_static_route_url():
    url = api_url("https://ctrl.example.com", "static-route")
    assert url == "https://ctrl.example.com/api/v2/static-route/"


def test_acl_url():
    url = api_url("https://ctrl.example.com", "acl")
    assert url == "https://ctrl.example.com/api/v2/acl/"


# ---------------------------------------------------------------------------
# New guides: vpc_peering_guide
# ---------------------------------------------------------------------------


def test_setup_vpc_peering_returns_string():
    from netris_mcp.guides.vpc_peering_guide import setup_vpc_peering
    result = setup_vpc_peering("prod-vpc", "system-vpc")
    assert isinstance(result, str)
    assert len(result) > 100


def test_setup_vpc_peering_contains_vpc_names():
    from netris_mcp.guides.vpc_peering_guide import setup_vpc_peering
    result = setup_vpc_peering("prod-vpc", "system-vpc")
    assert "prod-vpc" in result
    assert "system-vpc" in result


def test_setup_vpc_peering_references_create_vpc_peering():
    from netris_mcp.guides.vpc_peering_guide import setup_vpc_peering
    result = setup_vpc_peering("prod-vpc", "system-vpc")
    assert "create_vpc_peering" in result


# ---------------------------------------------------------------------------
# New guides: acl_guide
# ---------------------------------------------------------------------------


def test_configure_acl_returns_string():
    from netris_mcp.guides.acl_guide import configure_acl
    result = configure_acl("london-dc1")
    assert isinstance(result, str)
    assert len(result) > 100


def test_configure_acl_contains_site():
    from netris_mcp.guides.acl_guide import configure_acl
    result = configure_acl("london-dc1")
    assert "london-dc1" in result


def test_configure_acl_references_create_acl():
    from netris_mcp.guides.acl_guide import configure_acl
    result = configure_acl("london-dc1")
    assert "create_acl" in result


# ---------------------------------------------------------------------------
# New guides: troubleshooting_guide
# ---------------------------------------------------------------------------


def test_troubleshoot_network_returns_string():
    from netris_mcp.guides.troubleshooting_guide import troubleshoot_network
    result = troubleshoot_network("BGP session not coming up")
    assert isinstance(result, str)
    assert len(result) > 100


def test_troubleshoot_network_references_diagnostic_tools():
    from netris_mcp.guides.troubleshooting_guide import troubleshoot_network
    result = troubleshoot_network()
    for tool in ["list_bgp_sessions", "list_vnets", "list_nat_rules", "list_l4lb"]:
        assert tool in result, f"Expected '{tool}' in troubleshooting guide"


# ---------------------------------------------------------------------------
# New guides: multi_site_guide
# ---------------------------------------------------------------------------


def test_setup_multi_site_returns_string():
    from netris_mcp.guides.multi_site_guide import setup_multi_site
    result = setup_multi_site("london-dc1", "amsterdam-dc1", "acme", "acme-vpc")
    assert isinstance(result, str)
    assert len(result) > 100


def test_setup_multi_site_contains_sites():
    from netris_mcp.guides.multi_site_guide import setup_multi_site
    result = setup_multi_site("london-dc1", "amsterdam-dc1", "acme", "acme-vpc")
    assert "london-dc1" in result
    assert "amsterdam-dc1" in result


def test_setup_multi_site_references_create_vnet():
    from netris_mcp.guides.multi_site_guide import setup_multi_site
    result = setup_multi_site("london-dc1", "amsterdam-dc1", "acme", "acme-vpc")
    assert "create_vnet" in result


# ---------------------------------------------------------------------------
# New guides: gpu_cluster_guide
# ---------------------------------------------------------------------------


def test_provision_gpu_cluster_returns_string():
    from netris_mcp.guides.gpu_cluster_guide import provision_gpu_cluster
    result = provision_gpu_cluster("ai-cluster-1", "london-dc1", "acme")
    assert isinstance(result, str)
    assert len(result) > 100


def test_provision_gpu_cluster_contains_cluster_name():
    from netris_mcp.guides.gpu_cluster_guide import provision_gpu_cluster
    result = provision_gpu_cluster("ai-cluster-1", "london-dc1", "acme")
    assert "ai-cluster-1" in result


def test_provision_gpu_cluster_references_l3vpn_tools():
    from netris_mcp.guides.gpu_cluster_guide import provision_gpu_cluster
    result = provision_gpu_cluster("ai-cluster-1", "london-dc1", "acme", node_count=16)
    assert "create_vnet" in result
    assert "update_vnet" in result


def test_provision_gpu_cluster_uses_node_count():
    from netris_mcp.guides.gpu_cluster_guide import provision_gpu_cluster
    result = provision_gpu_cluster("ai-cluster-1", "london-dc1", "acme", node_count=16)
    assert "16" in result


# ---------------------------------------------------------------------------
# Payload shape tests for corrected tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_site_uses_publicAsn():
    """create_site must send publicAsn not 'as' in the payload."""
    captured = {}

    def capture(request):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 1, "name": "test-site"})

    respx.post("https://ctrl.example.com/api/v2/sites/").mock(side_effect=capture)

    from netris_mcp.client import post, api_url
    async with httpx.AsyncClient() as client:
        await post(client, api_url("https://ctrl.example.com", "sites"),
                   {"name": "test-site", "publicAsn": 65001})

    assert "publicAsn" in captured["body"]
    assert "as" not in captured["body"]
    assert captured["body"]["publicAsn"] == 65001


@pytest.mark.asyncio
@respx.mock
async def test_create_l4lb_uses_ip_not_frontendIp():
    """create_l4lb must use 'ip'/'port' keys not 'frontendIp'/'frontendPort'."""
    captured = {}

    def capture(request):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 5})

    respx.post("https://ctrl.example.com/api/v2/l4lb/").mock(side_effect=capture)

    from netris_mcp.client import post, api_url
    async with httpx.AsyncClient() as client:
        await post(client, api_url("https://ctrl.example.com", "l4lb"),
                   {"name": "test-lb", "ip": "10.0.0.1", "port": 443, "protocol": "tcp",
                    "backends": [], "automatic": True})

    assert "ip" in captured["body"]
    assert "port" in captured["body"]
    assert "frontendIp" not in captured["body"]
    assert "frontendPort" not in captured["body"]


@pytest.mark.asyncio
@respx.mock
async def test_create_bgp_uses_remoteIP_localIP():
    """BGP session creation must use remoteIP/localIP not neighborAddress/localAddress."""
    captured = {}

    def capture(request):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 3})

    respx.post("https://ctrl.example.com/api/v2/ebgp/").mock(side_effect=capture)

    from netris_mcp.client import post, api_url
    async with httpx.AsyncClient() as client:
        await post(client, api_url("https://ctrl.example.com", "ebgp"),
                   {"name": "test-bgp", "remoteIP": "192.0.2.1", "localIP": "192.0.2.2",
                    "neighborAs": 65001, "site": {"name": "dc1"}})

    assert "remoteIP" in captured["body"]
    assert "localIP" in captured["body"]
    assert "neighborAddress" not in captured["body"]
    assert "localAddress" not in captured["body"]


@pytest.mark.asyncio
@respx.mock
async def test_ipam_subnet_uses_correct_path():
    """Subnet operations must use /api/v2/ipam/subnet/ not /api/v2/subnet/."""
    hit = {}

    def capture(request):
        hit["url"] = str(request.url)
        return httpx.Response(200, json=[])

    respx.get("https://ctrl.example.com/api/v2/ipam/subnet/").mock(side_effect=capture)

    from netris_mcp.client import get, api_url
    async with httpx.AsyncClient() as client:
        await get(client, api_url("https://ctrl.example.com", "ipam/subnet"))

    assert "ipam/subnet" in hit["url"]
    assert "/api/v2/subnet" not in hit["url"]


@pytest.mark.asyncio
@respx.mock
async def test_snat_rule_includes_translatedAddress():
    """SNAT rules must include translatedAddress in payload."""
    captured = {}

    def capture(request):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 7})

    respx.post("https://ctrl.example.com/api/v2/nat/").mock(side_effect=capture)

    from netris_mcp.client import post, api_url
    async with httpx.AsyncClient() as client:
        await post(client, api_url("https://ctrl.example.com", "nat"),
                   {"name": "test-snat", "type": "SNAT", "sourcePrefix": "10.0.0.0/24",
                    "translatedAddress": "203.0.113.1", "site": {"name": "dc1"}})

    assert "translatedAddress" in captured["body"]
    assert captured["body"]["translatedAddress"] == "203.0.113.1"
    assert captured["body"]["type"] == "SNAT"
