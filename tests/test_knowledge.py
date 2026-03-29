"""Tests for OLR-001 knowledge health visualizations."""

import pytest

from forgeviz.charts.knowledge import (
    ddmrp_buffer_status,
    detection_ladder,
    evidence_timeline,
    knowledge_health_sparklines,
    maturity_trajectory,
    proactive_reactive_gauge,
    yield_from_cpk_curve,
)


class TestKnowledgeHealth:
    def test_sparklines(self):
        dates = ["W1", "W2", "W3", "W4"]
        spec = knowledge_health_sparklines(
            dates,
            calibration_rate=[0.3, 0.4, 0.5, 0.55],
            staleness_rate=[0.2, 0.15, 0.12, 0.10],
            contradiction_rate=[0.05, 0.04, 0.03, 0.02],
            gap_ratio=[0.5, 0.45, 0.4, 0.35],
        )
        assert spec.chart_type == "knowledge_health"
        assert len(spec.traces) == 4

    def test_maturity_trajectory(self):
        spec = maturity_trajectory(
            dates=["Jan", "Apr", "Jul", "Oct"],
            levels=[1, 1, 2, 2],
        )
        assert spec.chart_type == "maturity_trajectory"
        assert len(spec.zones) == 4  # one per level
        assert len(spec.traces) >= 1


class TestDetectionLadder:
    def test_basic(self):
        levels = {1: 2, 2: 3, 3: 5, 4: 8, 5: 2}
        spec = detection_ladder(levels, classification_tier="critical")
        assert spec.chart_type == "detection_ladder"
        assert "critical" in spec.subtitle

    def test_empty_levels(self):
        spec = detection_ladder({}, classification_tier="minor")
        assert spec.chart_type == "detection_ladder"


class TestEvidenceTimeline:
    def test_basic(self):
        spec = evidence_timeline(
            dates=["2026-01", "2026-02", "2026-03"],
            source_types=["doe", "investigation", "spc"],
            effect_sizes=[0.3, 0.25, None],
            retracted=[False, False, True],
        )
        assert spec.chart_type == "evidence_timeline"
        assert len(spec.traces) == 3


class TestProactiveReactive:
    def test_high_proactive(self):
        spec = proactive_reactive_gauge(proactive_pct=0.92)
        assert spec.chart_type == "proactive_gauge"
        assert len(spec.traces) >= 2

    def test_low_proactive(self):
        spec = proactive_reactive_gauge(proactive_pct=0.35)
        assert spec.chart_type == "proactive_gauge"


class TestDDMRPBuffer:
    def test_green_zone(self):
        spec = ddmrp_buffer_status(
            item_name="Widget A",
            net_flow_position=1500,
            top_of_green=1750,
            top_of_yellow=1250,
            top_of_red=750,
            red_base=500,
        )
        assert spec.chart_type == "ddmrp_buffer"
        assert len(spec.zones) == 4

    def test_red_zone(self):
        spec = ddmrp_buffer_status(
            item_name="Widget B",
            net_flow_position=300,
            top_of_green=1750,
            top_of_yellow=1250,
            top_of_red=750,
            red_base=500,
        )
        assert spec.chart_type == "ddmrp_buffer"


class TestYieldCpk:
    def test_basic_curve(self):
        spec = yield_from_cpk_curve()
        assert spec.chart_type == "yield_cpk"
        assert len(spec.traces) >= 1

    def test_with_current(self):
        spec = yield_from_cpk_curve(current_cpk=1.15)
        assert len(spec.annotations) >= 1
        assert "1.15" in spec.annotations[-1]["text"]

    def test_custom_range(self):
        spec = yield_from_cpk_curve(cpk_range=[0.5, 1.0, 1.5, 2.0])
        assert spec.traces[0].x == [0.5, 1.0, 1.5, 2.0]
