"""Tests for bug fixes and previously untested exports."""

import pytest

from forgeviz.charts.generic import area, bar, gauge, grouped_bar, line, multi_line, pie, sparkline, stacked_bar
from forgeviz.charts.effects import interaction_plot
from forgeviz.charts.distribution import box_plot
from forgeviz.charts.diagnostic import residual_histogram
from forgeviz.renderers.svg import to_svg
from forgeviz.core.spec import ChartSpec, render


# =============================================================================
# Generic chart builders
# =============================================================================

class TestGenericCharts:
    def test_bar(self):
        spec = bar(["A", "B", "C"], [10, 20, 15], title="Simple Bar")
        assert spec.chart_type == "bar"
        assert len(spec.traces) == 1

    def test_grouped_bar(self):
        spec = grouped_bar(["Q1", "Q2", "Q3"], {"Revenue": [100, 120, 110], "Cost": [80, 90, 85]})
        assert len(spec.traces) == 2

    def test_stacked_bar(self):
        spec = stacked_bar(["A", "B"], {"X": [10, 20], "Y": [5, 15]})
        assert len(spec.traces) == 2

    def test_line(self):
        spec = line([1, 2, 3, 4], [10, 12, 11, 15], title="Line")
        assert spec.chart_type == "line"

    def test_multi_line(self):
        spec = multi_line([1, 2, 3], {"A": [10, 12, 11], "B": [8, 9, 10]})
        assert len(spec.traces) == 2

    def test_area(self):
        spec = area([1, 2, 3], [10, 15, 12])
        assert spec.chart_type == "area"
        assert len(spec.traces) == 2  # fill + line

    def test_pie(self):
        spec = pie(["A", "B", "C"], [40, 35, 25])
        assert spec.chart_type == "pie"
        assert spec.traces[0]["type"] == "pie"

    def test_gauge(self):
        spec = gauge(75, 0, 100, title="Score", thresholds=[(50, "red"), (80, "yellow"), (100, "green")])
        assert spec.chart_type == "gauge"
        assert len(spec.zones) == 3

    def test_sparkline(self):
        spec = sparkline([1, 3, 2, 5, 4, 6])
        assert spec.chart_type == "sparkline"
        assert spec.width == 120
        assert spec.height == 30


# =============================================================================
# SVG renderer fixes — categorical x-axis
# =============================================================================

class TestSVGCategorical:
    def test_bar_with_string_x(self):
        spec = bar(["Alpha", "Beta", "Gamma"], [10, 20, 15])
        svg = to_svg(spec)
        assert "<rect" in svg  # bars rendered
        assert "Alpha" in svg  # labels rendered
        assert "No data" not in svg

    def test_pareto_svg(self):
        from forgeviz.charts.scatter import pareto
        spec = pareto(["Defect A", "Defect B", "Defect C"], [40, 30, 10])
        svg = to_svg(spec)
        assert "Defect A" in svg
        assert "No data" not in svg

    def test_forecast_svg(self):
        from forgeviz.charts.time_series import forecast_vs_actual
        spec = forecast_vs_actual(["Jan", "Feb", "Mar"], [100, 110, 105], [100, 108, 112])
        svg = to_svg(spec)
        assert "No data" not in svg

    def test_inventory_svg(self):
        from forgeviz.charts.time_series import inventory_position
        spec = inventory_position(["W1", "W2", "W3"], [500, 300, 100])
        svg = to_svg(spec)
        assert "No data" not in svg

    def test_capacity_svg(self):
        from forgeviz.charts.time_series import capacity_loading
        spec = capacity_loading(["Jan", "Feb"], [160, 160], [140, 170])
        svg = to_svg(spec)
        assert "No data" not in svg

    def test_main_effects_svg(self):
        from forgeviz.charts.effects import main_effects_plot
        spec = main_effects_plot(["Temp", "Press"], {"Temp": 4.5, "Press": 2.1})
        svg = to_svg(spec)
        assert "Temp" in svg
        assert "No data" not in svg


# =============================================================================
# SVG renderer — dict traces (box, contour)
# =============================================================================

