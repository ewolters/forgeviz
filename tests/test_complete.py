"""Tests for capability, gage, diagnostic, surface chart modules."""

import pytest

from forgeviz.charts.capability import capability_histogram, capability_sixpack
from forgeviz.charts.diagnostic import cooks_distance, four_in_one, qq_plot, residual_plot, residual_vs_order
from forgeviz.charts.gage import gage_rr_by_operator, gage_rr_by_part, gage_rr_components, gage_xbar_r
from forgeviz.charts.surface import contour_plot, response_surface_from_model, overlay_optimal_point
from forgeviz.charts.control import from_spc_result_pair


class TestCapability:
    def test_histogram(self):
        import random
        random.seed(42)
        data = [random.gauss(50, 2) for _ in range(100)]
        spec = capability_histogram(data, usl=56, lsl=44, cp=1.33, cpk=1.15)
        assert spec.chart_type == "capability_histogram"
        assert len(spec.annotations) >= 2

    def test_sixpack(self):
        import random
        random.seed(42)
        data = [random.gauss(50, 2) for _ in range(50)]
        specs = capability_sixpack(data, usl=56, lsl=44, cp=1.33, cpk=1.15, pp=1.30, ppk=1.10)
        assert len(specs) == 6
        assert specs[0].chart_type == "control_chart"
        assert specs[3].chart_type == "capability_histogram"
        assert specs[5].chart_type == "capability_summary"


class TestGage:
    def test_components(self):
        spec = gage_rr_components({"gage_rr": 15.2, "repeatability": 10.1, "reproducibility": 5.1, "part_to_part": 84.8})
        assert spec.chart_type == "gage_components"
        assert len(spec.reference_lines) >= 2

    def test_by_part(self):
        spec = gage_rr_by_part(
            ["P1", "P2", "P3"],
            {"P1": [10.1, 10.2, 10.3], "P2": [10.5, 10.6], "P3": [9.8, 9.9]},
        )
        assert spec.chart_type == "gage_by_part"

    def test_by_operator(self):
        spec = gage_rr_by_operator(
            ["Op1", "Op2"],
            {"Op1": [10.1, 10.2], "Op2": [10.3, 10.1]},
        )
        assert spec.chart_type == "gage_by_operator"

    def test_xbar_r(self):
        specs = gage_xbar_r(
            part_means=[10.1, 10.5, 9.8],
            part_ranges=[0.2, 0.1, 0.15],
            parts=["P1", "P2", "P3"],
            mean_ucl=10.8, mean_cl=10.13, mean_lcl=9.5,
            range_ucl=0.4, range_cl=0.15,
        )
        assert len(specs) == 2


class TestDiagnostic:
    def test_residual_plot(self):
        spec = residual_plot([1, 2, 3, 4, 5], [0.1, -0.2, 0.3, -0.1, 0.05])
        assert spec.chart_type == "residual"

    def test_qq_plot(self):
        import random
        random.seed(42)
        data = [random.gauss(0, 1) for _ in range(30)]
        spec = qq_plot(data)
        assert spec.chart_type == "qq_plot"

    def test_residual_vs_order(self):
        spec = residual_vs_order([0.1, -0.2, 0.3, -0.1, 0.05])
        assert spec.chart_type == "residual_order"

    def test_cooks_distance(self):
        spec = cooks_distance([0.01, 0.02, 1.5, 0.01, 0.03])
        assert spec.chart_type == "cooks_distance"
        assert len(spec.markers) >= 1  # influential point at index 2

    def test_four_in_one(self):
        specs = four_in_one([1, 2, 3, 4, 5], [0.1, -0.2, 0.3, -0.1, 0.05])
        assert len(specs) == 4


class TestSurface:
    def test_contour_plot(self):
        x = [-1, 0, 1]
        y = [-1, 0, 1]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        spec = contour_plot(x, y, z)
        assert spec.chart_type == "contour"
        assert spec.traces[0]["type"] == "contour"

    def test_from_model(self):
        coefficients = {"Intercept": 10, "A": 2, "B": 3, "A*B": 1.5, "A^2": -0.5}
        spec = response_surface_from_model(coefficients, "A", "B")
        assert spec.chart_type == "contour"
        assert len(spec.traces[0]["z"]) == 25  # grid_points default

    def test_overlay_optimal(self):
        x = [-1, 0, 1]
        y = [-1, 0, 1]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        spec = contour_plot(x, y, z)
        spec = overlay_optimal_point(spec, 0.5, 0.3, "Optimum")
        assert len(spec.annotations) >= 1


class TestSPCPair:
    def test_from_spc_result_pair(self):
        try:
            from forgespc.charts import xbar_r_chart
            data = [[23 + i * 0.1 + j * 0.05 for j in range(5)] for i in range(20)]
            result = xbar_r_chart(data)
            specs = from_spc_result_pair(result, title="X-bar/R")
            assert len(specs) >= 1
            if result.secondary_chart:
                assert len(specs) == 2
                assert specs[1].height == 200
        except ImportError:
            pytest.skip("forgespc not installed")


class TestImports:
    def test_charts_init_imports_all(self):
        """Verify all chart builders are importable from charts package."""
        from forgeviz.charts import (
            control_chart,
            detection_ladder,
        )
        assert callable(control_chart)
        assert callable(detection_ladder)

    def test_renderers_import(self):
        from forgeviz.renderers import to_plotly, to_svg
        assert callable(to_plotly)
        assert callable(to_svg)

    def test_core_import(self):
        from forgeviz.core import render, SVEND_COLORS
        assert callable(render)
        assert len(SVEND_COLORS) == 10
