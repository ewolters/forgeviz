"""Process capability visualization — histogram with spec overlay + normal curve."""

from __future__ import annotations

import math

from ..core.colors import STATUS_AMBER, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def capability_histogram(
    data: list[float],
    usl: float | None = None,
    lsl: float | None = None,
    target: float | None = None,
    cp: float | None = None,
    cpk: float | None = None,
    bins: int = 20,
    title: str = "Process Capability",
) -> ChartSpec:
    """Capability histogram with spec limits, normal fit, and Cpk annotation."""
    from .distribution import histogram

    spec = histogram(data, bins=bins, title=title, usl=usl, lsl=lsl, target=target, show_normal=True)
    spec.chart_type = "capability_histogram"

    # Add capability indices as annotations
    annotations = []
    if cp is not None:
        annotations.append({"x": 0.02, "y": 0.95, "text": f"Cp = {cp:.3f}", "color": STATUS_GREEN if cp >= 1.33 else STATUS_AMBER if cp >= 1.0 else STATUS_RED, "font_size": 11})
    if cpk is not None:
        annotations.append({"x": 0.02, "y": 0.88, "text": f"Cpk = {cpk:.3f}", "color": STATUS_GREEN if cpk >= 1.33 else STATUS_AMBER if cpk >= 1.0 else STATUS_RED, "font_size": 11})
    spec.annotations = annotations

    return spec


def capability_sixpack(
    data: list[float],
    usl: float | None = None,
    lsl: float | None = None,
    target: float | None = None,
    cp: float | None = None,
    cpk: float | None = None,
    pp: float | None = None,
    ppk: float | None = None,
) -> list[ChartSpec]:
    """Six-pack capability analysis — returns 6 chart specs for composition.

    1. I-chart (individuals)
    2. MR chart (moving range)
    3. Last 25 observations
    4. Capability histogram
    5. Normal probability plot
    6. Capability summary box
    """
    from .control import control_chart
    from .distribution import histogram
    from .effects import normal_probability_plot

    specs = []

    # 1. I-chart
    n = len(data)
    mean = sum(data) / n if n else 0
    mrs = [abs(data[i] - data[i - 1]) for i in range(1, n)]
    mr_bar = sum(mrs) / len(mrs) if mrs else 0
    sigma = mr_bar / 1.128 if mr_bar > 0 else 1

    specs.append(control_chart(
        data, ucl=mean + 3 * sigma, cl=mean, lcl=mean - 3 * sigma,
        title="I Chart", usl=usl, lsl=lsl,
    ))

    # 2. MR chart
    mr_ucl = mr_bar * 3.267
    specs.append(control_chart(
        mrs, ucl=mr_ucl, cl=mr_bar, lcl=0,
        title="MR Chart",
    ))

    # 3. Last 25 observations
    last_25 = data[-25:] if len(data) >= 25 else data
    run_spec = ChartSpec(title="Last 25 Observations", chart_type="run_chart", height=200)
    run_spec.add_trace(list(range(1, len(last_25) + 1)), last_25, trace_type="line", color=get_color(0), width=1.5, marker_size=4)
    if usl is not None:
        run_spec.add_reference_line(usl, color=STATUS_RED, dash="dashed", label="USL")
    if lsl is not None:
        run_spec.add_reference_line(lsl, color=STATUS_RED, dash="dashed", label="LSL")
    specs.append(run_spec)

    # 4. Capability histogram
    specs.append(capability_histogram(data, usl=usl, lsl=lsl, target=target, cp=cp, cpk=cpk, bins=15))

    # 5. Normal probability plot
    specs.append(normal_probability_plot(data, title="Normal Probability"))

    # 6. Summary
    summary = ChartSpec(title="Capability Summary", chart_type="capability_summary", height=200)
    summary.annotations = [
        {"x": 0.1, "y": 0.85, "text": f"Cp = {cp:.3f}" if cp else "Cp = —", "font_size": 12, "color": STATUS_GREEN if cp and cp >= 1.33 else STATUS_AMBER},
        {"x": 0.1, "y": 0.70, "text": f"Cpk = {cpk:.3f}" if cpk else "Cpk = —", "font_size": 12, "color": STATUS_GREEN if cpk and cpk >= 1.33 else STATUS_AMBER},
        {"x": 0.1, "y": 0.55, "text": f"Pp = {pp:.3f}" if pp else "Pp = —", "font_size": 11, "color": "#94a3b8"},
        {"x": 0.1, "y": 0.40, "text": f"Ppk = {ppk:.3f}" if ppk else "Ppk = —", "font_size": 11, "color": "#94a3b8"},
        {"x": 0.1, "y": 0.25, "text": f"n = {n}", "font_size": 11, "color": "#94a3b8"},
        {"x": 0.1, "y": 0.10, "text": f"Mean = {mean:.4f}, Std = {sigma:.4f}", "font_size": 10, "color": "#64748b"},
    ]
    specs.append(summary)

    return specs
