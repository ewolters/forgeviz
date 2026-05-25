"""Streaming specs — charts that maintain state and accept appended data.

A StreamingSpec wraps a ChartSpec and adds:
- append(x, y) — add data points, update running statistics
- Running mean, std, min, max without storing all history
- Alert detection (out-of-control, spec violation)
- Content hash versioning (changes on every append)

The streaming spec IS the monitoring system. No separate dashboard needed.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

from .spec import ChartSpec


@dataclass
class RunningStats:
    """Welford's online algorithm for mean and variance."""

    n: int = 0
    mean: float = 0.0
    m2: float = 0.0  # sum of squares of differences from current mean
    min_val: float = float("inf")
    max_val: float = float("-inf")

    def update(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.m2 += delta * delta2
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

    @property
    def variance(self) -> float:
        return self.m2 / (self.n - 1) if self.n > 1 else 0.0

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    def to_dict(self) -> dict:
        return {
            "n": self.n, "mean": round(self.mean, 6),
            "std": round(self.std, 6), "min": round(self.min_val, 6),
            "max": round(self.max_val, 6),
        }


@dataclass
class Alert:
    """A detected condition in the streaming data."""

    index: int
    alert_type: str  # "ooc_upper", "ooc_lower", "above_usl", "below_lsl", "trend", "shift"
    value: float
    message: str


@dataclass
class StreamingSpec:
    """A chart that maintains state and accepts appended data.

    Usage:
        stream = StreamingSpec.control_chart("Diameter", ucl=25.1, cl=25.0, lcl=24.9)
        stream.append(25.02)
        stream.append(25.05)
        stream.append(25.15)  # triggers alert
        spec = stream.to_chart_spec()  # ready for any renderer
    """

    title: str = ""
    chart_type: str = "streaming_control"
    x_data: list[Any] = field(default_factory=list)
    y_data: list[float] = field(default_factory=list)
    stats: RunningStats = field(default_factory=RunningStats)
    alerts: list[Alert] = field(default_factory=list)
    version: int = 0

    # Control limits (optional — set for SPC charts)
    ucl: float | None = None
    cl: float | None = None
    lcl: float | None = None
    usl: float | None = None
    lsl: float | None = None

    # Configuration
    max_points: int = 500  # rolling window for display (0 = unlimited)
    x_label: str = "Sample"
    y_label: str = "Value"

    def append(self, value: float, x: Any = None) -> list[Alert]:
        """Append a data point and return any triggered alerts."""
        self.version += 1
        self.stats.update(value)

        x_val = x if x is not None else self.stats.n
        self.x_data.append(x_val)
        self.y_data.append(value)

        # Trim to rolling window
        if self.max_points > 0 and len(self.y_data) > self.max_points:
            self.x_data = self.x_data[-self.max_points:]
            self.y_data = self.y_data[-self.max_points:]

        new_alerts = self._check_alerts(value, self.stats.n)
        self.alerts.extend(new_alerts)
        return new_alerts

    def append_batch(self, values: list[float], x_values: list[Any] | None = None) -> list[Alert]:
        """Append multiple data points. Returns all triggered alerts."""
        all_alerts = []
        for i, v in enumerate(values):
            xv = x_values[i] if x_values and i < len(x_values) else None
            all_alerts.extend(self.append(v, xv))
        return all_alerts

    def _check_alerts(self, value: float, index: int) -> list[Alert]:
        """Check a new value against limits and patterns."""
        alerts = []
        if self.ucl is not None and value > self.ucl:
            alerts.append(Alert(index, "ooc_upper", value, f"Above UCL ({self.ucl})"))
        if self.lcl is not None and value < self.lcl:
            alerts.append(Alert(index, "ooc_lower", value, f"Below LCL ({self.lcl})"))
        if self.usl is not None and value > self.usl:
            alerts.append(Alert(index, "above_usl", value, f"Above USL ({self.usl})"))
        if self.lsl is not None and value < self.lsl:
            alerts.append(Alert(index, "below_lsl", value, f"Below LSL ({self.lsl})"))

        # Run of 7 — all above or below CL
        if self.cl is not None and len(self.y_data) >= 7:
            last7 = self.y_data[-7:]
            if all(v > self.cl for v in last7):
                alerts.append(Alert(index, "shift", value, "7 consecutive above CL"))
            elif all(v < self.cl for v in last7):
                alerts.append(Alert(index, "shift", value, "7 consecutive below CL"))

        # Trend of 7 — monotonically increasing or decreasing
        if len(self.y_data) >= 7:
            last7 = self.y_data[-7:]
            if all(last7[i] < last7[i + 1] for i in range(6)):
                alerts.append(Alert(index, "trend", value, "7 consecutive increasing"))
            elif all(last7[i] > last7[i + 1] for i in range(6)):
                alerts.append(Alert(index, "trend", value, "7 consecutive decreasing"))

        return alerts

    def to_chart_spec(self) -> ChartSpec:
        """Render current state as a ChartSpec."""
        from ..charts.control import control_chart

        if self.ucl is not None and self.cl is not None and self.lcl is not None:
            ooc_indices = [a.index - (self.stats.n - len(self.y_data))
                           for a in self.alerts
                           if a.alert_type in ("ooc_upper", "ooc_lower")
                           and 0 <= a.index - (self.stats.n - len(self.y_data)) < len(self.y_data)]
            spec = control_chart(
                data_points=self.y_data,
                ucl=self.ucl, cl=self.cl, lcl=self.lcl,
                ooc_indices=ooc_indices,
                title=self.title or "Streaming Control Chart",
                usl=self.usl, lsl=self.lsl,
            )
        else:
            spec = ChartSpec(
                title=self.title or "Streaming Chart",
                chart_type="streaming",
                x_axis={"label": self.x_label},
                y_axis={"label": self.y_label},
            )
            spec.add_trace(list(self.x_data), list(self.y_data),
                           name="Data", trace_type="line", marker_size=3)

        # Embed streaming metadata
        spec.interactive = {
            "type": "streaming",
            "version": self.version,
            "stats": self.stats.to_dict(),
            "n_alerts": len(self.alerts),
            "latest_alerts": [
                {"index": a.index, "type": a.alert_type, "value": round(a.value, 4), "message": a.message}
                for a in self.alerts[-5:]  # last 5 alerts
            ],
            "content_hash": self.content_hash(),
        }

        return spec

    def content_hash(self) -> str:
        """Deterministic hash of current state."""
        state = json.dumps({
            "n": self.stats.n, "mean": self.stats.mean,
            "m2": self.stats.m2, "version": self.version,
        }, sort_keys=True)
        return hashlib.sha256(state.encode()).hexdigest()[:12]

    def summary(self) -> dict:
        """Return a summary of the streaming state."""
        return {
            "title": self.title,
            "version": self.version,
            "stats": self.stats.to_dict(),
            "n_alerts": len(self.alerts),
            "n_displayed": len(self.y_data),
            "content_hash": self.content_hash(),
            "in_control": not any(a.alert_type.startswith("ooc") for a in self.alerts[-10:]),
        }

    @classmethod
    def control_chart(
        cls,
        title: str = "Control Chart",
        ucl: float = 0,
        cl: float = 0,
        lcl: float = 0,
        usl: float | None = None,
        lsl: float | None = None,
        max_points: int = 500,
    ) -> StreamingSpec:
        """Factory for a streaming SPC control chart."""
        return cls(
            title=title, chart_type="streaming_control",
            ucl=ucl, cl=cl, lcl=lcl, usl=usl, lsl=lsl,
            max_points=max_points,
        )
