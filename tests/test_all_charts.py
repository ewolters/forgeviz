"""Tests for all remaining chart types — statistical, reliability, bayesian, interactive."""

import pytest

from forgeviz.charts.statistical import (
    bubble, dotplot, heatmap, individual_value_plot, interval_plot,
    mosaic, parallel_coordinates, scatter_matrix,
)
from forgeviz.charts.reliability import (
    hazard_function, reliability_block_diagram, survival_curve, weibull_probability_plot,
)
from forgeviz.charts.bayesian import (
    bayesian_acceptance, bayesian_capability, bayesian_changepoint, bayesian_control_chart,
)
from forgeviz.charts.interactive import (
    counterfactual_comparison, sensitivity_tornado, slider_chart,
)
from forgeviz.renderers.svg import to_svg


class TestStatistical:
    def test_heatmap(self):
        spec = heatmap(["A", "B", "C"], ["X", "Y"], [[1, 2, 3], [4, 5, 6]])
        assert spec.chart_type == "heatmap"

    def test_scatter_matrix(self):
        specs = scatter_matrix({"X": [1, 2, 3], "Y": [4, 5, 6]})
        assert len(specs) == 4  # 2x2 grid

    def test_individual_value_plot(self):
        spec = individual_value_plot({"A": [1, 2, 3, 4], "B": [2, 3, 4, 5]})
        assert spec.chart_type == "individual_value"

    def test_interval_plot(self):
        spec = interval_plot({"A": [1, 2, 3, 4, 5], "B": [2, 3, 4, 5, 6]})
        assert spec.chart_type == "interval_plot"

    def test_dotplot(self):
        spec = dotplot(["A", "B", "C"], [10, 20, 15])
        assert spec.chart_type == "dotplot"

    def test_bubble(self):
        spec = bubble([1, 2, 3], [4, 5, 6], [10, 20, 30])
        assert spec.chart_type == "bubble"

    def test_parallel_coordinates(self):
        spec = parallel_coordinates({"X": [1, 2, 3], "Y": [4, 5, 6], "Z": [7, 8, 9]})
        assert spec.chart_type == "parallel_coordinates"

    def test_mosaic(self):
        spec = mosaic({"Male": {"Yes": 30, "No": 20}, "Female": {"Yes": 35, "No": 15}})
        assert spec.chart_type == "mosaic"

    def test_heatmap_svg(self):
        spec = heatmap(["A", "B"], ["X", "Y"], [[1, 2], [3, 4]])
        svg = to_svg(spec)
        assert "No data" not in svg


class TestReliability:
    def test_weibull_plot(self):
        spec = weibull_probability_plot([100, 200, 300, 500, 800, 1200])
        assert spec.chart_type == "weibull_prob"
        assert len(spec.traces) >= 1

    def test_weibull_with_fit(self):
        spec = weibull_probability_plot([100, 200, 300], shape=2.0, scale=250)
        assert len(spec.traces) >= 2

    def test_hazard_function(self):
        spec = hazard_function(shape=2.5, scale=1000)
        assert spec.chart_type == "hazard"
        assert "wear-out" in spec.annotations[0]["text"]

    def test_hazard_infant_mortality(self):
        spec = hazard_function(shape=0.5, scale=1000)
        assert "infant mortality" in spec.annotations[0]["text"]

    def test_survival_curve(self):
        spec = survival_curve([10, 20, 30, 40, 50, 60, 70])
        assert spec.chart_type == "survival"
        assert len(spec.traces) >= 1

    def test_survival_with_censoring(self):
        spec = survival_curve([10, 20, 30, 40, 50], censored=[False, True, False, False, True])
        assert len(spec.traces) >= 2  # survival + censored markers

    def test_reliability_block(self):
        spec = reliability_block_diagram([
            {"name": "Motor", "reliability": 0.995},
            {"name": "Pump", "reliability": 0.98},
            {"name": "Valve", "reliability": 0.92},
        ])
        assert spec.chart_type == "reliability_block"


