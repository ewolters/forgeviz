"""SPC control chart visualizations.

Takes forgespc ControlChartResult → ForgeViz ChartSpec.
"""

from __future__ import annotations

from ..core.colors import STATUS_AMBER, STATUS_DIM, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec, Trace


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
        ooc_x = [i + 1 for i in ooc]
        ooc_y = [data_points[i] for i in ooc if i < len(data_points)]
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
    )

    # Add secondary chart if present (e.g., R chart for X-bar/R)
    if result.secondary_chart:
        # Secondary chart would be a separate ChartSpec in practice
        pass

    return spec
