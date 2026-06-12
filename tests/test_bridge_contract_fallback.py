"""Contract fallback: charts_from_result asks unrecognized types for their
complete portrait — views() when present, to_render() otherwise. The fallback
is LAST — remaining builders keep priority because they compose data-context
charts a result cannot draw from its own fields."""

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


class _PairViewsResult:
    """Unknown to the bridge; its complete portrait is two charts."""

    summary = "pair"

    def to_render(self):
        return ChartSpec(title="Primary", chart_type="line")

    def views(self):
        return [self.to_render(), ChartSpec(title="Secondary", chart_type="line")]


def test_multi_view_result_renders_all_views():
    charts = charts_from_result(_PairViewsResult())
    assert [c.title for c in charts] == ["Primary", "Secondary"]


def test_control_chart_pair_self_renders_via_views():
    # The I-MR pair now comes from ControlChartResult.views() (the result
    # carries its secondary chart) — no bridge builder, theme-neutral output.
    from forgespc.charts import individuals_moving_range_chart

    result = individuals_moving_range_chart([5.1, 5.0, 5.2, 4.9, 5.1, 5.3, 5.0, 5.1])
    charts = charts_from_result(result)

    assert len(charts) == 2  # the pair survives the builder's deletion
    assert charts[1].subtitle == "MR"
    # neutral colors prove the contract path, not the themed legacy builder
    assert charts[0].to_dict()["traces"][0]["color"] == ""
