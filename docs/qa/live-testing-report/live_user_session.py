"""Live End-to-End User Persona Simulation against Netris MCP Server.

Simulates an AI Cloud Network Architect / SRE performing an operational audit:
1. Fabric Discovery (Sites, Switches, Servers, VPCs)
2. AI Fabric Architecture Consultation (Front-End/Back-End, UFM, NVLink NVL72, ROH)
3. Fabric Health Assessment (Agent Heartbeats, Sensor Alarms, eBGP Sessions)
4. Multi-Layer Triage Playbooks (Root cause analysis)
5. Live Switch Execution via Controller Jump Host (Hostname resolution, loopback redirection, show commands)
6. Audit Log Queries (API logs, graceful events fallback)
7. Real-Time Telemetry & Visual Charting
8. Safe Mutation Dry-Run Previews (Read-only protection enforcement)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from dotenv import load_dotenv

# Load credentials from .env
load_dotenv(".env")

from app.config import get_config
from app.netris_client import NetrisClient
from fastmcp import FastMCP
from app.tools_dispatch import register_tools
from app.diagnostics_dispatch import register_diagnostics
from app.switch_exec import register_switch_exec
from app.mutations import register_mutations
from app.telemetry_dispatch import register_telemetry
from app.charting import register_charting

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_user_session")


async def run_live_user_session():
    cfg = get_config()
    client = NetrisClient(
        base_url=cfg.netris_url,
        username=cfg.netris_username,
        password=cfg.netris_password,
        verify_ssl=cfg.netris_verify_ssl,
    )

    mcp = FastMCP("LiveUserSession")
    register_tools(mcp, client)
    register_diagnostics(mcp, client)
    register_switch_exec(mcp, client)
    register_mutations(mcp, client)
    register_telemetry(mcp, client)
    register_charting(mcp)

    session_log = []

    async def execute_step(step_number: int, name: str, tool_name: str, kwargs: dict):
        logger.info("Step %d: %s (%s)", step_number, name, tool_name)
        start_time = time.time()
        try:
            tool = await mcp.get_tool(tool_name)
            raw_result = await tool.fn(**kwargs)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            # Attempt to parse json for neatness
            try:
                parsed_res = json.loads(raw_result)
            except Exception:
                parsed_res = raw_result

            record = {
                "step": step_number,
                "name": name,
                "tool": tool_name,
                "arguments": kwargs,
                "duration_ms": duration_ms,
                "status": "SUCCESS",
                "output": parsed_res,
            }
            session_log.append(record)
            logger.info("  -> Completed in %s ms", duration_ms)
            return record
        except Exception as err:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            record = {
                "step": step_number,
                "name": name,
                "tool": tool_name,
                "arguments": kwargs,
                "duration_ms": duration_ms,
                "status": "ERROR",
                "error": str(err),
            }
            session_log.append(record)
            logger.error("  -> Failed in %s ms: %s", duration_ms, err)
            return record

    logger.info("=== Commencing Live Netris MCP User Persona Session ===")

    # Step 1: Fabric Discovery
    await execute_step(
        1, "Discover High-Level Fabric Inventory",
        "fabric_inventory", {"domain": "summary"}
    )

    # Step 2: Switch Fleet Inspection
    await execute_step(
        2, "Inspect Switch Fleet",
        "fabric_inventory", {"domain": "switches", "limit": 10}
    )

    # Step 3: Compute Server Fleet Inspection
    await execute_step(
        3, "Inspect AI GPU Compute Nodes",
        "fabric_inventory", {"domain": "servers", "limit": 10}
    )

    # Step 4: AI Fabric Architecture Consultation
    await execute_step(
        4, "Consult AI Fabric Dual-Plane Design",
        "architecture_reference", {"platform": "ai_fabric"}
    )

    # Step 5: NVIDIA UFM InfiniBand Integration Guidance
    await execute_step(
        5, "Consult NVIDIA UFM Integration Architecture",
        "architecture_reference", {"platform": "nvidia_ufm"}
    )

    # Step 6: NVIDIA NVLink NVL72 Multi-Node Guidance
    await execute_step(
        6, "Consult NVIDIA NVLink NVL72 Architecture",
        "architecture_reference", {"platform": "nvidia_nvlink_nvl72"}
    )

    # Step 7: On-Host Networking (ROH) Guidance
    await execute_step(
        7, "Consult On-Host Networking & ROH Patterns",
        "architecture_reference", {"platform": "on_host_networking"}
    )

    # Step 8: Fabric Health Overview
    await execute_step(
        8, "Audit Fabric Health & Border BGP",
        "fabric_health", {"scope": "overview"}
    )

    # Step 9: Automated Triage Playbook
    await execute_step(
        9, "Execute Automated Fabric Health Triage",
        "triage", {"symptom": "fabric_health_check"}
    )

    # Step 10: Switch Live Execution via Hostname Resolution
    await execute_step(
        10, "Run BGP Summary on Leaf Switch by Hostname",
        "run_switch_command", {
            "switch_name_or_ip": "leaf-pod00-su1-r1",
            "command": 'sudo vtysh -c "show bgp summary"'
        }
    )

    # Step 11: Switch Live Execution via In-Band Loopback Redirection
    await execute_step(
        11, "Run NVUE Version on Leaf Switch by Loopback IP",
        "run_switch_command", {
            "switch_name_or_ip": "10.253.128.6",
            "command": "nv show system version"
        }
    )

    # Step 12: Spine Switch Live Execution
    await execute_step(
        12, "Run BGP Summary on Spine Switch by Hostname",
        "run_switch_command", {
            "switch_name_or_ip": "spine-0-pod00",
            "command": 'sudo vtysh -c "show bgp summary"'
        }
    )

    # Step 13: Switch Interface State
    await execute_step(
        13, "Inspect Interface Link Summary on Leaf",
        "run_switch_command", {
            "switch_name_or_ip": "leaf-pod00-su1-r1",
            "command": "ip -br link"
        }
    )

    # Step 14: Audit API Logs
    await execute_step(
        14, "Query Controller REST API Audit Trail",
        "fabric_audit", {"category": "api_logs", "limit": 5}
    )

    # Step 15: Event Logs Query with Graceful Fallback
    await execute_step(
        15, "Query Event Logs (Testing 500 Graceful Fallback)",
        "fabric_audit", {"category": "events", "limit": 5}
    )

    # Step 16: Sensor Monitoring Checks
    await execute_step(
        16, "Inspect Monitoring Check Thresholds",
        "fabric_audit", {"category": "monitoring_checks", "limit": 5}
    )

    # Step 17: Looking Glass Peers Inspection
    await execute_step(
        17, "Query Looking Glass BGP Peers",
        "looking_glass", {"query": "peers_list"}
    )

    # Step 18: Fabric Telemetry Utilisation
    await execute_step(
        18, "Inspect Fabric Interface Bandwidth Utilisation",
        "fabric_telemetry", {"intent": "interface_utilisation", "top_n": 5}
    )

    # Step 19: Telemetry Visual Chart Generation
    await execute_step(
        19, "Render Telemetry Visual Chart",
        "generate_telemetry_chart", {
            "chart_type": "bar",
            "title": "North-South Ingress Bandwidth Distribution",
            "labels": ["spine-0-pod00", "spine-1-pod00", "spine-2-pod00", "spine-3-pod00"],
            "values": [42.5, 38.2, 41.0, 39.7],
            "y_axis_label": "Throughput (Gbps)"
        }
    )

    # Step 20: Safe Mutation Preview (Dry Run)
    await execute_step(
        20, "Verify V-Net Creation Dry-Run Diff Preview",
        "mutate_vnet", {
            "operation": "create",
            "name": "mcp-qa-ai-train-dataset",
            "vpc_name": "Default",
            "gateways": "10.100.55.1/24",
            "dry_run": True
        }
    )

    # Step 21: Read-Only Enforcement Verification
    await execute_step(
        21, "Verify Live Mutation Rejection in Read-Only Mode",
        "mutate_vnet", {
            "operation": "create",
            "name": "mcp-qa-illegal-vnet",
            "vpc_name": "Default",
            "gateways": "10.100.60.1/24",
            "dry_run": False
        }
    )

    logger.info("=== Completed Live User Persona Session (%d steps) ===", len(session_log))

    # Persist log
    out_path = Path("docs/qa/live-testing-report/live_session_output.json")
    out_path.write_text(json.dumps(session_log, indent=2))
    logger.info("Persisted full session log to %s", out_path)


if __name__ == "__main__":
    asyncio.run(run_live_user_session())
