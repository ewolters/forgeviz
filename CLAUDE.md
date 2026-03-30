# ForgeViz

Zero-dependency data visualization. Python builds the spec, JS renders it, SVG for server-side.

## Architecture

```
forgeviz/
├── core/
│   ├── spec.py          # ChartSpec dataclass + render() dispatcher
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
│   └── interactive.py   # Slider, tornado, counterfactual
├── renderers/
│   ├── plotly.py        # ChartSpec → Plotly JSON (being phased out)
│   └── svg.py           # ChartSpec → SVG string (server-side)
├── themes/              # Re-exported from core.colors
├── calibration.py       # Empty adapter (rendering package, no golden cases)
└── static/js/
    └── forgeviz.js      # Client-side JS renderer (1,158 lines)
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Key Design Decisions

- **ChartSpec is the universal exchange format** — every builder returns one, every renderer consumes one
- **Dict traces for complex types** — pie, box, heatmap, contour use dict traces; line/scatter/bar use Trace dataclass
- **SVG renderer handles both** — Trace objects and dict traces, including categorical x-axes
- **JS renderer is shipped via static/** — Django collectstatic picks it up when forgeviz is in INSTALLED_APPS
- **Colors are single source of truth** — core/colors.py defines every color used across the platform
- **No matplotlib, no plotly dependency** — pure Python specs, rendering is JS or SVG
