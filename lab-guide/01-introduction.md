# 01 — Introduction: Netris MCP Server

The **Netris MCP Server** exposes the [Netris Network Automation Platform](https://netris.io) to AI models and Model Context Protocol (MCP) clients (Claude Desktop, Cursor, Anti-gravity IDE, VS Code, and the Netris Proof of Concept Demo Portal).

```mermaid
flowchart LR
    Client["AI Assistant (Claude / Cursor / IDE)"] -->|STDIO / JSON-RPC| Server["Netris MCP Server"]
    Portal["Demo Control Portal"] -->|HTTP /api/health| Web["Webserver (8750)"]
    Server -->|Umbrella Tools| Dispatch["Tools Dispatcher"]
    Dispatch -->|Cookie Auth / REST| Ctl["Netris Controller (v4.15)"]
    Dispatch -->|Jump Host SSH (Read-only)| Sw["Cumulus Linux Fabric Switches"]
```

## Core Architecture Highlights
1. **Demo Portal Plug-and-Play Contract:** Implements universal startup (`./start.sh`), teardown (`./stop.sh`), and health validation (`/api/health`).
2. **Compact Umbrella Tooling:** Minimises LLM context overhead by grouping related resources into cohesive dispatchers (`fabric_inventory`, `virtual_networks`, `routing_and_policy`, `fabric_links`, `fabric_health`, `triage`, `looking_glass`).
3. **Safety & Security by Default:** Read-only operation by default; command injection prevention on switch shells; automatic credential redaction in all logging streams.
4. **Direct Switch Execution with Multi-Vendor Hints:** Direct, audited show command execution on Cumulus switches with reference architecture hints for SONiC, Junos, Nokia SR Linux, and Arista EOS.
