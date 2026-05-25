"""Tufte-native chart builders and the tufte_mode() transform.

Edward Tufte's principles: maximize data-ink ratio, eliminate chartjunk,
range-frame axes, direct labels, small multiples. Every function here
produces charts that would survive Tufte's review.
"""

from __future__ import annotations

import copy
import math
from typing import Any

from ..core.colors import get_color
from ..core.spec import Axis, ChartSpec


def _tufte_base(title: str = "", x_label: str = "", y_label: str = "",
                width: int = 600, height: int = 350) -> ChartSpec:
    """Pre-configured ChartSpec with Tufte defaults."""
    return ChartSpec(
        title=title,
        theme="tufte",
        show_legend=False,
        width=width,
        height=height,
        x_axis=Axis(label=x_label, grid=False),
        y_axis=Axis(label=y_label, grid=False),
    )


def range_frame(
    x: list[float],
    y: list[float],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "#333333",
    marker_size: float = 4.0,
) -> ChartSpec:
    """Scatter plot with range-frame axes — axes run exactly from data min to max."""
    spec = _tufte_base(title, x_label, y_label)
    spec.chart_type = "range_frame"
    spec.add_trace(x, y, trace_type="scatter", color=color, marker_size=marker_size)
    spec.x_axis.min_val = min(x)
    spec.x_axis.max_val = max(x)
    spec.y_axis.min_val = min(y)
    spec.y_axis.max_val = max(y)
    return spec


