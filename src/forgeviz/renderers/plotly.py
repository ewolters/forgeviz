"""Plotly JSON renderer — backward compatible with SVEND's current frontend.

Converts ChartSpec → Plotly JSON (traces + layout dict).
Does NOT import plotly. Just builds the dict structure that Plotly.js expects.
"""

from __future__ import annotations

from ..core.colors import get_theme
from ..core.spec import ChartSpec


def to_plotly(spec: ChartSpec) -> dict:
    """Convert ChartSpec to Plotly-compatible JSON.

    Returns: {"data": [...traces], "layout": {...}}
    """
    theme = get_theme(spec.theme)
    traces = []
    shapes = []
    annotations = []

    # Convert traces
    for i, trace in enumerate(spec.traces):
        if isinstance(trace, dict):
            # Box plot or other dict-based traces
            traces.append(trace)
            continue

        plotly_trace = {
            "x": trace.x,
            "y": trace.y,
            "name": trace.name,
        }

        if trace.trace_type == "line":
            plotly_trace["type"] = "scatter"
            plotly_trace["mode"] = "lines+markers" if trace.marker_size > 0 else "lines"
            plotly_trace["line"] = {
                "color": trace.color or theme["colors"][i % len(theme["colors"])],
                "width": trace.width,
            }
            if trace.dash:
                plotly_trace["line"]["dash"] = trace.dash
            if trace.marker_size > 0:
                plotly_trace["marker"] = {"size": trace.marker_size}
        elif trace.trace_type == "scatter":
            plotly_trace["type"] = "scatter"
            plotly_trace["mode"] = "markers"
            plotly_trace["marker"] = {
                "size": trace.marker_size or 6,
                "color": trace.color or theme["colors"][i % len(theme["colors"])],
            }
        elif trace.trace_type == "bar":
            plotly_trace["type"] = "bar"
            plotly_trace["marker"] = {
                "color": trace.color or theme["colors"][i % len(theme["colors"])],
                "opacity": trace.opacity,
            }
        elif trace.trace_type == "area":
            plotly_trace["type"] = "scatter"
            plotly_trace["mode"] = "lines"
            plotly_trace["fill"] = trace.fill or "tozeroy"
            plotly_trace["line"] = {"color": trace.color, "width": 0}
            plotly_trace["fillcolor"] = trace.color.replace(")", f",{trace.opacity})").replace("rgb", "rgba") if "rgb" in (trace.color or "") else trace.color
        elif trace.trace_type == "step":
            plotly_trace["type"] = "scatter"
            plotly_trace["mode"] = "lines"
            plotly_trace["line"] = {"shape": "hv", "color": trace.color, "width": trace.width}

        traces.append(plotly_trace)

    # Convert reference lines to shapes
    for ref in spec.reference_lines:
        if ref.axis == "y":
            shapes.append({
                "type": "line",
                "y0": ref.value, "y1": ref.value,
                "x0": 0, "x1": 1, "xref": "paper",
                "line": {"color": ref.color, "width": ref.width, "dash": ref.dash},
            })
            if ref.label:
                annotations.append({
                    "x": 1, "xref": "paper", "y": ref.value,
                    "text": f" {ref.label}", "showarrow": False,
                    "xanchor": "left", "font": {"size": 10, "color": ref.color},
                })
        elif ref.axis == "x":
            shapes.append({
                "type": "line",
                "x0": ref.value, "x1": ref.value,
                "y0": 0, "y1": 1, "yref": "paper",
                "line": {"color": ref.color, "width": ref.width, "dash": ref.dash},
            })

    # Convert zones to shapes
    for zone in spec.zones:
        if zone.axis == "y":
            shapes.append({
                "type": "rect",
                "y0": zone.low, "y1": zone.high,
                "x0": 0, "x1": 1, "xref": "paper",
                "fillcolor": zone.color,
                "line": {"width": 0},
                "layer": "below",
            })

    # Convert markers to traces
    for marker in spec.markers:
        if marker.indices and spec.traces:
            first_trace = spec.traces[0]
            if hasattr(first_trace, 'x') and hasattr(first_trace, 'y'):
                mx = [first_trace.x[i] for i in marker.indices if i < len(first_trace.x)]
                my = [first_trace.y[i] for i in marker.indices if i < len(first_trace.y)]
                traces.append({
                    "type": "scatter",
                    "mode": "markers",
                    "x": mx, "y": my,
                    "name": marker.label or "Highlighted",
                    "marker": {"color": marker.color, "size": marker.size, "symbol": marker.symbol},
                    "showlegend": bool(marker.label),
                })

    # Layout
    x_axis_spec = spec.x_axis if isinstance(spec.x_axis, dict) else spec.x_axis.__dict__
    y_axis_spec = spec.y_axis if isinstance(spec.y_axis, dict) else spec.y_axis.__dict__

    layout = {
        "title": {"text": spec.title, "font": {"size": 14, "color": theme["text"]}},
        "paper_bgcolor": theme["bg"],
        "plot_bgcolor": theme["plot_bg"],
        "font": {"family": theme["font"], "size": 12, "color": theme["text"]},
        "xaxis": {
            "title": x_axis_spec.get("label", ""),
            "gridcolor": theme["grid"],
            "linecolor": theme["axis"],
            "zerolinecolor": theme["axis"],
        },
        "yaxis": {
            "title": y_axis_spec.get("label", ""),
            "gridcolor": theme["grid"],
            "linecolor": theme["axis"],
            "zerolinecolor": theme["axis"],
        },
        "shapes": shapes,
        "annotations": annotations,
        "showlegend": spec.show_legend,
        "legend": {"orientation": "h", "y": -0.15} if spec.legend_position == "bottom" else {},
        "margin": {"l": 60, "r": 20, "t": 40, "b": 60},
        "height": spec.height,
        "width": spec.width,
    }

    return {"data": traces, "layout": layout}
