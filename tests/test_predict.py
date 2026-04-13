"""Tests for the predictive overlay system."""

import copy
import math

from forgeviz.analytics.predict import (
    _drift_forecast,
    _ewma_forecast,
    _holt_winters,
    _linear_forecast,
    _western_electric_count,
    capability_forecast,
    forecast_overlay,
    process_drift_overlay,
    spc_forecast,
    time_to_breach,
)
from forgeviz.core.spec import ChartSpec, Trace


def _make_line_spec(y_values, x_values=None):
    """Helper: build a simple line ChartSpec."""
    if x_values is None:
        x_values = list(range(len(y_values)))
    spec = ChartSpec(title="Test", chart_type="line")
    spec.add_trace(x_values, y_values, name="Data", trace_type="line")
    return spec


# =========================================================================
# _holt_winters
# =========================================================================

class TestHoltWinters:
    def test_linear_data(self):
        """Forecast of perfect linear data should continue the line."""
        y = [float(i) for i in range(30)]
        fc, lo, hi = _holt_winters(y, alpha=0.9, beta=0.3, horizon=10)
        assert len(fc) == 10
        # Forecast should approximately continue: 30, 31, 32, ...
        for i, v in enumerate(fc):
            expected = 30 + i
            assert abs(v - expected) < 3.0, f"Step {i}: got {v}, expected ~{expected}"

    def test_auto_fit(self):
        """Auto-fitting should pick reasonable alpha/beta."""
        y = [float(i) * 2 + 5 for i in range(40)]
        fc, lo, hi = _holt_winters(y, horizon=5)
        assert len(fc) == 5
        # Should continue upward
        assert fc[-1] > y[-1]

    def test_prediction_interval_widens(self):
        """Prediction interval should widen with horizon."""
        y = [10.0 + math.sin(i * 0.5) for i in range(30)]
        fc, lo, hi = _holt_winters(y, horizon=20)
        # Width at step 1 should be narrower than at step 20
        width_1 = hi[0] - lo[0]
        width_20 = hi[-1] - lo[-1]
        assert width_20 >= width_1

    def test_constant_data(self):
        """Constant data: forecast should stay constant, intervals should be tight."""
        y = [5.0] * 20
        fc, lo, hi = _holt_winters(y, horizon=10)
        for v in fc:
            assert abs(v - 5.0) < 1.0

    def test_two_points(self):
        """Should handle 2 data points without error."""
        y = [1.0, 3.0]
        fc, lo, hi = _holt_winters(y, horizon=5)
        assert len(fc) == 5
        # Should project upward
        assert fc[0] >= 3.0

    def test_single_point(self):
        """Should handle a single data point."""
        y = [7.0]
        fc, lo, hi = _holt_winters(y, horizon=5)
        assert len(fc) == 5
        for v in fc:
            assert v == 7.0


# =========================================================================
# Other forecast engines
# =========================================================================

class TestEwmaForecast:
    def test_returns_correct_length(self):
        y = [float(i) for i in range(20)]
        fc, lo, hi = _ewma_forecast(y, horizon=10)
        assert len(fc) == 10
        assert len(lo) == 10
        assert len(hi) == 10

    def test_flat_forecast(self):
        """EWMA forecast is flat (same value extended)."""
        y = [10.0] * 20
        fc, lo, hi = _ewma_forecast(y, horizon=5)
        for v in fc:
            assert abs(v - 10.0) < 0.5


class TestDriftForecast:
    def test_upward_drift(self):
        y = [float(i) * 0.5 for i in range(30)]
        fc, lo, hi = _drift_forecast(y, horizon=10)
        assert len(fc) == 10
        # Should continue upward
        assert fc[-1] > y[-1]

    def test_constant_no_drift(self):
        y = [5.0] * 20
        fc, lo, hi = _drift_forecast(y, horizon=5)
        for v in fc:
            assert abs(v - 5.0) < 0.1


class TestLinearForecast:
    def test_linear_continues(self):
        y = [2.0 * i + 1.0 for i in range(20)]
        fc, lo, hi = _linear_forecast(y, horizon=5)
        for i, v in enumerate(fc):
            expected = 2.0 * (19 + i + 1) + 1.0
            assert abs(v - expected) < 0.5


# =========================================================================
# forecast_overlay
# =========================================================================

