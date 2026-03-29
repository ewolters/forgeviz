"""Tests for ForgeViz chart builders and renderers."""

import json

import pytest

from forgeviz.core.spec import ChartSpec, render
from forgeviz.charts.control import control_chart, from_spc_result
from forgeviz.charts.distribution import box_plot, histogram
from forgeviz.charts.effects import main_effects_plot, normal_probability_plot, pareto_of_effects
from forgeviz.charts.scatter import pareto, scatter
from forgeviz.charts.time_series import capacity_loading, forecast_vs_actual, inventory_position


class TestChartSpec:
    def test_create_empty(self):
        spec = ChartSpec(title="Test")
        assert spec.title == "Test"
        assert len(spec.traces) == 0

    def test_add_trace(self):
        spec = ChartSpec()
        spec.add_trace([1, 2, 3], [4, 5, 6], name="Data")
        assert len(spec.traces) == 1
        assert spec.traces[0].y == [4, 5, 6]

    def test_to_dict(self):
        spec = ChartSpec(title="Test")
        spec.add_trace([1], [2])
        d = spec.to_dict()
        assert d["title"] == "Test"
        assert len(d["traces"]) == 1

    def test_to_json(self):
        spec = ChartSpec(title="Test")
        j = spec.to_json()
        assert '"title": "Test"' in j

    def test_render_dict(self):
        spec = ChartSpec()
        result = render(spec, format="dict")
        assert isinstance(result, dict)


class TestControlChart:
    def test_basic(self):
        data = [23.1, 22.8, 23.4, 22.9, 23.0, 24.1, 22.5, 23.2, 22.7, 23.1]
        spec = control_chart(data, ucl=24.0, cl=23.0, lcl=22.0)
        assert spec.chart_type == "control_chart"
        assert len(spec.traces) >= 1
        assert len(spec.reference_lines) >= 3  # UCL, CL, LCL

    def test_with_ooc(self):
        data = [23.0] * 10
        data[5] = 25.0  # OOC
        spec = control_chart(data, ucl=24.0, cl=23.0, lcl=22.0, ooc_indices=[5])
        assert len(spec.markers) >= 1

    def test_with_spec_limits(self):
        data = [23.0] * 5
        spec = control_chart(data, ucl=24.0, cl=23.0, lcl=22.0, usl=25.0, lsl=21.0)
        assert len(spec.reference_lines) >= 5  # UCL, CL, LCL, USL, LSL

    def test_from_spc_result(self):
        """Test integration with forgespc ControlChartResult."""
        try:
            from forgespc.charts import individuals_moving_range_chart
            result = individuals_moving_range_chart([23.1, 22.8, 23.4, 22.9, 23.0] * 5)
            spec = from_spc_result(result)
            assert spec.chart_type == "control_chart"
            assert len(spec.traces) >= 1
        except ImportError:
            pytest.skip("forgespc not installed")


