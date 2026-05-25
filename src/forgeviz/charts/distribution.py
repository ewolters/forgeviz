"""Distribution charts — histogram, box plot, capability histogram."""

from __future__ import annotations

import math

from ..core.colors import STATUS_AMBER, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def _quantile(sorted_data: list[float], p: float) -> float:
    """Linear interpolation quantile (matches numpy default method)."""
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    pos = p * (n - 1)
    lower = int(pos)
    upper = min(lower + 1, n - 1)
    weight = pos - lower
    return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


def histogram(
    data: list[float],
    bins: int = 20,
    title: str = "Histogram",
    usl: float | None = None,
    lsl: float | None = None,
    target: float | None = None,
    show_normal: bool = False,
) -> ChartSpec:
    """Build a histogram spec with optional spec limits and normal overlay."""
    if not data:
        return ChartSpec(title=title, chart_type="histogram")

    min_val = min(data)
    max_val = max(data)
    bin_width = (max_val - min_val) / bins if bins > 0 and max_val > min_val else 1

    # Compute bin counts
    bin_edges = [min_val + i * bin_width for i in range(bins + 1)]
    counts = [0] * bins
    for val in data:
        idx = min(int((val - min_val) / bin_width), bins - 1) if bin_width > 0 else 0
        counts[idx] += 1

    bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(bins)]

    spec = ChartSpec(
        title=title,
        chart_type="histogram",
        x_axis={"label": "Value", "grid": False},
        y_axis={"label": "Frequency", "grid": True},
    )

    spec.add_trace(bin_centers, counts, name="Data", trace_type="bar", color=get_color(0), opacity=0.7)

    if usl is not None:
        spec.add_reference_line(usl, axis="x", color=STATUS_RED, dash="dashed", label="USL")
    if lsl is not None:
        spec.add_reference_line(lsl, axis="x", color=STATUS_RED, dash="dashed", label="LSL")
    if target is not None:
        spec.add_reference_line(target, axis="x", color=STATUS_GREEN, dash="solid", label="Target")

    if show_normal and len(data) >= 3:
        mean = sum(data) / len(data)
        std = math.sqrt(sum((x - mean) ** 2 for x in data) / (len(data) - 1))
        if std > 0:
            n_pts = 100
            x_range = [min_val + i * (max_val - min_val) / n_pts for i in range(n_pts + 1)]
            normal_y = [
                len(data) * bin_width * (1 / (std * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((x - mean) / std) ** 2)
                for x in x_range
            ]
            spec.add_trace(x_range, normal_y, name="Normal Fit", trace_type="line", color=STATUS_AMBER, width=2)

    return spec


def probability_plot(
    data: list[float],
    distribution: str = "normal",
    title: str = "",
) -> ChartSpec:
    """Probability plot — data quantiles vs theoretical quantiles.

    Supports: normal, lognormal, exponential, weibull.
    """
    import math

    if not data or len(data) < 3:
        return ChartSpec(title=title or f"Probability Plot ({distribution})", chart_type="probability_plot")

    sorted_d = sorted(data)
    n = len(sorted_d)
    # Plotting positions (Blom's formula)
    pp = [(i - 0.375) / (n + 0.25) for i in range(1, n + 1)]

    if distribution == "lognormal":
        sorted_d = [math.log(max(v, 1e-10)) for v in sorted_d]
        dist_label = "Lognormal"
    elif distribution == "exponential":
        # Exponential quantiles: -ln(1-p)
        theoretical = [-math.log(1 - p) for p in pp]
        spec = ChartSpec(
            title=title or "Probability Plot (Exponential)",
            chart_type="probability_plot",
            x_axis={"label": "Theoretical Quantiles (Exponential)"},
            y_axis={"label": "Ordered Data"},
        )
        spec.add_trace(theoretical, sorted_d, name="Data", trace_type="scatter", color=get_color(0), marker_size=5)
        # Fit line
        mean = sum(sorted_d) / n
        fit_x = [theoretical[0], theoretical[-1]]
        fit_y = [mean * theoretical[0], mean * theoretical[-1]]
        spec.add_trace(fit_x, fit_y, name="Fit", trace_type="line", color=STATUS_RED, dash="dashed", width=1.5)
        return spec
    else:
        dist_label = "Normal"

    # Normal/Lognormal: use inverse normal CDF approximation
    def _inv_norm(p):
        # Rational approximation (Abramowitz & Stegun 26.2.23)
        if p <= 0:
            return -4.0
        if p >= 1:
            return 4.0
        if p == 0.5:
            return 0.0
        if p > 0.5:
            return -_inv_norm(1 - p)
        t = math.sqrt(-2 * math.log(p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        return -(t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t))

    theoretical = [_inv_norm(p) for p in pp]

    spec = ChartSpec(
        title=title or f"Probability Plot ({dist_label})",
        chart_type="probability_plot",
        x_axis={"label": f"Theoretical Quantiles ({dist_label})"},
        y_axis={"label": "Ordered Data"},
    )
    spec.add_trace(theoretical, sorted_d, name="Data", trace_type="scatter", color=get_color(0), marker_size=5)

    # Reference line (mean + std * theoretical)
    mean = sum(sorted_d) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in sorted_d) / max(n - 1, 1))
    fit_x = [theoretical[0], theoretical[-1]]
    fit_y = [mean + std * theoretical[0], mean + std * theoretical[-1]]
    spec.add_trace(fit_x, fit_y, name="Reference", trace_type="line", color=STATUS_RED, dash="dashed", width=1.5)

    return spec


def ecdf(
    data: list[float],
    title: str = "ECDF",
) -> ChartSpec:
    """Empirical Cumulative Distribution Function."""
    if not data:
        return ChartSpec(title=title, chart_type="ecdf")

    sorted_d = sorted(data)
    n = len(sorted_d)
    y = [(i + 1) / n for i in range(n)]

    spec = ChartSpec(
        title=title,
        chart_type="ecdf",
        x_axis={"label": "Value"},
        y_axis={"label": "Cumulative Probability"},
    )
    spec.add_trace(sorted_d, y, name="ECDF", trace_type="step", color=get_color(0), width=2)
    return spec


def box_plot(
    datasets: dict[str, list[float]],
    title: str = "Box Plot",
) -> ChartSpec:
    """Build a box plot spec from named datasets."""
    spec = ChartSpec(title=title, chart_type="box_plot", x_axis={"label": ""}, y_axis={"label": "Value"})

    for i, (name, data) in enumerate(datasets.items()):
        if not data:
            continue
        sorted_d = sorted(data)
        q1 = _quantile(sorted_d, 0.25)
        q2 = _quantile(sorted_d, 0.50)
        q3 = _quantile(sorted_d, 0.75)
        iqr = q3 - q1
        whisker_low = max(min(data), q1 - 1.5 * iqr)
        whisker_high = min(max(data), q3 + 1.5 * iqr)
        outliers = [v for v in data if v < whisker_low or v > whisker_high]

        spec.traces.append({
            "type": "box",
            "name": name,
            "q1": q1,
            "median": q2,
            "q3": q3,
            "whisker_low": whisker_low,
            "whisker_high": whisker_high,
            "outliers": outliers,
            "color": get_color(i),
            "x_position": i,
        })

    return spec
