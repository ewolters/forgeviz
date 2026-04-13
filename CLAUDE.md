# ForgeViz

Zero-dependency data visualization platform. Python builds the spec, JS renders it, SVG for server-side.

## Architecture

```
forgeviz/
├── core/
│   ├── spec.py          # ChartSpec dataclass + render() dispatcher
│   ├── dashboard.py     # DashboardSpec + DashboardBuilder (grid layout, cross-filtering)
│   └── colors.py        # SVEND color system, themes, palettes
├── charts/              # Builders: data → ChartSpec
│   ├── generic.py       # bar, line, area, pie, donut, gauge, sparkline, bullet, risk_heatmap
│   ├── control.py       # SPC control charts (from forgespc results)
│   ├── capability.py    # Capability histogram, sixpack
│   ├── distribution.py  # Histogram, box plot
│   ├── scatter.py       # Scatter, pareto
│   ├── effects.py       # Main effects, interaction, normal probability, pareto of effects
│   ├── surface.py       # Contour, response surface
│   ├── diagnostic.py    # Residual plots, QQ, Cook's distance, four-in-one
│   ├── gage.py          # Gage R&R components, by part/operator, X-bar/R
│   ├── knowledge.py     # OLR-001: detection ladder, maturity, yield-from-Cpk
│   ├── time_series.py   # Forecast vs actual, inventory position, capacity loading
│   ├── reliability.py   # Survival, Weibull, hazard, reliability block diagram
│   ├── statistical.py   # Heatmap, dotplot, bubble, mosaic, parallel coordinates
│   ├── bayesian.py      # Bayesian control, capability, acceptance, changepoint
│   ├── interactive.py   # Slider, tornado, counterfactual
│   ├── advanced.py      # Waterfall, funnel, treemap, radar, violin, sankey, candlestick
│   └── trellis.py       # Small multiples / trellis grid (builds on DashboardSpec)
├── analytics/           # Auto-detection, enrichment, prediction
│   ├── auto.py          # Trend/outlier/changepoint/seasonality/cluster detection, enrich()
│   ├── predict.py       # Forecast overlays, time-to-breach, SPC forecast, capability forecast
│   └── recommend.py     # Chart recommendation engine, auto_dashboard()
├── renderers/
│   ├── plotly.py        # ChartSpec → Plotly JSON (backward compat)
│   └── svg.py           # ChartSpec → SVG string (server-side, handles all chart types)
├── themes/              # Re-exported from core.colors
├── calibration.py       # Empty adapter (rendering package, no golden cases)
└── static/js/
    ├── forgeviz.js          # Core client-side renderer (~2,100 lines)
    ├── forgeviz-interact.js # Zoom/pan, lasso, crosshair, annotations, linked brushing (~1,400 lines)
    └── forgeviz-dashboard.js # Dashboard grid renderer with cross-filtering (~900 lines)
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
# 293 tests, ~0.5s
```

## Key Design Decisions

