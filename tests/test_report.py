"""Tests for composed reports and updated themes."""

from forgeviz import ChartSpec, ReportBuilder, ReportSpec
from forgeviz.core.colors import THEMES, get_theme


# ── Theme Sync Tests ────────────────────────────────────────────────────


class TestThemeSync:
    def test_all_production_themes_present(self):
        expected = {"svend_dark", "light", "nordic", "sandstone", "midnight",
                    "high_contrast", "print", "precision", "tufte"}
        assert expected.issubset(set(THEMES.keys()))

    def test_theme_count(self):
        assert len(THEMES) == 9

    def test_svend_dark_matches_production(self):
        t = get_theme("svend_dark")
        assert t["bg"] == "#0a0f0a"
        assert t["accent"] == "#4a9f6e"
        assert t["text"] == "#e8efe8"

    def test_light_green_tinted(self):
        t = get_theme("light")
        assert t["bg"] == "#f5f7f5"
        assert t["text"] == "#1a2a1a"
        assert t["accent"] == "#2d7a4a"

    def test_nordic_frost(self):
        t = get_theme("nordic")
        assert t["bg"] == "#f2f5f8"  # light, cool — not old dark Nord

    def test_sandstone_warm(self):
        t = get_theme("sandstone")
        assert t["bg"] == "#f7f4f0"
        assert t["text"] == "#2a2420"

    def test_midnight_vivid(self):
        t = get_theme("midnight")
        assert t["bg"] == "#0a0a14"
        assert t["accent"] == "#6a7fff"

    def test_high_contrast_accessible(self):
        t = get_theme("high_contrast")
        assert t["bg"] == "#000000"
        assert t["text"] == "#ffffff"

    def test_precision_document(self):
        t = get_theme("precision")
        assert t["bg"] == "#f5f0e8"
        assert "Georgia" in t["font"]
        assert t["accent"] == "#2a5f8f"

    def test_all_themes_have_required_keys(self):
        required = {"bg", "plot_bg", "text", "text_secondary", "grid", "axis",
                    "accent", "font", "font_mono", "colors"}
        for name, theme in THEMES.items():
            missing = required - set(theme.keys())
            assert not missing, f"Theme '{name}' missing keys: {missing}"

    def test_all_themes_have_10_colors(self):
        for name, theme in THEMES.items():
            assert len(theme["colors"]) == 10, f"Theme '{name}' has {len(theme['colors'])} colors"


# ── Report Builder Tests ────────────────────────────────────────────────


class TestReportBuilder:
    def test_fluent_build(self):
        report = (ReportBuilder("Weekly Review")
            .subtitle("Plant 3")
            .author("Eric")
            .date("2026-05-25")
            .section("SPC")
            .text("Control charts look good.")
            .chart(ChartSpec(title="X-bar"))
            .page_break()
            .section("Capability")
            .chart(ChartSpec(title="Cpk"))
            .build())
        assert report.title == "Weekly Review"
        assert report.chart_count == 2
        assert report.section_count == 2
        assert len(report.blocks) == 6  # section, text, chart, break, section, chart

    def test_theme_propagation(self):
        report = ReportBuilder("Test", theme="precision").build()
        assert report.theme == "precision"

    def test_to_dict_serializable(self):
        import json
        report = (ReportBuilder("Test")
            .section("S1")
            .chart(ChartSpec(title="C1"))
            .build())
        d = report.to_dict()
        s = json.dumps(d)  # must not raise
        assert "S1" in s
        assert "C1" in s

    def test_to_dict_structure(self):
        report = (ReportBuilder("R")
            .section("S")
            .text("T")
            .chart(ChartSpec(title="C"))
            .page_break()
            .build())
        d = report.to_dict()
        assert d["blocks"][0]["type"] == "section"
        assert d["blocks"][1]["type"] == "text"
        assert d["blocks"][2]["type"] == "chart"
        assert d["blocks"][3]["type"] == "page_break"


class TestReportSpec:
    def test_add_methods(self):
        r = ReportSpec(title="T")
        r.add_section("S1")
        r.add_text("body")
        r.add_chart(ChartSpec(title="C1"))
        r.add_page_break()
        assert len(r.blocks) == 4

    def test_to_svg(self):
        r = ReportSpec(title="T")
        r.add_chart(ChartSpec(title="C1"))
        r.add_chart(ChartSpec(title="C2"))
        svgs = r.to_svg()
        assert len(svgs) == 2
        assert all("<svg" in s for s in svgs)

    def test_to_html(self):
        r = ReportSpec(title="Quality Report", theme="precision")
        r.add_section("Overview")
        r.add_text("Everything is fine.")
        spec = ChartSpec(title="Trend")
        spec.add_trace([1, 2, 3], [4, 5, 6])
        r.add_chart(spec)
        html = r.to_html()
        assert "<!DOCTYPE html>" in html
        assert "Quality Report" in html
        assert "Overview" in html
        assert "Everything is fine." in html
        assert "forgeviz:" in html

    def test_to_html_precision_theme(self):
        r = ReportSpec(title="T", theme="precision")
        r.add_chart(ChartSpec(title="C"))
        html = r.to_html()
        assert "#f5f0e8" in html  # precision bg

    def test_from_dict_round_trip(self):
        r = ReportSpec(title="RT")
        r.add_section("S")
        r.add_text("T")
        r.add_chart(ChartSpec(title="C"))
        r.add_page_break()
        d = r.to_dict()
        restored = ReportSpec.from_dict(d)
        assert restored.title == "RT"
        assert len(restored.blocks) == 4
        assert restored.blocks[0].block_type == "section"
        assert restored.blocks[2].block_type == "chart"

    def test_empty_report(self):
        r = ReportSpec()
        assert r.chart_count == 0
        assert r.section_count == 0
        html = r.to_html()
        assert "<!DOCTYPE html>" in html
