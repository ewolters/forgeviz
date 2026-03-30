"""Statistical visualization — heatmap, matrix, interval, dotplot, bubble, parallel coords, mosaic."""

from __future__ import annotations

import math

from ..core.colors import get_color, STATUS_DIM
from ..core.spec import ChartSpec


def heatmap(
    x_labels: list[str],
    y_labels: list[str],
    z_matrix: list[list[float]],
    title: str = "Heatmap",
    colorscale: str = "viridis",
) -> ChartSpec:
    """Generic heatmap — numeric values in a labeled grid."""
    spec = ChartSpec(title=title, chart_type="heatmap", x_axis={"label": ""}, y_axis={"label": ""})
    spec.traces.append({
        "type": "heatmap",
        "x": x_labels,
        "y": y_labels,
        "z": z_matrix,
        "colorscale": colorscale,
    })
    return spec


def scatter_matrix(
    data: dict[str, list[float]],
    title: str = "Scatter Matrix",
) -> list[ChartSpec]:
    """Scatter matrix — pairwise scatter plots for all variable combinations.

    Returns a list of ChartSpecs, one per pair. Use ForgeViz.compose() to render as grid.
    """
    from .scatter import scatter

    names = list(data.keys())
    specs = []
    for i, name_y in enumerate(names):
        for j, name_x in enumerate(names):
            if i == j:
                from .distribution import histogram
                specs.append(histogram(data[name_x], bins=10, title=name_x))
            else:
                specs.append(scatter(data[name_x], data[name_y], title="", x_label=name_x, y_label=name_y))
    return specs


def individual_value_plot(
    groups: dict[str, list[float]],
    title: str = "Individual Value Plot",
) -> ChartSpec:
    """Individual data points per group with mean line."""
    spec = ChartSpec(title=title, chart_type="individual_value", x_axis={"label": ""}, y_axis={"label": "Value"})

    names = list(groups.keys())
    for i, (name, values) in enumerate(groups.items()):
        x = [name] * len(values)
        spec.add_trace(x, values, name=name, trace_type="scatter", color=get_color(i), marker_size=5, opacity=0.6)
        mean = sum(values) / len(values) if values else 0
        spec.add_trace([name], [mean], name="", trace_type="scatter", color=get_color(i), marker_size=10)

    return spec


def interval_plot(
    groups: dict[str, list[float]],
    confidence: float = 0.95,
    title: str = "Interval Plot",
) -> ChartSpec:
    """Confidence interval bars per group."""
    spec = ChartSpec(title=title, chart_type="interval_plot", x_axis={"label": ""}, y_axis={"label": "Value"})

    for i, (name, values) in enumerate(groups.items()):
        if not values:
            continue
        n = len(values)
        mean = sum(values) / n
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / max(n - 1, 1))
        # CI using t-approximation
        z = 1.96 if confidence == 0.95 else 2.576 if confidence == 0.99 else 1.645
        margin = z * std / math.sqrt(n) if n > 0 else 0

        spec.add_trace([name], [mean], name=name, trace_type="scatter", color=get_color(i), marker_size=8)
        # Error bars as reference lines
        spec.annotations.append({"x": i, "y": mean + margin, "text": "┬", "color": get_color(i), "font_size": 10})
        spec.annotations.append({"x": i, "y": mean - margin, "text": "┴", "color": get_color(i), "font_size": 10})

    return spec


def dotplot(
    categories: list[str],
    values: list[float],
    title: str = "Dot Plot",
) -> ChartSpec:
    """Cleveland dot plot — horizontal dots with connecting line to axis."""
    spec = ChartSpec(title=title, chart_type="dotplot", x_axis={"label": "Value"}, y_axis={"label": ""})
    spec.add_trace(values, categories, trace_type="scatter", color=get_color(0), marker_size=8)
    return spec


def bubble(
    x: list[float],
    y: list[float],
    sizes: list[float],
    labels: list[str] | None = None,
    title: str = "Bubble Chart",
    x_label: str = "X",
    y_label: str = "Y",
) -> ChartSpec:
    """Bubble chart — scatter with size dimension."""
    spec = ChartSpec(title=title, chart_type="bubble", x_axis={"label": x_label}, y_axis={"label": y_label})

    max_size = max(sizes) if sizes else 1
    for i in range(min(len(x), len(y), len(sizes))):
        normalized_size = (sizes[i] / max_size) * 20 + 3
        label = labels[i] if labels and i < len(labels) else ""
        spec.add_trace([x[i]], [y[i]], name=label, trace_type="scatter", color=get_color(i % 10), marker_size=normalized_size)

    return spec


def parallel_coordinates(
    data: dict[str, list[float]],
    title: str = "Parallel Coordinates",
    highlight_idx: list[int] | None = None,
) -> ChartSpec:
    """Parallel coordinates — each variable is a vertical axis, each observation is a polyline.

    Stored as a special trace for the JS renderer.
    """
    spec = ChartSpec(title=title, chart_type="parallel_coordinates")
    spec.traces.append({
        "type": "parallel",
        "dimensions": list(data.keys()),
        "data": data,
        "highlight": highlight_idx or [],
    })
    return spec


def mosaic(
    contingency: dict[str, dict[str, int]],
    title: str = "Mosaic Plot",
) -> ChartSpec:
    """Mosaic plot for categorical data — area proportional to frequency.

    contingency: {row_category: {col_category: count}}
    """
    spec = ChartSpec(title=title, chart_type="mosaic")

    total = sum(sum(cols.values()) for cols in contingency.values())
    if total == 0:
        return spec

    row_names = list(contingency.keys())
    col_names = list(set(c for row in contingency.values() for c in row.keys()))

    # Build stacked bars representing proportions
    for i, col in enumerate(col_names):
        values = [contingency.get(row, {}).get(col, 0) / total * 100 for row in row_names]
        spec.add_trace(row_names, values, name=col, trace_type="bar", color=get_color(i))

    return spec