- **ChartSpec is the universal exchange format** — every builder returns one, every renderer consumes one
- **DashboardSpec for multi-chart layouts** — grid of ChartSpecs with cross-filtering, global filters, panel chrome
- **Dict traces for complex types** — pie, box, heatmap, treemap, radar, violin, sankey, candlestick, waterfall, funnel use dict traces; line/scatter/bar use Trace dataclass
- **SVG renderer handles all types** — Trace objects and all dict trace types, including categorical x-axes
- **JS renderer is shipped via static/** — Django collectstatic picks it up when forgeviz is in INSTALLED_APPS
- **Colors are single source of truth** — core/colors.py defines every color used across the platform
- **No matplotlib, no plotly dependency** — pure Python specs, rendering is JS or SVG
- **Analytics are pure Python** — trend detection (OLS), outlier detection (IQR/z-score/MAD), changepoint detection (CUSUM), seasonality (autocorrelation), clustering (k-means), forecasting (Holt-Winters with auto-fit, EWMA, drift) — all zero dependencies

## Module Quick Reference

### charts/ — 82+ chart builder functions

Every function: `f(data, ...) -> ChartSpec`

| Module | Functions |
|--------|-----------|
| generic | bar, grouped_bar, stacked_bar, line, multi_line, area, stacked_area, pie, donut, gauge, sparkline, bullet, risk_heatmap |
| control | control_chart, from_spc_result, from_spc_result_pair |
| capability | capability_histogram, capability_sixpack |
| distribution | histogram, box_plot |
| scatter | scatter, pareto |
| effects | main_effects_plot, interaction_plot, pareto_of_effects, normal_probability_plot |
| surface | contour_plot, response_surface_from_model, overlay_optimal_point |
| diagnostic | residual_plot, residual_histogram, qq_plot, residual_vs_order, cooks_distance, four_in_one |
| gage | gage_rr_components, gage_rr_by_part, gage_rr_by_operator, gage_xbar_r |
| knowledge | knowledge_health_sparklines, maturity_trajectory, detection_ladder, evidence_timeline, proactive_reactive_gauge, yield_from_cpk_curve, ddmrp_buffer_status |
| time_series | forecast_vs_actual, inventory_position, capacity_loading |
| reliability | weibull_probability_plot, hazard_function, survival_curve, reliability_block_diagram |
| statistical | heatmap, scatter_matrix, individual_value_plot, interval_plot, dotplot, bubble, parallel_coordinates, mosaic |
| bayesian | bayesian_capability, bayesian_changepoint, bayesian_control_chart, bayesian_acceptance |
| interactive | slider_chart, sensitivity_tornado, counterfactual_comparison |
| advanced | waterfall, funnel, treemap, radar, violin, sankey, candlestick |
| trellis | trellis, trellis_control_charts, trellis_histograms, trellis_scatter, trellis_from_dataframe |

### analytics/ — auto-detection, enrichment, prediction

| Function | What it does |
|----------|-------------|
| `enrich(spec, features)` | Auto-add trends, outliers, changepoints, moving average to any chart |
| `auto_annotate(spec)` | Add min/max labels, trend indicator |
| `detect_trends(y)` | Sliding-window OLS, returns segments with slope/R² |
| `detect_outliers(y)` | IQR, z-score, or MAD methods |
| `detect_changepoints(y)` | CUSUM-based structural break detection |
| `detect_seasonality(y)` | Autocorrelation-based period detection |
| `detect_clusters(x, y)` | K-means with auto-k selection |
| `suggest_chart_type(data)` | Recommend chart type from data shape |
| `recommend(data)` | Ranked list of chart suggestions with ready-to-render specs |
| `auto_dashboard(sources)` | Auto-compose a dashboard from multiple data sources |
| `forecast_overlay(spec, horizon, method)` | Add Holt-Winters/EWMA/drift forecast cone to any chart |
| `spc_forecast(data, ucl, cl, lcl, horizon)` | Full SPC chart + forecast + time-to-breach + drift |
| `time_to_breach(y, limit)` | Estimate steps until limit breach |
| `process_drift_overlay(spec)` | Rolling mean + sigma envelope + drift rate |
| `capability_forecast(data, usl, lsl)` | Project Cpk forward, recommend action |

### core/dashboard.py — multi-chart dashboards

```python
from forgeviz import DashboardBuilder
dash = (DashboardBuilder("Overview", columns=3)
    .panel(chart1, 0, 0, col_span=2, filter_field="date")
    .panel(chart2, 0, 2, listen_fields=["date"])
    .filter("shift", "select", options=["A", "B", "C"])
    .build())
```

### JS files — 3 scripts, zero CDN

```html
<script src="/static/js/forgeviz.js"></script>          <!-- Core renderer -->
<script src="/static/js/forgeviz-interact.js"></script>  <!-- Zoom/pan/select -->
<script src="/static/js/forgeviz-dashboard.js"></script> <!-- Dashboard engine -->
```

- `ForgeViz.render(el, spec, {interactive: true})` — chart with zoom/pan/select
- `ForgeViz.dashboard(el, dashSpec)` — full dashboard with cross-filtering
- `ForgeViz.trellis(el, dashSpec)` — small multiples with synchronized crosshair
- `ForgeViz.compose(el, [spec1, spec2])` — stacked charts with shared x-axis
- `ForgeViz.interact(el)` — add zoom/pan/select to existing chart

## Gotchas

- `treemap`, `radar`, `violin`, `sankey`, `candlestick`, `waterfall`, `funnel` all use dict traces (not Trace dataclass) — check `t.get("type")` not `t.trace_type`
- `trellis()` returns a `DashboardSpec`, not a `ChartSpec`
- `forecast_overlay()` and `enrich()` return new specs — they never mutate the input
- Holt-Winters auto-fit tries 45 parameter combinations (alpha × beta grid) — fast but not instantaneous on very large datasets
- `_trellis_metadata` is attached as a Python attribute on DashboardSpec (not in to_dict()) — the JS trellis renderer reads it from the dashSpec directly
