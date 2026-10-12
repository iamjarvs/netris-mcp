"""Switch-level direct execution via SSH Jump Host.

Security & Safety Rules:
- STRICTLY read-only command execution.
- Only allow-listed show commands permitted (Cumulus Linux / NVUE / FRR show commands).
- Dangerous syntax tokens (;, &&, ||, |, >, <, `) strictly blocked.
- Output capped to prevent token exhaustion.
- Automatic target resolution: maps switch hostnames (e.g. 'leaf-pod00-su1-r1')
  and in-band routing addresses (mainAddress) to out-of-band management IPs (mgmtAddress).
- Includes operational hints for Cumulus, SONiC, Junos, Nokia SRL, Arista, and AI Fabrics (UFM, NVL72, ROH).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from app.architecture_hints import NOS_ARCHITECTURES, get_architecture_hint
from app.config import NetrisConfig, get_config
from app.netris_client import NetrisClient

logger = logging.getLogger(__name__)

ALLOWED_PREFIXES = (
    "nv show",
    "net show",
    "vtysh -c 'show ",
    "vtysh -c \"show ",
    "sudo vtysh -c 'show ",
    "sudo vtysh -c \"show ",
    "ip -br link",
    "ip -br addr",
    "ip route show",
    "uname -a",
    "uptime",
    "roce_sys",
    "ibstat",
    "ibstatus",
    "ping ",
    "traceroute ",
)

BLOCKED_CHARS = re.compile(r"[;&|><`$]")

# In-memory switch target cache: (timestamp, name_map, main_ip_map, mgmt_ip_map)
_SWITCH_CACHE: dict[str, Any] = {
    "timestamp": 0.0,
    "name_map": {},
    "main_map": {},
    "mgmt_map": {},
}
_CACHE_TTL = 300.0  # 5 minutes


def is_safe_command(cmd: str) -> bool:
    cmd_clean = cmd.strip()
    if BLOCKED_CHARS.search(cmd_clean):
        return False
    return any(cmd_clean.startswith(prefix) for prefix in ALLOWED_PREFIXES)


async def get_switch_inventory(client: NetrisClient | None, cfg: Config) -> dict[str, Any]:
    """Retrieve and cache hardware inventory mapping names and mainAddresses to mgmtAddresses."""
    global _SWITCH_CACHE
    now = time.time()
    if _SWITCH_CACHE["timestamp"] and (now - _SWITCH_CACHE["timestamp"]) < _CACHE_TTL:
        return _SWITCH_CACHE

    name_map: dict[str, dict[str, Any]] = {}
    main_map: dict[str, dict[str, Any]] = {}
    mgmt_map: dict[str, dict[str, Any]] = {}

    if client:
        try:
            hw_list = await client.get("/api/v2/hw", params={"page": 1, "limit": 200}) or []
            for h in hw_list:
                name = str(h.get("name", "")).strip()
                mgmt = str(h.get("mgmtAddress", "")).strip()
                main = str(h.get("mainAddress", "")).strip()
                htype = str(h.get("type", "switch")).strip().lower()
                sw_role = str(h.get("swRole", "")).strip()
                user = "root" if htype in ("softgate", "server") else (cfg.ssh_switch_user or "cumulus")

                info = {
                    "name": name,
                    "mgmt": mgmt,
                    "main": main,
                    "type": htype,
                    "swRole": sw_role,
                    "user": user,
                }
                if name:
                    name_map[name.lower()] = info
                if main:
                    main_map[main] = info
                if mgmt:
                    mgmt_map[mgmt] = info

            _SWITCH_CACHE = {
                "timestamp": now,
                "name_map": name_map,
                "main_map": main_map,
                "mgmt_map": mgmt_map,
            }
            return _SWITCH_CACHE
        except Exception as e:
            logger.warning("Failed to refresh hardware inventory from Netris API: %s", e)

    return _SWITCH_CACHE


async def resolve_switch_target(
    target: str,
    client: NetrisClient | None,
    cfg: Config,
) -> tuple[str, str, str | None]:
    """Resolve switch target name or IP to (resolved_ip, switch_user, resolution_notice).

    Handles:
    1. Hostnames like 'leaf-pod00-su1-r1' mapped to out-of-band management IP (mgmtAddress).
    2. Underlay routing loopback mainAddress like '10.253.128.6' redirected to mgmtAddress '10.253.0.6'.
    3. Direct management IP input used as-is.
    4. Fallback lookup against jump host ~/.cloudsim_aliases if API lookup has no match.
    """
    clean_target = target.strip()
    inv = await get_switch_inventory(client, cfg)
    name_map = inv.get("name_map", {})
    main_map = inv.get("main_map", {})
    mgmt_map = inv.get("mgmt_map", {})

    target_low = clean_target.lower()

    # 1. Match by switch hostname (e.g., 'leaf-pod00-su1-r1')
    if target_low in name_map:
        info = name_map[target_low]
        resolved_ip = info["mgmt"] or info["main"]
        user = info["user"]
        notice = f"[Resolved '{clean_target}' to management IP {resolved_ip} ({user})]"
        return resolved_ip, user, notice

    # 2. Match by mainAddress (in-band routing loopback e.g., '10.253.128.6')
    if clean_target in main_map:
        info = main_map[clean_target]
        resolved_ip = info["mgmt"] or clean_target
        user = info["user"]
        notice = (
            f"[Redirected in-band routing address {clean_target} ({info['name']}) "
            f"to out-of-band management IP {resolved_ip} ({user})]"
        )
        return resolved_ip, user, notice

    # 3. Match by direct mgmtAddress
    if clean_target in mgmt_map:
        info = mgmt_map[clean_target]
        return clean_target, info["user"], None

    # 4. Fallback: check ~/.cloudsim_aliases on jump host if jump host is configured
    if cfg.ssh_jump_host and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", clean_target):
        try:
            jump_user = cfg.ssh_jump_user or "ubuntu"
            grep_cmd = [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                f"{jump_user}@{cfg.ssh_jump_host}",
                f"grep -E 'alias {clean_target}=' ~/.cloudsim_aliases",
            ]
            proc = await asyncio.create_subprocess_exec(
                *grep_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=6.0)
            line = stdout.decode("utf-8", errors="replace").strip()
            # Match e.g. alias leaf-pod00-su1-r1='ssh -o StrictHostKeyChecking=no cumulus@10.253.0.6'
            match = re.search(r"([a-zA-Z0-9_-]+)@([0-9.]+)", line)
            if match:
                user = match.group(1)
                resolved_ip = match.group(2)
                notice = f"[Resolved alias '{clean_target}' from jump host to {resolved_ip} ({user})]"
                return resolved_ip, user, notice
        except Exception as e:
            logger.debug("Jump host alias resolution error: %s", e)

    # Default to passing through
    default_user = cfg.ssh_switch_user or "cumulus"
    return clean_target, default_user, None


def register_switch_exec(mcp: FastMCP, client: NetrisClient | None = None):
    cfg = get_config()

    @mcp.tool()
    async def architecture_reference(
        platform: Annotated[
            Literal[
                "cumulus",
                "sonic",
                "junos",
                "nokia_sr_linux",
                "arista_eos",
                "ai_fabric",
                "nvidia_ufm",
                "nvidia_nvlink_nvl72",
                "on_host_networking",
                "all",
            ],
            Field(description="Target platform or AI fabric architecture domain to retrieve operational guidance and show commands for."),
        ] = "cumulus",
    ) -> str:
        """Retrieve operational architecture guidance, troubleshooting hints, and recommended show commands for network operating systems and AI fabrics."""
        import json
        if platform == "all":
            return json.dumps(NOS_ARCHITECTURES, indent=2)
        return json.dumps(get_architecture_hint(platform), indent=2)

    @mcp.tool()
    async def run_switch_command(
        switch_name_or_ip: Annotated[str, Field(description="Target switch management IP, loopback, or hostname (e.g. 'leaf-pod00-su1-r1', '10.253.0.6', or 'spine-0-pod00').")],
        command: Annotated[str, Field(description="Read-only show command (e.g., 'nv show router bgp', 'sudo vtysh -c \"show bgp summary\"').")],
    ) -> str:
        """Execute read-only show commands directly on fabric switches via the Netris controller jump host. Automatically resolves switch hostnames and in-band addresses to out-of-band management IPs."""
        if not is_safe_command(command):
            return (
                f"Command rejected by security policy: '{command}'. "
                "Only read-only show commands (nv show, net show, sudo vtysh -c 'show ...', ip route) without shell chaining are permitted."
            )

        if not cfg.ssh_jump_host:
            return (
                f"SSH Jump Host not configured in environment (SSH_JUMP_HOST). "
                f"Would execute safely on '{switch_name_or_ip}': '{command}'"
            )

        target_ip, switch_user, resolution_notice = await resolve_switch_target(switch_name_or_ip, client, cfg)
        jump_user = cfg.ssh_jump_user or "ubuntu"

        # Execute ssh to the switch directly from the jump host
        escaped_cmd = command.replace('"', '\\"')
        remote_script = (
            f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=6 "
            f"-i ~/.ssh/id_rsa {switch_user}@{target_ip} \"{escaped_cmd}\""
        )

        jump_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=8",
            f"{jump_user}@{cfg.ssh_jump_host}",
            remote_script,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *jump_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=14.0)

            output = stdout.decode("utf-8", errors="replace")
            err_msg = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                hint = ""
                if "Could not resolve hostname" in err_msg:
                    hint = f"\nHint: Hostname '{switch_name_or_ip}' was not found in DNS or inventory. Ensure the target exists in Netris hardware inventory (/api/v2/hw)."
                elif "Connection timed out" in err_msg:
                    hint = f"\nHint: Connection timed out connecting to {target_ip}. Verify the switch management plane is reachable from the jump host ({cfg.ssh_jump_host})."
                return f"Switch execution returned error code {proc.returncode}:\n{err_msg or output}{hint}"

            # Strip standard welcome banners
            output = re.sub(r"^Welcome to NVIDIA Cumulus \(R\) Linux \(R\)\s*", "", output)

            if len(output) > 4000:
                output = output[:4000] + "\n... [TRUNCATED FOR TOKEN SAFETY]"

            res_text = output.strip()
            if resolution_notice:
                return f"{resolution_notice}\n\n{res_text}"
            return res_text
        except asyncio.TimeoutError:
            return f"Timeout executing command on switch '{switch_name_or_ip}' (target IP: {target_ip})."
        except Exception as e:
            return f"Execution error: {e}"