class TestBayesian:
    def test_bayesian_capability(self):
        import random
        random.seed(42)
        samples = [random.gauss(1.2, 0.15) for _ in range(1000)]
        spec = bayesian_capability(samples, cpk_mean=1.2, cpk_ci_lower=0.95, cpk_ci_upper=1.45)
        assert spec.chart_type == "bayesian_capability"
        assert len(spec.annotations) >= 1

    def test_bayesian_changepoint(self):
        data = [10 + i * 0.01 for i in range(50)] + [12 + i * 0.01 for i in range(50)]
        spec = bayesian_changepoint(data, changepoint_index=50, changepoint_probability=0.95, pre_mean=10.25, post_mean=12.25)
        assert spec.chart_type == "bayesian_changepoint"

    def test_bayesian_control(self):
        data = [23 + i * 0.01 for i in range(30)]
        ucl = [24.5 - i * 0.01 for i in range(30)]  # tightening limits
        cl = [23.0] * 30
        lcl = [21.5 + i * 0.01 for i in range(30)]
        spec = bayesian_control_chart(data, ucl, cl, lcl)
        assert spec.chart_type == "bayesian_control"

    def test_bayesian_acceptance(self):
        spec = bayesian_acceptance(lot_size=1000, sample_size=50, defectives_found=1)
        assert spec.chart_type == "bayesian_acceptance"
        assert any("Decision" in a["text"] for a in spec.annotations)


class TestInteractive:
    def test_slider_chart(self):
        factors = [
            {"name": "Temp", "low": 150, "high": 250, "current": 200},
            {"name": "Pressure", "low": 10, "high": 30, "current": 20},
        ]
        coefficients = {"Intercept": 50, "Temp": 0.3, "Pressure": 1.5, "Temp*Pressure": 0.02}
        spec = slider_chart(factors, coefficients, response_name="Yield")
        assert spec.chart_type == "slider_chart"
        assert hasattr(spec, "__dict__") and "interactive" in spec.__dict__
        assert spec.__dict__["interactive"]["type"] == "slider"

    def test_counterfactual(self):
        spec = counterfactual_comparison(
            [1, 2, 3, 4, 5],
            [10, 12, 11, 13, 14],
            [10, 11.5, 12, 12.5, 13],
        )
        assert spec.chart_type == "counterfactual"
        assert len(spec.traces) >= 2

    def test_tornado(self):
        spec = sensitivity_tornado(
            ["Temp", "Pressure", "Speed"],
            [48, 49, 49.5],  # low setting impact
            [52, 51, 50.5],  # high setting impact
            baseline=50,
        )
        assert spec.chart_type == "tornado"
        assert len(spec.traces) >= 2

    def test_counterfactual_svg(self):
        spec = counterfactual_comparison([1, 2, 3], [10, 12, 11], [10, 11, 12])
        svg = to_svg(spec)
        assert "No data" not in svg


class TestAllImports:
    def test_everything_importable(self):
        from forgeviz.charts import (
            # Generic
            bar, line, area, pie, gauge, sparkline, grouped_bar, stacked_bar, multi_line,
            # Control
            control_chart, from_spc_result,
            # Distribution
            histogram, box_plot,
            # Effects
            main_effects_plot, interaction_plot, pareto_of_effects, normal_probability_plot,
            # Scatter
            scatter, pareto,
            # Capability
            capability_histogram, capability_sixpack,
            # Gage
            gage_rr_components, gage_rr_by_part, gage_rr_by_operator,
            # Diagnostic
            residual_plot, qq_plot, cooks_distance, four_in_one,
            # Surface
            contour_plot, response_surface_from_model,
            # Time series
            forecast_vs_actual, inventory_position, capacity_loading,
            # Knowledge (OLR-001)
            knowledge_health_sparklines, maturity_trajectory, detection_ladder,
            evidence_timeline, proactive_reactive_gauge, ddmrp_buffer_status, yield_from_cpk_curve,
            # Statistical
            heatmap, scatter_matrix, individual_value_plot, interval_plot,
            dotplot, bubble, parallel_coordinates, mosaic,
            # Reliability
            weibull_probability_plot, hazard_function, survival_curve, reliability_block_diagram,
            # Bayesian
            bayesian_capability, bayesian_changepoint, bayesian_control_chart, bayesian_acceptance,
            # Interactive
            slider_chart, counterfactual_comparison, sensitivity_tornado,
        )
        # If we got here without ImportError, everything is importable
        assert True
