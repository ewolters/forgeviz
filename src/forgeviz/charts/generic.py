"""Generic chart builders — bar, line, area, pie.

For when you need a plain chart without domain-specific assumptions.
"""

from __future__ import annotations

import math

from ..core.colors import get_color
from ..core.spec import ChartSpec


def bar(
    categories: list[str],
    values: list[float],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "",
    horizontal: bool = False,
) -> ChartSpec:
    """Simple bar chart."""
    spec = ChartSpec(title=title, chart_type="bar", x_axis={"label": x_label}, y_axis={"label": y_label})
    spec.add_trace(categories, values, trace_type="bar", color=color or get_color(0))
    return spec


def grouped_bar(
    categories: list[str],
    series: dict[str, list[float]],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> ChartSpec:
    """Grouped bar chart with multiple series."""
    spec = ChartSpec(title=title, chart_type="grouped_bar", x_axis={"label": x_label}, y_axis={"label": y_label})
    for i, (name, values) in enumerate(series.items()):
        spec.add_trace(categories, values, name=name, trace_type="bar", color=get_color(i))
    return spec


def stacked_bar(
    categories: list[str],
    series: dict[str, list[float]],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> ChartSpec:
    """Stacked bar chart."""
    spec = ChartSpec(title=title, chart_type="stacked_bar", x_axis={"label": x_label}, y_axis={"label": y_label})
    for i, (name, values) in enumerate(series.items()):
        spec.add_trace(categories, values, name=name, trace_type="bar", color=get_color(i))
    return spec


def line(
    x: list,
    y: list[float],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "",
    show_markers: bool = False,
) -> ChartSpec:
    """Simple line chart."""
    spec = ChartSpec(title=title, chart_type="line", x_axis={"label": x_label}, y_axis={"label": y_label})
    spec.add_trace(x, y, trace_type="line", color=color or get_color(0), width=2, marker_size=4 if show_markers else 0)
    return spec


def multi_line(
    x: list,
    series: dict[str, list[float]],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    show_markers: bool = False,
) -> ChartSpec:
    """Multiple line series on one chart."""
    spec = ChartSpec(title=title, chart_type="multi_line", x_axis={"label": x_label}, y_axis={"label": y_label})
    for i, (name, y_vals) in enumerate(series.items()):
        spec.add_trace(x, y_vals, name=name, trace_type="line", color=get_color(i), width=2, marker_size=4 if show_markers else 0)
    return spec


def area(
    x: list,
    y: list[float],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "",
) -> ChartSpec:
    """Area chart (filled line)."""
    spec = ChartSpec(title=title, chart_type="area", x_axis={"label": x_label}, y_axis={"label": y_label})
    spec.add_trace(x, y, trace_type="area", color=color or get_color(0), fill="tozeroy", opacity=0.3)
    spec.add_trace(x, y, trace_type="line", color=color or get_color(0), width=2)
    return spec


def pie(
    labels: list[str],
    values: list[float],
    title: str = "",
) -> ChartSpec:
    """Pie chart — stored as a special trace type.

    Note: SVG renderer draws this as a horizontal stacked bar.
    The JS renderer can draw a proper circle.
    """
    total = sum(values)
    pcts = [v / total * 100 if total > 0 else 0 for v in values]

    spec = ChartSpec(title=title, chart_type="pie", height=300)
    spec.traces.append({
        "type": "pie",
        "labels": labels,
        "values": values,
        "percentages": pcts,
    })
    return spec


def gauge(
    value: float,
    min_val: float = 0,
    max_val: float = 100,
    title: str = "",
    thresholds: list[tuple[float, str]] | None = None,
) -> ChartSpec:
    """Simple gauge/meter visualization.

    thresholds: [(value, color), ...] for zone coloring
    """
    spec = ChartSpec(title=title, chart_type="gauge", height=150, width=300)

    if thresholds:
        prev = min_val
        for threshold_val, color in thresholds:
            spec.add_zone(prev, threshold_val, color=color)
            prev = threshold_val

    spec.annotations = [
        {"x": 0.5, "y": 0.5, "text": f"{value:.1f}", "font_size": 24, "color": "#e8efe8"},
        {"x": 0.5, "y": 0.25, "text": f"/ {max_val:.0f}", "font_size": 12, "color": "#7a8f7a"},
    ]

    return spec


def sparkline(
    values: list[float],
    color: str = "",
    width: int = 120,
    height: int = 30,
) -> ChartSpec:
    """Tiny inline chart — no axes, no labels, just the line."""
    spec = ChartSpec(
        chart_type="sparkline",
        width=width, height=height,
        show_legend=False,
        x_axis={"label": "", "grid": False},
        y_axis={"label": "", "grid": False},
    )
    x = list(range(len(values)))
    spec.add_trace(x, values, trace_type="line", color=color or get_color(0), width=1.5)
    return spec
