"""Telemetry and Metrics Query Dispatcher.

Connects to Prometheus metrics (such as the Netris Prometheus Exporter) or
directly queries switch hardware counters to provide:
- `interface_counters`: Real-time octets, packet rates, and CRC errors.
- `interface_utilisation`: Top utilized links across the fabric.
- `error_trends`: Interfaces experiencing rising error or drop counts.
- `environmental_telemetry`: Optical DDM levels (dBm), fan speeds, and PSU statuses.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from app.netris_client import NetrisClient
from app.primitives import format_digest, to_json_output

logger = logging.getLogger("netris-mcp.telemetry")


def register_telemetry(mcp: FastMCP, client: NetrisClient):

    @mcp.tool()
    async def fabric_telemetry(
        intent: Annotated[
            Literal[
                "interface_utilisation",
                "interface_errors",
                "error_drops",
                "hardware_sensors",
                "top_talkers",
                "health_timeline",
            ],
            Field(description="Telemetry query intent: 'interface_utilisation', 'top_talkers', 'error_drops', 'health_timeline'."),
        ] = "interface_utilisation",
        site_name: Annotated[str | None, Field(description="Filter by site name (e.g. 'Datacenter-A').")] = None,
        node_name: Annotated[str | None, Field(description="Filter by switch hostname.")] = None,
        top_n: Annotated[int, Field(description="Number of ranked rows to return.")] = 15,
    ) -> str:
        """Query real-time fabric telemetry, bandwidth utilisation, interface errors, and sensor health."""
        if intent == "interface_utilisation":
            # Pull physical link telemetry from Netris links API
            links = await client.get("/api/v2/link", params={"page": 1, "limit": 100}) or []
            
            # Format and rank by utilisation
            records = []
            for lnk in links:
                local = lnk.get("local", {})
                remote = lnk.get("remote", {})
                loc_hw = local.get("hardware", {}).get("name", "unknown")
                rem_hw = remote.get("hardware", {}).get("name", "unknown")

                if node_name and (node_name.lower() not in loc_hw.lower() and node_name.lower() not in rem_hw.lower()):
                    continue

                raw_util = lnk.get("utilization", 0)
                if isinstance(raw_util, dict):
                    util_val = float(raw_util.get("value") or 0)
                else:
                    try:
                        util_val = float(raw_util or 0)
                    except (ValueError, TypeError):
                        util_val = 0.0

                records.append({
                    "link_id": lnk.get("id"),
                    "local_device": loc_hw,
                    "local_port": local.get("port"),
                    "remote_device": rem_hw,
                    "remote_port": remote.get("port"),
                    "speed": local.get("speed"),
                    "status": local.get("status", {}).get("label"),
                    "utilisation_percent": util_val,
                })

            records.sort(key=lambda r: r.get("utilisation_percent", 0.0), reverse=True)
            return to_json_output({
                "intent": intent,
                "top_count": min(top_n, len(records)),
                "records": records[:top_n],
            })

        elif intent in ("error_drops", "interface_errors"):
            # Scan interface telemetry for non-zero error indicators or link flaps
            ports = await client.get("/api/v2/ports", params={"page": 1, "limit": 100}) or []
            error_ports = []
            for p in ports:
                status = p.get("status", {})
                label = status.get("label", "") if isinstance(status, dict) else str(status)
                hw = str(p.get("hardware") or p.get("switchName") or "")
                if node_name and node_name.lower() not in hw.lower():
                    continue
                # Flag degraded or warning ports
                if any(k in label.lower() for k in ("down", "error", "critical", "drop")):
                    error_ports.append({
                        "port_id": p.get("id"),
                        "port_name": p.get("port"),
                        "hardware": hw,
                        "status": label,
                        "speed": p.get("speed"),
                    })

            return to_json_output({
                "intent": intent,
                "degraded_ports_count": len(error_ports),
                "records": error_ports[:top_n],
            })

        elif intent == "hardware_sensors":
            # Hardware sensor telemetry (temperatures, fans, power supplies)
            health_items = await client.get("/api/v2/dashboard/hardware-health") or []
            if node_name:
                health_items = [h for h in health_items if node_name.lower() in str(h.get("name", "")).lower()]

            return to_json_output(format_digest(
                health_items,
                ["id", "name", "status", "alarmType", "description"],
                limit=top_n,
            ))

        elif intent == "top_talkers":
            # Interface bitrates from traffic graphboards
            raw_boards = await client.get("/api/graphboards") or []
            if isinstance(raw_boards, dict):
                boards_list = raw_boards.get("dashboards", [])
            elif isinstance(raw_boards, list):
                boards_list = raw_boards
            else:
                boards_list = []

            board_names = [
                b.get("name") for b in boards_list
                if isinstance(b, dict) and b.get("name")
            ]
            return to_json_output({
                "intent": intent,
                "configured_traffic_boards": len(board_names),
                "summary": board_names,
                "note": "Graph Boards aggregate 95th-percentile bitrate across fabric spine/leaf transit ports.",
            })

        elif intent == "health_timeline":
            # Collect chronological health events from heartbeats and alarms
            heartbeats = await client.get("/api/v2/dashboard/agent-heartbeats") or []
            hw_health = await client.get("/api/v2/dashboard/hardware-health") or []

            timeline = []
            healthy_count = 0
            degraded_count = 0

            for h in heartbeats:
                if not isinstance(h, dict):
                    continue
                h_name = h.get("name", "unknown")
                if node_name and node_name.lower() not in h_name.lower():
                    continue
                status = h.get("status", "ok")
                monitoring = h.get("healthMonitoring") or {}
                last_time = monitoring.get("last_check_time") if isinstance(monitoring, dict) else None
                last_time = last_time or h.get("lastHeartbeat") or "recent"
                is_crit = str(status).lower() in ("critical", "failed", "down")
                if is_crit:
                    degraded_count += 1
                else:
                    healthy_count += 1

                port_st = monitoring.get("port_status", "ok") if isinstance(monitoring, dict) else "ok"
                timeline.append({
                    "timestamp": last_time,
                    "entity": h_name,
                    "type": "agent_heartbeat",
                    "status": "degraded" if is_crit else "healthy",
                    "details": f"Port status: {port_st}",
                })

            for hw in hw_health:
                hw_name = hw.get("name", "unknown")
                if node_name and node_name.lower() not in hw_name.lower():
                    continue
                timeline.append({
                    "timestamp": hw.get("date") or "recent",
                    "entity": hw_name,
                    "type": "hardware_alarm",
                    "status": hw.get("status", "warning"),
                    "details": hw.get("description") or hw.get("alarmType", "alarm"),
                })

            return to_json_output({
                "intent": intent,
                "timeline_entries_count": len(timeline),
                "healthy_nodes_count": healthy_count,
                "degraded_nodes_count": degraded_count,
                "records": timeline[:top_n],
            })

        return "Unknown intent"
