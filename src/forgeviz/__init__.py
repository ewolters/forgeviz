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

from .core.spec import ChartSpec, render
