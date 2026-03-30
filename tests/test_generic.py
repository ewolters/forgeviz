"""Tests for generic chart types — donut, bullet, stacked area, risk heatmap."""

from forgeviz.charts.generic import (
    bar, donut, stacked_area, bullet, risk_heatmap, pie, sparkline,
)


class TestDonut:
    def test_basic(self):
        spec = donut(["Done", "Remaining"], [72, 28], center_value="72%", center_label="Compliance")
        assert spec.chart_type == "donut"
        assert spec.traces[0]["type"] == "donut"
        assert spec.traces[0]["hole"] == 0.55
        assert len(spec.annotations) == 2
        assert spec.annotations[0]["text"] == "72%"
        assert spec.annotations[1]["text"] == "Compliance"

    def test_percentages(self):
        spec = donut(["A", "B", "C"], [50, 30, 20])
        assert spec.traces[0]["percentages"] == [50.0, 30.0, 20.0]

    def test_no_center(self):
        spec = donut(["X", "Y"], [60, 40])
        assert len(spec.annotations) == 0

    def test_zero_total(self):
        spec = donut(["A", "B"], [0, 0])
        assert spec.traces[0]["percentages"] == [0, 0]


class TestStackedArea:
    def test_basic(self):
        x = [1, 2, 3, 4, 5]
        series = {"Alerts": [10, 15, 12, 18, 14], "NCRs": [5, 8, 6, 9, 7]}
        spec = stacked_area(x, series, title="Signal Volume")
        assert spec.chart_type == "stacked_area"
        assert len(spec.traces) == 2

    def test_cumulative_stacking(self):
        x = [1, 2]
        series = {"A": [10, 20], "B": [5, 10]}
        spec = stacked_area(x, series)
        # First trace: cumulative = [10, 20]
        assert spec.traces[0].y == [10, 20]
        # Second trace: cumulative = [15, 30]
        assert spec.traces[1].y == [15, 30]

    def test_fill_type(self):
        x = [1, 2, 3]
        series = {"A": [1, 2, 3], "B": [4, 5, 6]}
        spec = stacked_area(x, series)
        assert spec.traces[0].fill == "tozeroy"
        assert spec.traces[1].fill == "tonexty"


class TestBullet:
    def test_basic(self):
        spec = bullet(actual=72, target=85, title="Readiness Score", subtitle="%")
        assert spec.chart_type == "bullet"
        assert spec.traces[0]["type"] == "bullet_bar"
        assert spec.traces[0]["value"] == 72
        assert len(spec.zones) == 3  # default 3 ranges

    def test_custom_ranges(self):
        spec = bullet(actual=50, target=80, ranges=[(40, "#400"), (70, "#440"), (100, "#040")])
        assert len(spec.zones) == 3

    def test_target_marker(self):
        spec = bullet(actual=72, target=85)
        assert any("Target" in str(r.get("label", "")) for r in spec.reference_lines)

    def test_annotation(self):
        spec = bullet(actual=72, target=85)
        assert spec.annotations[0]["text"] == "72"


class TestRiskHeatmap:
    def test_basic(self):
        rows = ["Low", "Med", "High"]
        cols = ["Rare", "Unlikely", "Possible", "Likely"]
        values = [[1, 2, 3, 4], [2, 4, 6, 8], [3, 6, 9, 12]]
        spec = risk_heatmap(rows, cols, values)
        assert spec.chart_type == "risk_heatmap"
        assert spec.traces[0]["type"] == "risk_heatmap"
        assert spec.traces[0]["z"] == values

    def test_with_labels(self):
        rows = ["S1", "S2"]
        cols = ["O1", "O2"]
        values = [[1, 2], [3, 4]]
        labels = [["Low", "Med"], ["Med", "High"]]
        spec = risk_heatmap(rows, cols, values, value_labels=labels)
        assert spec.traces[0]["value_labels"] == labels

    def test_colorscale(self):
        spec = risk_heatmap(["A"], ["B"], [[5]], low_color="#000", high_color="#fff")
        assert spec.traces[0]["colorscale"][0] == "#000"
        assert spec.traces[0]["colorscale"][2] == "#fff"


class TestExistingCharts:
    """Verify existing charts still work after modifications."""

    def test_bar(self):
        spec = bar(["A", "B", "C"], [10, 20, 30])
        assert spec.chart_type == "bar"

    def test_pie(self):
        spec = pie(["X", "Y"], [60, 40])
        assert spec.chart_type == "pie"

    def test_sparkline(self):
        spec = sparkline([1, 3, 2, 5, 4])
        assert spec.chart_type == "sparkline"
