"""Time series charts — forecast vs actual, trend, inventory position."""

from __future__ import annotations

from ..core.colors import STATUS_AMBER, STATUS_GREEN, STATUS_RED, get_color
from ..core.spec import ChartSpec


def forecast_vs_actual(
    dates: list[str],
    actual: list[float],
    forecast: list[float],
    title: str = "Forecast vs Actual",
    forecast_start_idx: int | None = None,
) -> ChartSpec:
    """Forecast overlaid on actual demand."""
    spec = ChartSpec(
        title=title, chart_type="forecast",
        x_axis={"label": "Period", "scale": "date"},
        y_axis={"label": "Demand"},
    )

    spec.add_trace(dates[:len(actual)], actual, name="Actual", trace_type="line", color=get_color(0), width=2)
    spec.add_trace(dates[:len(forecast)], forecast, name="Forecast", trace_type="line", color=get_color(1), width=2, dash="dashed")

    if forecast_start_idx is not None and forecast_start_idx < len(dates):
        spec.add_reference_line(forecast_start_idx, axis="x", color="#888", dash="dotted", label="Forecast start")

    return spec


def inventory_position(
    periods: list[str],
    on_hand: list[float],
    reorder_point: float | None = None,
    safety_stock: float | None = None,
    order_up_to: float | None = None,
    title: str = "Inventory Position",
) -> ChartSpec:
    """Inventory level over time with policy lines."""
    spec = ChartSpec(
        title=title, chart_type="inventory",
        x_axis={"label": "Period"},
        y_axis={"label": "Units", "min_val": 0},
    )

    spec.add_trace(periods, on_hand, name="On Hand", trace_type="area", color=get_color(0), fill="tozeroy", opacity=0.3)
    spec.add_trace(periods, on_hand, name="", trace_type="line", color=get_color(0), width=2)

    if reorder_point is not None:
        spec.add_reference_line(reorder_point, color=STATUS_AMBER, dash="dashed", label="Reorder Point")
    if safety_stock is not None:
        spec.add_reference_line(safety_stock, color=STATUS_RED, dash="dotted", label="Safety Stock")
    if order_up_to is not None:
        spec.add_reference_line(order_up_to, color=STATUS_GREEN, dash="dashed", label="Order-Up-To")

    # Highlight stockout periods
    stockout_indices = [i for i, v in enumerate(on_hand) if v <= 0]
    if stockout_indices:
        spec.add_marker(stockout_indices, color=STATUS_RED, size=8, symbol="x", label="Stockout")

    return spec


def capacity_loading(
    periods: list[str],
    available: list[float],
    loaded: list[float],
    title: str = "Capacity Loading",
) -> ChartSpec:
    """Capacity utilization bar chart."""
    spec = ChartSpec(
        title=title, chart_type="capacity",
        x_axis={"label": "Period"},
        y_axis={"label": "Hours"},
    )

    spec.add_trace(periods, available, name="Available", trace_type="bar", color=get_color(0), opacity=0.3)
    spec.add_trace(periods, loaded, name="Loaded", trace_type="bar", color=get_color(0))

    # Overload markers
    overload_indices = [i for i in range(len(loaded)) if i < len(available) and loaded[i] > available[i]]
    if overload_indices:
        spec.add_marker(overload_indices, color=STATUS_RED, size=8, symbol="triangle", label="Overloaded")

    return spec
