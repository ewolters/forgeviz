"""Tests for dashboard engine — DashboardSpec and DashboardBuilder."""

import json

import pytest

from forgeviz.core.dashboard import DashboardBuilder, DashboardPanel, DashboardSpec
from forgeviz.core.spec import ChartSpec


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def simple_chart():
    """A minimal ChartSpec for testing."""
    spec = ChartSpec(title="Test Chart", chart_type="line")
    spec.add_trace([1, 2, 3], [10, 20, 30], name="series1")
    return spec


@pytest.fixture
def bar_chart():
    spec = ChartSpec(title="Bar Chart", chart_type="bar")
    spec.add_trace(["A", "B", "C"], [100, 200, 150], name="categories")
    return spec


# =========================================================================
# DashboardPanel
# =========================================================================


class TestDashboardPanel:
    def test_default_values(self, simple_chart):
        panel = DashboardPanel(id="p0", spec=simple_chart)
        assert panel.row == 0
        assert panel.col == 0
        assert panel.row_span == 1
        assert panel.col_span == 1
        assert panel.filter_field == ""
        assert panel.listen_fields == []
        assert panel.data_source == ""
        assert panel.drilldown == {}

    def test_to_dict(self, simple_chart):
        panel = DashboardPanel(
            id="p1",
            spec=simple_chart,
            row=1,
            col=2,
            filter_field="category",
            listen_fields=["date", "shift"],
        )
        d = panel.to_dict()
        assert d["id"] == "p1"
        assert d["row"] == 1
        assert d["col"] == 2
        assert d["filter_field"] == "category"
        assert d["listen_fields"] == ["date", "shift"]
        assert "spec" in d
        assert d["spec"]["title"] == "Test Chart"

    def test_to_dict_is_json_serializable(self, simple_chart):
        panel = DashboardPanel(id="p0", spec=simple_chart, drilldown={"cat": "bar"})
        d = panel.to_dict()
        s = json.dumps(d)
        assert isinstance(s, str)
        assert '"drilldown"' in s


# =========================================================================
# DashboardSpec
# =========================================================================


class TestDashboardSpec:
    def test_defaults(self):
        dash = DashboardSpec()
        assert dash.title == ""
        assert dash.columns == 2
        assert dash.row_height == 350
        assert dash.theme == "svend_dark"
        assert dash.panels == []
        assert dash.filters == []

    def test_add_panel(self, simple_chart):
        dash = DashboardSpec(title="Test")
        panel = dash.add_panel(simple_chart, row=0, col=0, col_span=2)
        assert len(dash.panels) == 1
        assert panel.id == "panel_0"
        assert panel.col_span == 2
        assert panel.spec is simple_chart

    def test_add_multiple_panels(self, simple_chart, bar_chart):
        dash = DashboardSpec()
        p0 = dash.add_panel(simple_chart, row=0, col=0)
        p1 = dash.add_panel(bar_chart, row=0, col=1)
        assert p0.id == "panel_0"
        assert p1.id == "panel_1"
        assert len(dash.panels) == 2

    def test_add_filter_select(self):
        dash = DashboardSpec()
        dash.add_filter("shift", "select", options=["A", "B", "C"])
        assert len(dash.filters) == 1
        f = dash.filters[0]
        assert f["id"] == "filter_0"
        assert f["field"] == "shift"
        assert f["type"] == "select"
        assert f["options"] == ["A", "B", "C"]
        assert f["label"] == "shift"

    def test_add_filter_range(self):
        dash = DashboardSpec()
        dash.add_filter("temperature", "range", label="Temp (C)")
        f = dash.filters[0]
        assert f["type"] == "range"
        assert f["label"] == "Temp (C)"
        assert f["options"] == []

    def test_add_filter_date_range(self):
        dash = DashboardSpec()
        dash.add_filter("date", "date_range", label="Date Range")
        assert dash.filters[0]["type"] == "date_range"

    def test_get_panel(self, simple_chart):
        dash = DashboardSpec()
        dash.add_panel(simple_chart)
        assert dash.get_panel("panel_0") is not None
        assert dash.get_panel("nonexistent") is None

    def test_remove_panel(self, simple_chart, bar_chart):
        dash = DashboardSpec()
        dash.add_panel(simple_chart)
        dash.add_panel(bar_chart)
        assert len(dash.panels) == 2
        result = dash.remove_panel("panel_0")
        assert result is True
        assert len(dash.panels) == 1
        assert dash.panels[0].id == "panel_1"

    def test_remove_panel_not_found(self):
        dash = DashboardSpec()
        assert dash.remove_panel("nope") is False

    # ------------------------------------------------------------------
    # Grid introspection
    # ------------------------------------------------------------------

    def test_row_count_empty(self):
        assert DashboardSpec().row_count == 0

    def test_row_count(self, simple_chart):
        dash = DashboardSpec()
        dash.add_panel(simple_chart, row=0, col=0)
        dash.add_panel(simple_chart, row=2, col=0, row_span=2)
        assert dash.row_count == 4

    def test_filter_fields(self, simple_chart):
        dash = DashboardSpec()
        dash.add_panel(simple_chart, filter_field="category")
        dash.add_panel(simple_chart, filter_field="date")
        dash.add_panel(simple_chart)
        assert dash.filter_fields == {"category", "date"}

    def test_listen_field_set(self, simple_chart):
        dash = DashboardSpec()
        dash.add_panel(simple_chart, listen_fields=["category", "date"])
        dash.add_panel(simple_chart, listen_fields=["date", "shift"])
        assert dash.listen_field_set == {"category", "date", "shift"}

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def test_to_dict(self, simple_chart):
        dash = DashboardSpec(title="My Dashboard", columns=3)
        dash.add_panel(simple_chart, row=0, col=0, filter_field="x")
        dash.add_filter("shift", "select", options=["A", "B"])
        d = dash.to_dict()

        assert d["title"] == "My Dashboard"
        assert d["columns"] == 3
        assert d["row_height"] == 350
        assert d["theme"] == "svend_dark"
        assert len(d["panels"]) == 1
        assert d["panels"][0]["filter_field"] == "x"
        assert len(d["filters"]) == 1
        assert d["filters"][0]["field"] == "shift"

    def test_to_json(self, simple_chart):
        dash = DashboardSpec(title="JSON Test")
        dash.add_panel(simple_chart)
        j = dash.to_json(indent=2)
        parsed = json.loads(j)
        assert parsed["title"] == "JSON Test"
        assert len(parsed["panels"]) == 1

    def test_to_json_roundtrip_is_valid_json(self, simple_chart, bar_chart):
        dash = DashboardSpec(title="Roundtrip", columns=3)
        dash.add_panel(simple_chart, row=0, col=0, col_span=2, filter_field="date")
        dash.add_panel(bar_chart, row=0, col=2, listen_fields=["date"])
        dash.add_filter("shift", "select", options=["A", "B", "C"])
        dash.add_filter("temp", "range", label="Temperature")

        j = dash.to_json()
        parsed = json.loads(j)
        assert parsed["columns"] == 3
        assert len(parsed["panels"]) == 2
        assert len(parsed["filters"]) == 2

    def test_from_dict(self, simple_chart):
        dash = DashboardSpec(title="Original", columns=3, row_height=400)
        dash.add_panel(simple_chart, row=1, col=2, filter_field="x")
        dash.add_filter("shift", "select", options=["A"])

        d = dash.to_dict()
        restored = DashboardSpec.from_dict(d)

        assert restored.title == "Original"
        assert restored.columns == 3
        assert restored.row_height == 400
        assert len(restored.panels) == 1
        assert restored.panels[0].row == 1
        assert restored.panels[0].col == 2
        assert restored.panels[0].filter_field == "x"
        assert restored.panels[0].spec.title == "Test Chart"
        assert len(restored.filters) == 1

    def test_panel_with_drilldown(self, simple_chart):
        dash = DashboardSpec()
        p = dash.add_panel(simple_chart, drilldown={"category": "histogram"})
        assert p.drilldown == {"category": "histogram"}
        d = dash.to_dict()
        assert d["panels"][0]["drilldown"] == {"category": "histogram"}


