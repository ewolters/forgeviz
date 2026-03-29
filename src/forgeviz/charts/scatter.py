"""Scatter, regression, and correlation charts."""

from __future__ import annotations

from ..core.colors import get_color
from ..core.spec import ChartSpec


def scatter(
    x: list[float],
    y: list[float],
    title: str = "Scatter Plot",
    x_label: str = "X",
    y_label: str = "Y",
    color: str = "",
    show_regression: bool = False,
    groups: dict[str, list[int]] | None = None,
) -> ChartSpec:
    """Scatter plot with optional regression line and grouping."""
    spec = ChartSpec(title=title, chart_type="scatter", x_axis={"label": x_label}, y_axis={"label": y_label})

    if groups:
        for i, (name, indices) in enumerate(groups.items()):
            gx = [x[j] for j in indices if j < len(x)]
            gy = [y[j] for j in indices if j < len(y)]
            spec.add_trace(gx, gy, name=name, trace_type="scatter", color=get_color(i), marker_size=6)
    else:
        spec.add_trace(x, y, name="Data", trace_type="scatter", color=color or get_color(0), marker_size=6)

    if show_regression and len(x) >= 2:
        n = len(x)
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        ss_xy = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        ss_xx = sum((x[i] - x_mean) ** 2 for i in range(n))

        if ss_xx > 0:
            slope = ss_xy / ss_xx
            intercept = y_mean - slope * x_mean
            x_range = [min(x), max(x)]
            y_fit = [slope * xv + intercept for xv in x_range]
            spec.add_trace(x_range, y_fit, name=f"y = {slope:.3f}x + {intercept:.3f}", trace_type="line", color=get_color(1), width=2, dash="solid")

    return spec


def pareto(
    categories: list[str],
    values: list[float],
    title: str = "Pareto Chart",
    threshold: float = 0.80,
) -> ChartSpec:
    """Pareto chart — bars sorted descending + cumulative line."""
    paired = sorted(zip(categories, values), key=lambda x: x[1], reverse=True)
    sorted_cats = [p[0] for p in paired]
    sorted_vals = [p[1] for p in paired]

    total = sum(sorted_vals) if sorted_vals else 1
    cumulative = []
    cum = 0
    for v in sorted_vals:
        cum += v / total
        cumulative.append(cum)

    spec = ChartSpec(title=title, chart_type="pareto", x_axis={"label": ""}, y_axis={"label": "Count"})

    spec.add_trace(sorted_cats, sorted_vals, name="Count", trace_type="bar", color=get_color(0))
    spec.add_trace(sorted_cats, [c * 100 for c in cumulative], name="Cumulative %", trace_type="line", color=get_color(1), width=2)
    spec.add_reference_line(threshold * 100, color="#888", dash="dashed", label=f"{threshold:.0%}")

    return spec
