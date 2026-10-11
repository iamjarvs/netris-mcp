# 03 — Connecting AI Clients

## 1. Claude Desktop
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "netris": {
      "command": "/absolute/path/to/netris-mcp/.venv/bin/python",
      "args": ["-m", "app.server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/netris-mcp:/absolute/path/to/netris-mcp/app",
        "NETRIS_URL": "https://adam-ctl.netris.io",
        "NETRIS_USERNAME": "netris",
        "NETRIS_PASSWORD": "your-password"
      }
    }
  }
}
```

## 2. Anti-gravity IDE / Cursor / VS Code
The `setup_cli.py` wizard automatically configures `.vscode/mcp.json`. 

To verify:
1. Open the Anti-gravity / VS Code MCP panel.
2. Ensure `netris-mcp` is active and green.
3. Call `fabric_inventory` in chat: *"Summarise the health and inventory of my Netris fabric."*

## 3. Netris Demo Control Portal
Register in `demo-portal/tools.yaml`:

```yaml
- id: "netris-mcp"
  name: "Netris MCP Server"
  type: "git"
  url: "https://github.com/iamjarvs/netris-mcp.git"
  path: "./managed-tools/netris-mcp"
  description: "AI-native Model Context Protocol server for Netris fabric operations and triage."
  port: 8750
  health_endpoint: "http://localhost:8750/api/health"
```