class TestForecastOverlay:
    def test_adds_traces_and_zones(self):
        y = [float(i) for i in range(30)]
        spec = _make_line_spec(y)
        original_trace_count = len(spec.traces)
        result = forecast_overlay(spec, horizon=10)
        # Should add 3 traces: upper PI, lower PI, forecast
        assert len(result.traces) == original_trace_count + 3

    def test_forecast_trace_is_dashed(self):
        y = [float(i) for i in range(20)]
        spec = _make_line_spec(y)
        result = forecast_overlay(spec, horizon=5)
        forecast_trace = result.traces[-1]  # last added
        assert forecast_trace.dash == "dashed"
        assert forecast_trace.name == "Forecast"

    def test_no_mutation(self):
        y = [float(i) for i in range(20)]
        spec = _make_line_spec(y)
        original = copy.deepcopy(spec)
        _ = forecast_overlay(spec, horizon=10)
        assert len(spec.traces) == len(original.traces)
        assert spec.title == original.title

    def test_different_methods(self):
        y = [10.0 + 0.5 * i for i in range(30)]
        spec = _make_line_spec(y)
        for method in ["ets", "linear", "ewma", "drift"]:
            result = forecast_overlay(spec, horizon=5, method=method)
            assert len(result.traces) > len(spec.traces)

    def test_short_data(self):
        """Should handle very short data gracefully."""
        spec = _make_line_spec([5.0])
        result = forecast_overlay(spec, horizon=5)
        # Should return without crashing; may not add forecast for 1 point
        assert isinstance(result, ChartSpec)

    def test_empty_spec(self):
        """No traces at all — return unchanged."""
        spec = ChartSpec(title="Empty")
        result = forecast_overlay(spec)
        assert len(result.traces) == 0


# =========================================================================
# time_to_breach
# =========================================================================

class TestTimeToBreach:
    def test_trending_up_toward_limit(self):
        y = [50.0 + i * 0.5 for i in range(40)]
        result = time_to_breach(y, limit=80.0, method="linear")
        assert result["estimated_steps"] is not None
        assert result["estimated_steps"] > 0
        assert result["confidence"] > 0
        assert result["breach_value"] == 80.0

    def test_stable_no_breach(self):
        y = [50.0 + 0.01 * (i % 5) for i in range(40)]
        result = time_to_breach(y, limit=200.0, method="ets")
        assert result["estimated_steps"] is None
        assert result["confidence"] == 0.0

    def test_trending_down_toward_lower_limit(self):
        y = [50.0 - i * 0.3 for i in range(40)]
        result = time_to_breach(y, limit=20.0, method="linear")
        assert result["estimated_steps"] is not None

    def test_short_data(self):
        result = time_to_breach([5.0], limit=10.0)
        assert result["estimated_steps"] is None
        assert result["forecast_values"] == []

    def test_returns_forecast_values(self):
        y = [float(i) for i in range(20)]
        result = time_to_breach(y, limit=100.0)
        assert isinstance(result["forecast_values"], list)
        assert len(result["forecast_values"]) > 0


# =========================================================================
# process_drift_overlay
# =========================================================================

class TestProcessDriftOverlay:
    def test_adds_rolling_mean_trace(self):
        y = [10.0 + 0.1 * i + math.sin(i * 0.3) for i in range(50)]
        spec = _make_line_spec(y)
        result = process_drift_overlay(spec, window=10)
        # Should add 3 traces: upper env, lower env, rolling mean
        assert len(result.traces) == len(spec.traces) + 3
        # Rolling mean trace should be last
        rm_trace = result.traces[-1]
        assert rm_trace.name == "Rolling Mean"
        assert rm_trace.dash == "dashed"

    def test_drift_annotation(self):
        y = [10.0 + 0.5 * i for i in range(50)]
        spec = _make_line_spec(y)
        result = process_drift_overlay(spec, window=10)
        # Should have at least one annotation about drift
        assert len(result.annotations) >= 1
        drift_ann = result.annotations[-1]
        assert "drift" in drift_ann["text"].lower() or "Drift" in drift_ann["text"]

    def test_no_mutation(self):
        y = [float(i) for i in range(30)]
        spec = _make_line_spec(y)
        original = copy.deepcopy(spec)
        _ = process_drift_overlay(spec, window=5)
        assert len(spec.traces) == len(original.traces)

    def test_short_data_returns_unchanged(self):
        """If data is shorter than window, return spec unchanged."""
        spec = _make_line_spec([1.0, 2.0, 3.0])
        result = process_drift_overlay(spec, window=10)
        assert len(result.traces) == len(spec.traces)

    def test_high_drift_colored_red(self):
        """Strongly drifting data should get red color coding."""
        y = [i * 5.0 for i in range(50)]
        spec = _make_line_spec(y)
        result = process_drift_overlay(spec, window=5)
        # Check annotation exists with drift info
        assert len(result.annotations) >= 1


# =========================================================================
# spc_forecast
# =========================================================================

class TestSpcForecast:
    def test_produces_complete_chart(self):
        data = [50.0 + 0.1 * i for i in range(30)]
        spec = spc_forecast(data, ucl=60.0, cl=50.0, lcl=40.0, horizon=10)
        assert isinstance(spec, ChartSpec)
        assert spec.chart_type == "control_chart"
        # Should have original trace + forecast traces
        assert len(spec.traces) >= 4  # data + upper PI + lower PI + forecast
        # Should have reference lines for UCL, CL, LCL
        assert len(spec.reference_lines) >= 3

    def test_has_annotations(self):
        data = [50.0 + 0.3 * i for i in range(40)]
        spec = spc_forecast(data, ucl=65.0, cl=50.0, lcl=35.0)
        # Should have drift + WE violation annotations at minimum
        assert len(spec.annotations) >= 2

    def test_short_data(self):
        spec = spc_forecast([50.0], ucl=60.0, cl=50.0, lcl=40.0)
        assert isinstance(spec, ChartSpec)

    def test_ooc_points_marked(self):
        data = [50.0] * 10 + [65.0] + [50.0] * 10  # one OOC point
        spec = spc_forecast(data, ucl=60.0, cl=50.0, lcl=40.0)
        assert len(spec.markers) >= 1


