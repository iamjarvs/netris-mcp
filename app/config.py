"""Configuration loader for the Netris MCP integration.

Adheres to the Demo Tool template contract by checking environment variables first,
falling back to config.json, and providing sensible defaults.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ModeType = Literal["read-only", "read-write"]
ToolSurfaceType = Literal["compact", "full"]

@dataclass
class NetrisConfig:
    netris_url: str
    netris_username: str
    netris_password: str
    netris_verify_ssl: bool = False
    mode: ModeType = "read-only"
    tool_surface: ToolSurfaceType = "compact"
    port: int = 8750
    host: str = "0.0.0.0"
    
    # Optional jump host / switch access
    ssh_jump_host: str | None = None
    ssh_jump_port: int = 22
    ssh_jump_user: str | None = None
    ssh_switch_user: str | None = None

    def __repr__(self) -> str:
        """Protect secrets from accidentally leaking into log outputs."""
        return (
            f"NetrisConfig(url={self.netris_url!r}, username={self.netris_username!r}, "
            f"mode={self.mode!r}, tool_surface={self.tool_surface!r}, port={self.port}, "
            f"verify_ssl={self.netris_verify_ssl})"
        )


def _load_json_config(base_path: Path) -> dict[str, Any]:
    candidates = [base_path / "config.json", base_path / "config.example.json"]
    for path in candidates:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def get_config(root_dir: Path | str | None = None) -> NetrisConfig:
    """Load configuration prioritising environment variables over JSON config files."""
    if root_dir is None:
        base_path = Path(__file__).resolve().parent.parent
    else:
        base_path = Path(root_dir)

    # Automatically load .env if present
    env_file = base_path / ".env"
    if env_file.is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_file, override=False)
        except Exception:
            pass

    json_data = _load_json_config(base_path)

    # 1. Base URL
    netris_url = os.getenv("NETRIS_URL") or json_data.get("netris_url") or "https://adam-ctl.netris.io"
    netris_url = netris_url.rstrip("/")

    # 2. Authentication credentials
    username = os.getenv("NETRIS_USERNAME") or json_data.get("netris_username") or "netris"
    password = os.getenv("NETRIS_PASSWORD") or json_data.get("netris_password") or ""

    # 3. SSL Verification
    ssl_env = os.getenv("NETRIS_VERIFY_SSL")
    if ssl_env is not None:
        verify_ssl = ssl_env.lower() in ("1", "true", "yes")
    else:
        verify_ssl = bool(json_data.get("netris_verify_ssl", False))

    # 4. Mode (read-only vs read-write)
    mode_raw = os.getenv("NETRIS_MCP_MODE") or json_data.get("mode") or "read-only"
    mode: ModeType = "read-write" if mode_raw.lower() in ("read-write", "rw") else "read-only"

    # 5. Tool Surface (compact vs full)
    surface_raw = os.getenv("NETRIS_MCP_TOOL_SURFACE") or json_data.get("tool_surface") or "compact"
    tool_surface: ToolSurfaceType = "full" if surface_raw.lower() == "full" else "compact"

    # 6. Port and Host
    port_str = os.getenv("PORT") or json_data.get("port") or "8750"
    try:
        port = int(port_str)
    except ValueError:
        port = 8750

    host = os.getenv("HOST") or json_data.get("host") or "0.0.0.0"

    # 7. Jump Host settings
    ssh_jump_host = os.getenv("SSH_JUMP_HOST") or json_data.get("ssh_jump_host")
    ssh_jump_port = int(os.getenv("SSH_JUMP_PORT") or json_data.get("ssh_jump_port") or 22)
    ssh_jump_user = os.getenv("SSH_JUMP_USER") or json_data.get("ssh_jump_user")
    ssh_switch_user = os.getenv("SSH_SWITCH_USER") or json_data.get("ssh_switch_user")

    return NetrisConfig(
        netris_url=netris_url,
        netris_username=username,
        netris_password=password,
        netris_verify_ssl=verify_ssl,
        mode=mode,
        tool_surface=tool_surface,
        port=port,
        host=host,
        ssh_jump_host=ssh_jump_host,
        ssh_jump_port=ssh_jump_port,
        ssh_jump_user=ssh_jump_user,
        ssh_switch_user=ssh_switch_user,
    )
