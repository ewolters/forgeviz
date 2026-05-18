"""Tests for per-element styling: colors, sizes, labels on Trace."""

import unittest

from forgeviz.core.spec import ChartSpec, Trace, render


class TestPerPointColors(unittest.TestCase):
    """Per-point colors on Trace — like coloring individual bars in Excel."""

    def test_bar_per_point_colors(self):
        spec = ChartSpec(title="Plant Utilization")
        spec.add_trace(
            ["WIN", "ELL", "BTR", "BOU", "PHL"],
            [95, 78, 65, 42, 110],
            trace_type="bar",
            colors=["#4a9f6e", "#4a9f6e", "#4a9f6e", "#4a9f6e", "#d06060"],
        )
        svg = render(spec, "svg")
        # PHL bar should be red (#d06060), others green
        assert "#d06060" in svg
        assert "#4a9f6e" in svg

    def test_scatter_per_point_colors(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3, 4],
            [10, 20, 30, 40],
            trace_type="scatter",
            colors=["red", "blue", "green", "orange"],
        )
        svg = render(spec, "svg")
        for c in ("red", "blue", "green", "orange"):
            assert c in svg

    def test_line_markers_per_point_colors(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="line",
            marker_size=8,
            colors=["red", "", "blue"],  # empty string falls back to base
        )
        svg = render(spec, "svg")
        assert "red" in svg
        assert "blue" in svg

    def test_color_fallback_to_base(self):
        """Empty per-point color falls back to trace.color."""
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="bar",
            color="#111111",
            colors=["#222222", "", "#333333"],
        )
        svg = render(spec, "svg")
        assert "#222222" in svg
        assert "#111111" in svg  # fallback for index 1
        assert "#333333" in svg

    def test_fewer_colors_than_points(self):
        """If colors list is shorter than data, remaining use base color."""
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3, 4],
            [10, 20, 30, 40],
            trace_type="bar",
            color="#aaa",
            colors=["#bbb", "#ccc"],
        )
        svg = render(spec, "svg")
        assert "#bbb" in svg
        assert "#ccc" in svg
        assert "#aaa" in svg  # fallback for indices 2, 3

    def test_empty_colors_list_uses_base(self):
        """Empty colors list → all points use trace.color."""
        spec = ChartSpec()
        spec.add_trace(
            [1, 2],
            [10, 20],
            trace_type="bar",
            color="#ff0000",
            colors=[],
        )
        svg = render(spec, "svg")
        assert svg.count("#ff0000") >= 2


class TestPerPointSizes(unittest.TestCase):
    """Per-point sizes — like making important points bigger."""

    def test_scatter_per_point_sizes(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="scatter",
            sizes=[4, 12, 20],
        )
        svg = render(spec, "svg")
        # Radii should be 2, 6, 10 (size/2)
        assert 'r="2"' in svg or 'r="2.0"' in svg
        assert 'r="6"' in svg or 'r="6.0"' in svg
        assert 'r="10"' in svg or 'r="10.0"' in svg

    def test_line_markers_per_point_sizes(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="line",
            sizes=[6, 12, 6],  # sizes alone trigger marker rendering
        )
        svg = render(spec, "svg")
        assert "<circle" in svg  # markers rendered even without marker_size

    def test_sizes_fallback_to_marker_size(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="scatter",
            marker_size=10,
            sizes=[20],  # only first point, rest fall back to 10
        )
        svg = render(spec, "svg")
        assert 'r="10"' in svg or 'r="10.0"' in svg  # 20/2
        assert 'r="5"' in svg or 'r="5.0"' in svg    # 10/2


