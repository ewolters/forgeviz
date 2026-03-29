"""DOE effect charts — main effects, interaction, Pareto of effects, normal probability."""

from __future__ import annotations

import math

from ..core.colors import STATUS_RED, get_color
from ..core.spec import ChartSpec


def main_effects_plot(
    factor_names: list[str],
    effects: dict[str, float],
    title: str = "Main Effects Plot",
) -> ChartSpec:
    """Main effects plot — effect size per factor."""
    spec = ChartSpec(title=title, chart_type="main_effects", x_axis={"label": "Factor"}, y_axis={"label": "Effect"})

    names = [f for f in factor_names if f in effects]
    values = [effects[f] for f in names]

    spec.add_trace(names, values, name="Effect", trace_type="bar", color=get_color(0))
    spec.add_reference_line(0, color="#888", dash="solid")

    return spec


def interaction_plot(
    factor_a: str,
    factor_b: str,
    levels_a: list[float],
    means_b_low: list[float],
    means_b_high: list[float],
    title: str = "",
) -> ChartSpec:
    """Two-factor interaction plot."""
    spec = ChartSpec(
        title=title or f"Interaction: {factor_a} × {factor_b}",
        chart_type="interaction",
        x_axis={"label": factor_a},
        y_axis={"label": "Response"},
    )

    spec.add_trace(levels_a, means_b_low, name=f"{factor_b} Low", trace_type="line", color=get_color(0), width=2, marker_size=6)
    spec.add_trace(levels_a, means_b_high, name=f"{factor_b} High", trace_type="line", color=get_color(1), width=2, marker_size=6)

    return spec


def pareto_of_effects(
    effects: dict[str, float],
    alpha: float = 0.05,
    residual_df: int = 0,
    residual_ms: float = 0,
    title: str = "Pareto of Effects",
) -> ChartSpec:
    """Pareto chart of absolute effect sizes with significance line."""
    sorted_effects = sorted(effects.items(), key=lambda x: abs(x[1]), reverse=True)
    names = [e[0] for e in sorted_effects]
    abs_effects = [abs(e[1]) for e in sorted_effects]

    spec = ChartSpec(title=title, chart_type="pareto_effects", x_axis={"label": ""}, y_axis={"label": "|Effect|"})
    spec.add_trace(names, abs_effects, name="|Effect|", trace_type="bar", color=get_color(0))

    # Significance line (t-critical × SE)
    if residual_df > 0 and residual_ms > 0:
        try:
            from scipy import stats
            t_crit = stats.t.ppf(1 - alpha / 2, residual_df)
            se_effect = math.sqrt(4 * residual_ms / (2 ** len(effects)))
            sig_line = t_crit * se_effect
            spec.add_reference_line(sig_line, color=STATUS_RED, dash="dashed", label=f"Significance (α={alpha})")
        except ImportError:
            pass  # scipy not available — significance line omitted (forgeviz has zero deps)

    return spec


def normal_probability_plot(
    values: list[float],
    title: str = "Normal Probability Plot",
) -> ChartSpec:
    """Normal probability plot — ordered data vs expected normal quantiles."""
    n = len(values)
    if n < 3:
        return ChartSpec(title=title, chart_type="normal_prob")

    sorted_vals = sorted(values)

    # Expected normal quantiles (Filliben approximation)
    expected = []
    for i in range(n):
        p = (i + 0.5) / n
        # Rational approximation for normal quantile
        if p < 0.5:
            t = math.sqrt(-2 * math.log(p))
            z = -(t - (2.515517 + 0.802853 * t + 0.010328 * t * t) / (1 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t))
        else:
            t = math.sqrt(-2 * math.log(1 - p))
            z = t - (2.515517 + 0.802853 * t + 0.010328 * t * t) / (1 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t)
        expected.append(z)

    spec = ChartSpec(
        title=title, chart_type="normal_prob",
        x_axis={"label": "Normal Quantile"},
        y_axis={"label": "Ordered Value"},
    )

    spec.add_trace(expected, sorted_vals, name="Data", trace_type="scatter", color=get_color(0), marker_size=5)

    # Reference line (perfect normal)
    if len(expected) >= 2:
        x_range = [expected[0], expected[-1]]
        mean = sum(values) / n
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
        y_range = [mean + z * std for z in x_range]
        spec.add_trace(x_range, y_range, name="Normal Reference", trace_type="line", color="#888", dash="dashed", width=1)

    return spec
