"""ForgeViz Analytics — auto-detection, enrichment, and chart recommendation."""

from .auto import (
    add_confidence_band,
    add_moving_average,
    add_trend_line,
    auto_annotate,
    detect_changepoints,
    detect_clusters,
    detect_outliers,
    detect_seasonality,
    detect_trends,
    enrich,
    suggest_chart_type,
)
from .predict import (
    capability_forecast,
    forecast_overlay,
    process_drift_overlay,
    spc_forecast,
    time_to_breach,
)
from .recommend import auto_dashboard, recommend

__all__ = [
    "auto_annotate",
    "detect_trends",
    "detect_outliers",
    "detect_changepoints",
    "detect_seasonality",
    "detect_clusters",
    "suggest_chart_type",
    "add_trend_line",
    "add_confidence_band",
    "add_moving_average",
    "enrich",
    "recommend",
    "auto_dashboard",
    "forecast_overlay",
    "time_to_breach",
    "process_drift_overlay",
    "spc_forecast",
    "capability_forecast",
]
