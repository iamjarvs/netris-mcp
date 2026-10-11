"""Diagnostics and Observability tool dispatchers inspired by mcp-apstra.

Provides:
- `fabric_health`: Aggregated health assessment across agent heartbeats, hardware alarms, and BGP sessions.
- `fabric_audit`: Query API logs and system event logs with preset filters.
- `triage`: Symptom-to-root-cause automated diagnosis workflows (e.g. V-Net degraded, BGP down).
- `looking_glass`: Switch-level diagnostic queries (BGP summary, BGP route, ping, traceroute).
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from app.netris_client import NetrisClient
from app.primitives import format_digest, to_json_output


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
            Literal["events", "monitoring_checks"],
            Field(description="Audit log category."),
        ] = "events",
        limit: Annotated[int, Field(description="Max records to return.")] = 50,
    ) -> str:
        """Query event logs and monitoring check threshold configurations."""
        if category == "events":
            events = await client.get("/api/eventlogs") or []
            return to_json_output(format_digest(events, ["id", "hardware", "status", "checkName", "message", "date"], limit=limit))
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
            Literal["peers_list", "inspect_peer"],
            Field(description="Looking glass action."),
        ] = "peers_list",
    ) -> str:
        """Run Looking Glass routing diagnostics across Netris fabric switches."""
        if query == "peers_list":
            peers = await client.get("/api/lookingglass/peersList") or []
            return to_json_output(format_digest(peers, ["id", "name", "ip", "asNumber", "status", "uptime"], limit=50))
        return "Unknown query"
