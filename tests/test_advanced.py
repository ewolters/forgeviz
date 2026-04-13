"""Tests for advanced chart builders."""

import math

from forgeviz.charts.advanced import (
    candlestick,
    funnel,
    radar,
    sankey,
    treemap,
    violin,
    waterfall,
)
from forgeviz.core.spec import ChartSpec


class TestWaterfall:
    def test_basic(self):
        spec = waterfall(["A", "B", "C"], [100, -30, 50])
        assert isinstance(spec, ChartSpec)
        assert spec.chart_type == "waterfall"
        bars = spec.traces[0]["bars"]
        assert len(bars) == 4  # 3 + total
        assert bars[0]["start"] == 0
        assert bars[0]["end"] == 100
        assert bars[1]["start"] == 100
        assert bars[1]["end"] == 70  # 100 - 30
        assert bars[-1]["is_total"] is True

    def test_no_total(self):
        spec = waterfall(["A", "B"], [10, 20], show_total=False)
        bars = spec.traces[0]["bars"]
        assert len(bars) == 2

    def test_empty(self):
        spec = waterfall([], [])
        bars = spec.traces[0]["bars"]
        assert len(bars) == 1  # just total with value 0


class TestFunnel:
    def test_basic(self):
        spec = funnel(["Leads", "Qualified", "Closed"], [1000, 500, 100])
        assert spec.chart_type == "funnel"
        stages = spec.traces[0]["stages"]
        assert len(stages) == 3
        assert stages[0]["value"] == 1000

    def test_single_stage(self):
        spec = funnel(["Only"], [42])
        assert len(spec.traces[0]["stages"]) == 1


class TestTreemap:
    def test_basic(self):
        spec = treemap(["A", "B", "C"], [50, 30, 20])
        assert spec.chart_type == "treemap"
        rects = spec.traces[0]["rectangles"]
        assert len(rects) == 3
        # All rectangles should be within [0, 1] normalized space
        for r in rects:
            assert 0 <= r["x"] <= 1
            assert 0 <= r["y"] <= 1
            assert r["w"] > 0
            assert r["h"] > 0

    def test_area_proportional(self):
        spec = treemap(["Big", "Small"], [80, 20])
        rects = spec.traces[0]["rectangles"]
        areas = [r["w"] * r["h"] for r in rects]
        total = sum(areas)
        # Areas should be roughly proportional
        assert abs(areas[0] / total - 0.8) < 0.15
        assert abs(areas[1] / total - 0.2) < 0.15

    def test_empty_values(self):
        spec = treemap(["A"], [0])
        rects = spec.traces[0]["rectangles"]
        assert len(rects) == 0

    def test_single_value(self):
        spec = treemap(["Only"], [100])
        rects = spec.traces[0]["rectangles"]
        assert len(rects) == 1
        r = rects[0]
        assert abs(r["w"] - 1.0) < 0.01
        assert abs(r["h"] - 1.0) < 0.01


class TestRadar:
    def test_basic(self):
        spec = radar(
            ["Speed", "Power", "Range", "Armor", "Stealth"],
            {"Fighter": [8, 6, 5, 3, 7], "Bomber": [4, 9, 8, 7, 2]},
        )
        assert spec.chart_type == "radar"
        t = spec.traces[0]
        assert t["type"] == "radar"
        assert len(t["categories"]) == 5
        assert len(t["series"]) == 2

    def test_auto_max(self):
        spec = radar(["A", "B", "C"], {"S1": [10, 20, 30]})
        series = spec.traces[0]["series"][0]
        assert series["max_val"] == 30


class TestViolin:
    def test_basic(self):
        import random
        random.seed(42)
        data = [random.gauss(0, 1) for _ in range(100)]
        spec = violin({"Normal": data})
        assert spec.chart_type == "violin"
        t = spec.traces[0]
        assert t["type"] == "violin"
        assert len(t["density"]) == 50
        assert len(t["y_range"]) == 50
        assert "q1" in t
        assert "median" in t

    def test_multiple_groups(self):
        spec = violin({
            "A": [1, 2, 3, 4, 5, 6, 7, 8],
            "B": [3, 4, 5, 6, 7, 8, 9, 10],
        })
        assert len(spec.traces) == 2

    def test_empty_group(self):
        spec = violin({"Empty": [], "Full": [1, 2, 3, 4]})
        assert len(spec.traces) == 1  # empty skipped


class TestSankey:
    def test_basic(self):
        spec = sankey(
            ["A", "B", "C"],
            [
                {"source": 0, "target": 1, "value": 10},
                {"source": 0, "target": 2, "value": 5},
            ],
        )
        assert spec.chart_type == "sankey"
        t = spec.traces[0]
        assert len(t["nodes"]) == 3
        assert len(t["links"]) == 2

    def test_empty(self):
        spec = sankey([], [])
        assert len(spec.traces[0]["nodes"]) == 0

    def test_depth_ordering(self):
        spec = sankey(
            ["Source", "Mid", "Sink"],
            [
                {"source": 0, "target": 1, "value": 10},
                {"source": 1, "target": 2, "value": 10},
            ],
        )
        nodes = spec.traces[0]["nodes"]
        # Source should be leftmost, Sink rightmost
        assert nodes[0]["x"] < nodes[1]["x"]
        assert nodes[1]["x"] < nodes[2]["x"]


class TestCandlestick:
    def test_basic(self):
        spec = candlestick(
            ["Mon", "Tue", "Wed"],
            [100, 102, 101],  # open
            [105, 106, 104],  # high
            [98, 100, 99],    # low
            [103, 101, 103],  # close
        )
        assert spec.chart_type == "candlestick"
        candles = spec.traces[0]["candles"]
        assert len(candles) == 3
        assert candles[0]["open"] == 100
        assert candles[0]["high"] == 105

    def test_mismatched_lengths(self):
        spec = candlestick(
            ["A", "B"],
            [10, 20, 30],  # longer
            [15, 25],
            [5, 15],
            [12, 22],
        )
        candles = spec.traces[0]["candles"]
        assert len(candles) == 2  # min of all lengths


class TestRendering:
    """Test that all advanced charts can be rendered to dict and SVG."""

    def test_render_all_to_dict(self):
        from forgeviz import render
        specs = [
            waterfall(["A", "B"], [10, -5]),
            funnel(["L", "Q"], [100, 50]),
            treemap(["X", "Y"], [60, 40]),
            radar(["A", "B", "C"], {"S": [1, 2, 3]}),
            violin({"G": [1, 2, 3, 4, 5, 6, 7, 8]}),
            sankey(["A", "B"], [{"source": 0, "target": 1, "value": 5}]),
            candlestick(["D1"], [10], [15], [8], [12]),
        ]
        for spec in specs:
            d = render(spec, format="dict")
            assert isinstance(d, dict)
            assert "traces" in d
