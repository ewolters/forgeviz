"""Chart recommendation engine — suggest and auto-compose dashboards."""

from __future__ import annotations

from typing import Any

from ..charts.generic import bar, line, pie, stacked_area
from ..charts.distribution import histogram
from ..charts.scatter import pareto, scatter
from ..core.spec import ChartSpec
from .auto import suggest_chart_type


def recommend(
    data: dict,
    context: dict | None = None,
) -> list[dict]:
    """Recommend visualizations ranked by suitability.

    Args:
        data: Dict with keys like x, y, categories, time_series, groups.
        context: Optional {domain, goal, audience}.

    Returns list of {chart_type, score, reason, spec}.
    """
    context = context or {}
    suggestions = []

    has_x = "x" in data and data["x"]
    has_y = "y" in data and data["y"]
    has_cats = "categories" in data and data["categories"]
    is_ts = data.get("time_series", False)
    has_groups = "groups" in data and isinstance(data.get("groups"), dict)

    goal = context.get("goal", "")

    # Primary suggestion
    primary = suggest_chart_type(data)
    suggestions.append({
        "chart_type": primary,
        "score": 1.0,
        "reason": "Best fit for data shape",
        "spec": _build_spec(primary, data),
    })

    # Alternative suggestions
    if has_x and has_y:
        if primary != "scatter":
            suggestions.append({
                "chart_type": "scatter",
                "score": 0.7,
                "reason": "Shows correlation between X and Y",
                "spec": scatter(data["x"], data["y"], title="Scatter: X vs Y"),
            })
        if primary != "line" and len(data.get("y", [])) >= 5:
            suggestions.append({
                "chart_type": "line",
                "score": 0.6,
                "reason": "Shows trend over sequence",
                "spec": line(data["x"], data["y"], title="Line: Trend"),
            })

    if has_cats and has_y:
        if primary != "pareto":
            suggestions.append({
                "chart_type": "pareto",
                "score": 0.65,
                "reason": "Highlights vital few categories",
                "spec": pareto(data["categories"], data["y"], title="Pareto Analysis"),
            })

    if has_y and not has_x and primary != "histogram":
        suggestions.append({
            "chart_type": "histogram",
            "score": 0.5,
            "reason": "Shows distribution shape",
            "spec": histogram(data["y"], title="Distribution"),
        })

    # Sort by score
    suggestions.sort(key=lambda s: -s["score"])
    return suggestions


def auto_dashboard(
    data_sources: dict[str, dict],
    title: str = "Auto Dashboard",
) -> Any:
    """Auto-compose a dashboard from multiple data sources.

    Args:
        data_sources: Dict of {name: data_dict}.
        title: Dashboard title.

    Returns DashboardSpec.
    """
    from ..core.dashboard import DashboardBuilder

    n = len(data_sources)
    cols = 2 if n <= 4 else 3

    builder = DashboardBuilder(title=title, columns=cols)

    for i, (name, data) in enumerate(data_sources.items()):
        chart_type = suggest_chart_type(data)
        spec = _build_spec(chart_type, data)
        spec.title = name

        row = i // cols
        col = i % cols
        builder.panel(spec, row=row, col=col)

    return builder.build()


def _build_spec(chart_type: str, data: dict) -> ChartSpec:
    """Build a ChartSpec from chart type name and data dict."""
    x = data.get("x", [])
    y = data.get("y", [])
    cats = data.get("categories", [])
    groups = data.get("groups", {})

    if chart_type == "bar" and cats:
        return bar(cats, y[:len(cats)], title="Bar Chart")
    elif chart_type == "line" and y:
        x_vals = x if x else list(range(len(y)))
        return line(x_vals, y, title="Line Chart")
    elif chart_type == "scatter" and x and y:
        return scatter(x, y, title="Scatter Plot")
    elif chart_type == "histogram" and y:
        return histogram(y, title="Histogram")
    elif chart_type == "pie" and cats:
        return pie(cats, y[:len(cats)], title="Pie Chart")
    elif chart_type == "pareto" and cats:
        return pareto(cats, y[:len(cats)], title="Pareto")
    elif chart_type == "stacked_area" and y and groups:
        x_vals = x if x else list(range(len(y)))
        return stacked_area(x_vals, groups, title="Stacked Area")
    elif chart_type == "grouped_bar" and cats and groups:
        from ..charts.generic import grouped_bar
        return grouped_bar(cats, groups, title="Grouped Bar")
    else:
        # Fallback
        if y:
            x_vals = x if x else list(range(len(y)))
            return line(x_vals, y, title="Chart")
        return ChartSpec(title="Empty")
