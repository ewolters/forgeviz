"""Gage R&R visualization — component variation charts."""

from __future__ import annotations

from ..core.colors import STATUS_AMBER, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def gage_rr_components(
    pct_contribution: dict[str, float],
    title: str = "Gage R&R Components",
) -> ChartSpec:
    """Stacked bar showing variance component breakdown.

    pct_contribution: {gage_rr, repeatability, reproducibility, part_to_part}
    """
    spec = ChartSpec(title=title, chart_type="gage_components", height=200)

    gage = pct_contribution.get("gage_rr", 0)
    repeat = pct_contribution.get("repeatability", 0)
    reprod = pct_contribution.get("reproducibility", 0)
    part = pct_contribution.get("part_to_part", 0)

    spec.add_trace(
        ["Repeatability", "Reproducibility", "Part-to-Part"],
        [repeat, reprod, part],
        name="Variance Components",
        trace_type="bar",
        color=get_color(0),
    )

    # Threshold line at 30% for gage R&R
    spec.add_reference_line(30, color=STATUS_RED, dash="dashed", label="30% threshold")
    spec.add_reference_line(10, color=STATUS_GREEN, dash="dashed", label="10% acceptable")

    spec.annotations = [
        {"x": 0.5, "y": 0.95, "text": f"Gage R&R: {gage:.1f}%", "font_size": 14, "color": STATUS_GREEN if gage < 10 else STATUS_AMBER if gage < 30 else STATUS_RED},
    ]

    return spec


def gage_rr_by_part(
    parts: list[str],
    measurements: dict[str, list[float]],
    title: str = "Measurements by Part",
) -> ChartSpec:
    """Show measurement spread per part — reveals part-to-part variation."""
    spec = ChartSpec(title=title, chart_type="gage_by_part", x_axis={"label": "Part"}, y_axis={"label": "Measurement"})

    for i, (part, values) in enumerate(measurements.items()):
        x = [part] * len(values)
        spec.add_trace(x, values, name=part, trace_type="scatter", color=get_color(i % 10), marker_size=5)

    return spec


def gage_rr_by_operator(
    operators: list[str],
    measurements: dict[str, list[float]],
    title: str = "Measurements by Operator",
) -> ChartSpec:
    """Show measurement spread per operator — reveals reproducibility."""
    spec = ChartSpec(title=title, chart_type="gage_by_operator", x_axis={"label": "Operator"}, y_axis={"label": "Measurement"})

    for i, (op, values) in enumerate(measurements.items()):
        x = [op] * len(values)
        spec.add_trace(x, values, name=op, trace_type="scatter", color=get_color(i % 10), marker_size=5)

    return spec


def gage_xbar_r(
    part_means: list[float],
    part_ranges: list[float],
    parts: list[str],
    mean_ucl: float,
    mean_cl: float,
    mean_lcl: float,
    range_ucl: float,
    range_cl: float,
    title: str = "Gage R&R X-bar/R",
) -> list[ChartSpec]:
    """X-bar and R charts for Gage study — returns two chart specs for composition."""
    from .control import control_chart

    xbar = control_chart(part_means, ucl=mean_ucl, cl=mean_cl, lcl=mean_lcl, title="X-bar Chart (by Part)")
    r_chart = control_chart(part_ranges, ucl=range_ucl, cl=range_cl, lcl=0, title="R Chart (by Operator)")

    return [xbar, r_chart]
