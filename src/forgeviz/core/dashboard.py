"""Dashboard Engine — multi-chart layouts with cross-filtering.

DashboardSpec is the dashboard analogue of ChartSpec: a JSON-serializable
specification that describes a grid of panels, their layout, cross-filter
wiring, and global filter controls. The client-side renderer
(forgeviz-dashboard.js) consumes the JSON and builds the interactive UI.

Usage:
    from forgeviz.core.dashboard import DashboardSpec, DashboardBuilder
    from forgeviz.charts.generic import bar, line

    # Direct construction
    dash = DashboardSpec(title="Production Overview", columns=3)
    dash.add_panel(line(x, y, title="Trend"), row=0, col=0, col_span=2,
                   filter_field="date")
    dash.add_panel(bar(cats, vals, title="By Line"), row=0, col=2,
                   listen_fields=["date"])
    dash.add_filter("shift", filter_type="select", options=["A", "B", "C"])
    spec_json = dash.to_json(indent=2)

    # Fluent builder
    dash = (DashboardBuilder("Production Overview", columns=3)
        .panel(line(x, y, title="Trend"), 0, 0, col_span=2, filter_field="date")
        .panel(bar(cats, vals, title="By Line"), 0, 2, listen_fields=["date"])
        .filter("shift", "select", options=["A", "B", "C"])
        .build())
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .spec import ChartSpec


@dataclass
class DashboardPanel:
    """A single panel in a dashboard."""

    id: str  # unique panel ID
    spec: ChartSpec  # the chart
    row: int = 0  # grid row (0-indexed)
    col: int = 0  # grid column
    row_span: int = 1  # how many rows this panel spans
    col_span: int = 1  # how many columns
    filter_field: str = ""  # field name this panel filters on (when clicked)
    listen_fields: list[str] = field(default_factory=list)  # fields this panel responds to
    data_source: str = ""  # data source ID for cross-filtering
    drilldown: dict[str, Any] = field(default_factory=dict)  # {field: "next_chart_type"}

    def to_dict(self) -> dict:
        """Serialize panel including nested ChartSpec."""
        d = {
            "id": self.id,
            "spec": self.spec.to_dict(),
            "row": self.row,
            "col": self.col,
            "row_span": self.row_span,
            "col_span": self.col_span,
            "filter_field": self.filter_field,
            "listen_fields": list(self.listen_fields),
            "data_source": self.data_source,
            "drilldown": dict(self.drilldown),
        }
        return d


@dataclass
class DashboardSpec:
    """A multi-chart dashboard with cross-filtering.

    Panels are placed on a CSS Grid. Cross-filtering is wired via
    filter_field (emitter) and listen_fields (receiver). Global
    filters appear as controls above the grid.
    """

    title: str = ""
    panels: list[DashboardPanel] = field(default_factory=list)
    columns: int = 2  # grid columns
    row_height: int = 350  # default row height in px
    theme: str = "svend_dark"
    filters: list[dict[str, Any]] = field(default_factory=list)
    # [{id, field, type: "select"|"range"|"date_range", options: [...], label: str}]

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def add_panel(
        self,
        spec: ChartSpec,
        row: int = 0,
        col: int = 0,
        **kwargs: Any,
    ) -> DashboardPanel:
        """Add a chart panel to the dashboard and return it."""
        panel_id = f"panel_{len(self.panels)}"
        p = DashboardPanel(id=panel_id, spec=spec, row=row, col=col, **kwargs)
        self.panels.append(p)
        return p

    def add_filter(
        self,
        filter_field: str,
        filter_type: str = "select",
        options: list[Any] | None = None,
        label: str = "",
    ) -> None:
        """Add a global filter control."""
        self.filters.append(
            {
                "id": f"filter_{len(self.filters)}",
                "field": filter_field,
                "type": filter_type,
                "options": options or [],
                "label": label or filter_field,
            }
        )

    def get_panel(self, panel_id: str) -> DashboardPanel | None:
        """Look up a panel by ID."""
        for p in self.panels:
            if p.id == panel_id:
                return p
        return None

    def remove_panel(self, panel_id: str) -> bool:
        """Remove a panel by ID. Returns True if found."""
        for i, p in enumerate(self.panels):
            if p.id == panel_id:
                self.panels.pop(i)
                return True
        return False

    # ------------------------------------------------------------------
    # Grid introspection
    # ------------------------------------------------------------------

    @property
    def row_count(self) -> int:
        """Number of rows needed to contain all panels."""
        if not self.panels:
            return 0
        return max(p.row + p.row_span for p in self.panels)

    @property
    def filter_fields(self) -> set[str]:
        """All filter_field values declared across panels."""
        return {p.filter_field for p in self.panels if p.filter_field}

    @property
    def listen_field_set(self) -> set[str]:
        """All listen_fields values declared across panels."""
        s: set[str] = set()
        for p in self.panels:
            s.update(p.listen_fields)
        return s

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "title": self.title,
            "columns": self.columns,
            "row_height": self.row_height,
            "theme": self.theme,
            "filters": [dict(f) for f in self.filters],
            "panels": [p.to_dict() for p in self.panels],
        }

    def to_json(self, **kwargs: Any) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DashboardSpec:
        """Reconstruct from a serialized dict."""
        panels = []
        for pd in d.get("panels", []):
            spec_data = pd.pop("spec", {})
            chart_spec = ChartSpec(
                title=spec_data.get("title", ""),
                subtitle=spec_data.get("subtitle", ""),
                chart_type=spec_data.get("chart_type", ""),
                theme=spec_data.get("theme", "svend_dark"),
                width=spec_data.get("width", 800),
                height=spec_data.get("height", 400),
            )
            panels.append(DashboardPanel(spec=chart_spec, **pd))

        return cls(
            title=d.get("title", ""),
            columns=d.get("columns", 2),
            row_height=d.get("row_height", 350),
            theme=d.get("theme", "svend_dark"),
            filters=d.get("filters", []),
            panels=panels,
        )


class DashboardBuilder:
    """Fluent builder for dashboards.

    Usage:
        dash = (DashboardBuilder("My Dashboard", columns=3)
            .panel(chart1, 0, 0, col_span=2)
            .panel(chart2, 0, 2)
            .panel(chart3, 1, 0, col_span=3, filter_field="category")
            .filter("shift", "select", options=["A", "B", "C"])
            .row_height(400)
            .theme("nordic")
            .build())
    """

    def __init__(
        self,
        title: str = "",
        columns: int = 2,
        theme: str = "svend_dark",
    ) -> None:
        self.dashboard = DashboardSpec(
            title=title, columns=columns, theme=theme
        )

    def panel(
        self,
        spec: ChartSpec,
        row: int = 0,
        col: int = 0,
        row_span: int = 1,
        col_span: int = 1,
        **kwargs: Any,
    ) -> DashboardBuilder:
        """Add a panel and return self for chaining."""
        self.dashboard.add_panel(
            spec, row=row, col=col, row_span=row_span, col_span=col_span, **kwargs
        )
        return self

    def filter(
        self,
        filter_field: str,
        filter_type: str = "select",
        options: list[Any] | None = None,
        label: str = "",
    ) -> DashboardBuilder:
        """Add a global filter and return self for chaining."""
        self.dashboard.add_filter(filter_field, filter_type, options, label)
        return self

    def row_height(self, height: int) -> DashboardBuilder:
        """Set row height in pixels."""
        self.dashboard.row_height = height
        return self

    def theme(self, name: str) -> DashboardBuilder:
        """Set dashboard theme."""
        self.dashboard.theme = name
        return self

    def build(self) -> DashboardSpec:
        """Return the finished DashboardSpec."""
        return self.dashboard
