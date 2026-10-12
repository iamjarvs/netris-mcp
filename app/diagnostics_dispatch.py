"""Diagnostics and Observability tool dispatchers inspired by mcp-apstra.

Provides:
- `fabric_health`: Aggregated health assessment across agent heartbeats, hardware alarms, and BGP sessions.
- `fabric_audit`: Query API logs and system event logs with preset filters.
- `triage`: Symptom-to-root-cause automated diagnosis workflows (e.g. V-Net degraded, BGP down).
- `looking_glass`: Switch-level diagnostic queries (BGP summary, BGP route, ping, traceroute).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from app.netris_client import NetrisClient
from app.primitives import format_digest, to_json_output

logger = logging.getLogger(__name__)


async def _execute_switch_diag(
    target: str,
    cmd: str,
    client: NetrisClient | None,
) -> dict[str, Any]:
    """Execute diagnostic show, ping, or traceroute command via jump host or simulated mode."""
    from app.config import get_config
    from app.switch_exec import resolve_switch_target

    cfg = get_config()
    if not cfg.ssh_jump_host:
        return {
            "exit_code": 0,
            "output": f"[Simulated execution on {target}]: {cmd}",
            "simulated": True,
        }

    try:
        target_ip, switch_user, _ = await resolve_switch_target(target, client, cfg)
        jump_user = cfg.ssh_jump_user or "ubuntu"
        remote_script = (
            f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=6 "
            f"-i ~/.ssh/id_rsa {switch_user}@{target_ip} '{cmd}'"
        )
        jump_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=8",
            f"{jump_user}@{cfg.ssh_jump_host}",
            remote_script,
        ]
        proc = await asyncio.create_subprocess_exec(
            *jump_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=12.0)
        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()
        return {
            "exit_code": proc.returncode,
            "output": out_text or err_text,
            "simulated": False,
        }
    except Exception as e:
        logger.warning("Switch diagnostic execution failed for %s: %s", target, e)
        return {
            "exit_code": 1,
            "output": f"Execution error: {e}",
            "simulated": False,
        }


def register_diagnostics(mcp: FastMCP, client: NetrisClient):

    # -------------------------------------------------------------------------
    # 1. Fabric Health Umbrella Tool
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def fabric_health(
        scope: Annotated[
            Literal["overview", "heartbeats", "hardware_health", "ebgp_health"],
            Field(description="Scope of health audit."),
        ] = "overview",
        limit: Annotated[int, Field(description="Max items to list.")] = 50,
    ) -> str:
        """Evaluate overall health: agent heartbeats, sensor alarms, and border BGP sessions."""
        if scope == "overview":
            widgets = await client.get("/api/v2/dashboard/widgets") or []
            total_counts = await client.get("/api/dashboard/totalcounts") or {}
            heartbeats = await client.get("/api/v2/dashboard/agent-heartbeats") or []
            ebgp = await client.get("/api/v2/ebgp") or []
            
            critical_hb = [h for h in heartbeats if str(h.get("status", "")).lower() in ("critical", "failed", "down")]
            established_ebgp = [e for e in ebgp if str(e.get("bgp_state", "")).lower() == "established"]
            
            assessment = {
                "overall_status": "Degraded" if critical_hb else "Healthy",
                "summary": {
                    "total_heartbeat_nodes": len(heartbeats),
                    "critical_heartbeats_count": len(critical_hb),
                    "critical_nodes": [h.get("name") for h in critical_hb[:10]],
                    "ebgp_sessions_total": len(ebgp),
                    "ebgp_established": len(established_ebgp),
                },
                "dashboard_widgets": widgets,
            }
            return to_json_output(assessment)

        elif scope == "heartbeats":
            heartbeats = await client.get("/api/v2/dashboard/agent-heartbeats") or []
            return to_json_output(format_digest(heartbeats, ["id", "name", "status", "lastHeartbeat", "site"], limit=limit))

        elif scope == "hardware_health":
            hw_health = await client.get("/api/v2/dashboard/hardware-health") or []
            return to_json_output(format_digest(hw_health, ["id", "name", "status", "alarmType", "description"], limit=limit))

        elif scope == "ebgp_health":
            ebgp = await client.get("/api/v2/ebgp") or []
            return to_json_output(format_digest(ebgp, ["id", "name", "neighbor_as", "status", "local_ip", "remote_ip"], limit=limit))

        return "Unknown scope"

    # -------------------------------------------------------------------------
    # 2. Fabric Audit Tool
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def fabric_audit(
        category: Annotated[
            Literal["events", "monitoring_checks", "api_logs"],
            Field(description="Audit log category: 'api_logs' for controller API audit trail, 'events' for hardware event logs, 'monitoring_checks' for threshold rules."),
        ] = "events",
        limit: Annotated[int, Field(description="Max records to return.")] = 50,
    ) -> str:
        """Query event logs, API audit trails, and monitoring check threshold configurations."""
        now = int(time.time())
        start = now - (86400 * 3)  # Past 72 hours window

        if category == "api_logs":
            try:
                logs = await client.get(
                    "/api/apilogs",
                    params={
                        "start": start,
                        "end": now,
                        "pagination": f'{{"limit":{limit},"offset":0}}',
                        "sort": '{"sortBy":"createdAt","order":"DESC"}',
                    },
                ) or []
                return to_json_output(format_digest(logs, ["id", "createdAt", "method", "url", "user", "ip"], limit=limit))
            except Exception as e:
                return to_json_output({"error": f"Failed to retrieve API audit logs: {e}"})

        elif category == "events":
            try:
                events = await client.get("/api/eventlogs", params={"start": start, "end": now}) or []
                return to_json_output(format_digest(events, ["id", "hardware", "status", "checkName", "message", "date"], limit=limit))
            except Exception as e:
                # In environments where /api/eventlogs is uninitialised or returns 500, fallback gracefully to mutation audit logs
                logger.warning("/api/eventlogs query failed (%s); falling back gracefully to /api/apilogs mutations", e)
                try:
                    fallback_logs = await client.get(
                        "/api/apilogs",
                        params={
                            "start": start,
                            "end": now,
                            "pagination": f'{{"limit":{min(limit, 30)},"offset":0}}',
                            "filter": '{"method":["POST","PUT","PATCH","DELETE"]}',
                            "sort": '{"sortBy":"createdAt","order":"DESC"}',
                        },
                    ) or []
                    return to_json_output({
                        "notice": (
                            "Netris controller event log service (/api/eventlogs) is currently unconfigured or uninitialised in this deployment (HTTP 500). "
                            "Gracefully returning recent configuration mutation audit events from /api/apilogs instead."
                        ),
                        "fallback_category": "api_logs",
                        "recent_mutation_events": format_digest(fallback_logs, ["id", "createdAt", "method", "url", "user", "ip"], limit=limit),
                    })
                except Exception as fb_err:
                    return to_json_output({
                        "error": (
                            f"Controller /api/eventlogs returned 500 and audit log fallback encountered: {fb_err}. "
                            "Try querying with category='api_logs' or category='monitoring_checks'."
                        ),
                    })

        elif category == "monitoring_checks":
            checks = await client.get("/api/checkthresholds") or []
            return to_json_output(format_digest(checks, ["id", "name", "unit", "critLow", "warnLow", "warnHigh", "critHigh"], limit=limit))

        return "Unknown category"

    # -------------------------------------------------------------------------
    # 3. Fabric Triage Tool (Symptom-to-Root-Cause)
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def triage(
        symptom: Annotated[
            Literal["vnet_degraded", "bgp_session_down", "node_unreachable", "fabric_health_check"],
            Field(description="Observed anomaly or symptom to triage."),
        ],
        target_name: Annotated[str | None, Field(description="Target resource name (e.g., V-Net name, BGP name, Switch name).")] = None,
    ) -> str:
        """Automated diagnosis playbook analysing root causes across multiple subsystems."""
        findings = []
        verdict = "INCONCLUSIVE"

        if symptom == "vnet_degraded":
            vnets = await client.get("/api/v2/vnet") or []
            target = next((v for v in vnets if str(v.get("name", "")).lower() == (target_name or "").lower()), None)
            if not target and target_name:
                return f"V-Net '{target_name}' not found."
            
            # Audit state, gateways, and associated VPC
            target_list = [target] if target else vnets
            for v in target_list:
                state = v.get("state")
                v_name = v.get("name")
                if state != "active":
                    findings.append(f"V-Net '{v_name}' state is '{state}' (Expected 'active').")
            
            verdict = "HEALTHY" if not findings else "ANOMALY_DETECTED"
            return to_json_output({
                "symptom": symptom,
                "target": target_name or "ALL",
                "verdict": verdict,
                "findings": findings or ["All inspected V-Nets report active state."],
            })

        elif symptom == "bgp_session_down":
            ebgp = await client.get("/api/v2/ebgp") or []
            for b in ebgp:
                b_name = b.get("name")
                state = b.get("bgp_state") or b.get("status")
                if target_name and b_name.lower() != target_name.lower():
                    continue
                if str(state).lower() != "established":
                    findings.append(f"BGP session '{b_name}' to AS {b.get('neighbor_as')} is '{state}'. Local: {b.get('local_ip')}, Remote: {b.get('remote_ip')}")

            verdict = "HEALTHY" if not findings else "BGP_DOWN_DETECTED"
            return to_json_output({
                "symptom": symptom,
                "target": target_name or "ALL",
                "verdict": verdict,
                "findings": findings or ["All border BGP sessions are established."],
            })

        elif symptom == "node_unreachable":
            heartbeats = await client.get("/api/v2/dashboard/agent-heartbeats") or []
            for h in heartbeats:
                node = h.get("name")
                status = h.get("status")
                if target_name and str(node).lower() != target_name.lower():
                    continue
                if str(status).lower() in ("critical", "failed"):
                    findings.append(f"Switch daemon heartbeat for '{node}' is critical. Last seen: {h.get('lastHeartbeat')}")

            verdict = "HEALTHY" if not findings else "UNREACHABLE_NODES_FOUND"
            return to_json_output({
                "symptom": symptom,
                "target": target_name or "ALL",
                "verdict": verdict,
                "findings": findings or ["No unreachable nodes identified."],
            })

        elif symptom == "fabric_health_check":
            # Holistic multi-point verification
            hw = await client.get("/api/v2/hw") or []
            vnets = await client.get("/api/v2/vnet") or []
            ebgp = await client.get("/api/v2/ebgp") or []
            heartbeats = await client.get("/api/v2/dashboard/agent-heartbeats") or []

            down_ebgp = [b.get("name") for b in ebgp if str(b.get("bgp_state", "")).lower() != "established"]
            crit_hb = [h.get("name") for h in heartbeats if str(h.get("status")).lower() in ("critical", "failed")]
            
            return to_json_output({
                "verdict": "ATTENTION_REQUIRED" if (down_ebgp or crit_hb) else "OPTIMAL",
                "total_switches": len([d for d in hw if d.get("type") == "switch"]),
                "active_vnets": len(vnets),
                "unestablished_bgp": down_ebgp,
                "offline_nodes_count": len(crit_hb),
                "offline_nodes_sample": crit_hb[:5],
            })

        return "Unknown symptom"

    # -------------------------------------------------------------------------
    # 4. Looking Glass Diagnostic Execution
    # -------------------------------------------------------------------------
    @mcp.tool()
    async def looking_glass(
        query: Annotated[
            Literal[
                "peers_list",
                "bgp_summary",
                "bgp_route",
                "route",
                "ping",
                "traceroute",
                "inspect_peer",
            ],
            Field(description="Looking glass diagnostic query: 'peers_list', 'bgp_summary', 'bgp_route', 'route', 'ping', 'traceroute'."),
        ] = "peers_list",
        switch_name: Annotated[
            str | None,
            Field(description="Target switch hostname or management IP (e.g. 'leaf-pod00-su0-r0')."),
        ] = None,
        target_ip: Annotated[
            str | None,
            Field(description="Target IP address or destination host (for ping, traceroute, or route)."),
        ] = None,
        prefix: Annotated[
            str | None,
            Field(description="Target routing prefix (for bgp_route or route)."),
        ] = None,
        source_ip: Annotated[
            str | None,
            Field(description="Optional source IP address."),
        ] = None,
        ip_family: Annotated[
            Literal["ipv4", "ipv6"],
            Field(description="IP family: 'ipv4' or 'ipv6'."),
        ] = "ipv4",
        count: Annotated[
            int,
            Field(description="Number of ping probe packets."),
        ] = 3,
        limit: Annotated[
            int,
            Field(description="Max records to return for list queries."),
        ] = 50,
    ) -> str:
        """Run Looking Glass routing and network diagnostics across Netris fabric switches."""
        if query == "peers_list":
            peers = await client.get("/api/lookingglass/peersList") or []
            return to_json_output(format_digest(peers, ["id", "name", "ip", "asNumber", "status", "uptime"], limit=limit))

        elif query == "inspect_peer":
            peers = await client.get("/api/lookingglass/peersList") or []
            target = target_ip or switch_name or prefix
            matches = [
                p for p in peers
                if not target or target.lower() in str(p.get("name", "")).lower() or target in str(p.get("ip", ""))
            ]
            return to_json_output({
                "query": "inspect_peer",
                "target": target or "ALL",
                "total_matches": len(matches),
                "items": matches[:limit],
            })

        switch_target = switch_name or "leaf-pod00-su0-r0"

        if query == "bgp_summary":
            cmd = 'sudo vtysh -c "show bgp summary"'
            res = await _execute_switch_diag(switch_target, cmd, client)
            return to_json_output({
                "query": "bgp_summary",
                "target_switch": switch_target,
                "command": cmd,
                "status": "success" if res.get("exit_code") == 0 else "error",
                "output": res.get("output", ""),
            })

        elif query == "bgp_route":
            dst = prefix or target_ip or "0.0.0.0/0"
            cmd = f'sudo vtysh -c "show bgp {ip_family} unicast {dst}"'
            res = await _execute_switch_diag(switch_target, cmd, client)
            return to_json_output({
                "query": "bgp_route",
                "target_switch": switch_target,
                "prefix": dst,
                "ip_family": ip_family,
                "command": cmd,
                "status": "success" if res.get("exit_code") == 0 else "error",
                "output": res.get("output", ""),
            })

        elif query == "route":
            dst = prefix or target_ip or ""
            cmd = f"ip route show {dst}".strip()
            res = await _execute_switch_diag(switch_target, cmd, client)
            return to_json_output({
                "query": "route",
                "target_switch": switch_target,
                "prefix": dst or "default",
                "command": cmd,
                "status": "success" if res.get("exit_code") == 0 else "error",
                "output": res.get("output", ""),
            })

        elif query == "ping":
            dst = target_ip or prefix
            if not dst:
                return to_json_output({"query": "ping", "error": "target_ip is required for ping"})
            src_flag = f"-I {source_ip} " if source_ip else ""
            cmd = f"ping -c {count} {src_flag}{dst}".strip()
            res = await _execute_switch_diag(switch_target, cmd, client)
            return to_json_output({
                "query": "ping",
                "target_switch": switch_target,
                "destination": dst,
                "source_ip": source_ip,
                "count": count,
                "command": cmd,
                "status": "success" if res.get("exit_code") == 0 else "error",
                "output": res.get("output", ""),
            })

        elif query == "traceroute":
            dst = target_ip or prefix
            if not dst:
                return to_json_output({"query": "traceroute", "error": "target_ip is required for traceroute"})
            cmd = f"traceroute -m 15 {dst}"
            res = await _execute_switch_diag(switch_target, cmd, client)
            return to_json_output({
                "query": "traceroute",
                "target_switch": switch_target,
                "destination": dst,
                "command": cmd,
                "status": "success" if res.get("exit_code") == 0 else "error",
                "output": res.get("output", ""),
            })

        return "Unknown query"
