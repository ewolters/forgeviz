"""Trellis / Small Multiples — one chart function, many groups, shared axes.

Takes a dataset grouped by category and a chart-building function, then
produces a grid of identical charts (one per group) with shared axes for
easy visual comparison. Built on DashboardSpec for layout.

Usage:
    from forgeviz.charts.trellis import trellis, trellis_control_charts
    from forgeviz.charts.generic import line

    data = {
        "Line A": {"x": dates, "y": yields_a},
        "Line B": {"x": dates, "y": yields_b},
        "Line C": {"x": dates, "y": yields_c},
    }
    dash = trellis(data, line, title="Yield by Line", columns=3)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from ..core.dashboard import DashboardSpec
from ..core.spec import Axis, ChartSpec


# =========================================================================
# Compact panel height for trellis cells
# =========================================================================

_TRELLIS_HEIGHT = 250


# =========================================================================
# Core trellis function
# =========================================================================


def trellis(
    data_by_group: dict[str, dict],
    chart_fn: Callable[..., ChartSpec],
    title: str = "",
    columns: int = 3,
    shared_y: bool = True,
    shared_x: bool = True,
    **chart_kwargs: Any,
) -> DashboardSpec:
    """Build a small-multiples grid from grouped data.

    Args:
        data_by_group: {group_name: {"x": [...], "y": [...], ...}} where
            extra keys are passed through to chart_fn.
        chart_fn: Any forgeviz chart builder (line, scatter, control_chart, etc.).
        title: Overall trellis title.
        columns: Number of grid columns.
        shared_y: If True, all panels share the same y-axis range.
        shared_x: If True, all panels share the same x-axis range.
        **chart_kwargs: Extra kwargs forwarded to every chart_fn call.

    Returns:
        DashboardSpec with trellis metadata attached.
    """
    if not data_by_group:
        dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)
        dash._trellis_metadata = {"type": "trellis", "shared_y": shared_y, "shared_x": shared_x}
        return dash

    group_names = list(data_by_group.keys())
    n_groups = len(group_names)
    n_rows = (n_groups + columns - 1) // columns

    # Build a ChartSpec for each group
    specs: list[ChartSpec] = []
    for name in group_names:
        group_data = dict(data_by_group[name])
        x = group_data.pop("x", [])
        y = group_data.pop("y", [])
        merged = {**chart_kwargs, **group_data}
        spec = chart_fn(x=x, y=y, **merged)
        spec.subtitle = name
        spec.height = _TRELLIS_HEIGHT
        spec.show_legend = False
        specs.append(spec)

    # Shared y-axis: compute global min/max from traces
    if shared_y:
        _apply_shared_axis(specs, axis="y")

    # Shared x-axis: compute global min/max from traces
    if shared_x:
        _apply_shared_axis(specs, axis="x")

    # Build dashboard
    dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)

    for idx, (name, spec) in enumerate(zip(group_names, specs)):
        row = idx // columns
        col = idx % columns

        # Hide redundant axis labels on interior panels
        if shared_y and col != 0:
            spec.y_axis = _clear_axis_label(spec.y_axis)
        if shared_x and row != n_rows - 1:
            # Not the bottom row — hide x-axis label
            # But keep it for last-row panels even if they don't fill the row
            remaining = n_groups - row * columns
            if remaining > columns:
                spec.x_axis = _clear_axis_label(spec.x_axis)

        dash.add_panel(spec, row=row, col=col)

    dash._trellis_metadata = {
        "type": "trellis",
        "shared_y": shared_y,
        "shared_x": shared_x,
        "compact": True,
        "gap": 4,
    }

    return dash


# =========================================================================
# Convenience functions
# =========================================================================


def trellis_control_charts(
    data_by_group: dict[str, list[float]],
    ucl: float,
    cl: float,
    lcl: float,
    title: str = "",
    columns: int = 3,
    **kwargs: Any,
) -> DashboardSpec:
    """Trellis of SPC control charts sharing the same control limits.

    Args:
        data_by_group: {line_name: [data_points, ...]}.
        ucl: Upper control limit (shared across all panels).
        cl: Center line (shared).
        lcl: Lower control limit (shared).
        title: Overall title.
        columns: Grid columns.
        **kwargs: Extra args for control_chart().
    """
    from .control import control_chart

    if not data_by_group:
        dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)
        dash._trellis_metadata = {"type": "trellis", "shared_y": True, "shared_x": False}
        return dash

    group_names = list(data_by_group.keys())
    n_groups = len(group_names)
    n_rows = (n_groups + columns - 1) // columns

    specs: list[ChartSpec] = []
    for name in group_names:
        points = data_by_group[name]
        spec = control_chart(
            data_points=points,
            ucl=ucl,
            cl=cl,
            lcl=lcl,
            title="",
            **kwargs,
        )
        spec.subtitle = name
        spec.height = _TRELLIS_HEIGHT
        spec.show_legend = False
        specs.append(spec)

    # Shared y: use the control limits as basis, but also check data extremes
    all_vals = []
    for points in data_by_group.values():
        all_vals.extend(points)
    if all_vals:
        y_min = min(min(all_vals), lcl)
        y_max = max(max(all_vals), ucl)
        margin = (y_max - y_min) * 0.05
        for spec in specs:
            spec.y_axis = _ensure_axis(spec.y_axis)
            spec.y_axis.min_val = y_min - margin
            spec.y_axis.max_val = y_max + margin

    dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)

    for idx, (name, spec) in enumerate(zip(group_names, specs)):
        row = idx // columns
        col = idx % columns

        if col != 0:
            spec.y_axis = _clear_axis_label(spec.y_axis)
        remaining = n_groups - row * columns
        if remaining > columns:
            spec.x_axis = _clear_axis_label(spec.x_axis)

        dash.add_panel(spec, row=row, col=col)

    dash._trellis_metadata = {
        "type": "trellis",
        "shared_y": True,
        "shared_x": False,
        "compact": True,
        "gap": 4,
    }

    return dash


def trellis_histograms(
    data_by_group: dict[str, list[float]],
    title: str = "",
    columns: int = 3,
    bins: int = 20,
    shared_x: bool = True,
    **kwargs: Any,
) -> DashboardSpec:
    """Trellis of histograms for distribution comparison.

    Args:
        data_by_group: {group_name: [values, ...]}.
        title: Overall title.
        columns: Grid columns.
        bins: Number of histogram bins.
        shared_x: If True, all panels share the same x range.
        **kwargs: Extra args for histogram().
    """
    from .distribution import histogram

    if not data_by_group:
        dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)
        dash._trellis_metadata = {"type": "trellis", "shared_y": False, "shared_x": shared_x}
        return dash

    group_names = list(data_by_group.keys())
    n_groups = len(group_names)
    n_rows = (n_groups + columns - 1) // columns

    specs: list[ChartSpec] = []
    for name in group_names:
        values = data_by_group[name]
        spec = histogram(data=values, bins=bins, title="", **kwargs)
        spec.subtitle = name
        spec.height = _TRELLIS_HEIGHT
        spec.show_legend = False
        specs.append(spec)

    # Shared x-axis across all histograms
    if shared_x:
        all_vals = []
        for values in data_by_group.values():
            all_vals.extend(values)
        if all_vals:
            x_min = min(all_vals)
            x_max = max(all_vals)
            margin = (x_max - x_min) * 0.05 if x_max > x_min else 1.0
            for spec in specs:
                spec.x_axis = _ensure_axis(spec.x_axis)
                spec.x_axis.min_val = x_min - margin
                spec.x_axis.max_val = x_max + margin

    dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)

    for idx, (name, spec) in enumerate(zip(group_names, specs)):
        row = idx // columns
        col = idx % columns

        if col != 0:
            spec.y_axis = _clear_axis_label(spec.y_axis)
        remaining = n_groups - row * columns
        if remaining > columns:
            spec.x_axis = _clear_axis_label(spec.x_axis)

        dash.add_panel(spec, row=row, col=col)

    dash._trellis_metadata = {
        "type": "trellis",
        "shared_y": False,
        "shared_x": shared_x,
        "compact": True,
        "gap": 4,
    }

    return dash


def trellis_scatter(
    data_by_group: dict[str, dict],
    title: str = "",
    columns: int = 3,
    **kwargs: Any,
) -> DashboardSpec:
    """Trellis of scatter plots for comparison.

    Args:
        data_by_group: {group_name: {"x": [...], "y": [...]}}.
        title: Overall title.
        columns: Grid columns.
        **kwargs: Extra args for scatter().
    """
    from .scatter import scatter

    if not data_by_group:
        dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)
        dash._trellis_metadata = {"type": "trellis", "shared_y": True, "shared_x": True}
        return dash

    group_names = list(data_by_group.keys())
    n_groups = len(group_names)
    n_rows = (n_groups + columns - 1) // columns

    specs: list[ChartSpec] = []
    for name in group_names:
        gd = data_by_group[name]
        spec = scatter(x=gd.get("x", []), y=gd.get("y", []), title="", **kwargs)
        spec.subtitle = name
        spec.height = _TRELLIS_HEIGHT
        spec.show_legend = False
        specs.append(spec)

    _apply_shared_axis(specs, axis="y")
    _apply_shared_axis(specs, axis="x")

    dash = DashboardSpec(title=title, columns=columns, row_height=_TRELLIS_HEIGHT)

    for idx, (name, spec) in enumerate(zip(group_names, specs)):
        row = idx // columns
        col = idx % columns

        if col != 0:
            spec.y_axis = _clear_axis_label(spec.y_axis)
        remaining = n_groups - row * columns
        if remaining > columns:
            spec.x_axis = _clear_axis_label(spec.x_axis)

        dash.add_panel(spec, row=row, col=col)

    dash._trellis_metadata = {
        "type": "trellis",
        "shared_y": True,
        "shared_x": True,
        "compact": True,
        "gap": 4,
    }

    return dash


def trellis_from_dataframe(
    rows: list[dict],
    group_field: str,
    x_field: str,
    y_field: str,
    chart_fn: Callable[..., ChartSpec],
    title: str = "",
    columns: int = 3,
    **kwargs: Any,
) -> DashboardSpec:
    """Build a trellis from flat row data (e.g. Django queryset.values()).

    Groups rows by group_field, extracts x_field and y_field, then
    delegates to trellis().

    Args:
        rows: List of dicts, e.g. [{"line": "L1", "date": "2026-01-01", "yield": 98.2}, ...].
        group_field: Key to group by (e.g. "line").
        x_field: Key for x values (e.g. "date").
        y_field: Key for y values (e.g. "yield").
        chart_fn: Chart builder function.
        title: Overall title.
        columns: Grid columns.
        **kwargs: Extra args for chart_fn.

    Returns:
        DashboardSpec via trellis().
    """
    groups: dict[str, dict[str, list]] = defaultdict(lambda: {"x": [], "y": []})

    for row in rows:
        group_key = str(row.get(group_field, ""))
        groups[group_key]["x"].append(row.get(x_field))
        groups[group_key]["y"].append(row.get(y_field))

    return trellis(
        data_by_group=dict(groups),
        chart_fn=chart_fn,
        title=title,
        columns=columns,
        **kwargs,
    )


# =========================================================================
# Internal helpers
# =========================================================================


def _ensure_axis(axis_val: Any) -> Axis:
    """Ensure we have an Axis dataclass (may be a dict from ChartSpec init)."""
    if isinstance(axis_val, Axis):
        return axis_val
    if isinstance(axis_val, dict):
        return Axis(**{k: v for k, v in axis_val.items() if k in Axis.__dataclass_fields__})
    return Axis()


def _clear_axis_label(axis_val: Any) -> Axis:
    """Return an Axis with label cleared (for interior panels)."""
    ax = _ensure_axis(axis_val)
    ax.label = ""
    return ax


def _extract_numeric_values(traces: list, accessor: str) -> list[float]:
    """Pull all numeric values from traces for a given axis ('x' or 'y')."""
    vals: list[float] = []
    for t in traces:
        if hasattr(t, accessor):
            raw = getattr(t, accessor)
        elif isinstance(t, dict) and accessor in t:
            raw = t[accessor]
        else:
            continue
        for v in raw:
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                pass
    return vals


def _apply_shared_axis(specs: list[ChartSpec], axis: str = "y") -> None:
    """Set min_val/max_val across all specs so they share the same axis range."""
    all_vals: list[float] = []
    for spec in specs:
        all_vals.extend(_extract_numeric_values(spec.traces, axis))

    if not all_vals:
        return

    v_min = min(all_vals)
    v_max = max(all_vals)
    margin = (v_max - v_min) * 0.05 if v_max > v_min else 1.0

    for spec in specs:
        if axis == "y":
            spec.y_axis = _ensure_axis(spec.y_axis)
            spec.y_axis.min_val = v_min - margin
            spec.y_axis.max_val = v_max + margin
        else:
            spec.x_axis = _ensure_axis(spec.x_axis)
            spec.x_axis.min_val = v_min - margin
            spec.x_axis.max_val = v_max + margin
