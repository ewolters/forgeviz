"""Advanced chart builders — waterfall, funnel, treemap, radar, violin, sankey, candlestick.

All pure Python, zero dependencies. Complex layout algorithms
(squarified treemap, Gaussian KDE, Sankey positioning) implemented inline.
"""

from __future__ import annotations

import math
from typing import Any

from ..core.colors import STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


# =========================================================================
# Waterfall
# =========================================================================

def waterfall(
    categories: list[str],
    values: list[float],
    title: str = "Waterfall",
    show_total: bool = True,
    total_label: str = "Total",
) -> ChartSpec:
    """Waterfall chart — cumulative effect visualization.

    Each bar starts where the previous one ended. Positive = green,
    negative = red, total = accent.

    Args:
        categories: Bar labels.
        values: Incremental values (positive or negative).
        title: Chart title.
        show_total: Whether to append a total bar.
        total_label: Label for the total bar.
    """
    spec = ChartSpec(title=title, chart_type="waterfall")

    bars = []
    running = 0.0
    for i, (cat, val) in enumerate(zip(categories, values)):
        bars.append({
            "label": cat,
            "start": running,
            "end": running + val,
            "is_total": False,
        })
        running += val

    if show_total:
        bars.append({
            "label": total_label,
            "start": 0,
            "end": running,
            "is_total": True,
        })

    spec.traces.append({
        "type": "waterfall",
        "bars": bars,
    })

    return spec


# =========================================================================
# Funnel
# =========================================================================

def funnel(
    stages: list[str],
    values: list[float],
    title: str = "Funnel",
    colors: list[str] | None = None,
) -> ChartSpec:
    """Funnel chart — stage-based conversion visualization.

    Horizontal bars of decreasing width, centered. Shows conversion
    rate between each stage.

    Args:
        stages: Stage labels (top to bottom).
        values: Values for each stage.
        title: Chart title.
        colors: Optional per-stage colors.
    """
    spec = ChartSpec(title=title, chart_type="funnel")

    stage_dicts = []
    for i, (label, val) in enumerate(zip(stages, values)):
        d: dict[str, Any] = {"label": label, "value": val}
        if colors and i < len(colors):
            d["color"] = colors[i]
        else:
            d["color"] = get_color(i)
        stage_dicts.append(d)

    spec.traces.append({
        "type": "funnel",
        "stages": stage_dicts,
    })

    return spec


# =========================================================================
# Treemap — Squarified layout algorithm
# =========================================================================

def _squarify(values: list[float], x: float, y: float, w: float, h: float) -> list[dict]:
    """Squarified treemap layout. Returns list of {x, y, w, h, idx}."""
    if not values:
        return []

    total = sum(values)
    if total <= 0:
        return []

    # Single item
    if len(values) == 1:
        return [{"x": x, "y": y, "w": w, "h": h, "idx": 0}]

    # Normalize areas
    areas = [v / total * w * h for v in values]

    # Sort descending (indices track original order)
    indexed = sorted(enumerate(areas), key=lambda t: -t[1])
    sorted_indices = [t[0] for t in indexed]
    sorted_areas = [t[1] for t in indexed]

    rects: list[dict] = []
    _layout_row(sorted_areas, sorted_indices, x, y, w, h, rects)
    return rects


