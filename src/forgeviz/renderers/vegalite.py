"""Vega-Lite renderer — future alternative to Plotly.

Converts ChartSpec → Vega-Lite JSON specification.
Stub for now — Plotly and SVG are the primary renderers.
"""

from __future__ import annotations

from ..core.spec import ChartSpec


def to_vegalite(spec: ChartSpec) -> dict:
    """Convert ChartSpec to Vega-Lite specification. Stub."""
    raise NotImplementedError("Vega-Lite renderer not yet implemented. Use 'plotly' or 'svg' format.")
