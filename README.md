# ForgeViz

Zero-dependency data visualization. Python builds the spec. JS renders it. SVG for server-side.

No Plotly. No D3. No npm. No CDN. 15KB JS.

## Architecture

```
Python (spec layer)          JS (browser renderer)        Python (server renderer)
┌──────────────────┐         ┌───────────────────┐        ┌──────────────────┐
│ chart builders    │         │ forgeviz.js       │        │ renderers/svg.py │
│ → ChartSpec JSON │ ──────→ │ → SVG in browser  │        │ → SVG string     │
│                  │         │ + hover/click/zoom │        │ (for PDF/export) │
│ renderers/       │         └───────────────────┘        └──────────────────┘
│  plotly.py       │ ──→ Plotly JSON (backward compat)
│  svg.py          │ ──→ SVG string (server-side)
│  vegalite.py     │ ──→ Vega-Lite (future)
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
plotly_json = render(spec, format="plotly")   # For existing Plotly.js frontend
svg_string = render(spec, format="svg")       # For PDF export / ForgeDoc
chart_dict = render(spec, format="dict")      # Raw ChartSpec as dict
chart_json = render(spec, format="json")      # JSON string for forgeviz.js
```

## Browser Usage

```html
<div id="chart" style="width:800px;height:400px;"></div>
<script src="/static/js/forgeviz.js"></script>
<script>
    // Fetch spec from API
    fetch('/api/graph/chart/')
        .then(r => r.json())
        .then(spec => {
            const chart = ForgeViz.render(document.getElementById('chart'), spec);

            // Built-in actions
            chart.copyToClipboard();
            chart.downloadSVG('control_chart.svg');
            chart.downloadPNG('control_chart.png', 2);  // 2x scale
        });

    // Listen for click events
    document.getElementById('chart').addEventListener('forgeviz:click', e => {
        console.log('Clicked:', e.detail);  // {x, y, index, name}
    });
</script>
```

## Chart Types

| Builder | Module | Charts |
|---------|--------|--------|
| Control | `charts.control` | SPC control charts (any type), zone shading, OOC highlighting |
| Distribution | `charts.distribution` | Histogram + normal overlay, box plot |
| Effects | `charts.effects` | Main effects, interaction, Pareto of effects, normal probability |
| Scatter | `charts.scatter` | Scatter + regression, Pareto chart |
| Time Series | `charts.time_series` | Forecast vs actual, inventory position, capacity loading |

## Integration with Forge Packages

```python
# ForgeViz + ForgeSPC
from forgespc.charts import individuals_moving_range_chart
from forgeviz.charts.control import from_spc_result

spc_result = individuals_moving_range_chart(data)
chart_spec = from_spc_result(spc_result)  # Direct conversion
```

## JS Renderer Features

**Phase 1 (shipped):**
- SVG rendering (line, scatter, bar, area, step)
- Hover tooltips
- Click events (`forgeviz:click` CustomEvent)
- Copy to clipboard (SVG)
- Download SVG / PNG
- Responsive resize
- Theme support (svend_dark, light, print)

**Phase 2 (roadmap):**
- Linked brushing across charts
- Filter chips
- Annotation mode (click to add notes)
- Threshold dragging
- Chart composition (shared x-axis, synchronized cursors)

## Dependencies

**Python: ZERO.** Pure stdlib. No numpy. No scipy. No plotly.

**JS: ZERO.** Vanilla JS. No npm. No build. One `<script>` tag. ~15KB.

## Why Not Plotly?

| | Plotly.js | ForgeViz |
|---|----------|----------|
| Size | 3.5MB | ~15KB |
| Dependencies | D3.js, npm ecosystem | None |
| CDN required | Yes | No |
| First render | 200-500ms | <10ms |
| Custom behaviors | Fight the API | Write 10 lines of JS |
| Server-side SVG | Needs kaleido | Built-in (pure Python) |
| Click-through to graph | Impossible | Native CustomEvent |

## License

MIT