def _layout_row(
    areas: list[float],
    indices: list[int],
    x: float, y: float, w: float, h: float,
    rects: list[dict],
) -> None:
    """Recursive squarified layout."""
    if not areas:
        return

    total_area = sum(areas)

    if len(areas) == 1:
        rects.append({"x": x, "y": y, "w": w, "h": h, "idx": indices[0]})
        return

    # Try laying out along the shorter side
    if w >= h:
        # Lay out vertically on the left
        row = [areas[0]]
        row_idx = [indices[0]]
        row_sum = areas[0]

        best_ratio = _worst_ratio(row, row_sum, w, h)

        for i in range(1, len(areas)):
            trial = row + [areas[i]]
            trial_sum = row_sum + areas[i]
            ratio = _worst_ratio(trial, trial_sum, w, h)
            if ratio <= best_ratio:
                row.append(areas[i])
                row_idx.append(indices[i])
                row_sum = trial_sum
                best_ratio = ratio
            else:
                break

        # Layout this row
        row_w = row_sum / h if h > 0 else 0
        cy = y
        for j, a in enumerate(row):
            rect_h = a / row_w if row_w > 0 else 0
            rects.append({"x": x, "y": cy, "w": row_w, "h": rect_h, "idx": row_idx[j]})
            cy += rect_h

        # Recurse on remaining
        remaining_areas = areas[len(row):]
        remaining_idx = indices[len(row):]
        _layout_row(remaining_areas, remaining_idx, x + row_w, y, w - row_w, h, rects)
    else:
        # Lay out horizontally on top
        row = [areas[0]]
        row_idx = [indices[0]]
        row_sum = areas[0]

        best_ratio = _worst_ratio(row, row_sum, w, h)

        for i in range(1, len(areas)):
            trial = row + [areas[i]]
            trial_sum = row_sum + areas[i]
            ratio = _worst_ratio(trial, trial_sum, w, h)
            if ratio <= best_ratio:
                row.append(areas[i])
                row_idx.append(indices[i])
                row_sum = trial_sum
                best_ratio = ratio
            else:
                break

        row_h = row_sum / w if w > 0 else 0
        cx = x
        for j, a in enumerate(row):
            rect_w = a / row_h if row_h > 0 else 0
            rects.append({"x": cx, "y": y, "w": rect_w, "h": row_h, "idx": row_idx[j]})
            cx += rect_w

        remaining_areas = areas[len(row):]
        remaining_idx = indices[len(row):]
        _layout_row(remaining_areas, remaining_idx, x, y + row_h, w, h - row_h, rects)


def _worst_ratio(row: list[float], row_sum: float, w: float, h: float) -> float:
    """Aspect ratio metric for squarified layout."""
    if not row or row_sum <= 0:
        return float("inf")
    side = min(w, h)
    if side <= 0:
        return float("inf")
    s2 = (row_sum / (w * h) * side) ** 2 if w * h > 0 else 0
    max_r = max(row)
    min_r = min(row)
    if min_r <= 0 or s2 <= 0:
        return float("inf")
    return max(s2 * max_r / (row_sum ** 2), row_sum ** 2 / (s2 * min_r)) if row_sum > 0 else float("inf")


def treemap(
    labels: list[str],
    values: list[float],
    title: str = "Treemap",
    colors: list[str] | None = None,
    parents: list[str | None] | None = None,
) -> ChartSpec:
    """Treemap — hierarchical area chart using squarified layout.

    Args:
        labels: Node labels.
        values: Node values (determines area).
        title: Chart title.
        colors: Optional per-node colors.
        parents: Optional parent labels for hierarchy (None = root).
    """
    spec = ChartSpec(title=title, chart_type="treemap")

    # Filter out zero/negative values
    valid = [(i, l, v) for i, (l, v) in enumerate(zip(labels, values)) if v > 0]
    if not valid:
        spec.traces.append({"type": "treemap", "rectangles": []})
        return spec

    valid_values = [v for _, _, v in valid]

    # Run squarified layout (normalized to 0-1 space)
    layout = _squarify(valid_values, 0, 0, 1, 1)

    rectangles = []
    for rect in layout:
        orig_idx = valid[rect["idx"]][0]
        orig_label = valid[rect["idx"]][1]
        orig_value = valid[rect["idx"]][2]
        color = colors[orig_idx] if colors and orig_idx < len(colors) else get_color(orig_idx)
        rectangles.append({
            "x": rect["x"],
            "y": rect["y"],
            "w": rect["w"],
            "h": rect["h"],
            "label": orig_label,
            "value": orig_value,
            "color": color,
            "depth": 0,
        })

    spec.traces.append({
        "type": "treemap",
        "rectangles": rectangles,
    })

    return spec


