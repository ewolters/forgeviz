"""Bayesian SPC visualization — posterior capability, changepoint, Bayesian control limits, acceptance."""

from __future__ import annotations

from ..core.colors import STATUS_AMBER, STATUS_DIM, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def bayesian_capability(
    cpk_samples: list[float],
    cpk_mean: float,
    cpk_ci_lower: float,
    cpk_ci_upper: float,
    target_cpk: float = 1.33,
    title: str = "Bayesian Cpk Posterior",
) -> ChartSpec:
    """Full Bayesian posterior distribution of Cpk."""
    from .distribution import histogram

    spec = histogram(cpk_samples, bins=30, title=title)
    spec.chart_type = "bayesian_capability"

    spec.add_reference_line(target_cpk, color=STATUS_GREEN, dash="dashed", label=f"Target Cpk={target_cpk}")
    spec.add_reference_line(cpk_mean, color=get_color(0), dash="solid", label=f"Mean={cpk_mean:.3f}")
    spec.add_reference_line(cpk_ci_lower, color=STATUS_DIM, dash="dotted", label=f"CI Low={cpk_ci_lower:.3f}")
    spec.add_reference_line(cpk_ci_upper, color=STATUS_DIM, dash="dotted", label=f"CI High={cpk_ci_upper:.3f}")

    # Shade probability of meeting target
    pct_above = sum(1 for s in cpk_samples if s >= target_cpk) / len(cpk_samples) * 100 if cpk_samples else 0
    spec.annotations.append({
        "x": 0.7, "y": 0.9,
        "text": f"P(Cpk ≥ {target_cpk}) = {pct_above:.1f}%",
        "color": STATUS_GREEN if pct_above >= 95 else STATUS_AMBER if pct_above >= 80 else STATUS_RED,
        "font_size": 12,
    })

    return spec


def bayesian_changepoint(
    data: list[float],
    changepoint_index: int | None = None,
    changepoint_probability: float | None = None,
    pre_mean: float | None = None,
    post_mean: float | None = None,
    title: str = "Bayesian Changepoint Detection",
) -> ChartSpec:
    """Data with detected changepoint highlighted."""
    spec = ChartSpec(
        title=title, chart_type="bayesian_changepoint",
        x_axis={"label": "Observation"},
        y_axis={"label": "Value"},
    )

    x = list(range(1, len(data) + 1))
    spec.add_trace(x, data, name="Data", trace_type="line", color=get_color(0), width=1.5, marker_size=3)

    if changepoint_index is not None and 0 <= changepoint_index < len(data):
        spec.add_reference_line(changepoint_index + 1, axis="x", color=STATUS_RED, dash="dashed",
                                label=f"Changepoint ({changepoint_probability:.0%} prob)" if changepoint_probability else "Changepoint")

        if pre_mean is not None:
            spec.add_trace(x[:changepoint_index], [pre_mean] * changepoint_index,
                           name=f"Pre-mean={pre_mean:.3f}", trace_type="line", color=STATUS_GREEN, dash="dashed", width=1.5)
        if post_mean is not None:
            spec.add_trace(x[changepoint_index:], [post_mean] * (len(data) - changepoint_index),
                           name=f"Post-mean={post_mean:.3f}", trace_type="line", color=STATUS_RED, dash="dashed", width=1.5)

    return spec


def bayesian_control_chart(
    data: list[float],
    posterior_ucl: list[float],
    posterior_cl: list[float],
    posterior_lcl: list[float],
    title: str = "Bayesian Control Chart",
) -> ChartSpec:
    """Control chart with Bayesian-updating control limits.

    Limits evolve as more data arrives — tighten with more evidence.
    """
    x = list(range(1, len(data) + 1))

    spec = ChartSpec(
        title=title, chart_type="bayesian_control",
        x_axis={"label": "Sample"},
        y_axis={"label": "Value"},
    )

    # Uncertainty band (posterior limits as filled area)
    if len(posterior_ucl) == len(data) and len(posterior_lcl) == len(data):
        spec.add_trace(x, posterior_ucl, name="Posterior UCL", trace_type="line", color=STATUS_RED, width=1, dash="dashed")
        spec.add_trace(x, posterior_lcl, name="Posterior LCL", trace_type="line", color=STATUS_RED, width=1, dash="dashed")
        spec.add_trace(x, posterior_cl, name="Posterior CL", trace_type="line", color=STATUS_GREEN, width=1, dash="solid")

    # Data on top
    spec.add_trace(x, data, name="Data", trace_type="line", color=get_color(0), width=2, marker_size=4)

    # OOC detection against posterior limits
    ooc = []
    for i in range(min(len(data), len(posterior_ucl), len(posterior_lcl))):
        if data[i] > posterior_ucl[i] or data[i] < posterior_lcl[i]:
            ooc.append(i)
    if ooc:
        spec.add_marker(ooc, color=STATUS_RED, size=8, label="OOC (posterior)")

    return spec


def bayesian_acceptance(
    lot_size: int,
    sample_size: int,
    defectives_found: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    accept_threshold: float = 0.05,
    title: str = "Bayesian Acceptance Sampling",
) -> ChartSpec:
    """Posterior distribution of lot defect rate with accept/reject decision."""
    import math

    # Beta posterior
    alpha = prior_alpha + defectives_found
    beta = prior_beta + sample_size - defectives_found

    # Generate posterior PDF
    n_pts = 100
    x_vals = [i / n_pts for i in range(n_pts + 1)]
    y_vals = []
    for p in x_vals:
        if 0 < p < 1:
            # Beta PDF (unnormalized — scale doesn't matter for visualization)
            log_pdf = (alpha - 1) * math.log(p) + (beta - 1) * math.log(1 - p)
            y_vals.append(math.exp(min(500, log_pdf)))
        else:
            y_vals.append(0)

    # Normalize
    max_y = max(y_vals) if y_vals else 1
    y_vals = [y / max_y for y in y_vals]

    spec = ChartSpec(
        title=title, chart_type="bayesian_acceptance",
        x_axis={"label": "Defect Rate"},
        y_axis={"label": "Posterior Density"},
    )

    spec.add_trace(x_vals, y_vals, name="Posterior", trace_type="area", color=get_color(0), opacity=0.3)
    spec.add_trace(x_vals, y_vals, name="", trace_type="line", color=get_color(0), width=2)

    spec.add_reference_line(accept_threshold, axis="x", color=STATUS_RED, dash="dashed", label=f"Accept limit ({accept_threshold:.1%})")

    # Decision
    p_accept = sum(1 for x in x_vals if x <= accept_threshold and y_vals[x_vals.index(x)] > 0.01) / n_pts
    decision = "ACCEPT" if p_accept >= 0.95 else "REJECT"
    decision_color = STATUS_GREEN if decision == "ACCEPT" else STATUS_RED

    spec.annotations.append({
        "x": 0.7, "y": 0.9,
        "text": f"Decision: {decision}",
        "color": decision_color,
        "font_size": 14,
    })
    spec.annotations.append({
        "x": 0.7, "y": 0.8,
        "text": f"Found: {defectives_found}/{sample_size} defectives",
        "color": STATUS_DIM,
        "font_size": 10,
    })

    return spec
