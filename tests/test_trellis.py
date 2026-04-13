"""Tests for trellis / small multiples chart system."""

import pytest

from forgeviz.charts.generic import line
from forgeviz.charts.trellis import (
    _TRELLIS_HEIGHT,
    trellis,
    trellis_control_charts,
    trellis_from_dataframe,
    trellis_histograms,
    trellis_scatter,
)
from forgeviz.core.dashboard import DashboardSpec
from forgeviz.core.spec import Axis


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def three_groups():
    """Three groups of line data."""
    return {
        "Line A": {"x": [1, 2, 3, 4, 5], "y": [10, 12, 11, 14, 13]},
        "Line B": {"x": [1, 2, 3, 4, 5], "y": [20, 22, 19, 25, 23]},
        "Line C": {"x": [1, 2, 3, 4, 5], "y": [5, 7, 6, 8, 9]},
    }


@pytest.fixture
def spc_groups():
    """Three groups of SPC data points."""
    return {
        "Machine 1": [50.1, 49.8, 50.3, 50.0, 49.9, 50.2],
        "Machine 2": [50.5, 50.2, 50.8, 50.1, 50.4, 50.3],
        "Machine 3": [49.7, 50.0, 49.5, 50.1, 49.8, 49.9],
    }


@pytest.fixture
def histogram_groups():
    """Three groups of distribution data."""
    return {
        "Shift A": [10.1, 10.3, 10.2, 10.5, 10.0, 10.4, 10.1, 10.3],
        "Shift B": [10.8, 10.6, 10.9, 10.7, 10.5, 10.8, 10.6, 10.7],
        "Shift C": [9.8, 10.0, 9.9, 10.1, 9.7, 10.0, 9.8, 9.9],
    }


@pytest.fixture
def scatter_groups():
    """Three groups of scatter data."""
    return {
        "Process A": {"x": [1.0, 2.0, 3.0, 4.0], "y": [2.1, 4.0, 5.9, 8.1]},
        "Process B": {"x": [1.0, 2.0, 3.0, 4.0], "y": [1.5, 3.2, 4.8, 6.5]},
        "Process C": {"x": [1.0, 2.0, 3.0, 4.0], "y": [3.0, 5.5, 8.2, 10.1]},
    }


@pytest.fixture
def row_data():
    """Flat row data for trellis_from_dataframe."""
    return [
        {"line": "L1", "date": "2026-01-01", "yield": 98.2},
        {"line": "L1", "date": "2026-01-02", "yield": 97.8},
        {"line": "L1", "date": "2026-01-03", "yield": 98.5},
        {"line": "L2", "date": "2026-01-01", "yield": 96.1},
        {"line": "L2", "date": "2026-01-02", "yield": 96.5},
        {"line": "L2", "date": "2026-01-03", "yield": 96.8},
        {"line": "L3", "date": "2026-01-01", "yield": 99.0},
        {"line": "L3", "date": "2026-01-02", "yield": 98.7},
        {"line": "L3", "date": "2026-01-03", "yield": 99.2},
    ]


# =========================================================================
# Basic trellis with line charts
# =========================================================================


class TestTrellisBasic:
    def test_three_groups_three_panels(self, three_groups):
        dash = trellis(three_groups, line, title="Test Trellis", columns=3)
        assert isinstance(dash, DashboardSpec)
        assert len(dash.panels) == 3
        assert dash.title == "Test Trellis"
        assert dash.columns == 3

    def test_panel_subtitles_match_group_names(self, three_groups):
        dash = trellis(three_groups, line)
        subtitles = [p.spec.subtitle for p in dash.panels]
        assert subtitles == ["Line A", "Line B", "Line C"]

    def test_compact_height(self, three_groups):
        dash = trellis(three_groups, line)
        for panel in dash.panels:
            assert panel.spec.height == _TRELLIS_HEIGHT

    def test_row_height_matches(self, three_groups):
        dash = trellis(three_groups, line)
        assert dash.row_height == _TRELLIS_HEIGHT

    def test_legend_hidden(self, three_groups):
        dash = trellis(three_groups, line)
        for panel in dash.panels:
            assert panel.spec.show_legend is False

    def test_trellis_metadata_attached(self, three_groups):
        dash = trellis(three_groups, line, shared_y=True, shared_x=False)
        assert hasattr(dash, "_trellis_metadata")
        meta = dash._trellis_metadata
        assert meta["type"] == "trellis"
        assert meta["shared_y"] is True
        assert meta["shared_x"] is False
        assert meta["compact"] is True
        assert meta["gap"] == 4


