"""Auto-analytics engine — automatic pattern detection and chart enrichment.

Pure Python, zero dependencies. Takes a ChartSpec or raw data and
detects trends, outliers, changepoints, seasonality, clusters.
Returns enriched ChartSpecs with annotations, reference lines, and markers.
"""

from __future__ import annotations

import copy
import math
from typing import Any

from ..core.colors import STATUS_AMBER, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec, Marker, ReferenceLine, Trace


# =========================================================================
# Trend detection
# =========================================================================

def detect_trends(
    y_values: list[float],
    window: int = 10,
    min_r_squared: float = 0.7,
) -> list[dict]:
    """Detect linear trend segments using sliding-window least-squares.

    Returns list of {start_idx, end_idx, slope, intercept, r_squared,
    direction: "up"|"down"|"flat"}.
    """
    n = len(y_values)
    if n < 3:
        return []

    # Fit overall trend first
    overall = _linear_fit(list(range(n)), y_values)
    if overall["r_squared"] >= min_r_squared:
        return [overall]

    # Sliding window for segments
    segments = []
    i = 0
    while i < n - window + 1:
        seg_x = list(range(i, i + window))
        seg_y = y_values[i:i + window]
        fit = _linear_fit(seg_x, seg_y)

        if fit["r_squared"] >= min_r_squared:
            # Extend segment as far as r² holds
            end = i + window
            while end < n:
                ext_x = list(range(i, end + 1))
                ext_y = y_values[i:end + 1]
                ext_fit = _linear_fit(ext_x, ext_y)
                if ext_fit["r_squared"] >= min_r_squared:
                    fit = ext_fit
                    end += 1
                else:
                    break

            fit["start_idx"] = i
            fit["end_idx"] = end - 1
            segments.append(fit)
            i = end
        else:
            i += 1

    return segments


def _linear_fit(x: list[float], y: list[float]) -> dict:
    """Simple least-squares linear regression. Returns slope, intercept, r²."""
    n = len(x)
    if n < 2:
        return {"slope": 0, "intercept": y[0] if y else 0, "r_squared": 0,
                "start_idx": 0, "end_idx": 0, "direction": "flat"}

    sx = sum(x)
    sy = sum(y)
    sxx = sum(xi ** 2 for xi in x)
    sxy = sum(xi * yi for xi, yi in zip(x, y))

    denom = n * sxx - sx ** 2
    if abs(denom) < 1e-12:
        return {"slope": 0, "intercept": sy / n, "r_squared": 0,
                "start_idx": int(x[0]), "end_idx": int(x[-1]), "direction": "flat"}

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n

    # R²
    y_mean = sy / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    direction = "up" if slope > 0.001 else ("down" if slope < -0.001 else "flat")

    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": max(0, r_squared),
        "start_idx": int(x[0]),
        "end_idx": int(x[-1]),
        "direction": direction,
    }


# =========================================================================
# Outlier detection
# =========================================================================