class TestHistogram:
    def test_basic(self):
        data = [1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        spec = histogram(data, bins=5)
        assert spec.chart_type == "histogram"
        assert len(spec.traces) >= 1

    def test_with_normal_overlay(self):
        import random
        random.seed(42)
        data = [random.gauss(50, 5) for _ in range(100)]
        spec = histogram(data, bins=15, show_normal=True)
        assert len(spec.traces) >= 2  # bars + normal curve

    def test_with_spec_limits(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        spec = histogram(data, usl=4.5, lsl=1.5, target=3.0)
        assert len(spec.reference_lines) >= 3


class TestScatter:
    def test_basic(self):
        spec = scatter([1, 2, 3, 4], [2, 4, 5, 8])
        assert spec.chart_type == "scatter"

    def test_with_regression(self):
        spec = scatter([1, 2, 3, 4, 5], [2.1, 3.9, 6.2, 7.8, 10.1], show_regression=True)
        assert len(spec.traces) >= 2  # data + regression line

    def test_pareto(self):
        spec = pareto(["A", "B", "C", "D"], [40, 30, 20, 10])
        assert spec.chart_type == "pareto"
        assert len(spec.traces) >= 2  # bars + cumulative line


class TestEffects:
    def test_main_effects(self):
        spec = main_effects_plot(["Temp", "Pressure", "Speed"], {"Temp": 4.5, "Pressure": 2.1, "Speed": 0.3})
        assert spec.chart_type == "main_effects"

    def test_pareto_of_effects(self):
        spec = pareto_of_effects({"Temp": 4.5, "Pressure": -2.1, "Speed": 0.3})
        assert spec.chart_type == "pareto_effects"
        # Should be sorted by absolute value
        assert spec.traces[0].y[0] == 4.5  # Temp first

    def test_normal_probability(self):
        import random
        random.seed(42)
        data = [random.gauss(0, 1) for _ in range(30)]
        spec = normal_probability_plot(data)
        assert spec.chart_type == "normal_prob"
        assert len(spec.traces) >= 2  # data + reference line


class TestTimeSeries:
    def test_forecast_vs_actual(self):
        dates = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        actual = [100, 110, 105, 120, 115, 125]
        forecast = [100, 108, 110, 115, 118, 122]
        spec = forecast_vs_actual(dates, actual, forecast)
        assert spec.chart_type == "forecast"
        assert len(spec.traces) >= 2

    def test_inventory_position(self):
        periods = ["W1", "W2", "W3", "W4", "W5"]
        on_hand = [500, 350, 200, 50, -20]
        spec = inventory_position(periods, on_hand, reorder_point=150, safety_stock=50)
        assert len(spec.markers) >= 1  # stockout marker

    def test_capacity_loading(self):
        periods = ["Jan", "Feb", "Mar"]
        spec = capacity_loading(periods, available=[160, 160, 160], loaded=[140, 170, 150])
        assert len(spec.markers) >= 1  # overload in Feb


class TestPlotlyRenderer:
    def test_basic_render(self):
        from forgeviz.renderers.plotly import to_plotly

        spec = control_chart([1, 2, 3, 4, 5], ucl=5, cl=3, lcl=1)
        result = to_plotly(spec)
        assert "data" in result
        assert "layout" in result
        assert len(result["data"]) >= 1

    def test_has_shapes_for_reference_lines(self):
        from forgeviz.renderers.plotly import to_plotly

        spec = ChartSpec()
        spec.add_trace([1, 2], [3, 4])
        spec.add_reference_line(3.5, label="Threshold")
        result = to_plotly(spec)
        assert len(result["layout"]["shapes"]) >= 1


class TestSVGRenderer:
    def test_basic_render(self):
        from forgeviz.renderers.svg import to_svg

        spec = control_chart([23.1, 22.8, 23.4, 22.9, 23.0], ucl=24, cl=23, lcl=22)
        svg = to_svg(spec)
        assert svg.startswith("<svg")
        assert "</svg>" in svg
        assert "Control Chart" in svg

    def test_empty_chart(self):
        from forgeviz.renderers.svg import to_svg

        spec = ChartSpec(title="Empty")
        svg = to_svg(spec)
        assert "No data" in svg

    def test_histogram_svg(self):
        from forgeviz.renderers.svg import to_svg

        spec = histogram([1, 2, 3, 4, 5, 6, 7, 8], bins=4)
        svg = to_svg(spec)
        assert "<rect" in svg  # bars are rects

    def test_scatter_svg(self):
        from forgeviz.renderers.svg import to_svg

        spec = scatter([1, 2, 3], [4, 5, 6])
        svg = to_svg(spec)
        assert "<circle" in svg  # scatter points are circles


class TestRenderFunction:
    def test_dict_format(self):
        spec = ChartSpec(title="Test")
        result = render(spec, format="dict")
        assert result["title"] == "Test"

    def test_json_format(self):
        spec = ChartSpec(title="Test")
        result = render(spec, format="json")
        assert json.loads(result)["title"] == "Test"

    def test_plotly_format(self):
        spec = ChartSpec()
        spec.add_trace([1], [2])
        result = render(spec, format="plotly")
        assert "data" in result

    def test_svg_format(self):
        spec = ChartSpec()
        spec.add_trace([1, 2], [3, 4])
        result = render(spec, format="svg")
        assert "<svg" in result