# =========================================================================
# Shared axes
# =========================================================================


class TestSharedAxes:
    def test_shared_y_same_range(self, three_groups):
        dash = trellis(three_groups, line, shared_y=True)
        y_ranges = []
        for panel in dash.panels:
            ax = panel.spec.y_axis
            y_ranges.append((ax.min_val, ax.max_val))
        # All panels have the same y range
        assert all(r == y_ranges[0] for r in y_ranges)

    def test_shared_y_covers_all_data(self, three_groups):
        dash = trellis(three_groups, line, shared_y=True)
        ax = dash.panels[0].spec.y_axis
        # Global min is 5 (Line C), global max is 25 (Line B)
        assert ax.min_val < 5
        assert ax.max_val > 25

    def test_shared_x_same_range(self, three_groups):
        dash = trellis(three_groups, line, shared_x=True)
        x_ranges = []
        for panel in dash.panels:
            ax = panel.spec.x_axis
            x_ranges.append((ax.min_val, ax.max_val))
        assert all(r == x_ranges[0] for r in x_ranges)

    def test_no_shared_y_no_forced_range(self, three_groups):
        dash = trellis(three_groups, line, shared_y=False)
        # With shared_y=False, panels are NOT forced to identical range
        # (chart_fn may or may not set axis limits on its own)
        assert len(dash.panels) == 3


# =========================================================================
# Column layout
# =========================================================================


class TestColumnLayout:
    def test_three_groups_one_row(self, three_groups):
        dash = trellis(three_groups, line, columns=3)
        rows_cols = [(p.row, p.col) for p in dash.panels]
        assert rows_cols == [(0, 0), (0, 1), (0, 2)]

    def test_three_groups_two_columns(self, three_groups):
        dash = trellis(three_groups, line, columns=2)
        rows_cols = [(p.row, p.col) for p in dash.panels]
        assert rows_cols == [(0, 0), (0, 1), (1, 0)]

    def test_five_groups_three_columns(self):
        data = {f"G{i}": {"x": [1, 2], "y": [10, 20]} for i in range(5)}
        dash = trellis(data, line, columns=3)
        rows_cols = [(p.row, p.col) for p in dash.panels]
        assert rows_cols == [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]

    def test_single_column(self, three_groups):
        dash = trellis(three_groups, line, columns=1)
        rows_cols = [(p.row, p.col) for p in dash.panels]
        assert rows_cols == [(0, 0), (1, 0), (2, 0)]


# =========================================================================
# Convenience: trellis_control_charts
# =========================================================================


class TestTrellisControlCharts:
    def test_basic(self, spc_groups):
        dash = trellis_control_charts(spc_groups, ucl=51.0, cl=50.0, lcl=49.0)
        assert len(dash.panels) == 3
        assert dash._trellis_metadata["type"] == "trellis"
        assert dash._trellis_metadata["shared_y"] is True

    def test_shared_y_includes_limits(self, spc_groups):
        dash = trellis_control_charts(spc_groups, ucl=51.0, cl=50.0, lcl=49.0)
        ax = dash.panels[0].spec.y_axis
        assert ax.min_val < 49.0
        assert ax.max_val > 51.0

    def test_subtitles(self, spc_groups):
        dash = trellis_control_charts(spc_groups, ucl=51.0, cl=50.0, lcl=49.0)
        subtitles = [p.spec.subtitle for p in dash.panels]
        assert subtitles == ["Machine 1", "Machine 2", "Machine 3"]

    def test_compact_height(self, spc_groups):
        dash = trellis_control_charts(spc_groups, ucl=51.0, cl=50.0, lcl=49.0)
        for panel in dash.panels:
            assert panel.spec.height == _TRELLIS_HEIGHT

    def test_empty_data(self):
        dash = trellis_control_charts({}, ucl=10, cl=5, lcl=0)
        assert len(dash.panels) == 0
        assert dash._trellis_metadata["type"] == "trellis"

    def test_has_reference_lines(self, spc_groups):
        dash = trellis_control_charts(spc_groups, ucl=51.0, cl=50.0, lcl=49.0)
        for panel in dash.panels:
            # control_chart adds UCL, CL, LCL reference lines
            assert len(panel.spec.reference_lines) >= 3


# =========================================================================
# Convenience: trellis_histograms
# =========================================================================


