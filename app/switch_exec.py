"""Switch-level direct execution via SSH Jump Host.

Security & Safety Rules:
- STRICTLY read-only command execution.
- Only allow-listed show commands permitted (Cumulus Linux / NVUE / FRR show commands).
- Dangerous syntax tokens (;, &&, ||, |, >, <, `) strictly blocked.
- Output capped to prevent token exhaustion.
- Includes operational hints for Cumulus, SONiC, Junos, Nokia SRL, and Arista.
"""

from __future__ import annotations

import asyncio
import re
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from app.architecture_hints import NOS_ARCHITECTURES, get_architecture_hint
from app.config import get_config

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
)

BLOCKED_CHARS = re.compile(r"[;&|><`$]")


def is_safe_command(cmd: str) -> bool:
    cmd_clean = cmd.strip()
    if BLOCKED_CHARS.search(cmd_clean):
        return False
    return any(cmd_clean.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def register_switch_exec(mcp: FastMCP):
    cfg = get_config()

    @mcp.tool()
    async def architecture_reference(
        platform: Annotated[
            Literal["cumulus", "sonic", "junos", "nokia_sr_linux", "arista_eos", "all"],
            Field(description="Target NOS platform to retrieve operational architecture hints and commands for."),
        ] = "cumulus",
    ) -> str:
        """Retrieve operational architecture guidance, troubleshooting hints, and recommended show commands for network operating systems."""
        import json
        if platform == "all":
            return json.dumps(NOS_ARCHITECTURES, indent=2)
        return json.dumps(get_architecture_hint(platform), indent=2)

    @mcp.tool()
    async def run_switch_command(
        switch_name_or_ip: Annotated[str, Field(description="Target switch management IP or hostname (e.g. '10.253.0.1' or 'leaf-pod00-su0-r0').")],
        command: Annotated[str, Field(description="Read-only show command (e.g., 'nv show router bgp', 'sudo vtysh -c \"show bgp summary\"').")],
    ) -> str:
        """Execute read-only show commands directly on fabric switches via the Netris controller jump host."""
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

        jump_user = cfg.ssh_jump_user or "ubuntu"
        switch_user = cfg.ssh_switch_user or "cumulus"
        
        # Execute ssh to the switch directly from the jump host with jump host id_rsa identity
        escaped_cmd = command.replace('"', '\\"')
        remote_script = (
            f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
            f"-i ~/.ssh/id_rsa {switch_user}@{switch_name_or_ip} \"{escaped_cmd}\""
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
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=12.0)
            
            output = stdout.decode("utf-8", errors="replace")
            err_msg = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return f"Switch execution returned error code {proc.returncode}:\n{err_msg or output}"

            banner = "Welcome to NVIDIA Cumulus (R) Linux (R)\n"
            output = output.removeprefix(banner)

            if len(output) > 4000:
                output = output[:4000] + "\n... [TRUNCATED FOR TOKEN SAFETY]"

            return output.strip()
        except asyncio.TimeoutError:
            return f"Timeout executing command on switch '{switch_name_or_ip}'."
        except Exception as e:
            return f"Execution error: {e}"
