"""Data export — extract chart data as CSV/JSON for API consumers."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from .spec import ChartSpec, Trace


def to_csv(spec: ChartSpec) -> str:
    """Export all trace data from a ChartSpec as CSV.

    Columns: trace_name, x, y (one row per data point).
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["trace", "x", "y"])

    for trace in spec.traces:
        if isinstance(trace, dict):
            name = trace.get("name", "")
            x_vals = trace.get("x", [])
            y_vals = trace.get("y", [])
            for i in range(min(len(x_vals), len(y_vals))):
                writer.writerow([name, x_vals[i], y_vals[i]])
        elif isinstance(trace, Trace):
            for i in range(min(len(trace.x), len(trace.y))):
                writer.writerow([trace.name, trace.x[i], trace.y[i]])

    return output.getvalue()


def to_data_json(spec: ChartSpec, indent: int = 2) -> str:
    """Export all trace data from a ChartSpec as JSON.

    Returns: {"traces": [{"name": str, "x": [...], "y": [...]}, ...],
              "reference_lines": [...], "statistics": {...}}
    """
    traces = []
    for trace in spec.traces:
        if isinstance(trace, dict):
            traces.append({
                "name": trace.get("name", ""),
                "type": trace.get("type", ""),
                **{k: v for k, v in trace.items() if k not in ("name", "type")},
            })
        elif isinstance(trace, Trace):
            traces.append({
                "name": trace.name,
                "type": trace.trace_type,
                "x": trace.x,
                "y": trace.y,
            })

    ref_lines = []
    for r in spec.reference_lines:
        ref_lines.append({
            "label": r.label,
            "value": r.value,
            "axis": r.axis,
        })

    return json.dumps({
        "title": spec.title,
        "traces": traces,
        "reference_lines": ref_lines,
    }, indent=indent, default=str)


def to_table(spec: ChartSpec) -> list[dict[str, Any]]:
    """Export trace data as a list of row dicts (for DataFrame conversion).

    Returns: [{"trace": str, "x": val, "y": val}, ...]
    """
    rows = []
    for trace in spec.traces:
        if isinstance(trace, dict):
            name = trace.get("name", "")
            x_vals = trace.get("x", [])
            y_vals = trace.get("y", [])
            for i in range(min(len(x_vals), len(y_vals))):
                rows.append({"trace": name, "x": x_vals[i], "y": y_vals[i]})
        elif isinstance(trace, Trace):
            for i in range(min(len(trace.x), len(trace.y))):
                rows.append({"trace": trace.name, "x": trace.x[i], "y": trace.y[i]})
    return rows
