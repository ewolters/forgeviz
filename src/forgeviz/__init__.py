"""ForgeViz — zero-dependency data visualization.

Python builds the spec. JS renders it. SVG for server-side.
No Plotly. No D3. No npm. No CDN. 15KB JS.

Usage:
    from forgeviz.charts.control import control_chart
    from forgeviz.renderers.plotly import to_plotly
    from forgeviz.renderers.svg import to_svg

    spec = control_chart(data, ucl=24, lcl=22, cl=23)
    plotly_json = to_plotly(spec)    # Plotly JSON (backward compat)
    svg_string = to_svg(spec)        # Pure SVG for PDF/export
    # Or send spec as JSON to forgeviz.js on the client
"""

__version__ = "0.1.0"

from .core.dashboard import DashboardBuilder, DashboardSpec
from .core.export import to_csv, to_data_json, to_table
from .core.report import ReportBuilder, ReportSpec
from .core.spec import ChartSpec, render
from .core.streaming import StreamingSpec
from .renderers.html import content_hash, diff_specs, to_html

__all__ = [
    "ChartSpec", "DashboardBuilder", "DashboardSpec",
    "ReportBuilder", "ReportSpec", "StreamingSpec",
    "content_hash", "diff_specs",
    "render", "to_csv", "to_data_json", "to_html", "to_table",
    "__version__",
]
