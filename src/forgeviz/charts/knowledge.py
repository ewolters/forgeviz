"""OLR-001 Knowledge Health visualizations — unique to SVEND.

Charts that don't exist anywhere else:
- Knowledge health sparklines
- Maturity trajectory
- Detection ladder
- Evidence timeline
- Proactive/reactive gauge
"""

from __future__ import annotations

from ..core.colors import STATUS_AMBER, STATUS_DIM, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def knowledge_health_sparklines(
    dates: list[str],
    calibration_rate: list[float],
    staleness_rate: list[float],
    contradiction_rate: list[float],
    gap_ratio: list[float],
    title: str = "Knowledge Health",
) -> ChartSpec:
    """Multi-line sparklines showing knowledge health metrics over time.

    Each metric is a 0-1 value tracked daily/weekly.
    """
    spec = ChartSpec(
        title=title,
        chart_type="knowledge_health",
        x_axis={"label": "", "scale": "date"},
        y_axis={"label": "Rate", "min_val": 0, "max_val": 1},
        height=250,
    )

    spec.add_trace(dates, calibration_rate, name="Calibrated", trace_type="line", color=STATUS_GREEN, width=2)
    spec.add_trace(dates, staleness_rate, name="Stale", trace_type="line", color=STATUS_AMBER, width=2)
    spec.add_trace(dates, contradiction_rate, name="Contradicted", trace_type="line", color=STATUS_RED, width=2)
    spec.add_trace(dates, gap_ratio, name="Gaps", trace_type="line", color=STATUS_DIM, width=1.5, dash="dashed")

    return spec


def maturity_trajectory(
    dates: list[str],
    levels: list[int],
    title: str = "Maturity Trajectory",
) -> ChartSpec:
    """Maturity level (1-4) over time with colored zones.

    Shows the org's journey from Structured → Learning → Sustaining → Predictive.
    """
    spec = ChartSpec(
        title=title,
        chart_type="maturity_trajectory",
        x_axis={"label": ""},
        y_axis={"label": "Maturity Level", "min_val": 0.5, "max_val": 4.5},
        height=200,
    )

    # Zone shading for each level
    spec.add_zone(0.5, 1.5, color="rgba(239,68,68,0.08)", label="L1: Structured")
    spec.add_zone(1.5, 2.5, color="rgba(245,158,11,0.08)", label="L2: Learning")
    spec.add_zone(2.5, 3.5, color="rgba(34,197,94,0.08)", label="L3: Sustaining")
    spec.add_zone(3.5, 4.5, color="rgba(99,102,241,0.08)", label="L4: Predictive")

    # Actual trajectory
    spec.add_trace(dates, levels, name="Maturity", trace_type="step", color=get_color(0), width=3, marker_size=6)

    # Level labels on y-axis
    spec.annotations = [
        {"x": 0, "y": 1, "text": "Structured", "color": STATUS_RED, "font_size": 9},
        {"x": 0, "y": 2, "text": "Learning", "color": STATUS_AMBER, "font_size": 9},
        {"x": 0, "y": 3, "text": "Sustaining", "color": STATUS_GREEN, "font_size": 9},
        {"x": 0, "y": 4, "text": "Predictive", "color": "#6366f1", "font_size": 9},
    ]

    return spec


def detection_ladder(
    levels: dict[int, int],
    classification_tier: str = "critical",
    title: str = "Detection Mechanism Distribution",
) -> ChartSpec:
    """Detection hierarchy ladder — OLR-001 §9.

    Shows count of characteristics at each detection level (1-8).
    Red line at minimum level for the classification tier.
    """
    LEVEL_NAMES = {
        1: "Source Prevention",
        2: "Auto Arrest",
        3: "Auto Detect",
        4: "Auto Alert",
        5: "Structured Check",
        6: "Observation",
        7: "Downstream",
        8: "Undetectable",
    }

    TIER_MINIMUMS = {"critical": 4, "major": 5, "minor": 8}
    min_level = TIER_MINIMUMS.get(classification_tier, 8)

    # Build horizontal bar chart (level 1 at top)
    x_vals = []
    y_labels = []
    colors = []

    for level in range(1, 9):
        count = levels.get(level, 0)
        x_vals.append(count)
        y_labels.append(f"L{level}: {LEVEL_NAMES[level]}")
        # Color: green if above minimum, red if below
        if level <= min_level:
            colors.append(STATUS_GREEN if count > 0 else STATUS_DIM)
        else:
            colors.append(STATUS_RED if count > 0 else STATUS_DIM)

    spec = ChartSpec(
        title=title,
        subtitle=f"Tier: {classification_tier} (minimum: Level {min_level})",
        chart_type="detection_ladder",
        x_axis={"label": "Count"},
        y_axis={"label": ""},
        height=300,
    )

    spec.add_trace(y_labels, x_vals, name="Count", trace_type="bar", color=STATUS_GREEN)

    # Minimum level reference
    spec.add_reference_line(min_level - 0.5, axis="y", color=STATUS_RED, dash="dashed", label=f"Min for {classification_tier}")

    return spec


