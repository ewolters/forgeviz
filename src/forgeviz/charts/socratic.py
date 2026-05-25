"""Socratic charts — adversarial context with opt-in insight.

The chart renders the GAP between theoretical and actual as the primary visual.
The system pre-computes where the gap is heading (anticipatory) but only
reveals the explanation when asked (opt-in).

Manufacturing data IS gap data: Cpk, yield, OEE are all actual-vs-spec.
These charts make the gap the subject, not the data.
"""

from __future__ import annotations

import math

from ..core.colors import (
    STATUS_AMBER,
    STATUS_GREEN,
    STATUS_RED,
    get_color,
)
from ..core.spec import ChartSpec


def gap_chart(
    actual: list[float],
    theoretical: list[float] | float,
    x: list | None = None,
    title: str = "Gap Analysis",
    x_label: str = "Observation",
    y_label: str = "Value",
    gap_label: str = "Gap",
) -> ChartSpec:
    """Chart that renders the gap between actual and theoretical as primary visual.

    theoretical: a single target value, or a list matching actual length.
    The gap area is the dominant visual. The actual data is secondary.
    """
    n = len(actual)
    x_vals = x or list(range(1, n + 1))

    if isinstance(theoretical, (int, float)):
        theo_vals = [float(theoretical)] * n
    else:
        theo_vals = list(theoretical)[:n]

    gaps = [actual[i] - theo_vals[i] for i in range(n)]
    abs_gaps = [abs(g) for g in gaps]
    mean_gap = sum(gaps) / n if n > 0 else 0
    max_gap = max(abs_gaps) if abs_gaps else 0

    spec = ChartSpec(
        title=title,
        chart_type="gap_chart",
        x_axis={"label": x_label},
        y_axis={"label": y_label},
    )

    # Theoretical as solid reference
    spec.add_trace(x_vals, theo_vals, name="Theoretical", trace_type="line",
                   color=STATUS_GREEN, width=2, dash="solid")

    # Actual as data points
    point_colors = [STATUS_GREEN if abs(g) < max_gap * 0.3 else
                    STATUS_AMBER if abs(g) < max_gap * 0.7 else
                    STATUS_RED for g in gaps]
    spec.add_trace(x_vals, actual, name="Actual", trace_type="scatter",
                   color=get_color(0), marker_size=6, colors=point_colors)

    # Gap as shaded area between actual and theoretical
    spec.add_trace(x_vals, gaps, name=gap_label, trace_type="bar",
                   color="rgba(208,96,96,0.3)", opacity=0.4)

    # Anticipatory: embed trend projection in the spec
    if n >= 5:
        gap_trend = _linear_trend(gaps)
        projected = [gap_trend["intercept"] + gap_trend["slope"] * (n + i) for i in range(1, n // 2 + 1)]
        proj_x = list(range(n + 1, n + len(projected) + 1))

        spec.interactive = {
            "type": "socratic",
            "anticipatory": {
                "gap_trend_slope": round(gap_trend["slope"], 6),
                "gap_trend_r2": round(gap_trend["r2"], 4),
                "projected_gaps": [round(p, 4) for p in projected],
                "projected_x": proj_x,
                "mean_gap": round(mean_gap, 4),
                "max_gap": round(max_gap, 4),
                "direction": "widening" if gap_trend["slope"] > 0 else "narrowing" if gap_trend["slope"] < 0 else "stable",
            },
            "insight_available": True,
            "insight_prompt": "Click to reveal gap trend analysis",
        }

    return spec


def capability_gap(
    data: list[float],
    usl: float,
    lsl: float,
    target: float | None = None,
    title: str = "Capability Gap",
) -> ChartSpec:
    """Capability chart framed as gap-to-spec.

    Instead of "your Cpk is 1.2", shows "here's how much of your process
    falls outside spec, and here's where it's heading."
    """
    n = len(data)
    if n < 2:
        return ChartSpec(title=title, chart_type="capability_gap")

    mean = sum(data) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in data) / (n - 1))
    tgt = target if target is not None else (usl + lsl) / 2
    spec_range = usl - lsl

    # Cpk
    cpu = (usl - mean) / (3 * std) if std > 0 else float("inf")
    cpl = (mean - lsl) / (3 * std) if std > 0 else float("inf")
    cpk = min(cpu, cpl)

    # Fraction out of spec
    n_above = sum(1 for x in data if x > usl)
    n_below = sum(1 for x in data if x < lsl)
    pct_out = (n_above + n_below) / n * 100

    # Distance from target (normalized to spec range)
    centering_gap = abs(mean - tgt) / (spec_range / 2) * 100 if spec_range > 0 else 0

    spec = ChartSpec(
        title=title,
        subtitle=f"Cpk={cpk:.2f} | {pct_out:.1f}% out of spec | {centering_gap:.0f}% off-center",
        chart_type="capability_gap",
        x_axis={"label": "Value"},
        y_axis={"label": "Frequency"},
    )

    # Histogram
    bins = min(30, max(10, n // 5))
    min_val, max_val = min(data), max(data)
    bin_width = (max_val - min_val) / bins if bins > 0 and max_val > min_val else 1
    bin_edges = [min_val + i * bin_width for i in range(bins + 1)]
    counts = [0] * bins
    for val in data:
        idx = min(int((val - min_val) / bin_width), bins - 1) if bin_width > 0 else 0
        counts[idx] += 1
    centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(bins)]

    # Color bars by position relative to spec
    bar_colors = []
    for c in centers:
        if c < lsl or c > usl:
            bar_colors.append(STATUS_RED)
        elif abs(c - tgt) > spec_range * 0.35:
            bar_colors.append(STATUS_AMBER)
        else:
            bar_colors.append(STATUS_GREEN)

    spec.add_trace(centers, counts, name="Distribution", trace_type="bar",
                   colors=bar_colors, opacity=0.8)

    # Spec limits and target
    spec.add_reference_line(usl, color=STATUS_RED, dash="solid", label=f"USL={usl}")
    spec.add_reference_line(lsl, color=STATUS_RED, dash="solid", label=f"LSL={lsl}")
    spec.add_reference_line(tgt, color=STATUS_GREEN, dash="dashed", label=f"Target={tgt}")
    spec.add_reference_line(mean, color=get_color(8), dash="dotted", label=f"Mean={mean:.3f}")

    # Gap zones
    if n_above > 0:
        spec.add_zone(usl, max_val + bin_width, color="rgba(208,96,96,0.15)", label=f"{n_above} above USL")
    if n_below > 0:
        spec.add_zone(min_val - bin_width, lsl, color="rgba(208,96,96,0.15)", label=f"{n_below} below LSL")

    # Anticipatory: rolling Cpk trend
    if n >= 20:
        window = max(10, n // 5)
        cpk_series = []
        for i in range(window, n + 1):
            chunk = data[i - window:i]
            m = sum(chunk) / window
            s = math.sqrt(sum((x - m) ** 2 for x in chunk) / (window - 1)) if window > 1 else 0.001
            s = max(s, 0.001)
            cpk_series.append(min((usl - m) / (3 * s), (m - lsl) / (3 * s)))

        trend = _linear_trend(cpk_series)

        spec.interactive = {
            "type": "socratic",
            "anticipatory": {
                "cpk_current": round(cpk, 3),
                "cpk_trend_slope": round(trend["slope"], 6),
                "cpk_trend_r2": round(trend["r2"], 4),
                "cpk_direction": "improving" if trend["slope"] > 0 else "degrading" if trend["slope"] < 0 else "stable",
                "pct_out_of_spec": round(pct_out, 2),
                "centering_gap_pct": round(centering_gap, 1),
                "steps_to_incapable": _steps_to_threshold(cpk_series, 1.0, trend["slope"]) if trend["slope"] < 0 else None,
            },
            "insight_available": True,
            "insight_prompt": "Click to reveal capability trend",
        }

    return spec


def oee_gap(
    availability: list[float],
    performance: list[float],
    quality: list[float],
    targets: dict[str, float] | None = None,
    title: str = "OEE Gap Analysis",
) -> ChartSpec:
    """OEE broken down as three gaps: availability, performance, quality.

    Each component shown as distance from target. The biggest gap
    is where improvement effort should focus.
    """
    n = min(len(availability), len(performance), len(quality))
    tgt = targets or {"availability": 90, "performance": 95, "quality": 99.5}

    oee = [availability[i] * performance[i] * quality[i] / 10000 for i in range(n)]
    oee_target = tgt.get("availability", 90) * tgt.get("performance", 95) * tgt.get("quality", 99.5) / 10000

    # Average gaps
    avg_a = sum(availability[:n]) / n
    avg_p = sum(performance[:n]) / n
    avg_q = sum(quality[:n]) / n
    gaps = {
        "Availability": round(tgt.get("availability", 90) - avg_a, 1),
        "Performance": round(tgt.get("performance", 95) - avg_p, 1),
        "Quality": round(tgt.get("quality", 99.5) - avg_q, 1),
    }

    spec = ChartSpec(
        title=title,
        subtitle=f"OEE={sum(oee) / n:.1f}% (target {oee_target:.1f}%)",
        chart_type="oee_gap",
        x_axis={"label": "Component"},
        y_axis={"label": "Gap to Target (%)"},
    )

    cats = list(gaps.keys())
    vals = list(gaps.values())
    colors = [STATUS_RED if v > 5 else STATUS_AMBER if v > 2 else STATUS_GREEN for v in vals]
    spec.add_trace(cats, vals, name="Gap", trace_type="bar", colors=colors, opacity=0.8)
    spec.add_reference_line(0, color=STATUS_GREEN, dash="solid", label="Target")

    # Biggest loss
    biggest = max(gaps, key=lambda k: gaps[k])
    spec.annotations.append({
        "x": 0.5, "y": 0.95,
        "text": f"Focus: {biggest} (−{gaps[biggest]}%)",
        "color": STATUS_RED, "font_size": 13,
    })

    return spec


def _linear_trend(y: list[float]) -> dict:
    """Simple OLS linear trend. Returns slope, intercept, r2."""
    n = len(y)
    if n < 2:
        return {"slope": 0, "intercept": y[0] if y else 0, "r2": 0}
    x = list(range(n))
    mx = sum(x) / n
    my = sum(y) / n
    ss_xy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    ss_xx = sum((xi - mx) ** 2 for xi in x)
    slope = ss_xy / ss_xx if ss_xx > 0 else 0
    intercept = my - slope * mx
    y_pred = [intercept + slope * xi for xi in x]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((yi - my) ** 2 for yi in y)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return {"slope": slope, "intercept": intercept, "r2": r2}


def _steps_to_threshold(series: list[float], threshold: float, slope: float) -> int | None:
    """Estimate how many steps until series crosses threshold at current trend."""
    if slope >= 0 or not series:
        return None
    current = series[-1]
    if current <= threshold:
        return 0
    return int(math.ceil((threshold - current) / slope))
