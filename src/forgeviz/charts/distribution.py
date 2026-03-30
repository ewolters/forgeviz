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
