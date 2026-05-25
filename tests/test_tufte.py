"""Tests for Tufte rendering mode — theme, chart builders, tufte_mode transform."""

from forgeviz.core.colors import THEMES, get_theme
from forgeviz.core.spec import ChartSpec, render


class TestTufteTheme:
    def test_theme_exists(self):
        assert "tufte" in THEMES

    def test_theme_cream_background(self):
        t = get_theme("tufte")
        assert t["bg"] == "#fffff8"

    def test_theme_transparent_grid(self):
        t = get_theme("tufte")
        assert "0,0,0,0" in t["grid"]

    def test_theme_serif_font(self):
        t = get_theme("tufte")
        assert "Georgia" in t["font"]

    def test_theme_range_frame(self):
        t = get_theme("tufte")
        assert t.get("range_frame") is True

    def test_theme_narrow_bars(self):
        t = get_theme("tufte")
        assert t.get("bar_width_ratio") == 0.4


class TestRangeFrame:
    def test_basic(self):
        from forgeviz.charts.tufte import range_frame
        spec = range_frame([1, 5, 10], [2, 8, 3], title="Test")
        assert spec.chart_type == "range_frame"
        assert spec.theme == "tufte"
        assert spec.x_axis.min_val == 1
        assert spec.x_axis.max_val == 10
        assert spec.y_axis.min_val == 2
        assert spec.y_axis.max_val == 8

    def test_renders_svg(self):
        from forgeviz.charts.tufte import range_frame
        spec = range_frame([1, 2, 3], [4, 5, 6])
        svg = render(spec, "svg")
        assert "fffff8" in svg  # cream background


