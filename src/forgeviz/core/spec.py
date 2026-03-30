"""ChartSpec — the universal chart specification.

Every chart in forgeviz is a ChartSpec. Every renderer consumes it.
ChartSpec is a plain dict-like structure — JSON-serializable,
no dependencies, no magic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Trace:
    """A single data series on the chart."""

    x: list[Any]
    y: list[Any]
    name: str = ""
    trace_type: str = "line"  # line, scatter, bar, area, step
    color: str = ""
    dash: str = ""  # solid, dashed, dotted
    width: float = 1.5
    marker_size: float = 0
    marker_symbol: str = "circle"
    fill: str = ""  # "tozeroy", "tonexty", ""
    opacity: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)  # per-point data for tooltips


@dataclass
class ReferenceLine:
    """A horizontal or vertical reference line."""

    value: float
    axis: str = "y"  # "x" or "y"
    color: str = "#888"
    dash: str = "dashed"
    width: float = 1.0
    label: str = ""
    label_position: str = "right"  # right, left, top, bottom


@dataclass
class Zone:
    """A shaded zone between two values."""

    low: float
    high: float
    axis: str = "y"
    color: str = "rgba(255,0,0,0.1)"
    label: str = ""


@dataclass
class Marker:
    """Special markers on specific points."""

    indices: list[int]
    color: str = "red"
    size: float = 8
    symbol: str = "circle"  # circle, square, triangle, x
    label: str = ""


@dataclass
class Axis:
    """Axis configuration."""

    label: str = ""
    min_val: float | None = None
    max_val: float | None = None
    tick_format: str = ""  # ".2f", ".0%", etc.
    scale: str = "linear"  # linear, log, date
    grid: bool = True


@dataclass
class ChartSpec:
    """Universal chart specification.

    JSON-serializable. Every renderer consumes this.
    Send to forgeviz.js on the client, or to SVG/Plotly renderers on the server.
    """

    title: str = ""
    subtitle: str = ""
    chart_type: str = ""  # informational — "control_chart", "histogram", etc.

    traces: list[Trace] = field(default_factory=list)
    reference_lines: list[ReferenceLine] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)

    x_axis: Axis = field(default_factory=Axis)
    y_axis: Axis = field(default_factory=Axis)

    width: int = 800
    height: int = 400
    theme: str = "svend_dark"

    # Annotations
    annotations: list[dict] = field(default_factory=list)
    # [{x, y, text, color, font_size}]

    # Legend
    show_legend: bool = True
    legend_position: str = "bottom"  # top, bottom, right, none

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        from dataclasses import asdict
        return asdict(self)

    def to_json(self, **kwargs) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    def add_trace(self, x, y, **kwargs) -> Trace:
        t = Trace(x=list(x), y=list(y), **kwargs)
        self.traces.append(t)
        return t

    def add_reference_line(self, value, **kwargs) -> ReferenceLine:
        r = ReferenceLine(value=value, **kwargs)
        self.reference_lines.append(r)
        return r

    def add_zone(self, low, high, **kwargs) -> Zone:
        z = Zone(low=low, high=high, **kwargs)
        self.zones.append(z)
        return z

    def add_marker(self, indices, **kwargs) -> Marker:
        m = Marker(indices=indices, **kwargs)
        self.markers.append(m)
        return m


def render(spec: ChartSpec, format: str = "dict") -> Any:
    """Render a ChartSpec to the specified format.

    Args:
    """
    if format == "dict":
        return spec.to_dict()
    elif format == "json":
        return spec.to_json(indent=2)
    elif format == "plotly":
        from ..renderers.plotly import to_plotly
        return to_plotly(spec)
    elif format == "svg":
        from ..renderers.svg import to_svg
        return to_svg(spec)
    else:
        raise ValueError(f"Unknown format: {format}")
