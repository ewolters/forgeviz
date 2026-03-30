"""Interactive/counterfactual chart support — sliders and what-if.

Python side: generates the spec with parameter ranges.
JS side: ForgeViz.slider() renders sliders that re-compute and re-render.

The key insight: the chart spec includes a `model` function definition
(as coefficients + factor ranges) that the JS renderer evaluates client-side
for instant updates. No server round-trip for slider interactions.
"""

from __future__ import annotations

from ..core.colors import STATUS_AMBER, STATUS_GREEN, get_color
from ..core.spec import ChartSpec


def slider_chart(
    factors: list[dict],
    model_coefficients: dict[str, float],
    response_name: str = "Response",
    title: str = "What-If Explorer",
) -> ChartSpec:
    """Chart spec with embedded model for client-side slider interaction.

    factors: [{name, low, high, current, unit, step}]
    model_coefficients: {Intercept, factor_name, factor*factor, factor^2, ...}

    The JS renderer reads `spec.interactive` and renders sliders.
    Moving a slider re-evaluates the model and updates the chart instantly.
    """
    spec = ChartSpec(title=title, chart_type="slider_chart", height=400)

    # Current prediction
    current_values = {f["name"]: f.get("current", (f["low"] + f["high"]) / 2) for f in factors}
    current_pred = _evaluate_model(model_coefficients, current_values)

    # Sweep the first factor for the initial view
    primary = factors[0]
    n_pts = 50
    step = (primary["high"] - primary["low"]) / n_pts
    sweep_x = [primary["low"] + i * step for i in range(n_pts + 1)]
    sweep_y = []
    for x in sweep_x:
        values = dict(current_values)
        values[primary["name"]] = x
        sweep_y.append(_evaluate_model(model_coefficients, values))

    spec.add_trace(sweep_x, sweep_y, name=f"{response_name} vs {primary['name']}", trace_type="line", color=get_color(0), width=2)
    spec.add_trace([current_values[primary["name"]]], [current_pred], name="Current", trace_type="scatter", color=STATUS_AMBER, marker_size=10)

    # Embed the model for JS client-side evaluation
    spec.annotations.append({
        "x": 0.02, "y": 0.95,
        "text": f"Predicted {response_name}: {current_pred:.4f}",
        "color": STATUS_GREEN,
        "font_size": 13,
    })

    # Store interactive config in metadata (the JS renderer reads this)
    spec.__dict__["interactive"] = {
        "type": "slider",
        "factors": factors,
        "coefficients": model_coefficients,
        "response_name": response_name,
        "current_values": current_values,
        "current_prediction": current_pred,
    }

    return spec


def counterfactual_comparison(
    actual_x: list[float],
    actual_y: list[float],
    predicted_y: list[float],
    title: str = "Counterfactual: Predicted vs Actual",
    x_label: str = "Observation",
    y_label: str = "Value",
) -> ChartSpec:
    """Compare model prediction against actual post-change observations.

    Shows: did the change produce the effect the model predicted?
    """
    spec = ChartSpec(
        title=title, chart_type="counterfactual",
        x_axis={"label": x_label},
        y_axis={"label": y_label},
    )

    spec.add_trace(actual_x, actual_y, name="Actual", trace_type="line", color=get_color(0), width=2, marker_size=4)
    spec.add_trace(actual_x, predicted_y, name="Predicted", trace_type="line", color=get_color(1), width=2, dash="dashed")

    # Residuals as shaded area between
    for i in range(min(len(actual_y), len(predicted_y))):
        diff = actual_y[i] - predicted_y[i]
        color = STATUS_GREEN if abs(diff) < abs(predicted_y[i]) * 0.1 else STATUS_AMBER
        spec.annotations.append({
            "x": actual_x[i] if i < len(actual_x) else i,
            "y": (actual_y[i] + predicted_y[i]) / 2,
            "text": "",
            "color": color,
            "font_size": 1,
        })

    # Summary statistics
    if actual_y and predicted_y:
        n = min(len(actual_y), len(predicted_y))
        mape = sum(abs(actual_y[i] - predicted_y[i]) / abs(actual_y[i]) if actual_y[i] != 0 else 0 for i in range(n)) / n * 100
        bias = sum(actual_y[i] - predicted_y[i] for i in range(n)) / n

        spec.annotations.append({"x": 0.02, "y": 0.95, "text": f"MAPE: {mape:.1f}%", "color": STATUS_GREEN if mape < 10 else STATUS_AMBER, "font_size": 11})
        spec.annotations.append({"x": 0.02, "y": 0.88, "text": f"Bias: {bias:+.4f}", "color": STATUS_GREEN if abs(bias) < 0.1 else STATUS_AMBER, "font_size": 11})

    return spec


def sensitivity_tornado(
    factors: list[str],
    low_impacts: list[float],
    high_impacts: list[float],
    baseline: float,
    title: str = "Sensitivity Analysis (Tornado)",
) -> ChartSpec:
    """Tornado chart showing sensitivity of response to each factor.

    Factors sorted by total impact range (most sensitive at top).
    """
    # Sort by total impact
    impacts = [(f, abs(h - lo), lo, h) for f, lo, h in zip(factors, low_impacts, high_impacts)]
    impacts.sort(key=lambda x: x[1], reverse=True)

    sorted_factors = [i[0] for i in impacts]
    sorted_low = [i[2] for i in impacts]
    sorted_high = [i[3] for i in impacts]

    spec = ChartSpec(
        title=title, chart_type="tornado",
        x_axis={"label": "Response Value"},
        y_axis={"label": ""},
        height=max(200, len(factors) * 35 + 80),
    )

    # Low side bars (left of baseline)
    spec.add_trace(sorted_factors, sorted_low, name="Low Setting", trace_type="bar", color=get_color(8), opacity=0.7)
    # High side bars (right of baseline)
    spec.add_trace(sorted_factors, sorted_high, name="High Setting", trace_type="bar", color=get_color(0), opacity=0.7)

    # Baseline reference
    spec.add_reference_line(baseline, axis="x", color="#ffffff", dash="solid", label=f"Baseline: {baseline:.3f}")

    return spec


def _evaluate_model(coefficients: dict[str, float], values: dict[str, float]) -> float:
    """Evaluate a regression model at given factor values."""
    pred = coefficients.get("Intercept", 0)
    names = list(values.keys())

    # Main effects
    for name, val in values.items():
        pred += coefficients.get(name, 0) * val

    # Interactions
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            term = f"{names[i]}*{names[j]}"
            pred += coefficients.get(term, 0) * values[names[i]] * values[names[j]]

    # Quadratic
    for name, val in values.items():
        term = f"{name}^2"
        pred += coefficients.get(term, 0) * val ** 2

    return pred