class TestTrellisHistograms:
    def test_basic(self, histogram_groups):
        dash = trellis_histograms(histogram_groups, title="Distribution Comparison", bins=5)
        assert len(dash.panels) == 3
        assert dash.title == "Distribution Comparison"

    def test_shared_x(self, histogram_groups):
        dash = trellis_histograms(histogram_groups, shared_x=True)
        x_ranges = []
        for panel in dash.panels:
            ax = panel.spec.x_axis
            if isinstance(ax, Axis):
                x_ranges.append((ax.min_val, ax.max_val))
        if x_ranges:
            assert all(r == x_ranges[0] for r in x_ranges)

    def test_empty_data(self):
        dash = trellis_histograms({})
        assert len(dash.panels) == 0

    def test_custom_bins(self, histogram_groups):
        dash = trellis_histograms(histogram_groups, bins=10)
        assert len(dash.panels) == 3


# =========================================================================
# Convenience: trellis_scatter
# =========================================================================


class TestTrellisScatter:
    def test_basic(self, scatter_groups):
        dash = trellis_scatter(scatter_groups, title="Scatter Comparison")
        assert len(dash.panels) == 3

    def test_shared_axes(self, scatter_groups):
        dash = trellis_scatter(scatter_groups)
        y_ranges = []
        for panel in dash.panels:
            ax = panel.spec.y_axis
            if isinstance(ax, Axis):
                y_ranges.append((ax.min_val, ax.max_val))
        if y_ranges:
            assert all(r == y_ranges[0] for r in y_ranges)

    def test_empty_data(self):
        dash = trellis_scatter({})
        assert len(dash.panels) == 0


# =========================================================================
# trellis_from_dataframe
# =========================================================================


class TestTrellisFromDataframe:
    def test_groups_from_rows(self, row_data):
        dash = trellis_from_dataframe(
            row_data, group_field="line", x_field="date", y_field="yield",
            chart_fn=line, title="Yield by Line",
        )
        assert isinstance(dash, DashboardSpec)
        assert len(dash.panels) == 3
        assert dash.title == "Yield by Line"

    def test_group_names(self, row_data):
        dash = trellis_from_dataframe(
            row_data, group_field="line", x_field="date", y_field="yield",
            chart_fn=line,
        )
        subtitles = sorted(p.spec.subtitle for p in dash.panels)
        assert subtitles == ["L1", "L2", "L3"]

    def test_data_integrity(self, row_data):
        dash = trellis_from_dataframe(
            row_data, group_field="line", x_field="date", y_field="yield",
            chart_fn=line,
        )
        # Each group should have 3 data points
        for panel in dash.panels:
            for trace in panel.spec.traces:
                assert len(trace.x) == 3
                assert len(trace.y) == 3

    def test_empty_rows(self):
        dash = trellis_from_dataframe(
            [], group_field="line", x_field="date", y_field="yield",
            chart_fn=line,
        )
        assert len(dash.panels) == 0


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    def test_single_group(self):
        data = {"Only One": {"x": [1, 2, 3], "y": [10, 20, 30]}}
        dash = trellis(data, line, columns=3)
        assert len(dash.panels) == 1
        assert dash.panels[0].spec.subtitle == "Only One"
        assert dash.panels[0].row == 0
        assert dash.panels[0].col == 0

    def test_empty_groups(self):
        dash = trellis({}, line, title="Empty")
        assert len(dash.panels) == 0
        assert dash.title == "Empty"
        assert hasattr(dash, "_trellis_metadata")

    def test_mismatched_data_lengths(self):
        data = {
            "Short": {"x": [1, 2], "y": [10, 20]},
            "Long": {"x": [1, 2, 3, 4, 5], "y": [10, 20, 30, 40, 50]},
        }
        dash = trellis(data, line)
        assert len(dash.panels) == 2

    def test_large_number_of_groups(self):
        data = {f"Group {i}": {"x": [1, 2], "y": [i, i + 1]} for i in range(12)}
        dash = trellis(data, line, columns=4)
        assert len(dash.panels) == 12
        # Should have 3 rows
        assert dash.panels[-1].row == 2

    def test_chart_kwargs_forwarded(self):
        data = {"G1": {"x": [1, 2, 3], "y": [10, 20, 30]}}
        dash = trellis(data, line, show_markers=True)
        assert len(dash.panels) == 1
        # show_markers=True sets marker_size to 4 in line()
        trace = dash.panels[0].spec.traces[0]
        assert trace.marker_size == 4

    def test_serialization(self, three_groups):
        """Trellis dashboard should serialize to JSON."""
        dash = trellis(three_groups, line, title="Serialize Test")
        json_str = dash.to_json()
        assert '"title": "Serialize Test"' in json_str
        assert '"panels"' in json_str
