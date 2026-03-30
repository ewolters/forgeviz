"""SVG renderer — pure Python, zero dependencies.

Converts ChartSpec → SVG string. Handles:
- Numeric and categorical x-axes
- Line, scatter, bar, area, step traces (Trace objects)
- Box plot and contour traces (dict-based)
- Reference lines, zones, markers, annotations
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..core.colors import get_theme
from ..core.spec import ChartSpec, Trace


def to_svg(spec: ChartSpec, width: int | None = None, height: int | None = None) -> str:
    """Convert ChartSpec to SVG string."""
    w = width or spec.width or 800
    h = height or spec.height or 400
    theme = get_theme(spec.theme)

    ml, mr, mt, mb = 65, 30, 40 if spec.title else 20, 60
    pw = w - ml - mr
    ph = h - mt - mb

    # Collect all data to determine axis ranges
    all_x_numeric = []
    all_x_labels = []
    all_y = []
    is_categorical_x = False

    for trace in spec.traces:
        if isinstance(trace, dict):
            trace_type = trace.get("type", "")
            # Box plot — extract from quartile fields
            if trace_type == "box":
                for key in ("q1", "median", "q3", "whisker_low", "whisker_high"):
                    v = trace.get(key)
                    if isinstance(v, (int, float)):
                        all_y.append(v)
                for v in trace.get("outliers", []):
                    if isinstance(v, (int, float)):
                        all_y.append(v)
                all_x_numeric.append(trace.get("x_position", 0))
            # Contour — extract from x, y, z arrays
            elif trace_type in ("contour", "heatmap"):
                tx = trace.get("x", [])
                ty = trace.get("y", [])
                tz = trace.get("z", [])
                # Handle string or numeric x/y
                for v in tx:
                    if isinstance(v, (int, float)):
                        all_x_numeric.append(v)
                    else:
                        is_categorical_x = True
                        if str(v) not in all_x_labels:
                            all_x_labels.append(str(v))
                for v in ty:
                    if isinstance(v, (int, float)):
                        all_y.append(v)
                    else:
                        # Use index for y positioning
                        pass
                # Extract z range for y-axis if y is categorical
                if tz:
                    for row in tz:
                        if isinstance(row, list):
                            all_y.extend(v for v in row if isinstance(v, (int, float)))
                # Ensure we have y range even if labels are strings
                if not all_y and tz:
                    all_y = [0, len(ty)]
            # Generic dict with y list
            elif "y" in trace and isinstance(trace["y"], list):
                for v in trace["y"]:
                    if isinstance(v, (int, float)):
                        all_y.append(v)
            continue

        if not hasattr(trace, "x") or not hasattr(trace, "y"):
            continue

        for v in trace.x:
            if isinstance(v, (int, float)):
                all_x_numeric.append(v)
            else:
                is_categorical_x = True
                if str(v) not in all_x_labels:
                    all_x_labels.append(str(v))

        for v in trace.y:
            if isinstance(v, (int, float)):
                all_y.append(v)

    for ref in spec.reference_lines:
        if ref.axis == "y":
            all_y.append(ref.value)
    for zone in spec.zones:
        if zone.axis == "y":
            all_y.extend([zone.low, zone.high])

    # Handle empty data
    if not all_y:
        all_y = [0, 1]
    if not all_x_numeric and not all_x_labels:
        # Try to infer from trace lengths
        max_len = max((len(t.y) if hasattr(t, "y") else 0) for t in spec.traces) if spec.traces else 0
        if max_len > 0:
            all_x_numeric = list(range(max_len))
        else:
            return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><text x="{w // 2}" y="{h // 2}" text-anchor="middle" fill="{theme["text"]}">No data</text></svg>'

    # X-axis setup
    if is_categorical_x and all_x_labels:
        n_cats = len(all_x_labels)
        cat_width = pw / max(n_cats, 1)

        def sx(val):
            if isinstance(val, (int, float)):
                return ml + val * cat_width + cat_width / 2
            s = str(val)
            if s in all_x_labels:
                return ml + all_x_labels.index(s) * cat_width + cat_width / 2
            return ml + pw / 2

        x_min, x_max = 0, n_cats
    else:
        if not all_x_numeric:
            all_x_numeric = [0, 1]
        x_min = min(all_x_numeric)
        x_max = max(all_x_numeric)
        x_range = x_max - x_min or 1

        def sx(val):
            if isinstance(val, (int, float)):
                return ml + (val - x_min) / x_range * pw
            return ml + pw / 2

    y_min = min(all_y)
    y_max = max(all_y)
    y_range = y_max - y_min or 1
    y_min -= y_range * 0.05
    y_max += y_range * 0.05

    def sy(val):
        return mt + ph - (val - y_min) / (y_max - y_min) * ph if (y_max - y_min) else mt + ph / 2

    # Build SVG
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" style="background:{theme["bg"]};font-family:{theme["font"]}">']

    # Title
    if spec.title:
        parts.append(f'<text x="{w // 2}" y="20" text-anchor="middle" fill="{theme["text"]}" font-size="14" font-weight="500">{escape(spec.title)}</text>')

    # Y-axis grid and labels
    n_yticks = 5
    y_step = (y_max - y_min) / n_yticks if n_yticks > 0 else 1
    for i in range(n_yticks + 1):
        val = y_min + i * y_step
        yy = sy(val)
        parts.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml + pw}" y2="{yy:.1f}" stroke="{theme["grid"]}" stroke-width="1"/>')
        label = f"{val:.2f}" if abs(val) < 100 else f"{val:.0f}"
        parts.append(f'<text x="{ml - 5}" y="{yy + 4:.1f}" text-anchor="end" fill="{theme["text_secondary"]}" font-size="10">{label}</text>')

    # X-axis labels
    if is_categorical_x and all_x_labels:
        for i, label in enumerate(all_x_labels):
            xx = ml + i * cat_width + cat_width / 2
            display = escape(label[:12])
            parts.append(f'<text x="{xx:.1f}" y="{mt + ph + 18}" text-anchor="middle" fill="{theme["text_secondary"]}" font-size="10">{display}</text>')
    else:
        n_xticks = min(8, len(all_x_numeric))
        if n_xticks > 1 and all_x_numeric:
            x_step = (x_max - x_min) / n_xticks
            for i in range(n_xticks + 1):
                val = x_min + i * x_step
                xx = sx(val)
                label = f"{val:.1f}" if abs(val) < 100 else f"{val:.0f}"
                parts.append(f'<text x="{xx:.1f}" y="{mt + ph + 18}" text-anchor="middle" fill="{theme["text_secondary"]}" font-size="10">{label}</text>')

    # Zones
    for zone in spec.zones:
        if zone.axis == "y":
            zy1 = sy(zone.high)
            zy2 = sy(zone.low)
            parts.append(f'<rect x="{ml}" y="{zy1:.1f}" width="{pw}" height="{max(0, zy2 - zy1):.1f}" fill="{zone.color}"/>')

    # Reference lines
    for ref in spec.reference_lines:
        if ref.axis == "y" or not ref.axis:
            ry = sy(ref.value)
            dash = "8,4" if ref.dash == "dashed" else "3,3" if ref.dash == "dotted" else ""
            parts.append(f'<line x1="{ml}" y1="{ry:.1f}" x2="{ml + pw}" y2="{ry:.1f}" stroke="{ref.color}" stroke-width="{ref.width}" stroke-dasharray="{dash}"/>')
            if ref.label:
                parts.append(f'<text x="{ml + pw + 3}" y="{ry + 4:.1f}" fill="{ref.color}" font-size="9">{escape(ref.label)}</text>')
        elif ref.axis == "x":
            rx = sx(ref.value)
            dash = "8,4" if ref.dash == "dashed" else "3,3" if ref.dash == "dotted" else ""
            parts.append(f'<line x1="{rx:.1f}" y1="{mt}" x2="{rx:.1f}" y2="{mt + ph}" stroke="{ref.color}" stroke-width="{ref.width}" stroke-dasharray="{dash}"/>')

    # Traces
    for ti, trace in enumerate(spec.traces):
        # Handle dict traces (box, contour)
        if isinstance(trace, dict):
            _render_dict_trace(parts, trace, ti, sx, sy, ml, mt, pw, ph, theme, is_categorical_x, all_x_labels, cat_width if is_categorical_x else 0, y_min)
            continue

        if not hasattr(trace, "x") or not hasattr(trace, "y") or not trace.x or not trace.y:
            continue

        color = trace.color or theme["colors"][ti % len(theme["colors"])]
        n = min(len(trace.x), len(trace.y))

        if trace.trace_type in ("line", "step"):
            points = []
            for i in range(n):
                xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else (all_x_labels.index(str(trace.x[i])) if str(trace.x[i]) in all_x_labels else i)
                points.append(f"{sx(xv):.1f},{sy(trace.y[i]):.1f}")
            if points:
                dash = "8,4" if trace.dash == "dashed" else "3,3" if trace.dash == "dotted" else ""
                parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="{trace.width}" stroke-dasharray="{dash}"/>')
                if trace.marker_size > 0:
                    for i in range(n):
                        xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else (all_x_labels.index(str(trace.x[i])) if str(trace.x[i]) in all_x_labels else i)
                        parts.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(trace.y[i]):.1f}" r="{trace.marker_size / 2}" fill="{color}"/>')

        elif trace.trace_type == "scatter":
            for i in range(n):
                xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else (all_x_labels.index(str(trace.x[i])) if str(trace.x[i]) in all_x_labels else i)
                r = (trace.marker_size or 6) / 2
                parts.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(trace.y[i]):.1f}" r="{r}" fill="{color}" opacity="{trace.opacity}"/>')

        elif trace.trace_type == "bar":
            n_bars = len(trace.y)
            if is_categorical_x and all_x_labels:
                bar_w = max(3, cat_width * 0.6)
            else:
                bar_w = max(3, pw / max(n_bars, 1) * 0.7)

            for i in range(n):
                xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else (all_x_labels.index(str(trace.x[i])) if str(trace.x[i]) in all_x_labels else i)
                bx = sx(xv) - bar_w / 2
                by_top = sy(trace.y[i])
                by_bottom = sy(max(y_min, 0))
                bh = max(0, by_bottom - by_top)
                parts.append(f'<rect x="{bx:.1f}" y="{by_top:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="{trace.opacity}"/>')

        elif trace.trace_type == "area":
            points = []
            for i in range(n):
                xv = trace.x[i] if isinstance(trace.x[i], (int, float)) else (all_x_labels.index(str(trace.x[i])) if str(trace.x[i]) in all_x_labels else i)
                points.append(f"{sx(xv):.1f},{sy(trace.y[i]):.1f}")
            if points:
                last_xv = trace.x[n - 1] if isinstance(trace.x[n - 1], (int, float)) else (all_x_labels.index(str(trace.x[n - 1])) if str(trace.x[n - 1]) in all_x_labels else n - 1)
                first_xv = trace.x[0] if isinstance(trace.x[0], (int, float)) else (all_x_labels.index(str(trace.x[0])) if str(trace.x[0]) in all_x_labels else 0)
                points.append(f"{sx(last_xv):.1f},{sy(max(y_min, 0)):.1f}")
                points.append(f"{sx(first_xv):.1f},{sy(max(y_min, 0)):.1f}")
                parts.append(f'<polygon points="{" ".join(points)}" fill="{color}" opacity="{trace.opacity or 0.2}" stroke="none"/>')

    # Markers
    for marker in spec.markers:
        if marker.indices and spec.traces:
            first = spec.traces[0]
            if isinstance(first, Trace) and first.x and first.y:
                for idx in marker.indices:
                    if idx < len(first.x) and idx < len(first.y):
                        xv = first.x[idx] if isinstance(first.x[idx], (int, float)) else (all_x_labels.index(str(first.x[idx])) if is_categorical_x and str(first.x[idx]) in all_x_labels else idx)
                        parts.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(first.y[idx]):.1f}" r="{marker.size / 2}" fill="none" stroke="{marker.color}" stroke-width="2"/>')

    # Axes
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt + ph}" stroke="{theme["axis"]}" stroke-width="1"/>')
    parts.append(f'<line x1="{ml}" y1="{mt + ph}" x2="{ml + pw}" y2="{mt + ph}" stroke="{theme["axis"]}" stroke-width="1"/>')

    # Axis labels
    x_label = spec.x_axis.get("label", "") if isinstance(spec.x_axis, dict) else getattr(spec.x_axis, "label", "")
    y_label = spec.y_axis.get("label", "") if isinstance(spec.y_axis, dict) else getattr(spec.y_axis, "label", "")
    if x_label:
        parts.append(f'<text x="{ml + pw // 2}" y="{h - 8}" text-anchor="middle" fill="{theme["text_secondary"]}" font-size="11">{escape(x_label)}</text>')
    if y_label:
        parts.append(f'<text x="14" y="{mt + ph // 2}" text-anchor="middle" fill="{theme["text_secondary"]}" font-size="11" transform="rotate(-90,14,{mt + ph // 2})">{escape(y_label)}</text>')

    # Annotations
    for ann in spec.annotations:
        ax = ann.get("x", 0)
        ay = ann.get("y", 0)
        text = ann.get("text", "")
        color = ann.get("color", theme["text"])
        fs = ann.get("font_size", 10)
        # If x/y are 0-1 fractions, map to plot area
        if isinstance(ax, float) and 0 <= ax <= 1 and isinstance(ay, float) and 0 <= ay <= 1:
            px = ml + ax * pw
            py = mt + (1 - ay) * ph
        else:
            px = sx(ax) if isinstance(ax, (int, float)) else ml + pw / 2
            py = sy(ay) if isinstance(ay, (int, float)) else mt + ph / 2
        parts.append(f'<text x="{px:.1f}" y="{py:.1f}" fill="{color}" font-size="{fs}">{escape(text)}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _render_dict_trace(parts, trace, ti, sx, sy, ml, mt, pw, ph, theme, is_cat, labels, cat_w, y_min):
    """Render dict-based traces (box plots, contours)."""
    trace_type = trace.get("type", "")

    if trace_type == "box":
        # Box plot rendering
        x_pos = trace.get("x_position", ti)
        color = trace.get("color", theme["colors"][ti % len(theme["colors"])])
        q1 = trace.get("q1", 0)
        median = trace.get("median", 0)
        q3 = trace.get("q3", 0)
        wl = trace.get("whisker_low", q1)
        wh = trace.get("whisker_high", q3)

        cx = ml + (x_pos + 0.5) * (pw / max(1, ti + 2))
        box_w = min(60, pw / max(1, ti + 2) * 0.6)

        # Whiskers
        parts.append(f'<line x1="{cx:.1f}" y1="{sy(wl):.1f}" x2="{cx:.1f}" y2="{sy(q1):.1f}" stroke="{color}" stroke-width="1"/>')
        parts.append(f'<line x1="{cx:.1f}" y1="{sy(q3):.1f}" x2="{cx:.1f}" y2="{sy(wh):.1f}" stroke="{color}" stroke-width="1"/>')
        # Whisker caps
        parts.append(f'<line x1="{cx - box_w / 4:.1f}" y1="{sy(wl):.1f}" x2="{cx + box_w / 4:.1f}" y2="{sy(wl):.1f}" stroke="{color}" stroke-width="1"/>')
        parts.append(f'<line x1="{cx - box_w / 4:.1f}" y1="{sy(wh):.1f}" x2="{cx + box_w / 4:.1f}" y2="{sy(wh):.1f}" stroke="{color}" stroke-width="1"/>')
        # Box
        box_top = sy(q3)
        box_bottom = sy(q1)
        parts.append(f'<rect x="{cx - box_w / 2:.1f}" y="{box_top:.1f}" width="{box_w:.1f}" height="{max(0, box_bottom - box_top):.1f}" fill="{color}" opacity="0.15" stroke="{color}" stroke-width="1"/>')
        # Median line
        parts.append(f'<line x1="{cx - box_w / 2:.1f}" y1="{sy(median):.1f}" x2="{cx + box_w / 2:.1f}" y2="{sy(median):.1f}" stroke="{color}" stroke-width="2"/>')
        # Outliers
        for outlier in trace.get("outliers", []):
            parts.append(f'<circle cx="{cx:.1f}" cy="{sy(outlier):.1f}" r="3" fill="none" stroke="{color}" stroke-width="1"/>')

    elif trace_type in ("contour", "heatmap"):
        # Render as colored grid cells
        x_vals = trace.get("x", [])
        y_vals = trace.get("y", [])
        z_vals = trace.get("z", [])
        if not x_vals or not y_vals or not z_vals:
            return

        z_flat = [v for row in z_vals for v in row if isinstance(v, (int, float))]
        z_min = min(z_flat) if z_flat else 0
        z_max = max(z_flat) if z_flat else 1
        z_range = z_max - z_min or 1

        cell_w = pw / max(len(x_vals) - 1, 1)
        cell_h = ph / max(len(y_vals) - 1, 1)

        for yi, row in enumerate(z_vals):
            for xi, val in enumerate(row):
                if not isinstance(val, (int, float)):
                    continue
                intensity = (val - z_min) / z_range
                # Viridis-ish: dark purple → teal → yellow
                r = int(min(255, intensity * 2 * 255))
                g = int(min(255, (0.3 + intensity * 0.7) * 255))
                b = int(max(0, (1 - intensity * 1.5) * 200))
                color = f"rgb({r},{g},{b})"

                cx = ml + xi * cell_w
                cy = mt + ph - yi * cell_h - cell_h
                parts.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell_w + 1:.1f}" height="{cell_h + 1:.1f}" fill="{color}" opacity="0.8"/>')
