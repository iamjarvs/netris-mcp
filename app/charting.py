"""Visual Chart Rendering Engine.

Inspired by mcp-apstra's charting tool:
Renders line charts and bar charts of interface utilisation, error trends,
or traffic throughput using matplotlib, returning base64 PNG images directly to the client.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Annotated, Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastmcp import FastMCP
from pydantic import Field


def register_charting(mcp: FastMCP):

    @mcp.tool()
    async def generate_telemetry_chart(
        chart_type: Annotated[Literal["bar", "line"], Field(description="Chart visualization type.")] = "bar",
        title: Annotated[str, Field(description="Chart title (e.g. 'Top 5 Interface Utilisation %').")] = "Fabric Telemetry",
        labels: Annotated[list[str] | None, Field(description="List of X-axis categories or interface names.")] = None,
        values: Annotated[list[float] | None, Field(description="List of corresponding numerical values (e.g. utilization percentage or error count).")] = None,
        y_axis_label: Annotated[str, Field(description="Y-axis title.")] = "Utilisation (%)",
    ) -> str:
        """Render network telemetry data into a visual chart (PNG image encoded as markdown data URI)."""
        plot_labels = labels if labels is not None else ["swp1", "swp2", "swp3"]
        plot_values = values if values is not None else [45.2, 78.0, 12.5]

        if len(plot_labels) != len(plot_values):
            return "Error: Length of labels must match length of values."

        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=100)
        bar_color = "#1F7A8C"

        if chart_type == "bar":
            bars = ax.bar(plot_labels, plot_values, color=bar_color, width=0.55)
            ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=9)
        else:
            ax.plot(plot_labels, plot_values, marker="o", color=bar_color, linewidth=2)
            for i, val in enumerate(plot_values):
                ax.annotate(f"{val:.1f}", (plot_labels[i], val), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9)

        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
        ax.set_ylabel(y_axis_label, fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        plt.xticks(rotation=25, ha="right", fontsize=9)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)

        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"![{title}](data:image/png;base64,{img_b64})"
