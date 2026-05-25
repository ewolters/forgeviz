"""Statistical visualization — heatmap, matrix, interval, dotplot, bubble, parallel coords, mosaic."""

from __future__ import annotations

import math

from ..core.colors import get_color
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


def multi_vari_chart(
    data: dict[str, dict[str, list[float]]],
    title: str = "Multi-Vari Chart",
) -> ChartSpec:
    """Multi-vari chart — variation within and between groups.

    data: {factor_level: {sub_group: [values]}}
    Shows individual values connected within subgroups, across factor levels.
    """
    spec = ChartSpec(title=title, chart_type="multi_vari", x_axis={"label": "Factor Level"}, y_axis={"label": "Value"})

    x_pos = 0
    x_labels = []
    for level_name, subgroups in data.items():
        for sub_name, values in subgroups.items():
            x_vals = [x_pos] * len(values)
            spec.add_trace(x_vals, values, name=sub_name, trace_type="scatter", color=get_color(hash(sub_name) % 10), marker_size=6)
            # Connect within subgroup
            if len(values) > 1:
                spec.add_trace(x_vals, values, name="", trace_type="line", color=get_color(hash(sub_name) % 10), width=0.5)
            x_labels.append(f"{level_name}/{sub_name}")
            x_pos += 1
        # Mean line across subgroups for this level
        all_vals = [v for sg in subgroups.values() for v in sg]
        if all_vals:
            mean = sum(all_vals) / len(all_vals)
            spec.add_reference_line(mean, color=get_color(0), dash="dotted", width=0.5)

    return spec


def correlation_heatmap(
    data: dict[str, list[float]],
    title: str = "Correlation Matrix",
    method: str = "pearson",
) -> ChartSpec:
    """Correlation heatmap — auto-compute correlation matrix from column data."""
    names = list(data.keys())
    n = len(names)
    matrix = []

    for i in range(n):
        row = []
        for j in range(n):
            xi = data[names[i]]
            xj = data[names[j]]
            length = min(len(xi), len(xj))
            if length < 2:
                row.append(0.0)
                continue
            x1, x2 = xi[:length], xj[:length]
            mean1 = sum(x1) / length
            mean2 = sum(x2) / length
            if method == "spearman":
                # Rank-based
                r1 = [sorted(x1).index(v) for v in x1]
                r2 = [sorted(x2).index(v) for v in x2]
                x1, x2 = [float(v) for v in r1], [float(v) for v in r2]
                mean1 = sum(x1) / length
                mean2 = sum(x2) / length
            cov = sum((x1[k] - mean1) * (x2[k] - mean2) for k in range(length)) / (length - 1)
            std1 = math.sqrt(sum((v - mean1) ** 2 for v in x1) / (length - 1))
            std2 = math.sqrt(sum((v - mean2) ** 2 for v in x2) / (length - 1))
            r = cov / (std1 * std2) if std1 > 0 and std2 > 0 else 0
            row.append(round(r, 3))
        matrix.append(row)

    return heatmap(names, names, matrix, title=title)


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