class TestQuartilePlot:
    def test_basic(self):
        from forgeviz.charts.tufte import quartile_plot
        spec = quartile_plot({"A": [1, 2, 3, 4, 5], "B": [3, 4, 5, 6, 7]})
        assert spec.chart_type == "quartile_plot"
        assert len(spec.traces) == 2

    def test_renders_svg(self):
        from forgeviz.charts.tufte import quartile_plot
        spec = quartile_plot({"Group": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        svg = render(spec, "svg")
        assert "circle" in svg  # median and quartile dots

    def test_no_box_no_whiskers(self):
        from forgeviz.charts.tufte import quartile_plot
        spec = quartile_plot({"A": list(range(20))})
        svg = render(spec, "svg")
        # Should not contain rect (that would be a box)
        # The only rect is the zone/background — no box plot boxes
        trace = spec.traces[0]
        assert isinstance(trace, dict)
        assert "whisker_low" not in trace
        assert "whisker_high" not in trace


class TestDotDash:
    def test_basic(self):
        from forgeviz.charts.tufte import dot_dash
        spec = dot_dash([1, 2, 3, 4], [5, 6, 7, 8])
        assert spec.chart_type == "dot_dash"
        assert len(spec.traces) == 3  # scatter + rug_x + rug_y

    def test_rug_traces(self):
        from forgeviz.charts.tufte import dot_dash
        spec = dot_dash([1, 2, 3], [4, 5, 6])
        rug_types = [t.get("type") for t in spec.traces if isinstance(t, dict)]
        assert "rug_x" in rug_types
        assert "rug_y" in rug_types

    def test_renders_svg(self):
        from forgeviz.charts.tufte import dot_dash
        spec = dot_dash([1, 2, 3], [4, 5, 6])
        svg = render(spec, "svg")
        assert len(svg) > 100


class TestTufteBar:
    def test_basic(self):
        from forgeviz.charts.tufte import tufte_bar
        spec = tufte_bar(["A", "B", "C"], [10, 20, 30])
        assert spec.chart_type == "tufte_bar"
        assert spec.show_legend is False

    def test_value_labels(self):
        from forgeviz.charts.tufte import tufte_bar
        spec = tufte_bar(["A", "B"], [10, 20])
        assert spec.traces[0].labels == ["10.0", "20.0"]

    def test_renders_svg_narrow_bars(self):
        from forgeviz.charts.tufte import tufte_bar
        spec = tufte_bar(["A", "B", "C"], [10, 20, 30])
        svg = render(spec, "svg")
        assert "fffff8" in svg


class TestTufteLine:
    def test_basic(self):
        from forgeviz.charts.tufte import tufte_line
        spec = tufte_line([1, 2, 3], [4, 5, 6], series_label="Revenue")
        assert spec.chart_type == "tufte_line"
        assert len(spec.annotations) == 1
        assert "Revenue" in spec.annotations[0]["text"]

    def test_no_legend(self):
        from forgeviz.charts.tufte import tufte_line
        spec = tufte_line([1, 2, 3], [4, 5, 6])
        assert spec.show_legend is False


class TestRug:
    def test_basic(self):
        from forgeviz.charts.tufte import rug
        spec = rug([1, 2, 3, 4, 5])
        assert spec.chart_type == "rug"
        assert spec.height == 30

    def test_renders_svg(self):
        from forgeviz.charts.tufte import rug
        spec = rug([1, 2, 3, 4, 5])
        svg = render(spec, "svg")
        assert svg.count("<line") >= 5


class TestSlopeChart:
    def test_basic(self):
        from forgeviz.charts.tufte import slope_chart
        spec = slope_chart(["Team A", "Team B", "Team C"], [10, 20, 30], [15, 18, 35])
        assert spec.chart_type == "slope_chart"

    def test_renders_svg(self):
        from forgeviz.charts.tufte import slope_chart
        spec = slope_chart(["X", "Y"], [10, 20], [15, 25])
        svg = render(spec, "svg")
        assert "Before" in svg
        assert "After" in svg


class TestTufteMode:
    def test_does_not_mutate_input(self):
        from forgeviz.charts.tufte import tufte_mode
        original = ChartSpec(title="Original", theme="svend_dark")
        original.add_trace([1, 2, 3], [4, 5, 6], name="data")
        result = tufte_mode(original)
        assert original.theme == "svend_dark"
        assert result.theme == "tufte"

    def test_strips_grid(self):
        from forgeviz.charts.tufte import tufte_mode
        spec = ChartSpec(title="Test")
        spec.add_trace([1, 2], [3, 4])
        result = tufte_mode(spec)
        assert result.x_axis.grid is False
        assert result.y_axis.grid is False

    def test_removes_legend(self):
        from forgeviz.charts.tufte import tufte_mode
        spec = ChartSpec(title="Test", show_legend=True)
        spec.add_trace([1, 2], [3, 4], name="series")
        result = tufte_mode(spec)
        assert result.show_legend is False

    def test_adds_direct_labels(self):
        from forgeviz.charts.tufte import tufte_mode
        spec = ChartSpec(title="Test")
        spec.add_trace([1, 2, 3], [4, 5, 6], name="Revenue")
        result = tufte_mode(spec)
        assert any("Revenue" in str(a.get("text", "")) for a in result.annotations)

    def test_tightens_axes(self):
        from forgeviz.charts.tufte import tufte_mode
        spec = ChartSpec(title="Test")
        spec.add_trace([10, 20, 30], [100, 200, 300])
        result = tufte_mode(spec)
        assert result.y_axis.min_val == 100
        assert result.y_axis.max_val == 300
        assert result.x_axis.min_val == 10
        assert result.x_axis.max_val == 30

    def test_no_tighten_bars(self):
        from forgeviz.charts.tufte import tufte_mode
        spec = ChartSpec(title="Test", chart_type="bar")
        spec.add_trace(["A", "B"], [100, 200])
        result = tufte_mode(spec, tighten_axes=True)
        # Should not set min_val for bar charts (zero baseline)
        assert result.y_axis.min_val is None

    def test_quietens_zones(self):
        from forgeviz.charts.tufte import tufte_mode
        spec = ChartSpec(title="Test")
        spec.add_trace([1, 2], [3, 4])
        spec.add_zone(3, 4, color="rgba(255,0,0,0.2)")
        result = tufte_mode(spec)
        assert "0.1)" in result.zones[0].color  # alpha halved from 0.2

    def test_renders_svg(self):
        from forgeviz.charts.tufte import tufte_mode
        from forgeviz.charts.generic import multi_line
        spec = multi_line([1, 2, 3], {"A": [4, 5, 6], "B": [7, 8, 9]})
        result = tufte_mode(spec)
        svg = render(result, "svg")
        assert "fffff8" in svg
        assert "Georgia" in svg


class TestGridConditional:
    def test_grid_false_suppresses_lines(self):
        from forgeviz.core.spec import Axis
        spec = ChartSpec(title="No Grid")
        spec.y_axis = Axis(grid=False)
        spec.add_trace([1, 2, 3], [4, 5, 6])
        svg = render(spec, "svg")
        # Y gridlines use theme["grid"] color — with grid=False they shouldn't appear
        # Count gridlines (stroke with theme grid color)
        gridline_count = svg.count('stroke="rgba(255,255,255,0.06)"')
        assert gridline_count == 0


class TestBarWidthRatio:
    def test_tufte_theme_narrow_bars(self):
        from forgeviz.charts.tufte import tufte_bar
        spec = tufte_bar(["A", "B", "C", "D"], [10, 20, 30, 40])
        svg = render(spec, "svg")
        # Bars should render — exact width depends on ratio
        assert "<rect" in svg
