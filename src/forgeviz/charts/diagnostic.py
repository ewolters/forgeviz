"""Diagnostic plots — residuals, QQ, fitted vs actual, Cook's distance."""

from __future__ import annotations

import math

from ..core.colors import STATUS_RED, STATUS_DIM, get_color
from ..core.spec import ChartSpec


def residual_plot(
    fitted: list[float],
    residuals: list[float],
    title: str = "Residuals vs Fitted",
) -> ChartSpec:
    """Residual vs fitted values — check for patterns, heteroscedasticity."""
    spec = ChartSpec(title=title, chart_type="residual", x_axis={"label": "Fitted Value"}, y_axis={"label": "Residual"})
    spec.add_trace(fitted, residuals, trace_type="scatter", color=get_color(0), marker_size=5)
    spec.add_reference_line(0, color=STATUS_DIM, dash="solid")
    return spec


def residual_histogram(
    residuals: list[float],
    title: str = "Residual Distribution",
) -> ChartSpec:
    """Histogram of residuals — check normality."""
    from .distribution import histogram
    return histogram(residuals, bins=15, title=title, show_normal=True)


def qq_plot(
    residuals: list[float],
    title: str = "Q-Q Plot",
) -> ChartSpec:
    """Quantile-quantile plot — residuals vs theoretical normal."""
    from .effects import normal_probability_plot
    spec = normal_probability_plot(residuals, title=title)
    spec.chart_type = "qq_plot"
    return spec


def residual_vs_order(
    residuals: list[float],
    title: str = "Residuals vs Run Order",
) -> ChartSpec:
    """Residuals in run order — check for time-dependent patterns."""
    spec = ChartSpec(title=title, chart_type="residual_order", x_axis={"label": "Run Order"}, y_axis={"label": "Residual"})
    spec.add_trace(list(range(1, len(residuals) + 1)), residuals, trace_type="line", color=get_color(0), width=1, marker_size=4)
    spec.add_reference_line(0, color=STATUS_DIM, dash="solid")
    return spec


def cooks_distance(
    distances: list[float],
    threshold: float | None = None,
    title: str = "Cook's Distance",
) -> ChartSpec:
    """Cook's distance bar chart — identify influential observations."""
    n = len(distances)
    if threshold is None:
        threshold = 4 / n if n > 0 else 1

    spec = ChartSpec(title=title, chart_type="cooks_distance", x_axis={"label": "Observation"}, y_axis={"label": "Cook's Distance"})

    x = list(range(1, n + 1))
    spec.add_trace(x, distances, trace_type="bar", color=get_color(0), opacity=0.7)
    spec.add_reference_line(threshold, color=STATUS_RED, dash="dashed", label=f"Threshold ({threshold:.3f})")

    # Mark influential points
    influential = [i for i, d in enumerate(distances) if d > threshold]
    if influential:
        spec.add_marker(influential, color=STATUS_RED, size=8, label="Influential")

    return spec


def four_in_one(
    fitted: list[float],
    residuals: list[float],
) -> list[ChartSpec]:
    """Standard 4-in-1 residual diagnostic plot set.

    Returns 4 ChartSpecs for composition:
    1. Residuals vs fitted
    2. Normal Q-Q
    3. Residual histogram
    4. Residuals vs run order
    """
    return [
        residual_plot(fitted, residuals),
        qq_plot(residuals),
        residual_histogram(residuals),
        residual_vs_order(residuals),
    ]
