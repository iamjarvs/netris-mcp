# Netris MCP Server — Open Questions & Next Steps

This document records architectural decisions and design questions identified during development for review and iteration.

---

## 1. Multi-instance Support vs Single Controller
- **Current implementation:** Configured against a primary controller URL via `.env` / `config.json` (aligned with the `netris-demo-tool-template` pattern).
- **Inspiration from `mcp-apstra`:** `mcp-apstra` supports multiple instances via an optional `config/instances.yaml`.
- **Question for Adam:** Would you like to introduce multi-instance switching in the Netris MCP server (e.g., managing distinct lab vs production controller instances simultaneously), or keep single-target configuration per instance?

---

## 2. Granular Legacy Tools vs Compact Dispatchers
- **Current default:** By default, tools are grouped into compact umbrella dispatchers (`fabric_inventory`, `virtual_networks`, `routing_and_policy`, `fabric_links`, `fabric_health`, `triage`, `looking_glass`). This keeps prompt context compact.
- **Toggle available:** `NETRIS_MCP_TOOL_SURFACE=full` can be supported to expose individual per-endpoint functions (e.g., `get_vnet`, `create_vnet`, `list_sites`).
- **Question for Adam:** Do you prefer keeping the compact umbrella approach as the permanent default, or should we expose all individual tools side-by-side?

---

## 3. Direct Switch Execution via SSH Jump Host
- **Current implementation:** `run_switch_command` includes strict regex command sanitisation, blocking shell chaining and allowing only read-only show commands (`nv show`, `vtysh -c 'show...'`, `ip route`).
- **Controller requirement:** The Netris controller itself acts as the jump host (`SSH_JUMP_HOST=adam-ctl.netris.io`).
- **Question for Adam:** Would you like to enable and verify live switch SSH connectivity in your lab environment using designated switch keys?
