"""Contract fallback: charts_from_result tries result.to_render() for types
the bridge doesn't recognize. The fallback is LAST — known builders keep
priority because they compose richer views (chart pairs, data-context charts)
than a result can self-render from its own fields."""

from forgecore import ChartSpec

from forgeviz.core.bridge import charts_from_result


class _SelfRenderingResult:
    """An unknown-to-the-bridge result that speaks the forgecore contract."""

    summary = "self-rendered"

    def to_render(self):
        spec = ChartSpec(title="Self Portrait", chart_type="bar")
        spec.add_trace([1, 2, 3], [4, 5, 6], name="series")
        return spec


class _MuteResult:
    summary = "nothing to draw"


class _BrokenRenderResult:
    summary = "raises"

    def to_render(self):
        raise RuntimeError("solver bug")


def test_unmatched_type_with_to_render_self_renders():
    charts = charts_from_result(_SelfRenderingResult())
    assert len(charts) == 1
    assert charts[0].title == "Self Portrait"


def test_unmatched_type_without_to_render_returns_empty():
    assert charts_from_result(_MuteResult()) == []


def test_broken_to_render_returns_empty_not_raise():
    assert charts_from_result(_BrokenRenderResult()) == []


def test_known_builder_keeps_priority_over_to_render():
    # ControlChartResult HAS to_render() (single chart) but the bridge's
    # pair builder (primary + secondary, e.g. I + MR) must keep winning.
    from forgespc.charts import individuals_moving_range_chart

    result = individuals_moving_range_chart([5.1, 5.0, 5.2, 4.9, 5.1, 5.3, 5.0, 5.1])
    assert callable(getattr(result, "to_render", None))  # contract present
    charts = charts_from_result(result)
    assert len(charts) == 2  # pair, not the single self-rendered chart