# =========================================================================
# DashboardBuilder
# =========================================================================


class TestDashboardBuilder:
    def test_basic_build(self, simple_chart):
        dash = DashboardBuilder("Builder Test", columns=3, theme="nordic").build()
        assert dash.title == "Builder Test"
        assert dash.columns == 3
        assert dash.theme == "nordic"
        assert dash.panels == []

    def test_fluent_chaining(self, simple_chart, bar_chart):
        dash = (
            DashboardBuilder("Fluent")
            .panel(simple_chart, 0, 0, col_span=2, filter_field="date")
            .panel(bar_chart, 0, 2, listen_fields=["date"])
            .filter("shift", "select", options=["A", "B"])
            .row_height(400)
            .theme("light")
            .build()
        )
        assert dash.title == "Fluent"
        assert len(dash.panels) == 2
        assert dash.panels[0].col_span == 2
        assert dash.panels[0].filter_field == "date"
        assert dash.panels[1].listen_fields == ["date"]
        assert len(dash.filters) == 1
        assert dash.row_height == 400
        assert dash.theme == "light"

    def test_returns_self_for_chaining(self, simple_chart):
        builder = DashboardBuilder()
        result = builder.panel(simple_chart, 0, 0)
        assert result is builder
        result = builder.filter("x")
        assert result is builder
        result = builder.row_height(500)
        assert result is builder
        result = builder.theme("print")
        assert result is builder

    def test_panel_ids_sequential(self, simple_chart):
        dash = (
            DashboardBuilder()
            .panel(simple_chart, 0, 0)
            .panel(simple_chart, 0, 1)
            .panel(simple_chart, 1, 0)
            .build()
        )
        ids = [p.id for p in dash.panels]
        assert ids == ["panel_0", "panel_1", "panel_2"]

    def test_complex_layout(self, simple_chart, bar_chart):
        """3x3 grid with spanning panels."""
        dash = (
            DashboardBuilder("Complex Layout", columns=3)
            .panel(simple_chart, 0, 0, col_span=3, row_span=1)  # full-width header
            .panel(bar_chart, 1, 0, row_span=2)  # tall left
            .panel(simple_chart, 1, 1)
            .panel(simple_chart, 1, 2)
            .panel(bar_chart, 2, 1, col_span=2)  # wide bottom-right
            .build()
        )
        assert len(dash.panels) == 5
        assert dash.row_count == 3
        assert dash.panels[0].col_span == 3  # header spans all cols
        assert dash.panels[1].row_span == 2  # tall panel
        assert dash.panels[4].col_span == 2  # wide panel

    def test_serializable(self, simple_chart, bar_chart):
        """Builder output must be fully JSON-serializable."""
        dash = (
            DashboardBuilder("Serialize", columns=2)
            .panel(simple_chart, 0, 0, filter_field="x")
            .panel(bar_chart, 0, 1, listen_fields=["x"])
            .filter("shift", "select", options=["A", "B", "C"])
            .build()
        )
        j = dash.to_json()
        parsed = json.loads(j)
        assert parsed["title"] == "Serialize"
        assert len(parsed["panels"]) == 2
        assert len(parsed["filters"]) == 1
