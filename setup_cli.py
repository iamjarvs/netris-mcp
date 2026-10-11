"""Automated Setup and Client Configuration CLI for Netris MCP Server.

Provides:
- Interactive setup prompting for Netris Controller URL and credentials.
- Automatic verification of controller connectivity and authentication.
- Automatic generation of .env and config.json.
- Automatic generation of MCP client configuration files:
  - Claude Desktop (`claude_desktop_config.json`)
  - VS Code / Cursor / Anti-gravity (`.vscode/mcp.json`)
  - Netris Demo Portal registration snippet (`tools.yaml`)
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

import httpx


def prompt_input(prompt: str, default: str = "") -> str:
    msg = f"{prompt} [{default}]: " if default else f"{prompt}: "
    val = input(msg).strip()
    return val or default


def verify_controller_connection(url: str, user: str, pwd: str, verify_ssl: bool = False) -> bool:
    print(f"\n[*] Validating connection to Netris Controller at {url}...")
    try:
        with httpx.Client(base_url=url.rstrip("/"), verify=verify_ssl, timeout=10.0) as client:
            res = client.post("/api/auth", json={"user": user, "password": pwd, "auth_schema_key": "local"})
            if res.status_code == 200:
                print("  [✓] Authentication succeeded! Controller is reachable and credentials are valid.")
                return True
            else:
                print(f"  [✗] Controller returned HTTP {res.status_code}: {res.text}")
                return False
    except Exception as e:
        print(f"  [✗] Connection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Netris MCP Setup & Configuration Utility")
    parser.add_argument("--url", help="Netris Controller URL")
    parser.add_argument("--username", help="Netris Controller username")
    parser.add_argument("--password", help="Netris Controller password")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts")
    args = parser.parse_args()

    print("=" * 65)
    print("      Netris MCP Server — Interactive Setup Wizard")
    print("=" * 65)

    base_dir = Path(__file__).resolve().parent

    url = args.url or prompt_input("Netris Controller URL", "https://adam-ctl.netris.io")
    user = args.username or prompt_input("Controller Username", "netris")
    if args.password:
        pwd = args.password
    else:
        pwd = getpass.getpass("Controller Password [press Enter to keep existing if configured]: ").strip()
        if not pwd and (base_dir / ".env").is_file():
            # Keep existing from .env
            from dotenv import dotenv_values
            env_vals = dotenv_values(base_dir / ".env")
            pwd = env_vals.get("NETRIS_PASSWORD", "")

    ok = verify_controller_connection(url, user, pwd, verify_ssl=False)
    if not ok and not args.non_interactive:
        retry = prompt_input("Proceed saving configuration anyway? (y/n)", "n")
        if retry.lower() != "y":
            print("[!] Aborted setup.")
            sys.exit(1)

    # 1. Write .env
    env_content = f"""# Netris MCP Server Configuration
NETRIS_URL={url}
NETRIS_USERNAME={user}
NETRIS_PASSWORD={pwd}
NETRIS_VERIFY_SSL=false
NETRIS_MCP_MODE=read-only
PORT=8750
HOST=127.0.0.1

# Switch Jump Host Configuration
SSH_JUMP_HOST=adam-ctl.netris.io
SSH_JUMP_PORT=22
SSH_JUMP_USER=ubuntu
SSH_SWITCH_USER=cumulus
"""
    (base_dir / ".env").write_text(env_content, encoding="utf-8")
    print(f"[✓] Written configuration to {base_dir / '.env'}")

    # 2. Write VS Code / Anti-gravity mcp.json
    vscode_dir = base_dir / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    mcp_config = {
        "mcpServers": {
            "netris-mcp": {
                "command": str(base_dir / ".venv" / "bin" / "python"),
                "args": ["-m", "app.server"],
                "env": {
                    "PYTHONPATH": f"{base_dir}:{base_dir / 'app'}",
                    "NETRIS_URL": url,
                    "NETRIS_USERNAME": user,
                    "NETRIS_PASSWORD": pwd,
                    "NETRIS_VERIFY_SSL": "false",
                    "NETRIS_MCP_MODE": "read-only",
                    "SSH_JUMP_HOST": "adam-ctl.netris.io",
                    "SSH_JUMP_USER": "ubuntu",
                    "SSH_SWITCH_USER": "cumulus",
                },
            }
        }
    }
    (vscode_dir / "mcp.json").write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")
    print(f"[✓] Generated IDE configuration in {vscode_dir / 'mcp.json'}")

    # 3. Print Claude Desktop configuration
    claude_snippet = {
        "mcpServers": {
            "netris": {
                "command": f"{base_dir}/.venv/bin/python",
                "args": ["-m", "app.server"],
                "env": {
                    "PYTHONPATH": f"{base_dir}:{base_dir}/app",
                    "NETRIS_URL": url,
                    "NETRIS_USERNAME": user,
                    "NETRIS_PASSWORD": pwd,
                },
            }
        }
    }
    (base_dir / "claude_desktop_config.example.json").write_text(json.dumps(claude_snippet, indent=2))
    print(f"[✓] Generated Claude Desktop snippet in claude_desktop_config.example.json")

    print("\n" + "=" * 65)
    print(" Setup Complete! Next steps:")
    print("   1. Start Demo Tool HTTP Service: ./start.sh")
    print("   2. Run in CLI/STDIO Mode:        ./start.sh --stdio")
    print("   3. Run full test suite:          ./.venv/bin/pytest")
    print("=" * 65)


if __name__ == "__main__":
    main()