# =========================================================================
# Radar / Spider chart
# =========================================================================

def radar(
    categories: list[str],
    series: dict[str, list[float]],
    title: str = "Radar",
    max_val: float | None = None,
) -> ChartSpec:
    """Radar/spider chart — multi-axis polygon overlay.

    Args:
        categories: Axis labels (minimum 3).
        series: Dict of {series_name: values}. Each value list must
                match len(categories).
        title: Chart title.
        max_val: Maximum scale value. If None, auto-detected.
    """
    spec = ChartSpec(title=title, chart_type="radar", show_legend=True)

    if max_val is None:
        all_vals = [v for vals in series.values() for v in vals]
        max_val = max(all_vals) if all_vals else 1

    series_list = []
    for i, (name, values) in enumerate(series.items()):
        series_list.append({
            "name": name,
            "values": values,
            "max_val": max_val,
            "color": get_color(i),
        })

    spec.traces.append({
        "type": "radar",
        "categories": categories,
        "series": series_list,
    })

    return spec


# =========================================================================
# Violin plot — Gaussian KDE
# =========================================================================

def _gaussian_kde(data: list[float], n_points: int = 50) -> tuple[list[float], list[float]]:
    """Gaussian KDE with Silverman's rule for bandwidth. Pure Python."""
    if len(data) < 2:
        return [data[0]] if data else [0], [1.0] if data else [0.0]

    n = len(data)
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / n
    std = math.sqrt(variance) if variance > 0 else 1.0

    # Silverman's rule of thumb
    bandwidth = 1.06 * std * n ** (-0.2)
    if bandwidth <= 0:
        bandwidth = 0.1

    d_min = min(data) - 3 * bandwidth
    d_max = max(data) + 3 * bandwidth
    step = (d_max - d_min) / (n_points - 1) if n_points > 1 else 1

    y_range = [d_min + i * step for i in range(n_points)]
    density = []
    for y in y_range:
        d = sum(math.exp(-0.5 * ((y - xi) / bandwidth) ** 2) for xi in data)
        d /= n * bandwidth * math.sqrt(2 * math.pi)
        density.append(d)

    return y_range, density


