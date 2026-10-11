"""Switch-level direct execution via SSH Jump Host.

Security & Safety Rules:
- STRICTLY read-only command execution.
- Only allow-listed show commands permitted (Cumulus Linux / NVUE show commands).
- Dangerous syntax tokens (;, &&, ||, |, >, <, `) strictly blocked.
- Output capped to prevent token exhaustion.
"""

from __future__ import annotations

import asyncio
import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from app.config import get_config

# Allow-listed read-only commands
ALLOWED_PREFIXES = (
    "nv show",
    "net show",
    "vtysh -c 'show ",
    "vtysh -c \"show ",
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
    async def run_switch_command(
        switch_name: Annotated[str, Field(description="Target switch hostname/IP.")],
        command: Annotated[str, Field(description="Read-only show command (e.g., 'nv show interface', 'vtysh -c \"show bgp summary\"').")],
    ) -> str:
        """Execute read-only show commands directly on Cumulus Linux switches via the controller jump host."""
        if not is_safe_command(command):
            return (
                f"Command rejected by security policy: '{command}'. "
                "Only read-only show commands (nv show, net show, vtysh -c 'show ...', ip route) without shell chaining are permitted."
            )

        if not cfg.ssh_jump_host:
            return (
                f"SSH Jump Host not configured in environment (SSH_JUMP_HOST). "
                f"Would execute safely on '{switch_name}': '{command}'"
            )

        # Build proxy jump SSH command
        jump_user = cfg.ssh_jump_user or "ubuntu"
        switch_user = cfg.ssh_switch_user or "cumulus"
        
        ssh_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=8",
            "-J", f"{jump_user}@{cfg.ssh_jump_host}:{cfg.ssh_jump_port}",
            f"{switch_user}@{switch_name}",
            command,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=12.0)
            
            output = stdout.decode("utf-8", errors="replace")
            err_msg = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return f"Switch execution returned error code {proc.returncode}:\n{err_msg or output}"

            # Limit output to 4,000 characters for token safety
            if len(output) > 4000:
                output = output[:4000] + "\n... [TRUNCATED FOR TOKEN SAFETY]"

            return output
        except asyncio.TimeoutError:
            return f"Timeout executing command on switch '{switch_name}'."
        except Exception as e:
            return f"Execution error: {e}"