class TestSVGDictTraces:
    def test_box_plot_svg(self):
        spec = box_plot({"A": [1, 2, 3, 4, 5], "B": [2, 3, 4, 5, 6]})
        svg = to_svg(spec)
        assert "No data" not in svg
        # Should have box elements (rects)
        assert "<rect" in svg or "<line" in svg

    def test_contour_svg(self):
        from forgeviz.charts.surface import contour_plot
        spec = contour_plot([0, 1, 2], [0, 1, 2], [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        svg = to_svg(spec)
        assert "No data" not in svg
        assert "<rect" in svg  # heatmap cells


# =============================================================================
# Previously untested exports
# =============================================================================

class TestUntestedExports:
    def test_interaction_plot(self):
        spec = interaction_plot("Temp", "Pressure", [-1, 1], [10, 15], [12, 20])
        assert spec.chart_type == "interaction"
        assert len(spec.traces) == 2

    def test_box_plot(self):
        spec = box_plot({"Group A": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        assert spec.chart_type == "box_plot"

    def test_residual_histogram(self):
        spec = residual_histogram([0.1, -0.2, 0.3, -0.1, 0.05, -0.15, 0.2])
        assert "Residual" in spec.title


class TestBoxPlotQuantiles:
    """Verify box plot uses linear interpolation, not naive integer indexing."""

    def test_even_count_quantiles(self):
        # [1, 2, 3, 4, 5, 6] — correct Q1=2.25, Q2=3.5, Q3=4.75
        spec = box_plot({"test": [1, 2, 3, 4, 5, 6]})
        t = spec.traces[0]
        assert abs(t["q1"] - 2.25) < 0.01, f"Q1 should be 2.25, got {t['q1']}"
        assert abs(t["median"] - 3.5) < 0.01, f"Median should be 3.5, got {t['median']}"
        assert abs(t["q3"] - 4.75) < 0.01, f"Q3 should be 4.75, got {t['q3']}"

    def test_odd_count_quantiles(self):
        # [1, 2, 3, 4, 5] — correct Q1=2.0, Q2=3.0, Q3=4.0
        spec = box_plot({"test": [1, 2, 3, 4, 5]})
        t = spec.traces[0]
        assert abs(t["q1"] - 2.0) < 0.01
        assert abs(t["median"] - 3.0) < 0.01
        assert abs(t["q3"] - 4.0) < 0.01

    def test_two_points(self):
        spec = box_plot({"test": [10, 20]})
        t = spec.traces[0]
        assert abs(t["median"] - 15.0) < 0.01
        assert abs(t["q1"] - 12.5) < 0.01
        assert abs(t["q3"] - 17.5) < 0.01

    def test_single_point(self):
        spec = box_plot({"test": [42]})
        t = spec.traces[0]
        assert t["q1"] == 42
        assert t["median"] == 42
        assert t["q3"] == 42

    def test_iqr_and_whiskers(self):
        # [1,2,3,4,5,6,7,8,9,10,100] — 100 should be an outlier
        spec = box_plot({"test": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]})
        t = spec.traces[0]
        assert 100 in t["outliers"], "100 should be an outlier"
        assert t["whisker_high"] <= 20, "Whisker should not extend to outlier"


# =============================================================================
# Edge cases
# =============================================================================

class TestEdgeCases:
    def test_empty_data(self):
        spec = ChartSpec()
        svg = to_svg(spec)
        assert "No data" in svg

    def test_single_point(self):
        spec = line([1], [5], title="One Point")
        svg = to_svg(spec)
        assert "No data" not in svg

    def test_mismatched_lengths(self):
        spec = ChartSpec()
        spec.add_trace([1, 2, 3], [4, 5], trace_type="line")  # y shorter than x
        svg = to_svg(spec)
        assert "No data" not in svg  # should render what it can

    def test_normal_prob_few_points(self):
        from forgeviz.charts.effects import normal_probability_plot
        spec = normal_probability_plot([1])  # less than 3
        assert spec.chart_type == "normal_prob"
        assert len(spec.traces) == 0  # graceful empty

    def test_vegalite_removed(self):
        """Vega-Lite renderer should not exist."""
        with pytest.raises(ValueError, match="Unknown format"):
            render(ChartSpec(), format="vegalite")