def violin(
    datasets: dict[str, list[float]],
    title: str = "Violin Plot",
    show_quartiles: bool = True,
) -> ChartSpec:
    """Violin plot — KDE density with quartile overlay.

    Args:
        datasets: Dict of {group_name: data_values}.
        title: Chart title.
        show_quartiles: Show Q1/median/Q3 inside violin.
    """
    spec = ChartSpec(title=title, chart_type="violin")

    for i, (name, data) in enumerate(datasets.items()):
        if not data:
            continue

        y_range, density = _gaussian_kde(data)
        sorted_data = sorted(data)
        n = len(sorted_data)

        trace: dict[str, Any] = {
            "type": "violin",
            "name": name,
            "density": density,
            "y_range": y_range,
            "color": get_color(i),
        }

        if show_quartiles and n >= 4:
            q1_idx = n // 4
            q3_idx = 3 * n // 4
            trace["q1"] = sorted_data[q1_idx]
            trace["median"] = sorted_data[n // 2]
            trace["q3"] = sorted_data[q3_idx]

        spec.traces.append(trace)

    return spec


# =========================================================================
# Sankey diagram — iterative relaxation positioning
# =========================================================================

def sankey(
    nodes: list[str],
    links: list[dict],
    title: str = "Sankey Diagram",
    colors: list[str] | None = None,
) -> ChartSpec:
    """Sankey/flow diagram with curved links.

    Args:
        nodes: Node names.
        links: List of {source: int, target: int, value: float, color?: str}.
        title: Chart title.
        colors: Optional per-node colors.
    """
    spec = ChartSpec(title=title, chart_type="sankey")

    n = len(nodes)
    if n == 0:
        spec.traces.append({"type": "sankey", "nodes": [], "links": []})
        return spec

    # Compute node depths (layers) via topological ordering
    # depth[i] = longest path from a source node
    outgoing: dict[int, list[int]] = {i: [] for i in range(n)}
    incoming: dict[int, list[int]] = {i: [] for i in range(n)}
    for link in links:
        s, t = link["source"], link["target"]
        if 0 <= s < n and 0 <= t < n:
            outgoing[s].append(t)
            incoming[t].append(s)

    depth = [0] * n
    visited = [False] * n

    def compute_depth(node: int) -> int:
        if visited[node]:
            return depth[node]
        visited[node] = True
        if not incoming[node]:
            depth[node] = 0
        else:
            depth[node] = max(compute_depth(p) + 1 for p in incoming[node])
        return depth[node]

    for i in range(n):
        compute_depth(i)

    max_depth = max(depth) if depth else 0

    # Compute node values (sum of links)
    node_values = [0.0] * n
    for link in links:
        s, t = link["source"], link["target"]
        val = link.get("value", 1)
        if 0 <= s < n:
            node_values[s] = max(node_values[s], val)
        if 0 <= t < n:
            node_values[t] += val

    # For source nodes, use outgoing sum
    for i in range(n):
        if not incoming[i]:
            node_values[i] = sum(link.get("value", 1) for link in links if link["source"] == i)

    max_node_val = max(node_values) if node_values else 1

    # Position nodes
    layers: dict[int, list[int]] = {}
    for i, d in enumerate(depth):
        layers.setdefault(d, []).append(i)

    node_dicts = []
    node_y_pos = {}
    for i in range(n):
        layer = depth[i]
        layer_nodes = layers[layer]
        idx_in_layer = layer_nodes.index(i)
        n_in_layer = len(layer_nodes)

        x = layer / max(max_depth, 1) * 0.85 + 0.02
        h = max(0.03, node_values[i] / max_node_val * 0.3)
        y = (idx_in_layer + 0.5) / max(n_in_layer, 1) * (1 - h)

        node_y_pos[i] = y
        color = colors[i] if colors and i < len(colors) else get_color(i)
        node_dicts.append({
            "name": nodes[i],
            "x": x,
            "y": y,
            "h": h,
            "color": color,
        })

    # Position links
    max_value = max((link.get("value", 1) for link in links), default=1)
    link_dicts = []
    for link in links:
        s, t = link["source"], link["target"]
        if 0 <= s < n and 0 <= t < n:
            link_dicts.append({
                "source": s,
                "target": t,
                "value": link.get("value", 1),
                "color": link.get("color", ""),
                "sy": node_y_pos.get(s, 0),
                "ty": node_y_pos.get(t, 0),
            })

    spec.traces.append({
        "type": "sankey",
        "nodes": node_dicts,
        "links": link_dicts,
        "max_value": max_value,
    })

    return spec


# =========================================================================
# Candlestick / OHLC
# =========================================================================

def candlestick(
    dates: list[Any],
    open_vals: list[float],
    high_vals: list[float],
    low_vals: list[float],
    close_vals: list[float],
    title: str = "Candlestick",
) -> ChartSpec:
    """OHLC candlestick chart.

    Green body when close >= open, red when close < open.
    Wicks extend to high/low.

    Args:
        dates: X-axis labels (dates or indices).
        open_vals: Opening prices/values.
        high_vals: High prices/values.
        low_vals: Low prices/values.
        close_vals: Closing prices/values.
        title: Chart title.
    """
    spec = ChartSpec(title=title, chart_type="candlestick")

    candles = []
    for i in range(min(len(dates), len(open_vals), len(high_vals), len(low_vals), len(close_vals))):
        candles.append({
            "date": dates[i],
            "open": open_vals[i],
            "high": high_vals[i],
            "low": low_vals[i],
            "close": close_vals[i],
        })

    spec.traces.append({
        "type": "candlestick",
        "candles": candles,
    })

    return spec
