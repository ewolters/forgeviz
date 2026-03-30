"""Generic chart builders — bar, line, area, pie, donut, bullet, stacked area, risk heatmap.

For when you need a plain chart without domain-specific assumptions.
"""

from __future__ import annotations


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


def donut(
    labels: list[str],
    values: list[float],
    title: str = "",
    center_label: str = "",
    center_value: str = "",
) -> ChartSpec:
    """Donut (ring) chart — pie with center label for KPI display.

    Args:
        labels: Segment labels.
        values: Segment values.
        title: Chart title.
        center_label: Small text below center value (e.g. "Compliance").
        center_value: Large text in center (e.g. "72%").
    """
    total = sum(values)
    pcts = [v / total * 100 if total > 0 else 0 for v in values]

    spec = ChartSpec(title=title, chart_type="donut", height=300)
    spec.traces.append({
        "type": "donut",
        "labels": labels,
        "values": values,
        "percentages": pcts,
        "hole": 0.55,
    })
    if center_value:
        spec.annotations.append({
            "x": 0.5, "y": 0.5, "text": center_value,
            "font_size": 28, "color": "#e8efe8",
        })
    if center_label:
        spec.annotations.append({
            "x": 0.5, "y": 0.35, "text": center_label,
            "font_size": 12, "color": "#7a8f7a",
        })

    return spec


def stacked_area(
    x: list,
    series: dict[str, list[float]],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> ChartSpec:
    """Stacked area chart — time-axis stacked areas for volume trends.

    Each series is stacked on top of the previous one.

    Args:
        x: Shared x-axis values (typically dates or time periods).
        series: Dict of {series_name: y_values}. Order determines stacking.
        title: Chart title.
        x_label: X-axis label.
        y_label: Y-axis label.
    """
    spec = ChartSpec(
        title=title, chart_type="stacked_area",
        x_axis={"label": x_label}, y_axis={"label": y_label},
    )

    # Compute cumulative stacks
    names = list(series.keys())
    cumulative = [0.0] * len(x)

    for i, name in enumerate(names):
        y_vals = series[name]
        new_cum = [c + v for c, v in zip(cumulative, y_vals)]

        # Area trace (filled from previous cumulative to new)
        spec.add_trace(
            x, new_cum, name=name, trace_type="area",
            color=get_color(i), fill="tonexty" if i > 0 else "tozeroy",
            opacity=0.7,
        )
        cumulative = new_cum

    return spec


def bullet(
    actual: float,
    target: float,
    ranges: list[tuple[float, str]] | None = None,
    title: str = "",
    subtitle: str = "",
    min_val: float = 0,
    max_val: float | None = None,
) -> ChartSpec:
    """Bullet chart — KPI actual vs target with qualitative ranges.

    Args:
        actual: Current value.
        target: Target/goal value.
        ranges: Qualitative ranges as [(upper_bound, color), ...].
            Default: poor (red), satisfactory (amber), good (green).
        title: Metric name (e.g. "Readiness Score").
        subtitle: Unit or context (e.g. "%").
        min_val: Minimum scale value.
        max_val: Maximum scale value (default: max of target, actual, ranges).
    """
    if ranges is None:
        # Default traffic-light ranges relative to target
        ranges = [
            (target * 0.6, "#3b1a1a"),   # poor — dark red bg
            (target * 0.85, "#3b2a1a"),   # satisfactory — dark amber bg
            (target * 1.2, "#1a2a1a"),    # good — dark green bg
        ]

    if max_val is None:
        range_max = max(r[0] for r in ranges) if ranges else 0
        max_val = max(actual, target, range_max) * 1.1

    spec = ChartSpec(title=title, subtitle=subtitle, chart_type="bullet", height=80, width=400)

    # Qualitative ranges as zones
    prev = min_val
    for bound, color in ranges:
        spec.add_zone(prev, bound, color=color)
        prev = bound

    # Actual value bar
    spec.traces.append({
        "type": "bullet_bar",
        "value": actual,
        "min": min_val,
        "max": max_val,
        "color": get_color(0),
    })

    # Target marker
    spec.reference_lines.append({
        "value": target,
        "axis": "x",
        "color": "#e8efe8",
        "width": 2.5,
        "label": f"Target: {target}",
    })

    spec.annotations.append({
        "x": 0.02, "y": 0.5, "text": f"{actual}",
        "font_size": 16, "color": "#e8efe8",
    })

    return spec


def risk_heatmap(
    row_labels: list[str],
    col_labels: list[str],
    values: list[list[float]],
    title: str = "Risk Matrix",
    low_color: str = "#1a2a1a",
    mid_color: str = "#3b2a1a",
    high_color: str = "#3b1a1a",
    value_labels: list[list[str]] | None = None,
) -> ChartSpec:
    """Risk heatmap — severity × occurrence grid with color-coded cells.

    Designed for FMIS risk matrices, FMEA prioritization, and similar.

    Args:
        row_labels: Row labels (e.g. severity levels).
        col_labels: Column labels (e.g. occurrence levels).
        values: 2D matrix of risk scores (rows × cols).
        title: Chart title.
        low_color: Color for lowest risk values.
        mid_color: Color for medium risk values.
        high_color: Color for highest risk values.
        value_labels: Optional 2D matrix of display labels per cell.
    """
    spec = ChartSpec(
        title=title, chart_type="risk_heatmap",
        x_axis={"label": ""}, y_axis={"label": ""},
    )

    spec.traces.append({
        "type": "risk_heatmap",
        "x": col_labels,
        "y": row_labels,
        "z": values,
        "value_labels": value_labels,
        "colorscale": [low_color, mid_color, high_color],
    })

    return spec
