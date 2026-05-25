"""SPC control chart visualizations.

Takes forgespc ControlChartResult → ForgeViz ChartSpec.
"""

from __future__ import annotations

from ..core.colors import STATUS_AMBER, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def control_chart(
    data_points: list[float],
    ucl: float,
    cl: float,
    lcl: float,
    ooc_indices: list[int] | None = None,
    title: str = "Control Chart",
    chart_type_label: str = "",
    usl: float | None = None,
    lsl: float | None = None,
    secondary_data: list[float] | None = None,
    secondary_ucl: float | None = None,
    secondary_cl: float | None = None,
    secondary_lcl: float | None = None,
    secondary_title: str = "",
    run_violations: list[dict] | None = None,
) -> ChartSpec:
    """Build a control chart spec from SPC results.

    Works with any chart type: I-MR, X-bar/R, p, c, u, np, CUSUM, EWMA.
    """
    x = list(range(1, len(data_points) + 1))
    ooc = set(ooc_indices or [])

    spec = ChartSpec(
        title=title,
        subtitle=chart_type_label,
        chart_type="control_chart",
        x_axis={"label": "Sample", "grid": True},
        y_axis={"label": "Value", "grid": True},
    )

    # Main data trace
    spec.add_trace(x, data_points, name="Data", trace_type="line", color=get_color(0), width=1.5, marker_size=4)

    # OOC points highlighted
    if ooc:
        spec.add_marker(list(ooc), color=STATUS_RED, size=8, symbol="circle", label="Out of Control")

    # Control limits
    spec.add_reference_line(ucl, color=STATUS_RED, dash="dashed", label="UCL", width=1)
    spec.add_reference_line(cl, color=STATUS_GREEN, dash="solid", label="CL", width=1)
    spec.add_reference_line(lcl, color=STATUS_RED, dash="dashed", label="LCL", width=1)

    # Spec limits if provided
    if usl is not None:
        spec.add_reference_line(usl, color=STATUS_AMBER, dash="dotted", label="USL", width=0.75)
    if lsl is not None:
        spec.add_reference_line(lsl, color=STATUS_AMBER, dash="dotted", label="LSL", width=0.75)

    # Zone shading (1-sigma, 2-sigma)
    if ucl > cl > lcl:
        one_sigma = (ucl - cl) / 3
        spec.add_zone(cl + 2 * one_sigma, ucl, color="rgba(239,68,68,0.05)", label="Zone A")
        spec.add_zone(cl + one_sigma, cl + 2 * one_sigma, color="rgba(245,158,11,0.03)", label="Zone B")
        spec.add_zone(lcl, cl - 2 * one_sigma, color="rgba(245,158,11,0.03)")
        spec.add_zone(cl - 2 * one_sigma, lcl, color="rgba(239,68,68,0.05)")

    # Nelson/Western Electric run rule violations — amber diamonds
    if run_violations:
        violation_indices = set()
        for v in run_violations:
            for idx in v.get("indices", []):
                violation_indices.add(idx)
        # Remove any that are already OOC (avoid double-marking)
        violation_only = violation_indices - ooc
        if violation_only:
            spec.add_marker(sorted(violation_only), color=STATUS_AMBER, size=7, symbol="diamond", label="Run Rule")

    return spec


def from_conformal_result(result, title: str = "Conformal Control Chart") -> list[ChartSpec]:
    """Convert a forgespc ConformalControlResult to ChartSpec(s).

    Returns a list of ChartSpecs:
      [0] Main chart: data + prediction intervals + OOC markers + phase separator
      [1] Nonconformity scores vs threshold
    """
    data = result.data_points
    n = len(data)
    n_cal = result.n_calibration
    threshold = result.threshold
    ooc_idx = set(result.ooc_indices or [])
    pi = result.prediction_intervals

    x = list(range(n))

    # Chart 1: Main conformal control chart
    main = ChartSpec(
        title=title,
        subtitle="Distribution-free (Burger et al. 2025)",
        chart_type="control_chart",
        x_axis={"label": "Observation", "grid": True},
        y_axis={"label": "Value", "grid": True},
    )

    # Data trace — color by phase
    main.add_trace(x[:n_cal], data[:n_cal], name="Calibration", color=get_color(0), width=1.5, marker_size=3)
    main.add_trace(x[n_cal:], data[n_cal:], name="Monitoring", color=get_color(1), width=1.5, marker_size=3)

    # Prediction interval bands
    if pi and len(pi) == n:
        upper = [p[1] if isinstance(p, (list, tuple)) else getattr(p, "upper", None) for p in pi]
        lower = [p[0] if isinstance(p, (list, tuple)) else getattr(p, "lower", None) for p in pi]
        if upper[0] is not None:
            main.add_trace(x, upper, name="Upper PI", color=STATUS_RED, dash="dashed", width=1)
            main.add_trace(x, lower, name="Lower PI", color=STATUS_RED, dash="dashed", width=1)

    # OOC markers
    if ooc_idx:
        main.add_marker(sorted(ooc_idx), color=STATUS_RED, size=8, symbol="circle", label="OOC")

    # Phase separator
    main.add_reference_line(n_cal, color=STATUS_AMBER, dash="dashdot", label="Cal|Mon", axis="x")

    # Chart 2: Nonconformity scores
    scores = result.nonconformity_scores
    if scores and len(scores) == n:
        score_chart = ChartSpec(
            title="Nonconformity Scores vs Threshold",
            chart_type="bar",
            x_axis={"label": "Observation"},
            y_axis={"label": "|X − median|"},
        )
        score_chart.add_trace(x, scores, name="Score", trace_type="bar", color=get_color(0))
        score_chart.add_reference_line(threshold, color=STATUS_RED, dash="dashed", label=f"q={threshold:.3f}")
        return [main, score_chart]

    return [main]


