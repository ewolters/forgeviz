"""Composed Reports — multi-chart documents delivered as atomic units.

A ReportSpec sequences ChartSpecs into a paginated document with sections,
headers, and narrative blocks. The app decides what goes in the report;
ForgeViz renders it as a single artifact.

Not a dashboard (interactive, grid layout, cross-filtering).
A report (sequential, paginated, printable, emailable).

Usage:
    from forgeviz.core.report import ReportSpec, ReportBuilder

    report = (ReportBuilder("Weekly Quality Review")
        .section("SPC Overview")
        .text("Control charts for critical characteristics.")
        .chart(xbar_spec)
        .chart(capability_spec)
        .section("Gage R&R")
        .text("Measurement system validated per AIAG guidelines.")
        .chart(grr_spec)
        .page_break()
        .section("Recommendations")
        .text("1. Investigate Tool 3 wear pattern.\\n2. Revalidate Gage #7.")
        .build())

    html = report.to_html()       # self-contained HTML document
    svg_pages = report.to_svg()   # list of SVG strings, one per page
    data = report.to_dict()       # JSON-serializable
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .spec import ChartSpec


@dataclass
class ReportBlock:
    """A single block in a report."""

    block_type: str  # "chart", "text", "section", "page_break"
    content: Any = None  # ChartSpec for chart, str for text/section, None for page_break

    def to_dict(self) -> dict:
        d = {"type": self.block_type}
        if self.block_type == "chart" and self.content is not None:
            d["spec"] = self.content.to_dict() if hasattr(self.content, "to_dict") else self.content
        elif self.block_type in ("text", "section"):
            d["content"] = self.content
        return d


@dataclass
class ReportSpec:
    """A composed report — sequential document of charts, text, and sections."""

    title: str = ""
    subtitle: str = ""
    author: str = ""
    date: str = ""
    theme: str = "svend_dark"
    blocks: list[ReportBlock] = field(default_factory=list)

    # Page dimensions (for HTML/PDF rendering)
    page_width: int = 900
    margin: int = 40

    def add_section(self, title: str) -> ReportSpec:
        self.blocks.append(ReportBlock("section", title))
        return self

    def add_text(self, text: str) -> ReportSpec:
        self.blocks.append(ReportBlock("text", text))
        return self

    def add_chart(self, spec: ChartSpec) -> ReportSpec:
        self.blocks.append(ReportBlock("chart", spec))
        return self

    def add_page_break(self) -> ReportSpec:
        self.blocks.append(ReportBlock("page_break"))
        return self

    @property
    def chart_count(self) -> int:
        return sum(1 for b in self.blocks if b.block_type == "chart")

    @property
    def section_count(self) -> int:
        return sum(1 for b in self.blocks if b.block_type == "section")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "date": self.date,
            "theme": self.theme,
            "page_width": self.page_width,
            "blocks": [b.to_dict() for b in self.blocks],
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)

    def to_svg(self) -> list[str]:
        """Render each chart block as SVG. Returns list of SVGs."""
        from ..renderers.svg import to_svg
        svgs = []
        for block in self.blocks:
            if block.block_type == "chart" and isinstance(block.content, ChartSpec):
                svgs.append(to_svg(block.content))
        return svgs

    def to_html(self) -> str:
        """Render as a self-contained HTML report document."""
        from ..renderers.html import _load_js, content_hash
        from .colors import get_theme

        theme = get_theme(self.theme)
        core_js = _load_js("forgeviz.js")
        interact_js = _load_js("forgeviz-interact.js")

        # Build chart specs JSON array for JS rendering
        chart_specs = []
        for block in self.blocks:
            if block.block_type == "chart" and isinstance(block.content, ChartSpec):
                chart_specs.append(block.content.to_dict())

        specs_json = json.dumps(chart_specs, default=str)
        report_hash = content_hash(ChartSpec(title=self.title)) if not chart_specs else content_hash(
            next(b.content for b in self.blocks if b.block_type == "chart")
        )

        # Build body HTML
        body_parts = []
        chart_idx = 0

        for block in self.blocks:
            if block.block_type == "section":
                body_parts.append(
                    f'<h2 style="color:{theme["text"]};font-size:18px;margin:32px 0 12px;'
                    f'padding-bottom:6px;border-bottom:1px solid {theme.get("axis", "#333")}">'
                    f'{block.content}</h2>'
                )
            elif block.block_type == "text":
                lines = block.content.replace("\n", "<br>")
                body_parts.append(
                    f'<p style="color:{theme["text_secondary"]};font-size:13px;'
                    f'line-height:1.6;margin:8px 0 16px">{lines}</p>'
                )
            elif block.block_type == "chart":
                body_parts.append(f'<div id="chart-{chart_idx}" style="margin:16px 0 24px"></div>')
                chart_idx += 1
            elif block.block_type == "page_break":
                body_parts.append('<div style="page-break-after:always;margin:40px 0;'
                                  f'border-top:1px solid {theme.get("axis", "#333")}"></div>')

        body_html = "\n".join(body_parts)

        # Render charts JS
        render_js_parts = []
        for i in range(len(chart_specs)):
            render_js_parts.append(
                f'ForgeViz.render(document.getElementById("chart-{i}"), specs[{i}], '
                f'{{interactive: true, toolbar: true}});'
            )
        render_js = "\n    ".join(render_js_parts)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self.title or "ForgeViz Report"}</title>
<meta name="generator" content="ForgeViz Report">
<meta name="forgeviz-hash" content="{report_hash}">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: {theme["bg"]};
    color: {theme["text"]};
    font-family: {theme["font"]};
    max-width: {self.page_width}px;
    margin: 0 auto;
    padding: {self.margin}px;
    line-height: 1.5;
  }}
  .report-header {{
    margin-bottom: 32px;
    padding-bottom: 16px;
    border-bottom: 2px solid {theme.get("accent", "#4a9f6e")};
  }}
  .report-title {{
    font-size: 24px;
    font-weight: 600;
    color: {theme["text"]};
  }}
  .report-subtitle {{
    font-size: 14px;
    color: {theme["text_secondary"]};
    margin-top: 4px;
  }}
  .report-meta {{
    font-size: 11px;
    color: {theme["text_secondary"]};
    margin-top: 8px;
    font-family: {theme.get("font_mono", "monospace")};
  }}
  .report-footer {{
    margin-top: 40px;
    padding-top: 12px;
    border-top: 1px solid {theme.get("axis", "#333")};
    text-align: center;
    font-size: 10px;
    color: {theme["text_secondary"]};
    font-family: {theme.get("font_mono", "monospace")};
  }}
  @media print {{
    body {{ background: white; color: black; }}
    .report-footer {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="report-header">
  <div class="report-title">{self.title}</div>
  {"<div class='report-subtitle'>" + self.subtitle + "</div>" if self.subtitle else ""}
  <div class="report-meta">
    {f"{self.author} · " if self.author else ""}{self.date if self.date else ""}
    {f" · {self.chart_count} charts, {self.section_count} sections" if self.chart_count else ""}
  </div>
</div>

{body_html}

<div class="report-footer">
  forgeviz:{report_hash} · {self.chart_count} charts
</div>

<script>
{core_js}
</script>
<script>
{interact_js}
</script>
<script>
(function() {{
  var specs = {specs_json};
  {render_js}
}})();
</script>
</body>
</html>"""

    @classmethod
    def from_dict(cls, d: dict) -> ReportSpec:
        """Reconstruct from serialized dict."""
        blocks = []
        for bd in d.get("blocks", []):
            bt = bd.get("type", "text")
            if bt == "chart":
                spec_data = bd.get("spec", {})
                blocks.append(ReportBlock("chart", ChartSpec(
                    title=spec_data.get("title", ""),
                    chart_type=spec_data.get("chart_type", ""),
                    theme=spec_data.get("theme", "svend_dark"),
                )))
            elif bt == "page_break":
                blocks.append(ReportBlock("page_break"))
            else:
                blocks.append(ReportBlock(bt, bd.get("content", "")))

        return cls(
            title=d.get("title", ""),
            subtitle=d.get("subtitle", ""),
            author=d.get("author", ""),
            date=d.get("date", ""),
            theme=d.get("theme", "svend_dark"),
            blocks=blocks,
        )


class ReportBuilder:
    """Fluent builder for composed reports."""

    def __init__(self, title: str = "", theme: str = "svend_dark") -> None:
        self.report = ReportSpec(title=title, theme=theme)

    def subtitle(self, text: str) -> ReportBuilder:
        self.report.subtitle = text
        return self

    def author(self, name: str) -> ReportBuilder:
        self.report.author = name
        return self

    def date(self, date_str: str) -> ReportBuilder:
        self.report.date = date_str
        return self

    def section(self, title: str) -> ReportBuilder:
        self.report.add_section(title)
        return self

    def text(self, content: str) -> ReportBuilder:
        self.report.add_text(content)
        return self

    def chart(self, spec: ChartSpec) -> ReportBuilder:
        self.report.add_chart(spec)
        return self

    def page_break(self) -> ReportBuilder:
        self.report.add_page_break()
        return self

    def theme(self, name: str) -> ReportBuilder:
        self.report.theme = name
        return self

    def build(self) -> ReportSpec:
        return self.report
