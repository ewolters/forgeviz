"""ForgeViz chart builders — every function takes data → returns ChartSpec."""

from .bayesian import bayesian_acceptance, bayesian_capability, bayesian_changepoint, bayesian_control_chart
from .capability import capability_histogram, capability_sixpack
from .control import control_chart, from_conformal_result, from_mewma_result, from_spc_result, from_spc_result_pair, run_chart
from .diagnostic import cooks_distance, four_in_one, qq_plot, residual_histogram, residual_plot, residual_vs_order
from .distribution import box_plot, ecdf, histogram, probability_plot
from .effects import interaction_plot, main_effects_plot, normal_probability_plot, pareto_of_effects
from .gage import bland_altman, gage_rr_by_operator, gage_rr_by_part, gage_rr_components, gage_xbar_r
from .generic import (
    area, bar, bullet, donut, gauge, grouped_bar, line, multi_line, pie,
    risk_heatmap, sparkline, stacked_area, stacked_bar,
)
from .interactive import counterfactual_comparison, sensitivity_tornado, slider_chart
from .socratic import capability_gap, gap_chart, oee_gap
from .tufte import (
    dot_dash, quartile_plot, range_frame, rug,
    slope_chart, tufte_bar, tufte_line, tufte_mode,
)
from .knowledge import (
    ddmrp_buffer_status,
    detection_ladder,
    evidence_timeline,
    knowledge_health_sparklines,
    maturity_trajectory,
    proactive_reactive_gauge,
    yield_from_cpk_curve,
)
from .reliability import hazard_function, reliability_block_diagram, survival_curve, weibull_probability_plot
from .scatter import pareto, scatter
from .statistical import (
    bubble,
    correlation_heatmap,
    dotplot,
    heatmap,
    individual_value_plot,
    interval_plot,
    mosaic,
    multi_vari_chart,
    parallel_coordinates,
    scatter_matrix,
)
from .surface import contour_plot, overlay_optimal_point, response_surface_from_model
from .advanced import candlestick, funnel, radar, sankey, treemap, violin, waterfall
from .time_series import capacity_loading, forecast_vs_actual, inventory_position
from .trellis import (
    trellis,
    trellis_control_charts,
    trellis_from_dataframe,
    trellis_histograms,
    trellis_scatter,
)

__all__ = [
    # advanced
    "candlestick",
    "funnel",
    "radar",
    "sankey",
    "treemap",
    "violin",
    "waterfall",
    # bayesian
    "bayesian_acceptance",
    "bayesian_capability",
    "bayesian_changepoint",
    "bayesian_control_chart",
    # capability
    "capability_histogram",
    "capability_sixpack",
    # control
    "control_chart",
    "from_conformal_result",
    "from_mewma_result",
    "from_spc_result",
    "from_spc_result_pair",
    "run_chart",
    # diagnostic
    "cooks_distance",
    "four_in_one",
    "qq_plot",
    "residual_histogram",
    "residual_plot",
    "residual_vs_order",
    # distribution
    "box_plot",
    "ecdf",
    "histogram",
    "probability_plot",
    # effects
    "interaction_plot",
    "main_effects_plot",
    "normal_probability_plot",
    "pareto_of_effects",
    # gage
    "bland_altman",
    "gage_rr_by_operator",
    "gage_rr_by_part",
    "gage_rr_components",
    "gage_xbar_r",
    # generic
    "area",
    "bar",
    "bullet",
    "donut",
    "gauge",
    "grouped_bar",
    "line",
    "multi_line",
    "pie",
    "risk_heatmap",
    "sparkline",
    "stacked_area",
    "stacked_bar",
    # interactive
    "counterfactual_comparison",
    "sensitivity_tornado",
    "slider_chart",
    # socratic
    "capability_gap",
    "gap_chart",
    "oee_gap",
    # knowledge
    "ddmrp_buffer_status",
    "detection_ladder",
    "evidence_timeline",
    "knowledge_health_sparklines",
    "maturity_trajectory",
    "proactive_reactive_gauge",
    "yield_from_cpk_curve",
    # reliability
    "hazard_function",
    "reliability_block_diagram",
    "survival_curve",
    "weibull_probability_plot",
    # scatter
    "pareto",
    "scatter",
    # statistical
    "bubble",
    "correlation_heatmap",
    "dotplot",
    "heatmap",
    "individual_value_plot",
    "interval_plot",
    "mosaic",
    "multi_vari_chart",
    "parallel_coordinates",
    "scatter_matrix",
    # tufte
    "dot_dash",
    "quartile_plot",
    "range_frame",
    "rug",
    "slope_chart",
    "tufte_bar",
    "tufte_line",
    "tufte_mode",
    # surface
    "contour_plot",
    "overlay_optimal_point",
    "response_surface_from_model",
    # time_series
    "capacity_loading",
    "forecast_vs_actual",
    "inventory_position",
    # trellis
    "trellis",
    "trellis_control_charts",
    "trellis_from_dataframe",
    "trellis_histograms",
    "trellis_scatter",
]
