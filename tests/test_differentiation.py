"""Tests for ForgeViz differentiation features — diffable, socratic, streaming."""

import json

import pytest


# ── Diffable Charts ─────────────────────────────────────────────────────


class TestToHtml:
    def test_self_contained(self):
        from forgeviz import ChartSpec, to_html
        spec = ChartSpec(title="Test Chart")
        spec.add_trace([1, 2, 3], [4, 5, 6], name="data")
        html = to_html(spec)
        assert "<!DOCTYPE html>" in html
        assert "ForgeViz" in html
        assert "Test Chart" in html
        assert "forgeviz:" in html  # content hash

    def test_embedded_data(self):
        from forgeviz import ChartSpec, to_html
        spec = ChartSpec(title="Data Test")
        spec.add_trace([10, 20], [30, 40])
        html = to_html(spec)
        assert "10" in html
        assert "30" in html

    def test_content_hash_deterministic(self):
        from forgeviz import ChartSpec, content_hash
        spec = ChartSpec(title="Hash Test")
        spec.add_trace([1, 2], [3, 4])
        h1 = content_hash(spec)
        h2 = content_hash(spec)
        assert h1 == h2
        assert len(h1) == 12

    def test_content_hash_changes(self):
        from forgeviz import ChartSpec, content_hash
        spec1 = ChartSpec(title="V1")
        spec1.add_trace([1, 2], [3, 4])
        spec2 = ChartSpec(title="V2")
        spec2.add_trace([1, 2], [3, 5])
        assert content_hash(spec1) != content_hash(spec2)

    def test_diff_specs_identical(self):
        from forgeviz import ChartSpec, diff_specs
        spec = ChartSpec(title="Same")
        spec.add_trace([1, 2], [3, 4])
        result = diff_specs(spec, spec)
        assert result["identical"]

    def test_diff_specs_title_change(self):
        from forgeviz import ChartSpec, diff_specs
        a = ChartSpec(title="Old Title")
        a.add_trace([1], [2])
        b = ChartSpec(title="New Title")
        b.add_trace([1], [2])
        result = diff_specs(a, b)
        assert "title" in result
        assert result["title"]["from"] == "Old Title"
        assert result["title"]["to"] == "New Title"

    def test_diff_specs_data_change(self):
        from forgeviz import ChartSpec, diff_specs
        a = ChartSpec(title="T")
        a.add_trace([1, 2, 3], [4, 5, 6])
        b = ChartSpec(title="T")
        b.add_trace([1, 2, 3], [4, 5, 99])
        result = diff_specs(a, b)
        assert "traces" in result
        assert result["traces"][0]["changes"]["y"]["values_changed"] == 1


# ── Socratic Charts ─────────────────────────────────────────────────────


class TestGapChart:
    def test_basic_gap(self):
        from forgeviz.charts.socratic import gap_chart
        actual = [10.1, 10.5, 9.8, 11.2, 10.0, 9.5, 10.3, 10.8, 9.9, 10.1]
        spec = gap_chart(actual, theoretical=10.0, title="Diameter Gap")
        assert spec.chart_type == "gap_chart"
        assert len(spec.traces) == 3  # theoretical + actual + gap bars
        assert spec.title == "Diameter Gap"

    def test_anticipatory_embedded(self):
        from forgeviz.charts.socratic import gap_chart
        actual = [10 + i * 0.1 for i in range(20)]
        spec = gap_chart(actual, theoretical=10.0)
        assert spec.interactive is not None
        assert spec.interactive["type"] == "socratic"
        assert "anticipatory" in spec.interactive
        assert "direction" in spec.interactive["anticipatory"]

    def test_list_theoretical(self):
        from forgeviz.charts.socratic import gap_chart
        actual = [10, 11, 12, 13, 14]
        theoretical = [10, 10.5, 11, 11.5, 12]
        spec = gap_chart(actual, theoretical=theoretical)
        assert len(spec.traces) == 3


