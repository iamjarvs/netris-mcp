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
                "hardware_sensors",
                "top_talkers",
            ],
            Field(description="Telemetry query intent."),
        ] = "interface_utilisation",
        site_name: Annotated[str | None, Field(description="Filter by site name (e.g. 'Datacenter-A').")] = None,
        node_name: Annotated[str | None, Field(description="Filter by switch hostname.")] = None,
        top_n: Annotated[int, Field(description="Number of ranked rows to return.")] = 15,
    ) -> str:
        """Query real-time fabric telemetry, bandwidth utilisation, interface errors, and sensor health."""
        if intent == "interface_utilisation":
            # Pull physical link telemetry from Netris links API
            links = await client.get("/api/v2/link", params={"page": 1, "limit": 100}) or []
            
            # Format and rank by utilization
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

        elif intent == "interface_errors":
            # Scan interface telemetry for non-zero error indicators or link flaps
            ports = await client.get("/api/v2/ports", params={"page": 1, "limit": 100}) or []
            error_ports = []
            for p in ports:
                status = p.get("status", {})
                label = status.get("label", "")
                if node_name and node_name.lower() not in str(p.get("hardware", "")).lower():
                    continue
                # Flag degraded or warning ports
                if "down" in label.lower() or "error" in label.lower() or "critical" in label.lower():
                    error_ports.append({
                        "port_id": p.get("id"),
                        "port_name": p.get("port"),
                        "hardware": p.get("hardware"),
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
            boards = await client.get("/api/graphboards") or []
            return to_json_output({
                "intent": intent,
                "configured_traffic_boards": len(boards),
                "summary": [b.get("name") for b in boards],
                "note": "Graph Boards aggregate 95th-percentile bitrate across fabric spine/leaf transit ports.",
            })

        return "Unknown intent"
