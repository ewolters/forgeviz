"""ChartSpec — re-exported from the forgerender contract package.

The schema now lives in `forgerender` (zero-dep, shared by solvers and renderers).
forgeviz re-exports it here for backward compatibility and owns `render()` —
the dispatcher that turns a ChartSpec into dict/json/plotly/svg output.
"""

from __future__ import annotations

from typing import Any

from forgerender import (  # noqa: F401  (re-exported for back-compat)
    Annotation,
    Axis,
    ChartSpec,
    Marker,
    ReferenceLine,
    Trace,
    Zone,
)


def render(spec: ChartSpec, format: str = "dict") -> Any:
    """Render a ChartSpec to the specified format."""
    if format == "dict":
        return spec.to_dict()
    elif format == "json":
        return spec.to_json(indent=2)
    elif format == "plotly":
        from ..renderers.plotly import to_plotly
        return to_plotly(spec)
    elif format == "svg":
        from ..renderers.svg import to_svg
        return to_svg(spec)
    else:
        raise ValueError(f"Unknown format: {format}")
