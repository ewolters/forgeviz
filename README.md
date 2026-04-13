# ForgeViz

Zero-dependency data visualization platform. Python builds the spec. JS renders it. SVG for server-side.

No Plotly. No D3. No npm. No CDN. ~4.4KB JS total.

## Architecture

```
Python (spec layer)          JS (browser renderer)        Python (server renderer)
┌──────────────────┐         ┌───────────────────┐        ┌──────────────────┐
│ chart builders    │         │ forgeviz.js       │        │ renderers/svg.py │
│ → ChartSpec JSON │ ──────→ │ → SVG in browser  │        │ → SVG string     │
│                  │         │ + hover/click/zoom │        │ (for PDF/export) │
│ analytics/       │         ├───────────────────┤        └──────────────────┘
│  auto-detection  │         │ forgeviz-interact  │
│  forecasting     │         │ → zoom/pan/select  │
│  recommendations │         ├───────────────────┤
│                  │         │ forgeviz-dashboard │
│ dashboard engine │ ──────→ │ → grid + filtering │
│  cross-filtering │         └───────────────────┘
│  trellis grids   │
└──────────────────┘
```

## Install

```bash
pip install forgeviz    # Zero dependencies
```

## Python Usage

```python
from forgeviz.charts.control import control_chart
from forgeviz import render

# Build a chart spec
spec = control_chart(
    data_points=[23.1, 22.8, 23.4, 22.9, 23.0, 24.1, 22.5],
    ucl=24.0, cl=23.0, lcl=22.0,
    ooc_indices=[5],
    title="I-MR Chart — Line 2"
)

# Output formats
chart_dict = render(spec, format="dict")      # Raw ChartSpec as dict
chart_json = render(spec, format="json")      # JSON string for forgeviz.js
svg_string = render(spec, format="svg")       # For PDF export
plotly_json = render(spec, format="plotly")    # Backward compat
```

## Dashboards

```python
from forgeviz import DashboardBuilder
from forgeviz.charts.generic import bar, line
from forgeviz.charts.control import control_chart

dash = (DashboardBuilder("Production Overview", columns=3)
    .panel(control_chart(data, ucl=24, cl=23, lcl=22), 0, 0, col_span=2,
           filter_field="date")
    .panel(bar(categories, values, title="By Line"), 0, 2,
           listen_fields=["date"])
    .filter("shift", "select", options=["A", "B", "C"])
    .build())

spec_json = dash.to_json()
```

## Small Multiples / Trellis

```python
from forgeviz.charts.trellis import trellis, trellis_control_charts
from forgeviz.charts.generic import line

# Same chart, every production line
data = {
    "Line A": {"x": dates, "y": yields_a},
    "Line B": {"x": dates, "y": yields_b},
    "Line C": {"x": dates, "y": yields_c},
}
dash = trellis(data, line, title="Yield by Line", columns=3, shared_y=True)

# SPC trellis with shared limits
spc_data = {"Line 1": measurements_1, "Line 2": measurements_2}
dash = trellis_control_charts(spc_data, ucl=25, cl=20, lcl=15)
```

## Auto-Analytics

```python
from forgeviz.analytics import enrich, forecast_overlay, spc_forecast

# Auto-enrich any chart with trends, outliers, annotations
spec = line(dates, measurements, title="Process Data")
enriched = enrich(spec)  # adds trend line, outlier markers, min/max labels

# Forecast overlay with Holt-Winters
spec = forecast_overlay(spec, horizon=20, method="ets", confidence=0.95)

# Full SPC forecast: chart + forecast cone + time-to-breach
spec = spc_forecast(data, ucl=25, cl=20, lcl=15, horizon=30)
# → "Process will breach UCL in ~18 samples"

# Capability projection
from forgeviz.analytics import capability_forecast
result = capability_forecast(data, usl=80, lsl=20, horizon=20)
# → {current_cpk: 1.42, steps_to_critical: 15, recommendation: "monitor"}
```

## Browser Usage

