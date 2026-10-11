"""Shared primitives for Netris MCP server.

Includes:
- Context dataclass passed to tool executions.
- Output formatting helpers (digest, summary, table formatting).
- Token-safety caps and pagination bounds.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.config import NetrisConfig
from app.netris_client import NetrisClient


@dataclass
class NetrisContext:
    config: NetrisConfig
    client: NetrisClient


def format_digest(
    items: list[dict[str, Any]],
    fields: list[str],
    total_count: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Produce a token-efficient digest of resources."""
    total = total_count if total_count is not None else len(items)
    displayed = items[:limit]
    
    compact_rows = []
    for item in displayed:
        row = {}
        for f in fields:
            val = item.get(f)
            if isinstance(val, dict):
                # Pick name or id if available
                val = val.get("name") or val.get("id") or str(val)
            row[f] = val
        compact_rows.append(row)

    return {
        "total_records": total,
        "displayed_records": len(compact_rows),
        "truncated": total > len(compact_rows),
        "items": compact_rows,
    }


def to_json_output(data: Any) -> str:
    """Format data as pretty JSON string."""
    return json.dumps(data, indent=2)