def from_mewma_result(result, title: str = "MEWMA Chart") -> ChartSpec:
    """Convert a forgespc MEWMAResult to ChartSpec.

    MEWMAResult has: t2_values, ucl, in_control, out_of_control_indices,
    lambda_param, n, n_vars.
    """
    t2 = result.t2_values
    ucl = result.ucl
    ooc_idx = set(result.out_of_control_indices or [])
    x = list(range(1, len(t2) + 1))

    spec = ChartSpec(
        title=title,
        subtitle=f"λ={result.lambda_param}, {result.n_vars} variables",
        chart_type="control_chart",
        x_axis={"label": "Sample", "grid": True},
        y_axis={"label": "T² Statistic", "grid": True},
    )

    spec.add_trace(x, t2, name="T²", trace_type="line", color=get_color(0), width=1.5, marker_size=3)
    spec.add_reference_line(ucl, color=STATUS_RED, dash="dashed", label=f"UCL={ucl:.2f}")

    if ooc_idx:
        spec.add_marker(sorted(ooc_idx), color=STATUS_RED, size=8, symbol="circle", label="OOC")

    return spec


def from_spc_result(result, title: str = "") -> ChartSpec:
    """Convert a forgespc ControlChartResult directly to ChartSpec."""
    ooc_indices = [p["index"] for p in result.out_of_control] if result.out_of_control else []

    spec = control_chart(
        data_points=result.data_points,
        ucl=result.limits.ucl,
        cl=result.limits.cl,
        lcl=result.limits.lcl,
        ooc_indices=ooc_indices,
        title=title or f"{result.chart_type} Control Chart",
        chart_type_label=result.chart_type,
        usl=result.limits.usl,
        lsl=result.limits.lsl,
        run_violations=getattr(result, "run_violations", None),
    )

    return spec


def run_chart(
    data_points: list[float],
    title: str = "Run Chart",
    center: float | None = None,
) -> ChartSpec:
    """Run chart — data plotted in time order with median line.

    Simpler than a control chart: no control limits, just sequence and center.
    """
    x = list(range(1, len(data_points) + 1))
    median = center if center is not None else sorted(data_points)[len(data_points) // 2] if data_points else 0

    spec = ChartSpec(
        title=title,
        chart_type="run_chart",
        x_axis={"label": "Observation"},
        y_axis={"label": "Value"},
    )
    spec.add_trace(x, data_points, name="Data", trace_type="line", color=get_color(0), width=1.5, marker_size=4)
    spec.add_reference_line(median, color=STATUS_GREEN, dash="solid", label=f"Median: {median:.3f}")
    return spec


def from_spc_result_pair(result, title: str = "") -> list[ChartSpec]:
    """Convert a forgespc ControlChartResult with secondary chart to a pair of ChartSpecs.

    Returns [primary_chart, secondary_chart] for composition via ForgeViz.compose().
    """
    specs = [from_spc_result(result, title)]

    if result.secondary_chart:
        sec = result.secondary_chart
        sec_ooc = [p["index"] for p in sec.out_of_control] if sec.out_of_control else []
        sec_spec = control_chart(
            data_points=sec.data_points,
            ucl=sec.limits.ucl,
            cl=sec.limits.cl,
            lcl=sec.limits.lcl,
            ooc_indices=sec_ooc,
            title=f"{sec.chart_type} Chart",
            chart_type_label=sec.chart_type,
        )
        sec_spec.height = 200  # secondary is shorter
        specs.append(sec_spec)

    return specs