class TestPerPointLabels(unittest.TestCase):
    """Per-point text labels — auto-placed value labels."""

    def test_bar_labels(self):
        spec = ChartSpec()
        spec.add_trace(
            ["A", "B", "C"],
            [10, 25, 15],
            trace_type="bar",
            labels=["10%", "25%", "15%"],
        )
        svg = render(spec, "svg")
        assert "10%" in svg
        assert "25%" in svg
        assert "15%" in svg

    def test_scatter_labels(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="scatter",
            labels=["low", "mid", "high"],
        )
        svg = render(spec, "svg")
        assert "low" in svg
        assert "mid" in svg
        assert "high" in svg

    def test_line_labels_without_markers(self):
        """Labels should render on lines even without marker_size set."""
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="line",
            labels=["a", "b", "c"],
        )
        svg = render(spec, "svg")
        assert ">a<" in svg
        assert ">b<" in svg
        assert ">c<" in svg

    def test_label_position_bottom(self):
        spec = ChartSpec()
        spec.add_trace(
            [1],
            [10],
            trace_type="scatter",
            labels=["bottom_label"],
            label_position="bottom",
        )
        svg = render(spec, "svg")
        assert "bottom_label" in svg

    def test_empty_label_skipped(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2],
            [10, 20],
            trace_type="bar",
            labels=["show", ""],
        )
        svg = render(spec, "svg")
        assert "show" in svg

    def test_area_labels(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="area",
            labels=["start", "", "end"],
        )
        svg = render(spec, "svg")
        assert "start" in svg
        assert "end" in svg


class TestInlineTheme(unittest.TestCase):
    """Theme as dict — user-defined branding, no presets."""

    def test_dict_theme_used(self):
        my_theme = {
            "bg": "#f5f0e8",
            "plot_bg": "#f5f0e8",
            "text": "#1a1a1a",
            "text_secondary": "#4a4a46",
            "grid": "rgba(26,26,26,0.07)",
            "axis": "rgba(26,26,26,0.2)",
            "accent": "#2a5f8f",
            "font": "IBM Plex Sans, sans-serif",
            "font_mono": "IBM Plex Mono, monospace",
            "colors": ["#2a5f8f", "#c04040", "#4a7a5a", "#9a7a2a"],
        }
        spec = ChartSpec(title="Branded Chart", theme=my_theme)
        spec.add_trace([1, 2, 3], [10, 20, 30], trace_type="bar")
        svg = render(spec, "svg")
        assert "#f5f0e8" in svg  # custom bg
        assert "#1a1a1a" in svg  # custom text
        assert "#2a5f8f" in svg  # custom bar color from palette

    def test_string_theme_still_works(self):
        spec = ChartSpec(title="Default", theme="light")
        spec.add_trace([1, 2], [10, 20], trace_type="bar")
        svg = render(spec, "svg")
        assert "#ffffff" in svg  # light theme bg

    def test_unknown_string_theme_falls_back(self):
        spec = ChartSpec(title="Unknown", theme="nonexistent")
        spec.add_trace([1, 2], [10, 20], trace_type="bar")
        svg = render(spec, "svg")
        assert "svg" in svg  # renders without error


class TestCombined(unittest.TestCase):
    """Combine per-point colors + sizes + labels — the full Excel experience."""

    def test_all_three_on_scatter(self):
        spec = ChartSpec()
        spec.add_trace(
            [1, 2, 3],
            [10, 20, 30],
            trace_type="scatter",
            colors=["red", "green", "blue"],
            sizes=[6, 12, 18],
            labels=["small", "medium", "large"],
        )
        svg = render(spec, "svg")
        for c in ("red", "green", "blue"):
            assert c in svg
        for lbl in ("small", "medium", "large"):
            assert lbl in svg

    def test_all_three_on_bar(self):
        spec = ChartSpec()
        spec.add_trace(
            ["WIN", "ELL", "BTR"],
            [95, 78, 65],
            trace_type="bar",
            colors=["#d06060", "#e89547", "#4a9f6e"],
            labels=["95%", "78%", "65%"],
        )
        svg = render(spec, "svg")
        assert "#d06060" in svg
        assert "#4a9f6e" in svg
        assert "95%" in svg
        assert "65%" in svg

    def test_serialization_roundtrip(self):
        """Per-element fields survive to_dict/to_json."""
        spec = ChartSpec()
        spec.add_trace(
            [1, 2],
            [10, 20],
            trace_type="bar",
            colors=["red", "blue"],
            sizes=[4, 8],
            labels=["a", "b"],
            label_position="bottom",
        )
        d = spec.to_dict()
        trace_d = d["traces"][0]
        assert trace_d["colors"] == ["red", "blue"]
        assert trace_d["sizes"] == [4, 8]
        assert trace_d["labels"] == ["a", "b"]
        assert trace_d["label_position"] == "bottom"


if __name__ == "__main__":
    unittest.main()
