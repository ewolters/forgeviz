"""Predictive overlay system for SPC and process data.

Given historical data (especially SPC data), project forward and show
forecast cones, time-to-breach estimates, and process drift visualization.

Pure Python, zero external dependencies.
"""

from __future__ import annotations

import copy
import math
from typing import Any

from ..core.colors import STATUS_AMBER, STATUS_GREEN, STATUS_RED, rgba
from ..core.spec import ChartSpec, Trace


# =========================================================================
# Internal forecasting engines
# =========================================================================

def _holt_winters(
    y: list[float],
    alpha: float | None = None,
    beta: float | None = None,
    horizon: int = 20,
    confidence: float = 0.95,
) -> tuple[list[float], list[float], list[float]]:
    """Holt-Winters additive double exponential smoothing (no seasonality).

    If alpha/beta are not provided, auto-fit via grid search on the data.
    Fits on the first 80% of data, validates on the last 20%.

    Returns:
        (forecast, lower_bound, upper_bound) each of length ``horizon``.
    """
    n = len(y)
    if n < 2:
        val = y[0] if y else 0.0
        fc = [val] * horizon
        return fc, fc[:], fc[:]

    # Auto-fit if params not given
    if alpha is None or beta is None:
        alpha, beta = _auto_fit_hw(y)

    # Run Holt-Winters on full series to get final level/trend
    level = y[0]
    trend = (y[min(1, n - 1)] - y[0]) if n >= 2 else 0.0

    residuals = []
    for t in range(1, n):
        prev_level = level
        level = alpha * y[t] + (1 - alpha) * (prev_level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
        fitted = prev_level + trend
        residuals.append(y[t] - fitted)

    # Residual standard deviation
    sigma = _std(residuals) if residuals else 0.0

    # z-value for prediction interval
    z = _z_score(confidence)

    forecast = []
    lower = []
    upper = []
    for h in range(1, horizon + 1):
        fc = level + h * trend
        # Prediction interval widens with horizon
        margin = z * sigma * math.sqrt(1 + h / max(n, 1))
        forecast.append(fc)
        lower.append(fc - margin)
        upper.append(fc + margin)

    return forecast, lower, upper


def _auto_fit_hw(y: list[float]) -> tuple[float, float]:
    """Grid search for best alpha/beta on Holt-Winters.

    Fits on first 80%, validates on last 20%. Minimizes MAE.
    """
    n = len(y)
    if n < 4:
        return 0.3, 0.1

    split = max(2, int(n * 0.8))
    train = y[:split]
    val = y[split:]

    if not val:
        return 0.3, 0.1

    alphas = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    betas = [0.01, 0.05, 0.1, 0.2, 0.3]

    best_alpha = 0.3
    best_beta = 0.1
    best_mae = float("inf")

    for a in alphas:
        for b in betas:
            # Train
            level = train[0]
            trend = (train[1] - train[0]) if len(train) >= 2 else 0.0
            for t in range(1, len(train)):
                prev_level = level
                level = a * train[t] + (1 - a) * (prev_level + trend)
                trend = b * (level - prev_level) + (1 - b) * trend

            # Validate: forecast each step ahead
            mae = 0.0
            fc_level = level
            fc_trend = trend
            for t in range(len(val)):
                fc = fc_level + (t + 1) * fc_trend
                mae += abs(val[t] - fc)

            mae /= len(val)
            if mae < best_mae:
                best_mae = mae
                best_alpha = a
                best_beta = b

    return best_alpha, best_beta


def _ewma_forecast(
    y: list[float],
    lambda_: float = 0.2,
    horizon: int = 20,
    confidence: float = 0.95,
) -> tuple[list[float], list[float], list[float]]:
    """EWMA forecast with prediction intervals.

    The EWMA statistic converges to a weighted average. Forecast is the
    last EWMA value extended forward, with widening intervals.

    Returns:
        (forecast, lower_bound, upper_bound) each of length ``horizon``.
    """
    n = len(y)
    if n < 1:
        return [0.0] * horizon, [0.0] * horizon, [0.0] * horizon

    # Compute EWMA
    ewma = y[0]
    for t in range(1, n):
        ewma = lambda_ * y[t] + (1 - lambda_) * ewma

    # Residual std
    residuals = []
    s = y[0]
    for t in range(1, n):
        s = lambda_ * y[t] + (1 - lambda_) * s
        residuals.append(y[t] - s)

    sigma = _std(residuals) if residuals else 0.0
    z = _z_score(confidence)

    # EWMA forecast is flat (last EWMA value) but intervals widen
    forecast = []
    lower = []
    upper = []
    for h in range(1, horizon + 1):
        margin = z * sigma * math.sqrt(1 + h / max(n, 1))
        forecast.append(ewma)
        lower.append(ewma - margin)
        upper.append(ewma + margin)

    return forecast, lower, upper


def _drift_forecast(
    y: list[float],
    horizon: int = 20,
    confidence: float = 0.95,
) -> tuple[list[float], list[float], list[float]]:
    """Random walk with drift forecast.

    Drift is the mean of first differences. Variance grows linearly
    with the forecast horizon.

    Returns:
        (forecast, lower_bound, upper_bound) each of length ``horizon``.
    """
    n = len(y)
    if n < 2:
        val = y[0] if y else 0.0
        fc = [val] * horizon
        return fc, fc[:], fc[:]

    # First differences
    diffs = [y[t] - y[t - 1] for t in range(1, n)]
    drift = sum(diffs) / len(diffs)
    diff_std = _std(diffs) if len(diffs) > 1 else 0.0

    z = _z_score(confidence)
    last = y[-1]

    forecast = []
    lower = []
    upper = []
    for h in range(1, horizon + 1):
        fc = last + h * drift
        margin = z * diff_std * math.sqrt(h)
        forecast.append(fc)
        lower.append(fc - margin)
        upper.append(fc + margin)

    return forecast, lower, upper


def _linear_forecast(
    y: list[float],
    horizon: int = 20,
    confidence: float = 0.95,
) -> tuple[list[float], list[float], list[float]]:
    """Linear extrapolation forecast from least-squares trend.

    Returns:
        (forecast, lower_bound, upper_bound) each of length ``horizon``.
    """
    n = len(y)
    if n < 2:
        val = y[0] if y else 0.0
        fc = [val] * horizon
        return fc, fc[:], fc[:]

    x = list(range(n))
    fit = _linear_fit(x, y)
    slope = fit["slope"]
    intercept = fit["intercept"]

    # Residual std
    residuals = [y[i] - (slope * i + intercept) for i in range(n)]
    sigma = _std(residuals)
    z = _z_score(confidence)

    forecast = []
    lower = []
    upper = []
    for h in range(1, horizon + 1):
        t = n - 1 + h
        fc = slope * t + intercept
        margin = z * sigma * math.sqrt(1 + h / max(n, 1))
        forecast.append(fc)
        lower.append(fc - margin)
        upper.append(fc + margin)

    return forecast, lower, upper


# =========================================================================
# Public API
# =========================================================================

def forecast_overlay(
    spec: ChartSpec,
    horizon: int = 20,
    method: str = "ets",
    confidence: float = 0.95,
) -> ChartSpec:
    """Add a forecast cone to any line or control chart.

    Takes a ChartSpec with at least one line trace, extracts y-values
    from the first trace, forecasts ``horizon`` points forward, and adds:
      - Forecast line (dashed)
      - Upper/lower prediction interval (shaded zone traces)

    Args:
        spec: Input ChartSpec (not mutated).
        horizon: Number of points to forecast forward.
        method: Forecasting method -- "ets", "linear", "ewma", or "drift".
        confidence: Confidence level for prediction interval (0 to 1).

    Returns:
        Enriched ChartSpec with forecast overlay.
    """
    spec = copy.deepcopy(spec)

    # Find the first line-like trace
    trace = _find_first_trace(spec)
    if trace is None or not trace.y or len(trace.y) < 2:
        return spec

    y = [v for v in trace.y if isinstance(v, (int, float))]
    if len(y) < 2:
        return spec

    # Run the forecast
    fc, lo, hi = _dispatch_forecast(y, method, horizon, confidence)

    # Build x-values for the forecast region
    last_x = trace.x[-1] if trace.x else len(y) - 1
    if isinstance(last_x, (int, float)):
        step = 1
        if len(trace.x) >= 2:
            x0 = trace.x[-2]
            x1 = trace.x[-1]
            if isinstance(x0, (int, float)) and isinstance(x1, (int, float)):
                step = x1 - x0
        fc_x = [last_x + step * h for h in range(1, horizon + 1)]
    else:
        fc_x = list(range(len(y), len(y) + horizon))

    # Connect forecast to last historical point
    connect_x = [trace.x[-1]] + fc_x
    connect_fc = [y[-1]] + fc
    connect_lo = [y[-1]] + lo
    connect_hi = [y[-1]] + hi

    # Add upper bound trace (for fill)
    spec.add_trace(
        connect_x, connect_hi,
        name="Upper PI",
        trace_type="line",
        color=rgba(STATUS_AMBER, 0.0),
        dash="dotted",
        width=0.5,
        opacity=0.3,
    )

    # Add lower bound trace (for fill between)
    spec.add_trace(
        connect_x, connect_lo,
        name="Lower PI",
        trace_type="line",
        color=rgba(STATUS_AMBER, 0.0),
        dash="dotted",
        width=0.5,
        fill="tonexty",
        opacity=0.15,
    )

    # Add forecast line
    spec.add_trace(
        connect_x, connect_fc,
        name="Forecast",
        trace_type="line",
        color=STATUS_AMBER,
        dash="dashed",
        width=2.0,
        opacity=0.9,
    )

    return spec


def time_to_breach(
    y_values: list[float],
    limit: float,
    method: str = "ets",
    max_horizon: int = 200,
) -> dict:
    """Estimate when a process will breach a given limit.

    Projects the data forward and finds the first step where the
    forecast crosses ``limit``.

    Args:
        y_values: Historical data points.
        limit: The limit value (USL, UCL, etc.).
        method: Forecasting method.
        max_horizon: Maximum number of steps to project.

    Returns:
        Dict with estimated_steps, confidence, current_trend,
        breach_value, and forecast_values.
    """
    n = len(y_values)
    if n < 2:
        return {
            "estimated_steps": None,
            "confidence": 0.0,
            "current_trend": 0.0,
            "breach_value": limit,
            "forecast_values": [],
        }

    fc, _, _ = _dispatch_forecast(y_values, method, max_horizon, 0.95)

    # Current trend (slope of last segment)
    trend = _current_trend(y_values)

    # Determine breach direction
    last_val = y_values[-1]
    breach_above = limit > last_val  # we breach by going above
    # If limit is below current, we breach by going below
    breach_below = limit < last_val

    estimated_steps = None
    for i, v in enumerate(fc):
        if breach_above and v >= limit:
            estimated_steps = i + 1
            break
        elif breach_below and v <= limit:
            estimated_steps = i + 1
            break

    # Confidence: higher if trend is strong and consistent
    if estimated_steps is not None:
        # Closer breaches are more confident
        proximity_factor = max(0.3, 1.0 - estimated_steps / max_horizon)
        # Trend consistency
        trend_factor = min(1.0, abs(trend) * n * 0.1) if trend != 0 else 0.1
        conf = min(0.95, proximity_factor * 0.6 + trend_factor * 0.4)
    else:
        conf = 0.0

    return {
        "estimated_steps": estimated_steps,
        "confidence": round(conf, 3),
        "current_trend": round(trend, 6),
        "breach_value": limit,
        "forecast_values": fc,
    }


def process_drift_overlay(
    spec: ChartSpec,
    window: int = 10,
) -> ChartSpec:
    """Visualize process drift on a chart.

    Adds a rolling mean trace, a +/-1 sigma envelope, and annotates
    the drift rate. Color-codes drift severity:
      - Green: drift < 0.5 sigma per window
      - Amber: drift < 1.0 sigma per window
      - Red: drift >= 1.0 sigma per window

    Args:
        spec: Input ChartSpec (not mutated).
        window: Rolling window size for mean/std calculation.

    Returns:
        Enriched ChartSpec with drift overlay.
    """
    spec = copy.deepcopy(spec)

    trace = _find_first_trace(spec)
    if trace is None or not trace.y or len(trace.y) < window:
        return spec

    y = trace.y
    n = len(y)

    # Rolling mean and std
    roll_mean = []
    roll_std = []
    for i in range(n):
        start = max(0, i - window + 1)
        w = y[start:i + 1]
        m = sum(w) / len(w)
        roll_mean.append(m)
        if len(w) >= 2:
            s = math.sqrt(sum((v - m) ** 2 for v in w) / len(w))
        else:
            s = 0.0
        roll_std.append(s)

    # Upper and lower envelopes (1-sigma)
    upper_env = [roll_mean[i] + roll_std[i] for i in range(n)]
    lower_env = [roll_mean[i] - roll_std[i] for i in range(n)]

    # Drift rate: slope of rolling mean
    x_vals = list(range(n))
    fit = _linear_fit(x_vals, roll_mean)
    drift_rate = fit["slope"]

    # Overall process sigma
    overall_sigma = _std(y)

    # Drift severity coloring
    if overall_sigma > 0:
        drift_ratio = abs(drift_rate * window) / overall_sigma
    else:
        drift_ratio = 0.0

    if drift_ratio < 0.5:
        drift_color = STATUS_GREEN
        drift_label = "Low drift"
    elif drift_ratio < 1.0:
        drift_color = STATUS_AMBER
        drift_label = "Moderate drift"
    else:
        drift_color = STATUS_RED
        drift_label = "High drift"

    # Add upper envelope
    spec.add_trace(
        trace.x, upper_env,
        name="+1\u03c3",
        trace_type="line",
        color=rgba(drift_color, 0.0),
        dash="dotted",
        width=0.5,
        opacity=0.3,
    )

    # Add lower envelope (with fill to upper)
    spec.add_trace(
        trace.x, lower_env,
        name="-1\u03c3",
        trace_type="line",
        color=rgba(drift_color, 0.0),
        dash="dotted",
        width=0.5,
        fill="tonexty",
        opacity=0.1,
    )

    # Add rolling mean
    spec.add_trace(
        trace.x, roll_mean,
        name="Rolling Mean",
        trace_type="line",
        color=drift_color,
        dash="dashed",
        width=2.0,
        opacity=0.8,
    )

    # Drift annotation
    spec.annotations.append({
        "x": 0.02,
        "y": 0.95,
        "text": f"{drift_label}: {drift_rate:+.4f}/step",
        "color": drift_color,
        "font_size": 10,
    })

    return spec


def spc_forecast(
    data_points: list[float],
    ucl: float,
    cl: float,
    lcl: float,
    horizon: int = 20,
    title: str = "SPC Forecast",
) -> ChartSpec:
    """All-in-one SPC forecast chart.

    Creates a complete control chart with historical data, control limits,
    forecast cone, time-to-breach annotations, drift rate, and Western
    Electric rule violation counts.

    Args:
        data_points: Historical data values.
        ucl: Upper control limit.
        cl: Center line.
        lcl: Lower control limit.
        horizon: Number of points to forecast.
        title: Chart title.

    Returns:
        Complete ChartSpec with forecast overlay.
    """
    from ..charts.control import control_chart

    n = len(data_points)
    if n < 2:
        return control_chart(
            data_points=data_points, ucl=ucl, cl=cl, lcl=lcl, title=title,
        )

    # Detect OOC points
    ooc = [i for i, v in enumerate(data_points) if v > ucl or v < lcl]

    # Build base control chart
    spec = control_chart(
        data_points=data_points,
        ucl=ucl,
        cl=cl,
        lcl=lcl,
        ooc_indices=ooc,
        title=title,
        chart_type_label="SPC Forecast",
    )

    # Add forecast cone
    spec = forecast_overlay(spec, horizon=horizon, method="ets")

    # Time-to-breach for UCL and LCL
    ttb_ucl = time_to_breach(data_points, ucl, method="ets")
    ttb_lcl = time_to_breach(data_points, lcl, method="ets")

    # Annotate breach estimates
    annotations_y = 0.90
    if ttb_ucl["estimated_steps"] is not None:
        spec.annotations.append({
            "x": 0.02,
            "y": annotations_y,
            "text": f"UCL breach in ~{ttb_ucl['estimated_steps']} steps (conf: {ttb_ucl['confidence']:.0%})",
            "color": STATUS_RED,
            "font_size": 9,
        })
        annotations_y -= 0.06

    if ttb_lcl["estimated_steps"] is not None:
        spec.annotations.append({
            "x": 0.02,
            "y": annotations_y,
            "text": f"LCL breach in ~{ttb_lcl['estimated_steps']} steps (conf: {ttb_lcl['confidence']:.0%})",
            "color": STATUS_RED,
            "font_size": 9,
        })
        annotations_y -= 0.06

    # Drift rate
    trend = _current_trend(data_points)
    spec.annotations.append({
        "x": 0.02,
        "y": annotations_y,
        "text": f"Drift: {trend:+.4f}/step",
        "color": STATUS_AMBER,
        "font_size": 9,
    })
    annotations_y -= 0.06

    # Western Electric rule violations
    we_count = _western_electric_count(data_points, ucl, cl, lcl)
    spec.annotations.append({
        "x": 0.02,
        "y": annotations_y,
        "text": f"WE violations: {we_count}",
        "color": STATUS_RED if we_count > 0 else STATUS_GREEN,
        "font_size": 9,
    })

    return spec


def capability_forecast(
    data_points: list[float],
    usl: float,
    lsl: float,
    horizon: int = 20,
    window: int = 30,
) -> dict:
    """Project how Cpk will evolve if current trends continue.

    Uses a rolling window to track process mean and std over time,
    then extrapolates forward to predict future Cpk values.

    Args:
        data_points: Historical measurements.
        usl: Upper specification limit.
        lsl: Lower specification limit.
        horizon: Number of future steps to project.
        window: Rolling window size for Cpk calculation.

    Returns:
        Dict with current_cpk, projected_cpk, steps_to_incapable,
        steps_to_critical, and recommendation.
    """
    n = len(data_points)
    if n < 3:
        return {
            "current_cpk": 0.0,
            "projected_cpk": [],
            "steps_to_incapable": None,
            "steps_to_critical": None,
            "recommendation": "insufficient data",
        }

    spec_width = usl - lsl
    if spec_width <= 0:
        return {
            "current_cpk": 0.0,
            "projected_cpk": [],
            "steps_to_incapable": None,
            "steps_to_critical": None,
            "recommendation": "invalid specification limits",
        }

    # Calculate rolling Cpk values
    eff_window = min(window, n)
    cpk_history = []
    for i in range(eff_window - 1, n):
        w = data_points[i - eff_window + 1:i + 1]
        cpk = _cpk(w, usl, lsl)
        cpk_history.append(cpk)

    if len(cpk_history) < 2:
        current_cpk = cpk_history[0] if cpk_history else 0.0
        return {
            "current_cpk": round(current_cpk, 3),
            "projected_cpk": [],
            "steps_to_incapable": None,
            "steps_to_critical": None,
            "recommendation": "stable" if current_cpk >= 1.33 else "monitor",
        }

    current_cpk = cpk_history[-1]

    # Project Cpk forward using linear extrapolation of Cpk history
    fc, _, _ = _linear_forecast(cpk_history, horizon=horizon)
    projected_cpk = [round(v, 3) for v in fc]

    # Find steps to thresholds
    steps_incapable = None
    steps_critical = None
    for i, v in enumerate(projected_cpk):
        if steps_critical is None and v < 1.33:
            steps_critical = i + 1
        if steps_incapable is None and v < 1.0:
            steps_incapable = i + 1

    # Recommendation
    if current_cpk >= 1.33 and steps_critical is None:
        recommendation = "stable"
    elif current_cpk >= 1.33 and steps_critical is not None:
        recommendation = "monitor"
    elif current_cpk >= 1.0:
        recommendation = "monitor"
    else:
        recommendation = "intervene"

    return {
        "current_cpk": round(current_cpk, 3),
        "projected_cpk": projected_cpk,
        "steps_to_incapable": steps_incapable,
        "steps_to_critical": steps_critical,
        "recommendation": recommendation,
    }


# =========================================================================
# Helpers
# =========================================================================

def _find_first_trace(spec: ChartSpec) -> Trace | None:
    """Find the first Trace object in a ChartSpec."""
    for t in spec.traces:
        if isinstance(t, Trace) and t.y:
            return t
    return None


def _dispatch_forecast(
    y: list[float],
    method: str,
    horizon: int,
    confidence: float,
) -> tuple[list[float], list[float], list[float]]:
    """Dispatch to the appropriate forecasting engine."""
    if method == "ets":
        return _holt_winters(y, horizon=horizon, confidence=confidence)
    elif method == "linear":
        return _linear_forecast(y, horizon=horizon, confidence=confidence)
    elif method == "ewma":
        return _ewma_forecast(y, horizon=horizon, confidence=confidence)
    elif method == "drift":
        return _drift_forecast(y, horizon=horizon, confidence=confidence)
    else:
        raise ValueError(f"Unknown forecast method: {method!r}")


def _linear_fit(x: list[float], y: list[float]) -> dict:
    """Simple least-squares linear regression. Returns slope, intercept, r_squared."""
    n = len(x)
    if n < 2:
        return {"slope": 0.0, "intercept": y[0] if y else 0.0, "r_squared": 0.0}

    sx = sum(x)
    sy = sum(y)
    sxx = sum(xi ** 2 for xi in x)
    sxy = sum(xi * yi for xi, yi in zip(x, y))

    denom = n * sxx - sx ** 2
    if abs(denom) < 1e-12:
        return {"slope": 0.0, "intercept": sy / n, "r_squared": 0.0}

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n

    y_mean = sy / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {"slope": slope, "intercept": intercept, "r_squared": max(0, r_squared)}


def _std(values: list[float]) -> float:
    """Population standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def _z_score(confidence: float) -> float:
    """Approximate z-score for common confidence levels."""
    if confidence >= 0.99:
        return 2.576
    elif confidence >= 0.975:
        return 2.241
    elif confidence >= 0.95:
        return 1.96
    elif confidence >= 0.9:
        return 1.645
    elif confidence >= 0.8:
        return 1.282
    else:
        return 1.0


def _current_trend(y: list[float]) -> float:
    """Calculate the current trend (slope) from the data."""
    n = len(y)
    if n < 2:
        return 0.0
    # Use last min(20, n) points for recent trend
    recent = y[-min(20, n):]
    x = list(range(len(recent)))
    fit = _linear_fit(x, recent)
    return fit["slope"]


def _cpk(values: list[float], usl: float, lsl: float) -> float:
    """Calculate Cpk from a set of values."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    sigma = _std(values)
    if sigma == 0:
        # Perfect data: if inside spec, Cpk is "infinite" (cap at 10)
        if lsl <= mean <= usl:
            return 10.0
        return 0.0
    cpu = (usl - mean) / (3 * sigma)
    cpl = (mean - lsl) / (3 * sigma)
    return min(cpu, cpl)


def _western_electric_count(
    data: list[float],
    ucl: float,
    cl: float,
    lcl: float,
) -> int:
    """Count Western Electric rule violations.

    Rules checked:
    1. Any point beyond 3-sigma (beyond UCL/LCL)
    2. 2 of 3 consecutive points beyond 2-sigma (Zone A)
    3. 4 of 5 consecutive points beyond 1-sigma (Zone B)
    4. 8 consecutive points on one side of center line
    """
    n = len(data)
    if n < 2:
        return 0

    one_sigma = (ucl - cl) / 3 if ucl > cl else 1.0
    violations = 0

    # Rule 1: beyond 3-sigma
    for v in data:
        if v > ucl or v < lcl:
            violations += 1

    # Rule 2: 2 of 3 beyond 2-sigma
    zone_a_upper = cl + 2 * one_sigma
    zone_a_lower = cl - 2 * one_sigma
    for i in range(2, n):
        window = data[i - 2:i + 1]
        above = sum(1 for v in window if v > zone_a_upper)
        below = sum(1 for v in window if v < zone_a_lower)
        if above >= 2 or below >= 2:
            violations += 1

    # Rule 3: 4 of 5 beyond 1-sigma
    zone_b_upper = cl + one_sigma
    zone_b_lower = cl - one_sigma
    for i in range(4, n):
        window = data[i - 4:i + 1]
        above = sum(1 for v in window if v > zone_b_upper)
        below = sum(1 for v in window if v < zone_b_lower)
        if above >= 4 or below >= 4:
            violations += 1

    # Rule 4: 8 consecutive on same side
    for i in range(7, n):
        window = data[i - 7:i + 1]
        if all(v > cl for v in window) or all(v < cl for v in window):
            violations += 1

    return violations