```html
<!-- 3 script tags, zero CDN, zero npm -->
<script src="/static/js/forgeviz.js"></script>
<script src="/static/js/forgeviz-interact.js"></script>
<script src="/static/js/forgeviz-dashboard.js"></script>

<script>
    // Interactive chart with zoom, crosshair, selection
    ForgeViz.render(document.getElementById('chart'), spec, {
        interactive: true,  // enables zoom/pan/select
        toolbar: true,      // floating toolbar
    });

    // Dashboard with cross-filtering
    const db = ForgeViz.dashboard(document.getElementById('dash'), dashSpec);
    db.setFilter('shift', 'A');
    db.clearFilters();

    // Trellis with synchronized crosshair
    ForgeViz.trellis(document.getElementById('grid'), trellisSpec);

    // Events
    el.addEventListener('forgeviz:click', e => console.log(e.detail));
    el.addEventListener('forgeviz:select', e => console.log(e.detail.indices));
</script>
```

## Chart Types (82+)

| Module | Charts |
|--------|--------|
| generic | bar, grouped_bar, stacked_bar, line, multi_line, area, stacked_area, pie, donut, gauge, sparkline, bullet, risk_heatmap |
| control | SPC control charts (any type), zone shading, OOC highlighting |
| capability | Capability histogram, sixpack (6-panel) |
| distribution | Histogram + normal overlay, box plot |
| scatter | Scatter + regression, Pareto chart |
| effects | Main effects, interaction, Pareto of effects, normal probability |
| surface | Contour, response surface from model |
| diagnostic | Residual plots, QQ, Cook's distance, four-in-one |
| gage | Gage R&R components, by part/operator, X-bar/R |
| knowledge | Detection ladder, maturity trajectory, yield-from-Cpk |
| time_series | Forecast vs actual, inventory position, capacity loading |
| reliability | Survival, Weibull, hazard, reliability block diagram |
| statistical | Heatmap, scatter matrix, bubble, parallel coordinates, mosaic |
| bayesian | Bayesian control, capability, acceptance, changepoint |
| interactive | What-if slider, sensitivity tornado, counterfactual comparison |
| advanced | Waterfall, funnel, treemap, radar/spider, violin, sankey, candlestick |
| trellis | Small multiples grid (any chart × any grouping) |

## Analytics Engine

| Function | What |
|----------|------|
| `enrich(spec)` | Auto-add trends, outliers, changepoints, moving average |
| `forecast_overlay(spec, horizon)` | Holt-Winters / EWMA / drift forecast cone |
| `spc_forecast(data, ucl, cl, lcl)` | Full SPC chart + forecast + time-to-breach |
| `time_to_breach(y, limit)` | "How many samples until we hit the limit?" |
| `capability_forecast(data, usl, lsl)` | Project Cpk forward, recommend action |
| `process_drift_overlay(spec)` | Rolling mean + sigma envelope |
| `detect_trends / outliers / changepoints / seasonality / clusters` | Pattern detection |
| `suggest_chart_type(data)` | Recommend best visualization |
| `auto_dashboard(sources)` | Auto-compose dashboard from data |

## Integration with Forge Packages

```python
# ForgeViz + ForgeSPC
from forgespc.charts import individuals_moving_range_chart
from forgeviz.charts.control import from_spc_result

spc_result = individuals_moving_range_chart(data)
chart_spec = from_spc_result(spc_result)
```

## JS Interactivity

- **Zoom**: box-zoom (click+drag), scroll wheel, double-click reset
- **Selection**: shift+drag (box), alt+drag (lasso)
- **Crosshair**: snap-to-nearest cursor overlay
- **Annotations**: right-click to add persistent text labels
- **Linked brushing**: selections propagate across charts
- **Threshold dragging**: drag control limits to explore what-if
- **Chart composition**: stacked charts with shared x-axis, synced cursors
- **Style panel**: edit title, axis labels, colors, theme
- **Data table**: toggle underlying data view
- **Export**: copy, SVG, PNG

## Dependencies

**Python: ZERO.** Pure stdlib. No numpy. No scipy. No plotly.

**JS: ZERO.** Vanilla JS. No npm. No build. Three `<script>` tags. ~4.4KB total.

## Why Not Plotly?

| | Plotly.js | ForgeViz |
|---|----------|----------|
| Size | 3.5MB | ~4.4KB |
| Dependencies | D3.js, npm | None |
| CDN required | Yes | No |
| First render | 200-500ms | <10ms |
| Dashboard engine | Separate (Dash) | Built-in |
| Auto-analytics | None | Trends, forecasts, anomalies |
| Small multiples | Manual | One function call |
| SPC forecasting | None | Holt-Winters + time-to-breach |
| Server-side SVG | Needs kaleido | Built-in (pure Python) |

## License

MIT
