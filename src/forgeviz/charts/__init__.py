"""ForgeViz chart builders — every function takes data → returns ChartSpec."""

from .capability import capability_histogram, capability_sixpack
from .control import control_chart, from_spc_result, from_spc_result_pair
from .diagnostic import cooks_distance, four_in_one, qq_plot, residual_histogram, residual_plot, residual_vs_order
from .distribution import box_plot, histogram
from .effects import interaction_plot, main_effects_plot, normal_probability_plot, pareto_of_effects
from .gage import gage_rr_by_operator, gage_rr_by_part, gage_rr_components, gage_xbar_r
from .generic import area, bar, gauge, grouped_bar, line, multi_line, pie, sparkline, stacked_bar
from .knowledge import (
    ddmrp_buffer_status,
    detection_ladder,
    evidence_timeline,
    knowledge_health_sparklines,
    maturity_trajectory,
    proactive_reactive_gauge,
    yield_from_cpk_curve,
)
from .scatter import pareto, scatter
from .surface import contour_plot, overlay_optimal_point, response_surface_from_model
from .time_series import capacity_loading, forecast_vs_actual, inventory_position
