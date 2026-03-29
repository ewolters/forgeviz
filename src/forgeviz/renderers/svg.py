"""SVG renderer — pure Python, zero dependencies.

Converts ChartSpec → SVG string. Used for:
- PDF export (ForgeDoc embeds SVG)
- Server-side rendering (no browser needed)
- Static image export
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..core.colors import get_theme
from ..core.spec import ChartSpec


def to_svg(spec: ChartSpec, width: int | None = None, height: int | None = None) -> str:
    """Convert ChartSpec to SVG string."""
    w = width or spec.width or 800
    h = height or spec.height or 400
    theme = get_theme(spec.theme)

    # Plot area margins
    ml, mr, mt, mb = 60, 20, 40, 60
    pw = w - ml - mr
    ph = h - mt - mb

    # Compute data ranges
    all_x = []
    all_y = []
    for trace in spec.traces:
        if hasattr(trace, 'x') and hasattr(trace, 'y'):
            all_x.extend([v for v in trace.x if isinstance(v, (int, float))])
            all_y.extend([v for v in trace.y if isinstance(v, (int, float))])
    for ref in spec.reference_lines:
        if ref.axis == "y":
            all_y.append(ref.value)

    if not all_x or not all_y:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><text x="{w//2}" y="{h//2}" text-anchor="middle" fill="{theme["text"]}">No data</text></svg>'

    x_min = min(all_x) if all(isinstance(v, (int, float)) for v in all_x) else 0
    x_max = max(all_x) if all(isinstance(v, (int, float)) for v in all_x) else len(all_x)
    y_min = min(all_y)
    y_max = max(all_y)

    # Add padding
    y_range = y_max - y_min or 1
    y_min -= y_range * 0.05
    y_max += y_range * 0.05
    x_range = x_max - x_min or 1

    def sx(val):
        return ml + (val - x_min) / x_range * pw if x_range else ml + pw / 2

    def sy(val):
        return mt + ph - (val - y_min) / (y_max - y_min) * ph if (y_max - y_min) else mt + ph / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'style="background:{theme["bg"]};font-family:{theme["font"]}">'
    ]

    # Title
    if spec.title:
        parts.append(f'<text x="{w//2}" y="20" text-anchor="middle" fill="{theme["text"]}" font-size="14" font-weight="500">{escape(spec.title)}</text>')

    # Grid lines
    x_axis_spec = spec.x_axis if isinstance(spec.x_axis, dict) else spec.x_axis.__dict__ if hasattr(spec.x_axis, '__dict__') else {}
    y_axis_spec = spec.y_axis if isinstance(spec.y_axis, dict) else spec.y_axis.__dict__ if hasattr(spec.y_axis, '__dict__') else {}

    n_yticks = 5
    y_step = (y_max - y_min) / n_yticks
    for i in range(n_yticks + 1):
        val = y_min + i * y_step
        yy = sy(val)
        parts.append(f'<line x1="{ml}" y1="{yy}" x2="{ml+pw}" y2="{yy}" stroke="{theme["grid"]}" stroke-width="1"/>')
        parts.append(f'<text x="{ml-5}" y="{yy+4}" text-anchor="end" fill="{theme["text_secondary"]}" font-size="10">{val:.2f}</text>')

    # Zones
    for zone in spec.zones:
        if zone.axis == "y":
            zy1 = sy(zone.high)
            zy2 = sy(zone.low)
            parts.append(f'<rect x="{ml}" y="{zy1}" width="{pw}" height="{zy2-zy1}" fill="{zone.color}"/>')

    # Reference lines
    for ref in spec.reference_lines:
        if ref.axis == "y":
            ry = sy(ref.value)
            dash = "8,4" if ref.dash == "dashed" else "3,3" if ref.dash == "dotted" else ""
            parts.append(f'<line x1="{ml}" y1="{ry}" x2="{ml+pw}" y2="{ry}" stroke="{ref.color}" stroke-width="{ref.width}" stroke-dasharray="{dash}"/>')
            if ref.label:
                parts.append(f'<text x="{ml+pw+3}" y="{ry+4}" fill="{ref.color}" font-size="9">{escape(ref.label)}</text>')

    # Traces
    for ti, trace in enumerate(spec.traces):
        if isinstance(trace, dict):
            continue
        if not hasattr(trace, 'x') or not hasattr(trace, 'y'):
            continue
        if not trace.x or not trace.y:
            continue

        color = trace.color or theme["colors"][ti % len(theme["colors"])]

        if trace.trace_type in ("line", "step"):
            points = []
            for i in range(min(len(trace.x), len(trace.y))):
                xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else i
                points.append(f"{sx(xv):.1f},{sy(trace.y[i]):.1f}")
            if points:
                dash = "8,4" if trace.dash == "dashed" else "3,3" if trace.dash == "dotted" else ""
                parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="{trace.width}" stroke-dasharray="{dash}"/>')

                if trace.marker_size > 0:
                    for i in range(min(len(trace.x), len(trace.y))):
                        xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else i
                        parts.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(trace.y[i]):.1f}" r="{trace.marker_size/2}" fill="{color}"/>')

        elif trace.trace_type == "scatter":
            for i in range(min(len(trace.x), len(trace.y))):
                xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else i
                r = (trace.marker_size or 6) / 2
                parts.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(trace.y[i]):.1f}" r="{r}" fill="{color}" opacity="{trace.opacity}"/>')

        elif trace.trace_type == "bar":
            n_bars = len(trace.y)
            bar_w = max(2, pw / n_bars * 0.7)
            for i in range(min(len(trace.x), len(trace.y))):
                xv = i if not isinstance(trace.x[i], (int, float)) else trace.x[i]
                bx = sx(xv) - bar_w / 2
                by = sy(trace.y[i])
                bh = sy(y_min) - by
                parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="{trace.opacity}"/>')

    # Markers (OOC points etc)
    for marker in spec.markers:
        if marker.indices and spec.traces:
            first = spec.traces[0]
            if hasattr(first, 'x') and hasattr(first, 'y'):
                for idx in marker.indices:
                    if idx < len(first.x) and idx < len(first.y):
                        xv = first.x[idx] if isinstance(first.x[idx], (int, float)) else idx
                        parts.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(first.y[idx]):.1f}" r="{marker.size/2}" fill="none" stroke="{marker.color}" stroke-width="2"/>')

    # Axes
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="{theme["axis"]}" stroke-width="1"/>')
    parts.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="{theme["axis"]}" stroke-width="1"/>')

    # Axis labels
    x_label = x_axis_spec.get("label", "")
    y_label = y_axis_spec.get("label", "")
    if x_label:
        parts.append(f'<text x="{ml+pw//2}" y="{h-10}" text-anchor="middle" fill="{theme["text_secondary"]}" font-size="11">{escape(x_label)}</text>')
    if y_label:
        parts.append(f'<text x="15" y="{mt+ph//2}" text-anchor="middle" fill="{theme["text_secondary"]}" font-size="11" transform="rotate(-90,15,{mt+ph//2})">{escape(y_label)}</text>')

    parts.append("</svg>")
    return "\n".join(parts)