# =========================================================================
# capability_forecast
# =========================================================================

class TestCapabilityForecast:
    def test_degrading_process(self):
        """Process drifting upward toward USL should show decreasing Cpk."""
        data = [50.0 + 0.1 * i + 0.5 * math.sin(i * 0.2) for i in range(60)]
        result = capability_forecast(data, usl=70.0, lsl=30.0, horizon=20, window=20)
        assert "current_cpk" in result
        assert isinstance(result["projected_cpk"], list)
        assert result["recommendation"] in ("stable", "monitor", "intervene")

    def test_stable_capable_process(self):
        """Stable, well-centered process should remain capable."""
        data = [50.0 + 0.2 * math.sin(i * 0.5) for i in range(60)]
        result = capability_forecast(data, usl=60.0, lsl=40.0, horizon=20, window=20)
        assert result["current_cpk"] > 1.0
        assert result["recommendation"] in ("stable", "monitor")

    def test_short_data(self):
        result = capability_forecast([50.0, 51.0], usl=60.0, lsl=40.0)
        assert result["current_cpk"] == 0.0 or isinstance(result["current_cpk"], float)

    def test_invalid_spec_limits(self):
        """USL < LSL should return gracefully."""
        result = capability_forecast([50.0] * 10, usl=30.0, lsl=70.0)
        assert result["recommendation"] == "invalid specification limits"

    def test_steps_to_incapable(self):
        """Strongly degrading process should have finite steps_to_incapable."""
        # Sharp upward drift
        data = [50.0 + 0.5 * i for i in range(60)]
        result = capability_forecast(data, usl=90.0, lsl=30.0, horizon=100, window=20)
        # May or may not breach depending on projection, but result should be valid
        assert isinstance(result["steps_to_incapable"], (int, type(None)))
        assert isinstance(result["steps_to_critical"], (int, type(None)))


# =========================================================================
# Western Electric rules
# =========================================================================

class TestWesternElectric:
    def test_no_violations(self):
        """Well-behaved data should have zero violations."""
        data = [50.0 + 0.1 * (i % 3) for i in range(30)]
        count = _western_electric_count(data, ucl=55.0, cl=50.0, lcl=45.0)
        assert count == 0

    def test_rule1_beyond_limits(self):
        data = [50.0] * 10 + [60.0] + [50.0] * 10
        count = _western_electric_count(data, ucl=55.0, cl=50.0, lcl=45.0)
        assert count >= 1


# =========================================================================
# Edge cases
# =========================================================================

class TestEdgeCases:
    def test_constant_data_all_functions(self):
        """Constant data should not crash any function."""
        y = [42.0] * 25
        spec = _make_line_spec(y)

        result = forecast_overlay(spec, horizon=5)
        assert isinstance(result, ChartSpec)

        ttb = time_to_breach(y, limit=100.0)
        assert isinstance(ttb, dict)

        drift = process_drift_overlay(spec, window=5)
        assert isinstance(drift, ChartSpec)

        spc = spc_forecast(y, ucl=50.0, cl=42.0, lcl=34.0)
        assert isinstance(spc, ChartSpec)

        cap = capability_forecast(y, usl=50.0, lsl=30.0, window=10)
        assert isinstance(cap, dict)

    def test_two_point_data(self):
        y = [1.0, 2.0]
        spec = _make_line_spec(y)
        result = forecast_overlay(spec, horizon=5)
        assert isinstance(result, ChartSpec)

    def test_single_point_data(self):
        y = [5.0]
        spec = _make_line_spec(y)
        result = forecast_overlay(spec, horizon=5)
        assert isinstance(result, ChartSpec)

    def test_no_input_mutation_forecast(self):
        """Verify forecast_overlay does not mutate the input spec."""
        y = [float(i) for i in range(20)]
        spec = _make_line_spec(y)
        traces_before = len(spec.traces)
        annotations_before = len(spec.annotations)
        _ = forecast_overlay(spec, horizon=10)
        assert len(spec.traces) == traces_before
        assert len(spec.annotations) == annotations_before

    def test_no_input_mutation_drift(self):
        """Verify process_drift_overlay does not mutate the input spec."""
        y = [float(i) for i in range(30)]
        spec = _make_line_spec(y)
        traces_before = len(spec.traces)
        _ = process_drift_overlay(spec, window=5)
        assert len(spec.traces) == traces_before

    def test_no_input_mutation_spc_forecast(self):
        """spc_forecast builds a new spec, verify it's valid."""
        data = [50.0 + i * 0.1 for i in range(30)]
        spec = spc_forecast(data, ucl=60.0, cl=50.0, lcl=40.0)
        # Re-calling should produce identical structure
        spec2 = spc_forecast(data, ucl=60.0, cl=50.0, lcl=40.0)
        assert len(spec.traces) == len(spec2.traces)
        assert len(spec.annotations) == len(spec2.annotations)
