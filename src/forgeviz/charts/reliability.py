"""Reliability visualization — Weibull, hazard, survival curves."""

from __future__ import annotations

import math

from ..core.colors import STATUS_AMBER, STATUS_DIM, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def weibull_probability_plot(
    failure_times: list[float],
    shape: float | None = None,
    scale: float | None = None,
    title: str = "Weibull Probability Plot",
) -> ChartSpec:
    """Weibull probability plot — linearized CDF for reliability data.

    If shape/scale provided, overlays the fitted line.
    """
    if not failure_times:
        return ChartSpec(title=title, chart_type="weibull_prob")

    sorted_times = sorted(failure_times)
    n = len(sorted_times)

    # Median rank (Bernard's approximation)
    ranks = [(i - 0.3) / (n + 0.4) for i in range(1, n + 1)]

    # Weibull linearization: ln(t) vs ln(-ln(1-F))
    x = [math.log(t) if t > 0 else -10 for t in sorted_times]
    y = [math.log(-math.log(1 - r)) if r < 1 else 5 for r in ranks]

    spec = ChartSpec(
        title=title, chart_type="weibull_prob",
        x_axis={"label": "ln(Time)"},
        y_axis={"label": "ln(-ln(1-F))"},
    )

    spec.add_trace(x, y, name="Data", trace_type="scatter", color=get_color(0), marker_size=6)

    # Fitted line
    if shape is not None and scale is not None and scale > 0:
        x_range = [min(x), max(x)]
        y_fit = [shape * (xv - math.log(scale)) for xv in x_range]
        spec.add_trace(x_range, y_fit, name=f"Fit (β={shape:.2f}, η={scale:.1f})", trace_type="line", color=get_color(1), width=2, dash="dashed")

    return spec


def hazard_function(
    shape: float,
    scale: float,
    max_time: float | None = None,
    title: str = "Hazard Function",
) -> ChartSpec:
    """Hazard rate over time — the bathtub curve.

    h(t) = (shape/scale) * (t/scale)^(shape-1)
    """
    if max_time is None:
        max_time = scale * 3

    n_pts = 100
    times = [max_time * i / n_pts for i in range(1, n_pts + 1)]
    hazard = []
    for t in times:
        if t <= 0 or scale <= 0:
            hazard.append(0)
        else:
            h = (shape / scale) * (t / scale) ** (shape - 1)
            hazard.append(h)

    spec = ChartSpec(
        title=title, chart_type="hazard",
        x_axis={"label": "Time"},
        y_axis={"label": "Hazard Rate h(t)"},
    )

    spec.add_trace(times, hazard, name="Hazard", trace_type="line", color=get_color(0), width=2)

    # Annotate shape interpretation
    if shape < 1:
        spec.annotations.append({"x": 0.7, "y": 0.9, "text": "Decreasing hazard (infant mortality)", "color": STATUS_AMBER, "font_size": 10})
    elif shape == 1:
        spec.annotations.append({"x": 0.7, "y": 0.9, "text": "Constant hazard (random failures)", "color": STATUS_DIM, "font_size": 10})
    else:
        spec.annotations.append({"x": 0.7, "y": 0.9, "text": "Increasing hazard (wear-out)", "color": STATUS_RED, "font_size": 10})

    return spec


def survival_curve(
    failure_times: list[float],
    censored: list[bool] | None = None,
    title: str = "Survival Curve",
) -> ChartSpec:
    """Kaplan-Meier survival curve.

    Shows probability of surviving beyond time t.
    """
    if not failure_times:
        return ChartSpec(title=title, chart_type="survival")

    n = len(failure_times)
    cens = censored or [False] * n

    # Sort by time
    events = sorted(zip(failure_times, cens), key=lambda x: x[0])

    times = [0]
    survival = [1.0]
    at_risk = n
    s = 1.0

    for t, is_censored in events:
        if not is_censored:
            s *= (at_risk - 1) / at_risk if at_risk > 0 else 0
            times.append(t)
            survival.append(s)
        at_risk -= 1

    # Extend to last time
    times.append(events[-1][0] * 1.1)
    survival.append(s)

    spec = ChartSpec(
        title=title, chart_type="survival",
        x_axis={"label": "Time"},
        y_axis={"label": "Survival Probability", "min_val": 0, "max_val": 1},
    )

    spec.add_trace(times, survival, name="Survival", trace_type="step", color=get_color(0), width=2)

    # 50% survival reference
    spec.add_reference_line(0.5, color=STATUS_DIM, dash="dotted", label="50% Survival")

    # Mark censored observations
    if any(cens):
        cens_times = [t for t, c in events if c]
        # Find survival at censored times
        cens_surv = []
        for ct in cens_times:
            for i in range(len(times) - 1):
                if times[i] <= ct <= times[i + 1]:
                    cens_surv.append(survival[i])
                    break
            else:
                cens_surv.append(survival[-1])
        spec.add_trace(cens_times, cens_surv, name="Censored", trace_type="scatter", color=get_color(0), marker_size=6)

    return spec


def reliability_block_diagram(
    components: list[dict],
    title: str = "System Reliability",
) -> ChartSpec:
    """System reliability bar chart — reliability per component.

    components: [{name, reliability, mtbf}]
    """
    spec = ChartSpec(title=title, chart_type="reliability_block", x_axis={"label": ""}, y_axis={"label": "Reliability", "min_val": 0, "max_val": 1})

    names = [c["name"] for c in components]
    reliabilities = [c.get("reliability", 0) for c in components]

    colors = []
    for r in reliabilities:
        if r >= 0.99:
            colors.append(STATUS_GREEN)
        elif r >= 0.95:
            colors.append(STATUS_AMBER)
        else:
            colors.append(STATUS_RED)

    spec.add_trace(names, reliabilities, trace_type="bar", color=STATUS_GREEN)
    spec.add_reference_line(0.99, color=STATUS_GREEN, dash="dashed", label="99%")
    spec.add_reference_line(0.95, color=STATUS_AMBER, dash="dotted", label="95%")

    return spec