def detect_outliers(
    y_values: list[float],
    method: str = "iqr",
    threshold: float = 1.5,
) -> list[int]:
    """Detect outlier indices using IQR or z-score method.

    Args:
        y_values: Data values.
        method: "iqr" (default) or "zscore".
        threshold: IQR multiplier (default 1.5) or z-score threshold (default 3).
    """
    n = len(y_values)
    if n < 4:
        return []

    if method == "zscore":
        mean = sum(y_values) / n
        std = math.sqrt(sum((v - mean) ** 2 for v in y_values) / n)
        if std == 0:
            return []
        z_threshold = threshold if threshold > 2 else 3
        return [i for i, v in enumerate(y_values) if abs((v - mean) / std) > z_threshold]

    # IQR method
    sorted_vals = sorted(y_values)
    q1 = sorted_vals[n // 4]
    q3 = sorted_vals[3 * n // 4]
    iqr = q3 - q1
    if iqr == 0:
        # Fall back to median absolute deviation
        median = sorted_vals[n // 2]
        mad = sorted(abs(v - median) for v in y_values)[n // 2]
        if mad == 0:
            # Use distance from median > 0 as outlier heuristic
            return [i for i, v in enumerate(y_values) if v != median]
        lower = median - threshold * 3 * mad
        upper = median + threshold * 3 * mad
        return [i for i, v in enumerate(y_values) if v < lower or v > upper]

    lower = q1 - threshold * iqr
    upper = q3 + threshold * iqr
    return [i for i, v in enumerate(y_values) if v < lower or v > upper]


# =========================================================================
# Changepoint detection (CUSUM)
# =========================================================================

def detect_changepoints(
    y_values: list[float],
    min_segment: int = 5,
    threshold: float | None = None,
) -> list[int]:
    """Detect structural breaks using CUSUM-based detection.

    Returns list of indices where the mean level shifts.
    """
    n = len(y_values)
    if n < 2 * min_segment:
        return []

    if threshold is None:
        std = _std(y_values)
        threshold = std * 1.5 if std > 0 else 1.0

    mean = sum(y_values) / n
    cusum_pos = [0.0]
    cusum_neg = [0.0]

    changepoints = []

    for i in range(1, n):
        cp = max(0, cusum_pos[-1] + (y_values[i] - mean) - threshold * 0.5)
        cn = max(0, cusum_neg[-1] - (y_values[i] - mean) - threshold * 0.5)
        cusum_pos.append(cp)
        cusum_neg.append(cn)

        if (cp > threshold or cn > threshold) and i >= min_segment and (n - i) >= min_segment:
            # Verify mean shift
            before = sum(y_values[max(0, i - min_segment):i]) / min_segment
            after = sum(y_values[i:min(n, i + min_segment)]) / min_segment
            if abs(after - before) > threshold * 0.5:
                if not changepoints or (i - changepoints[-1]) >= min_segment:
                    changepoints.append(i)
                    # Reset CUSUM
                    cusum_pos[-1] = 0
                    cusum_neg[-1] = 0
                    mean = sum(y_values[i:]) / (n - i)

    return changepoints


# =========================================================================
# Seasonality detection (autocorrelation)
# =========================================================================

def detect_seasonality(
    y_values: list[float],
    max_period: int | None = None,
) -> dict | None:
    """Detect periodic patterns using autocorrelation.

    Returns {period, strength, phase} or None if no significant seasonality.
    """
    n = len(y_values)
    if n < 6:
        return None

    if max_period is None:
        max_period = n // 2

    mean = sum(y_values) / n
    centered = [v - mean for v in y_values]
    var = sum(c ** 2 for c in centered)
    if var == 0:
        return None

    best_period = 0
    best_strength = 0.0

    for lag in range(2, min(max_period + 1, n // 2)):
        autocorr = sum(centered[i] * centered[i + lag] for i in range(n - lag))
        autocorr /= var
        if autocorr > best_strength:
            best_strength = autocorr
            best_period = lag

    if best_strength < 0.3:
        return None

    return {
        "period": best_period,
        "strength": best_strength,
        "phase": 0,
    }


# =========================================================================
# Cluster detection (k-means)
# =========================================================================

def detect_clusters(
    x: list[float],
    y: list[float],
    max_clusters: int = 5,
) -> list[dict]:
    """Detect clusters in 2D data using k-means. Pure Python.

    Returns list of {center_x, center_y, radius, count, indices}.
    """
    n = len(x)
    if n < 3:
        return []

    k = min(max_clusters, n)

    # Find optimal k using silhouette-like heuristic
    best_k = 1
    best_score = float("inf")

    for trial_k in range(1, k + 1):
        centers, labels = _kmeans(x, y, trial_k, max_iter=20)
        # Compute within-cluster sum of squares
        wcss = 0
        for i in range(n):
            cx, cy = centers[labels[i]]
            wcss += (x[i] - cx) ** 2 + (y[i] - cy) ** 2
        # Penalize more clusters (elbow method approximation)
        score = wcss * (1 + trial_k * 0.3)
        if score < best_score:
            best_score = score
            best_k = trial_k

    centers, labels = _kmeans(x, y, best_k, max_iter=50)

    clusters = []
    for ci in range(best_k):
        indices = [i for i in range(n) if labels[i] == ci]
        if not indices:
            continue
        cx = sum(x[i] for i in indices) / len(indices)
        cy = sum(y[i] for i in indices) / len(indices)
        radius = max(math.sqrt((x[i] - cx) ** 2 + (y[i] - cy) ** 2) for i in indices) if indices else 0
        clusters.append({
            "center_x": cx,
            "center_y": cy,
            "radius": radius,
            "count": len(indices),
            "indices": indices,
        })

    return clusters


def _kmeans(
    x: list[float], y: list[float], k: int, max_iter: int = 50,
) -> tuple[list[tuple[float, float]], list[int]]:
    """Simple k-means. Returns (centers, labels)."""
    n = len(x)
    # Initialize centers with evenly-spaced points
    step = max(1, n // k)
    centers = [(x[min(i * step, n - 1)], y[min(i * step, n - 1)]) for i in range(k)]
    labels = [0] * n

    for _ in range(max_iter):
        # Assign
        changed = False
        for i in range(n):
            best_c = 0
            best_d = float("inf")
            for ci, (cx, cy) in enumerate(centers):
                d = (x[i] - cx) ** 2 + (y[i] - cy) ** 2
                if d < best_d:
                    best_d = d
                    best_c = ci
            if labels[i] != best_c:
                labels[i] = best_c
                changed = True

        if not changed:
            break

        # Update centers
        for ci in range(k):
            members = [i for i in range(n) if labels[i] == ci]
            if members:
                centers[ci] = (
                    sum(x[i] for i in members) / len(members),
                    sum(y[i] for i in members) / len(members),
                )

    return centers, labels


# =========================================================================
# Chart type suggestion
# =========================================================================

def suggest_chart_type(data: dict) -> str:
    """Suggest the best chart type from data shape.

    Keys: x, y, categories, time_series (bool), groups (dict).
    Returns chart function name as a string.
    """
    has_x = "x" in data and data["x"]
    has_y = "y" in data and data["y"]
    has_cats = "categories" in data and data["categories"]
    is_ts = data.get("time_series", False)
    has_groups = "groups" in data and data["groups"]

    if has_cats and has_groups:
        return "grouped_bar"
    if has_cats and has_y:
        n = len(data.get("categories", []))
        if n <= 6:
            return "pie"
        return "bar"
    if is_ts and has_y:
        if has_groups:
            return "stacked_area"
        return "line"
    if has_x and has_y:
        return "scatter"
    if has_y and not has_x:
        return "histogram"
    return "bar"


# =========================================================================
# Enrichment functions
# =========================================================================

def add_trend_line(spec: ChartSpec, trace_idx: int = 0) -> ChartSpec:
    """Add a least-squares trend line to the specified trace."""
    spec = copy.deepcopy(spec)
    traces = [t for t in spec.traces if isinstance(t, Trace)]
    if trace_idx >= len(traces):
        return spec

    trace = traces[trace_idx]
    if not trace.x or not trace.y:
        return spec

    x_vals = [v if isinstance(v, (int, float)) else i for i, v in enumerate(trace.x)]
    fit = _linear_fit(x_vals, trace.y)

    trend_y = [fit["slope"] * xi + fit["intercept"] for xi in x_vals]
    spec.add_trace(
        trace.x, trend_y,
        name=f"Trend (R²={fit['r_squared']:.2f})",
        trace_type="line",
        color=STATUS_AMBER,
        dash="dashed",
        width=1.5,
    )

    return spec


def add_confidence_band(
    spec: ChartSpec, trace_idx: int = 0, confidence: float = 0.95,
) -> ChartSpec:
    """Add a confidence band around the specified trace as zones."""
    spec = copy.deepcopy(spec)
    traces = [t for t in spec.traces if isinstance(t, Trace)]
    if trace_idx >= len(traces):
        return spec

    trace = traces[trace_idx]
    if not trace.y or len(trace.y) < 3:
        return spec

    std = _std(trace.y)
    # Approximate z-value for confidence
    z = 1.96 if confidence >= 0.95 else (1.645 if confidence >= 0.9 else 1.0)
    margin = z * std / math.sqrt(len(trace.y))

    mean = sum(trace.y) / len(trace.y)
    spec.add_zone(mean - margin, mean + margin, color="rgba(74,159,110,0.1)", label=f"{confidence:.0%} CI")

    return spec


def add_moving_average(
    spec: ChartSpec, trace_idx: int = 0, window: int = 5,
) -> ChartSpec:
    """Add a moving average overlay as a new dashed trace."""
    spec = copy.deepcopy(spec)
    traces = [t for t in spec.traces if isinstance(t, Trace)]
    if trace_idx >= len(traces):
        return spec

    trace = traces[trace_idx]
    if not trace.y or len(trace.y) < window:
        return spec

    ma = []
    for i in range(len(trace.y)):
        start = max(0, i - window + 1)
        window_vals = trace.y[start:i + 1]
        ma.append(sum(window_vals) / len(window_vals))

    spec.add_trace(
        trace.x, ma,
        name=f"MA({window})",
        trace_type="line",
        color=STATUS_AMBER,
        dash="dashed",
        width=1.5,
    )

    return spec


def auto_annotate(spec: ChartSpec) -> ChartSpec:
    """Analyze traces and add smart annotations (min/max, flat regions, sharp changes)."""
    spec = copy.deepcopy(spec)
    traces = [t for t in spec.traces if isinstance(t, Trace)]
    if not traces:
        return spec

    trace = traces[0]
    if not trace.y or len(trace.y) < 2:
        return spec

    y = trace.y
    n = len(y)

    # Min/max
    min_idx = y.index(min(y))
    max_idx = y.index(max(y))

    x_min = trace.x[min_idx] if min_idx < len(trace.x) else min_idx
    x_max = trace.x[max_idx] if max_idx < len(trace.x) else max_idx

    spec.annotations.append({
        "x": x_min, "y": y[min_idx],
        "text": f"Min: {y[min_idx]:.2f}",
        "color": STATUS_RED, "font_size": 9,
    })
    spec.annotations.append({
        "x": x_max, "y": y[max_idx],
        "text": f"Max: {y[max_idx]:.2f}",
        "color": STATUS_GREEN, "font_size": 9,
    })

    # Trend direction
    trends = detect_trends(y, window=max(3, n // 5))
    if trends:
        t = trends[0]
        arrow = "↑" if t["direction"] == "up" else ("↓" if t["direction"] == "down" else "→")
        spec.annotations.append({
            "x": 0.98, "y": 0.95,
            "text": f"Trend: {arrow} (R²={t['r_squared']:.2f})",
            "color": STATUS_GREEN if t["direction"] == "up" else STATUS_AMBER,
            "font_size": 10,
        })

    return spec


def enrich(
    spec: ChartSpec,
    features: list[str] | None = None,
) -> ChartSpec:
    """Main entry point. Enrich a ChartSpec with auto-detected analytics.

    Args:
        spec: Input ChartSpec.
        features: List of features to add. Options:
            "trends", "outliers", "changepoints", "moving_average",
            "confidence", "annotate"
            If None, auto-detect what's useful.
    """
    spec = copy.deepcopy(spec)
    traces = [t for t in spec.traces if isinstance(t, Trace)]
    if not traces:
        return spec

    trace = traces[0]
    if not trace.y or len(trace.y) < 3:
        return spec

    if features is None:
        n = len(trace.y)
        features = ["annotate"]
        if n >= 10:
            features.append("trends")
        if n >= 8:
            features.append("outliers")
        if n >= 20:
            features.append("moving_average")

    if "annotate" in features:
        spec = auto_annotate(spec)

    if "trends" in features:
        spec = add_trend_line(spec)

    if "outliers" in features:
        outlier_idx = detect_outliers(trace.y)
        if outlier_idx:
            spec.markers.append(Marker(
                indices=outlier_idx,
                color=STATUS_RED,
                size=10,
                symbol="circle",
                label="Outlier",
            ))

    if "changepoints" in features:
        cps = detect_changepoints(trace.y)
        for cp in cps:
            x_val = trace.x[cp] if cp < len(trace.x) else cp
            if isinstance(x_val, (int, float)):
                spec.reference_lines.append(ReferenceLine(
                    value=x_val, axis="x",
                    color=STATUS_AMBER, dash="dashed",
                    label=f"Shift @{cp}",
                ))

    if "moving_average" in features:
        spec = add_moving_average(spec, window=max(3, len(trace.y) // 10))

    if "confidence" in features:
        spec = add_confidence_band(spec)

    return spec


# =========================================================================
# Helpers
# =========================================================================

def _std(values: list[float]) -> float:
    """Standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)