def evidence_timeline(
    dates: list[str],
    source_types: list[str],
    effect_sizes: list[float | None],
    retracted: list[bool],
    title: str = "Evidence Stack",
) -> ChartSpec:
    """Chronological evidence records on an edge.

    Shows when evidence was added, what type, and whether retracted.
    Effect size shown as bar height. Retracted entries are dimmed.
    """
    spec = ChartSpec(
        title=title,
        chart_type="evidence_timeline",
        x_axis={"label": "Date", "scale": "date"},
        y_axis={"label": "Effect Size"},
        height=200,
    )

    # Color by source type
    TYPE_COLORS = {
        "doe": STATUS_GREEN,
        "investigation": "#60a5fa",
        "spc": STATUS_AMBER,
        "process_confirmation": "#a78bfa",
        "forced_failure_test": "#f472b6",
        "gage_rr": "#4dc9c0",
        "operator": STATUS_DIM,
        "literature": "#94a3b8",
    }

    for i, (date, src, eff, ret) in enumerate(zip(dates, source_types, effect_sizes, retracted)):
        color = TYPE_COLORS.get(src, STATUS_DIM)
        opacity = 0.2 if ret else 0.8
        val = eff if eff is not None else 0.5

        spec.add_trace(
            [date], [val],
            name=src if i == 0 or source_types[i - 1] != src else "",
            trace_type="bar",
            color=color,
            opacity=opacity,
        )

    return spec


def proactive_reactive_gauge(
    proactive_pct: float,
    title: str = "Customer Satisfaction — Proactive Detection",
) -> ChartSpec:
    """Proactive/reactive ratio gauge — OLR-001 §12.

    Shows what % of customer-affecting issues were detected internally
    before the customer reported them.
    """
    spec = ChartSpec(
        title=title,
        chart_type="proactive_gauge",
        height=150,
    )

    reactive_pct = 1.0 - proactive_pct

    # Stacked horizontal bar
    spec.add_trace(
        ["Detection"], [proactive_pct * 100],
        name=f"Proactive ({proactive_pct:.0%})",
        trace_type="bar", color=STATUS_GREEN, opacity=0.8,
    )
    spec.add_trace(
        ["Detection"], [reactive_pct * 100],
        name=f"Reactive ({reactive_pct:.0%})",
        trace_type="bar", color=STATUS_RED, opacity=0.5,
    )

    # Threshold markers
    spec.add_reference_line(90, color=STATUS_GREEN, dash="dashed", label="Target (90%)")

    return spec


def ddmrp_buffer_status(
    item_name: str,
    net_flow_position: float,
    top_of_green: float,
    top_of_yellow: float,
    top_of_red: float,
    red_base: float,
    title: str = "",
) -> ChartSpec:
    """DDMRP buffer visualization — red/yellow/green zones with NFP marker.

    Shows buffer health for a single item.
    """
    spec = ChartSpec(
        title=title or f"Buffer: {item_name}",
        chart_type="ddmrp_buffer",
        x_axis={"label": ""},
        y_axis={"label": "Units", "min_val": 0, "max_val": top_of_green * 1.1},
        height=200,
        width=300,
    )

    # Zone shading
    spec.add_zone(0, red_base, color="rgba(239,68,68,0.3)")  # red base
    spec.add_zone(red_base, top_of_red, color="rgba(239,68,68,0.15)")  # red safety
    spec.add_zone(top_of_red, top_of_yellow, color="rgba(245,158,11,0.15)")  # yellow
    spec.add_zone(top_of_yellow, top_of_green, color="rgba(34,197,94,0.15)")  # green

    # Net flow position marker
    spec.add_reference_line(net_flow_position, color="#ffffff", dash="solid", label=f"NFP: {net_flow_position:.0f}", width=2)

    # Zone boundaries
    spec.add_reference_line(top_of_green, color=STATUS_GREEN, dash="dashed", label="TOG")
    spec.add_reference_line(top_of_yellow, color=STATUS_AMBER, dash="dashed", label="TOY")
    spec.add_reference_line(top_of_red, color=STATUS_RED, dash="dashed", label="TOR")

    return spec


def yield_from_cpk_curve(
    cpk_range: list[float] | None = None,
    current_cpk: float | None = None,
    title: str = "Yield vs Process Capability",
) -> ChartSpec:
    """Yield as a function of Cpk — the ForgeSIOP differentiator visualization.

    Shows the nonlinear relationship between Cpk and yield.
    Highlights current Cpk position.
    """
    import math

    if cpk_range is None:
        cpk_range = [i * 0.05 for i in range(1, 41)]  # 0.05 to 2.0

    def _yield(cpk):
        if cpk <= 0:
            return 50.0
        z = 3 * cpk
        # Normal CDF approximation
        cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        return (2 * cdf - 1) * 100

    yields = [_yield(c) for c in cpk_range]

    spec = ChartSpec(
        title=title,
        chart_type="yield_cpk",
        x_axis={"label": "Cpk"},
        y_axis={"label": "Yield %", "min_val": 90, "max_val": 100},
        height=300,
    )

    spec.add_trace(cpk_range, yields, name="Yield", trace_type="line", color=get_color(0), width=2)

    # Reference lines for common targets
    spec.add_reference_line(1.0, axis="x", color=STATUS_AMBER, dash="dotted", label="Cpk=1.0")
    spec.add_reference_line(1.33, axis="x", color=STATUS_GREEN, dash="dotted", label="Cpk=1.33")
    spec.add_reference_line(99.73, axis="y", color=STATUS_DIM, dash="dotted", label="3σ (99.73%)")

    # Current position
    if current_cpk is not None:
        current_yield = _yield(current_cpk)
        spec.add_marker([0], color=STATUS_RED, size=10, symbol="circle", label=f"Current: Cpk={current_cpk:.2f}, Yield={current_yield:.2f}%")
        # The marker index is wrong for arbitrary x — add as annotation instead
        spec.annotations.append({
            "x": current_cpk,
            "y": current_yield,
            "text": f"Current: {current_cpk:.2f}",
            "color": STATUS_RED,
            "font_size": 10,
        })

    return spec
