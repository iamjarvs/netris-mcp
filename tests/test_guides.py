"""
Tests for netris_mcp.guides — prompt functions return well-formed markdown.
"""

import os
import pytest

os.environ.setdefault("NETRIS_HOST", "test.example.com")
os.environ.setdefault("NETRIS_USERNAME", "admin")
os.environ.setdefault("NETRIS_PASSWORD", "secret")

from netris_mcp.guides.site_onboarding import onboard_new_site  # noqa: E402
from netris_mcp.guides.vpc_provisioning import provision_vpc  # noqa: E402
from netris_mcp.guides.bgp_setup import setup_bgp_peering  # noqa: E402
from netris_mcp.guides.l4lb_setup import setup_load_balancer  # noqa: E402
from netris_mcp.guides.network_bootstrap import bootstrap_network  # noqa: E402


# ---------------------------------------------------------------------------
# onboard_new_site
# ---------------------------------------------------------------------------


def test_onboard_new_site_returns_string():
    result = onboard_new_site("london-dc1", 65001)
    assert isinstance(result, str)
    assert len(result) > 100


def test_onboard_new_site_contains_site_name():
    result = onboard_new_site("london-dc1", 65001)
    assert "london-dc1" in result


def test_onboard_new_site_contains_asn():
    result = onboard_new_site("london-dc1", 65001)
    assert "65001" in result


def test_onboard_new_site_references_create_site_tool():
    result = onboard_new_site("london-dc1", 65001)
    assert "create_site" in result


def test_onboard_new_site_with_location():
    result = onboard_new_site("london-dc1", 65001, location="London, UK")
    assert "London, UK" in result


# ---------------------------------------------------------------------------
# provision_vpc
# ---------------------------------------------------------------------------


def test_provision_vpc_returns_string():
    result = provision_vpc("prod-vpc", "acme")
    assert isinstance(result, str)
    assert len(result) > 100


def test_provision_vpc_contains_vpc_name():
    result = provision_vpc("prod-vpc", "acme")
    assert "prod-vpc" in result


def test_provision_vpc_contains_tenant():
    result = provision_vpc("prod-vpc", "acme")
    assert "acme" in result


def test_provision_vpc_references_create_vpc_tool():
    result = provision_vpc("prod-vpc", "acme")
    assert "create_vpc" in result


def test_provision_vpc_with_subnet():
    result = provision_vpc("prod-vpc", "acme", subnet_prefix="10.10.0.0/16")
    assert "10.10.0.0/16" in result


# ---------------------------------------------------------------------------
# setup_bgp_peering
# ---------------------------------------------------------------------------


def test_setup_bgp_peering_returns_string():
    result = setup_bgp_peering("upstream-peer", 64512, "192.0.2.1", "192.0.2.2", "london-dc1")
    assert isinstance(result, str)


def test_setup_bgp_peering_contains_peer_name():
    result = setup_bgp_peering("upstream-peer", 64512, "192.0.2.1", "192.0.2.2", "london-dc1")
    assert "upstream-peer" in result


def test_setup_bgp_peering_contains_neighbor_as():
    result = setup_bgp_peering("upstream-peer", 64512, "192.0.2.1", "192.0.2.2", "london-dc1")
    assert "64512" in result


def test_setup_bgp_peering_references_create_bgp_session_tool():
    result = setup_bgp_peering("upstream-peer", 64512, "192.0.2.1", "192.0.2.2", "london-dc1")
    assert "create_bgp_session" in result


# ---------------------------------------------------------------------------
# setup_load_balancer
# ---------------------------------------------------------------------------


def test_setup_load_balancer_returns_string():
    result = setup_load_balancer("web-lb", "london-dc1", "acme", "10.0.0.100", 443)
    assert isinstance(result, str)


def test_setup_load_balancer_contains_lb_name():
    result = setup_load_balancer("web-lb", "london-dc1", "acme", "10.0.0.100", 443)
    assert "web-lb" in result


def test_setup_load_balancer_contains_frontend_ip():
    result = setup_load_balancer("web-lb", "london-dc1", "acme", "10.0.0.100", 443)
    assert "10.0.0.100" in result


def test_setup_load_balancer_contains_port():
    result = setup_load_balancer("web-lb", "london-dc1", "acme", "10.0.0.100", 443)
    assert "443" in result


def test_setup_load_balancer_references_create_l4lb_tool():
    result = setup_load_balancer("web-lb", "london-dc1", "acme", "10.0.0.100", 443)
    assert "create_l4lb" in result


# ---------------------------------------------------------------------------
# bootstrap_network
# ---------------------------------------------------------------------------


def test_bootstrap_network_returns_string():
    result = bootstrap_network("acme", "london-dc1", 65001, "10.100.0.0/24", "10.200.0.0/24", "203.0.113.0/24")
    assert isinstance(result, str)
    assert len(result) > 100


def test_bootstrap_network_contains_tenant():
    result = bootstrap_network("acme", "london-dc1", 65001, "10.100.0.0/24", "10.200.0.0/24", "203.0.113.0/24")
    assert "acme" in result


def test_bootstrap_network_contains_address_block():
    result = bootstrap_network("acme", "london-dc1", 65001, "10.100.0.0/24", "10.200.0.0/24", "203.0.113.0/24")
    assert "10.100.0.0/24" in result


def test_bootstrap_network_references_multiple_tools():
    result = bootstrap_network("acme", "london-dc1", 65001, "10.100.0.0/24", "10.200.0.0/24", "203.0.113.0/24")
    # Should reference the key tools needed for a full bootstrap
    for tool in ["create_site", "create_vpc"]:
        assert tool in result, f"Expected '{tool}' to appear in bootstrap guide"