def quartile_plot(
    groups: dict[str, list[float]],
    title: str = "",
    y_label: str = "",
    color: str = "#333333",
    dot_size: float = 5.0,
) -> ChartSpec:
    """Tufte's box plot replacement — median dot, quartile dots, thin line. No box."""
    spec = _tufte_base(title, y_label=y_label)
    spec.chart_type = "quartile_plot"

    for i, (name, data) in enumerate(groups.items()):
        if len(data) < 3:
            continue
        sorted_d = sorted(data)
        n = len(sorted_d)
        q1 = sorted_d[n // 4]
        median = sorted_d[n // 2]
        q3 = sorted_d[(3 * n) // 4]

        spec.traces.append({
            "type": "quartile_plot",
            "name": name,
            "x_position": i,
            "median": median,
            "q1": q1,
            "q3": q3,
            "color": color,
            "dot_size": dot_size,
        })

    return spec


def dot_dash(
    x: list[float],
    y: list[float],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "#333333",
    rug_length: float = 6.0,
    marker_size: float = 4.0,
) -> ChartSpec:
    """Scatter with marginal rug marks replacing axes."""
    spec = _tufte_base(title, x_label, y_label)
    spec.chart_type = "dot_dash"
    spec.add_trace(x, y, trace_type="scatter", color=color, marker_size=marker_size)
    spec.traces.append({"type": "rug_x", "values": list(x), "color": color, "length": rug_length})
    spec.traces.append({"type": "rug_y", "values": list(y), "color": color, "length": rug_length})
    spec.x_axis.min_val = min(x)
    spec.x_axis.max_val = max(x)
    spec.y_axis.min_val = min(y)
    spec.y_axis.max_val = max(y)
    return spec


def tufte_bar(
    categories: list[str],
    values: list[float],
    title: str = "",
    color: str = "#333333",
    value_labels: bool = True,
) -> ChartSpec:
    """Bar chart with no grid, direct value labels, narrow bars with wide gaps."""
    spec = _tufte_base(title)
    spec.chart_type = "tufte_bar"
    labels = [f"{v:.1f}" for v in values] if value_labels else []
    spec.add_trace(categories, values, trace_type="bar", color=color,
                   opacity=1.0, labels=labels, label_position="top")
    return spec


def tufte_line(
    x: list,
    y: list[float],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "#333333",
    series_label: str = "",
    width: float = 1.0,
) -> ChartSpec:
    """Line chart with thin stroke, no fill, direct end-label instead of legend."""
    spec = _tufte_base(title, x_label, y_label)
    spec.chart_type = "tufte_line"
    spec.add_trace(x, y, trace_type="line", color=color, width=width)
    spec.x_axis.min_val = min(x) if x and isinstance(x[0], (int, float)) else None
    spec.x_axis.max_val = max(x) if x and isinstance(x[0], (int, float)) else None
    spec.y_axis.min_val = min(y)
    spec.y_axis.max_val = max(y)

    if series_label and x and y:
        spec.annotations.append({
            "x": x[-1], "y": y[-1],
            "text": f"  {series_label}",
            "color": color, "font_size": 10,
        })

    return spec


def rug(
    data: list[float],
    axis: str = "x",
    color: str = "#333333",
    length: float = 8.0,
    width: int = 400,
    height: int = 30,
) -> ChartSpec:
    """Pure rug plot — marginal tick marks. Compose with other charts."""
    spec = _tufte_base(width=width, height=height)
    spec.chart_type = "rug"
    spec.traces.append({
        "type": f"rug_{axis}",
        "values": list(data),
        "color": color,
        "length": length,
    })
    if axis == "x":
        spec.x_axis.min_val = min(data)
        spec.x_axis.max_val = max(data)
    return spec


def slope_chart(
    labels: list[str],
    before: list[float],
    after: list[float],
    before_label: str = "Before",
    after_label: str = "After",
    title: str = "",
    highlight_changes: bool = True,
) -> ChartSpec:
    """Slopegraph — two columns connected by lines showing change. No grid."""
    spec = _tufte_base(title, height=max(250, len(labels) * 30 + 80))
    spec.chart_type = "slope_chart"
    spec.traces.append({
        "type": "slope_chart",
        "labels": list(labels),
        "before": list(before),
        "after": list(after),
        "before_label": before_label,
        "after_label": after_label,
        "base_color": "#333333",
        "highlight_changes": highlight_changes,
        "increase_color": "#2980b9",
        "decrease_color": "#c0392b",
    })
    return spec


def tufte_mode(
    spec: ChartSpec,
    direct_labels: bool = True,
    tighten_axes: bool = True,
) -> ChartSpec:
    """Transform any ChartSpec to Tufte principles. Returns a new spec."""
    new = copy.deepcopy(spec)

    new.theme = "tufte"
    new.background_color = "#fffff8"
    new.show_legend = False

    # Disable grids
    if isinstance(new.x_axis, Axis):
        new.x_axis.grid = False
    if isinstance(new.y_axis, Axis):
        new.y_axis.grid = False

    # Strip area fills (chartjunk)
    for trace in new.traces:
        if hasattr(trace, "trace_type"):
            if trace.trace_type == "area":
                trace.fill = ""
                trace.opacity = 0.1
            # Strip decorative borders
            trace.border_width = 0
            trace.border_color = ""
            trace.border_colors = []

    # Tighten axes to data range (range-frame)
    if tighten_axes and new.chart_type not in ("bar", "grouped_bar", "stacked_bar", "tufte_bar"):
        all_y = []
        all_x = []
        for trace in new.traces:
            if hasattr(trace, "y"):
                all_y.extend(v for v in trace.y if isinstance(v, (int, float)))
            if hasattr(trace, "x"):
                all_x.extend(v for v in trace.x if isinstance(v, (int, float)))
            elif isinstance(trace, dict):
                all_y.extend(v for v in trace.get("y", []) if isinstance(v, (int, float)))
                all_x.extend(v for v in trace.get("x", []) if isinstance(v, (int, float)))
        if all_y and isinstance(new.y_axis, Axis):
            new.y_axis.min_val = min(all_y)
            new.y_axis.max_val = max(all_y)
        if all_x and isinstance(new.x_axis, Axis):
            new.x_axis.min_val = min(all_x)
            new.x_axis.max_val = max(all_x)

    # Quieten zones (reduce alpha)
    for zone in new.zones:
        c = zone.color
        if "rgba" in c:
            # Halve the alpha
            parts = c.replace("rgba(", "").replace(")", "").split(",")
            if len(parts) == 4:
                zone.color = f"rgba({parts[0]},{parts[1]},{parts[2]},{float(parts[3]) * 0.5})"
        elif c.startswith("#") and len(c) == 7:
            zone.color = f"rgba({int(c[1:3], 16)},{int(c[3:5], 16)},{int(c[5:7], 16)},0.05)"

    # Direct-label traces (replace legend with end-of-line annotations)
    if direct_labels:
        for trace in new.traces:
            if hasattr(trace, "name") and trace.name and hasattr(trace, "x") and trace.x:
                last_x = trace.x[-1]
                last_y = trace.y[-1] if trace.y else 0
                new.annotations.append({
                    "x": last_x, "y": last_y,
                    "text": f"  {trace.name}",
                    "color": trace.color or "#333333",
                    "font_size": 9,
                })

    return new