class TestCapabilityGap:
    def test_basic(self):
        import random
        random.seed(42)
        from forgeviz.charts.socratic import capability_gap
        data = [random.gauss(25, 0.5) for _ in range(100)]
        spec = capability_gap(data, usl=26.0, lsl=24.0)
        assert spec.chart_type == "capability_gap"
        assert "Cpk" in spec.subtitle
        assert len(spec.reference_lines) >= 3  # USL, LSL, target, mean

    def test_anticipatory_cpk_trend(self):
        import random
        random.seed(42)
        from forgeviz.charts.socratic import capability_gap
        data = [random.gauss(25, 0.5) for _ in range(50)]
        spec = capability_gap(data, usl=26.0, lsl=24.0)
        assert spec.interactive is not None
        assert "cpk_current" in spec.interactive["anticipatory"]
        assert "cpk_direction" in spec.interactive["anticipatory"]


class TestOeeGap:
    def test_basic(self):
        from forgeviz.charts.socratic import oee_gap
        spec = oee_gap(
            availability=[88, 90, 85, 92, 87],
            performance=[93, 95, 91, 94, 92],
            quality=[99, 99.5, 98.5, 99.2, 99.1],
        )
        assert spec.chart_type == "oee_gap"
        assert "OEE=" in spec.subtitle
        assert len(spec.traces) >= 1


# ── Streaming Specs ─────────────────────────────────────────────────────


class TestStreamingSpec:
    def test_append_and_stats(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=26, cl=25, lcl=24)
        stream.append(25.1)
        stream.append(25.2)
        stream.append(24.8)
        assert stream.stats.n == 3
        assert abs(stream.stats.mean - 25.033) < 0.01
        assert len(stream.y_data) == 3

    def test_alert_ooc(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=26, cl=25, lcl=24)
        alerts = stream.append(27.0)  # above UCL
        assert len(alerts) == 1
        assert alerts[0].alert_type == "ooc_upper"

    def test_alert_shift(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=30, cl=25, lcl=20)
        for v in [26, 27, 26.5, 27.1, 26.8, 27.3, 26.9]:
            alerts = stream.append(v)
        # Last append should trigger shift alert (7 above CL)
        assert any(a.alert_type == "shift" for a in alerts)

    def test_alert_trend(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=50, cl=25, lcl=0)
        for v in [20, 21, 22, 23, 24, 25, 26]:
            alerts = stream.append(v)
        assert any(a.alert_type == "trend" for a in alerts)

    def test_to_chart_spec(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Diameter", ucl=26, cl=25, lcl=24)
        stream.append_batch([25.1, 25.2, 24.8, 25.0, 25.3])
        spec = stream.to_chart_spec()
        assert spec.title == "Diameter"
        assert spec.chart_type == "control_chart"
        assert spec.interactive is not None
        assert spec.interactive["type"] == "streaming"
        assert spec.interactive["stats"]["n"] == 5

    def test_rolling_window(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=30, cl=25, lcl=20, max_points=10)
        stream.append_batch([25 + i * 0.01 for i in range(20)])
        assert len(stream.y_data) == 10  # trimmed to window
        assert stream.stats.n == 20  # stats track all data

    def test_content_hash_changes(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=30, cl=25, lcl=20)
        stream.append(25.0)
        h1 = stream.content_hash()
        stream.append(25.1)
        h2 = stream.content_hash()
        assert h1 != h2

    def test_summary(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=30, cl=25, lcl=20)
        stream.append_batch([25.0, 25.1, 24.9])
        s = stream.summary()
        assert s["version"] == 3
        assert s["in_control"]
        assert s["stats"]["n"] == 3

    def test_batch_with_x_values(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec(title="Custom")
        stream.append_batch([1, 2, 3], x_values=["a", "b", "c"])
        assert stream.x_data == ["a", "b", "c"]

    def test_spec_violation_alerts(self):
        from forgeviz import StreamingSpec
        stream = StreamingSpec.control_chart("Test", ucl=30, cl=25, lcl=20, usl=28, lsl=22)
        alerts = stream.append(29.0)  # above USL but within UCL
        assert any(a.alert_type == "above_usl" for a in alerts)
