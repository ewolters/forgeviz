"""Tests for the result→ChartSpec bridge.

The bridge dispatches by result type *name* (no import coupling), so these
tests use lightweight fakes named to match — keeping forgeviz dependency-free.
"""


from forgeviz.core.bridge import charts_from_result
from forgeviz.core.spec import ChartSpec


class CUSUMResult:
    """Advanced-SPC results self-render via the contract (to_render); the
    bridge has no builder for them anymore."""

    def to_render(self):
        return ChartSpec(chart_type="control_chart", subtitle="CUSUM")


class EWMAResult:
    def to_render(self):
        return ChartSpec(chart_type="control_chart", subtitle="EWMA")


class TestAdvancedSPCBridge:
    def test_cusum_self_renders_via_contract_fallback(self):
        charts = charts_from_result(CUSUMResult())
        assert len(charts) == 1
        assert charts[0].subtitle == "CUSUM"  # the result's own spec, untouched

    def test_ewma_self_renders_via_contract_fallback(self):
        charts = charts_from_result(EWMAResult())
        assert len(charts) == 1
        assert charts[0].subtitle == "EWMA"


# The ML builders (_charts_from_ml/_pca/_cluster) are GONE — forgeml's MLResult
# carries its raw points (§5b) and self-renders via the contract fallback. That
# behavior is covered in forgeml/tests/test_contract.py.


class WeibullFit:
    """Weibull self-renders via the contract — it carries failure_times (§5b),
    so with a sample it draws prob-plot + survival + hazard, hazard-only without."""

    def __init__(self, failure_times=None):
        self.shape = 2.0
        self.scale = 100.0
        self.failure_times = failure_times or []

    def to_render(self):
        return ChartSpec(chart_type="line", title="Hazard Function")

    def views(self):
        if self.failure_times:
            return [ChartSpec(chart_type="scatter", title="Weibull Probability Plot"),
                    ChartSpec(chart_type="line", title="Survival Curve"),
                    ChartSpec(chart_type="line", title="Hazard Function")]
        return [self.to_render()]


class TestWeibullBridge:
    def test_weibull_with_sample_self_renders_panel(self):
        charts = charts_from_result(WeibullFit(failure_times=[10, 20, 35, 50, 70, 90, 120]))
        assert len(charts) == 3
        assert all(isinstance(c, ChartSpec) for c in charts)

    def test_weibull_without_sample_falls_back_to_hazard(self):
        charts = charts_from_result(WeibullFit())
        assert len(charts) == 1
        assert charts[0].chart_type == "line"


# The _charts_from_bayesian_test builder is GONE — forgestat's BayesianTestResult
# self-renders its posterior density (field-only) via the contract fallback.
# Covered in forgestat/tests/test_contract.py.


class RegressionResult:
    """Regression self-renders its 4-in-1 via the contract — the result carries
    fitted+residuals, so the duck-typed regression builder is gone."""

    def views(self):
        return [ChartSpec(chart_type=t, title=t) for t in
                ("scatter", "scatter", "bar", "line")]


class TestRegressionBridge:
    def test_regression_self_renders_four_in_one(self):
        charts = charts_from_result(RegressionResult())
        assert len(charts) == 4
        assert all(isinstance(c, ChartSpec) for c in charts)


class ProcessCapability:
    """Capability results self-render via the contract (views carries the
    histogram + probability pair); the bridge has no builder for them anymore."""

    def views(self):
        return [
            ChartSpec(chart_type="capability_histogram"),
            ChartSpec(chart_type="probability_plot"),
        ]


class TestCapabilityBridge:
    def test_capability_self_renders_its_pair_via_contract_fallback(self):
        charts = charts_from_result(ProcessCapability())
        assert [c.chart_type for c in charts] == ["capability_histogram", "probability_plot"]


# The distribution builder (_charts_from_distribution) is GONE — the entire
# forgestat statistical family now carries its own data and self-renders via the
# contract fallback. That behavior is covered in forgestat/tests/test_contract.py.


# The _charts_from_gage_rr builder is GONE — forgestat's GageRRResult carries its
# raw measurements (§5b) and self-renders components + by-part/operator spreads
# via the contract fallback. Covered in forgestat/tests/test_contract.py.


class KaplanMeierResult:
    """KM self-renders via the contract — it already carries its computed
    survival curve, so the bridge forwards no failure_times= and has no builder."""

    def to_render(self):
        return ChartSpec(chart_type="line", title="Survival Curve")

    def views(self):
        return [self.to_render()]


class TestKaplanMeierBridge:
    def test_km_self_renders_survival_curve(self):
        charts = charts_from_result(KaplanMeierResult())
        assert len(charts) == 1
        assert charts[0].chart_type == "line"


class TestUnknownResult:
    def test_unknown_type_returns_empty(self):
        class SomethingElse:
            pass
        assert charts_from_result(SomethingElse()) == []


# ---------------------------------------------------------------------------
# Time-series family. Most result types carry their own arrays (pure type-name
# dispatch); ChangepointResult is the exception — it needs the raw series
# forwarded via chart_ctx (data=).
# ---------------------------------------------------------------------------


class DecompositionResult:
    """Decomposition self-renders via the contract (views carries the
    observed/trend/seasonal/residual panel); the bridge has no builder."""

    def views(self):
        return [ChartSpec(chart_type="line", title=t)
                for t in ("Observed", "Trend", "Seasonal", "Residual")]


class TestDecompositionBridge:
    def test_produces_four_line_panels(self):
        charts = charts_from_result(DecompositionResult())
        assert len(charts) == 4
        assert all(c.chart_type == "line" for c in charts)


class ACFResult:
    """ACF results self-render via the contract (views carries the ACF + PACF
    correlogram pair); the bridge has no builder for them anymore."""

    def views(self):
        acf = ChartSpec(chart_type="bar", title="Autocorrelation (ACF)")
        acf.add_reference_line(0.35, axis="y", dash="dashed")
        acf.add_reference_line(-0.35, axis="y", dash="dashed")
        pacf = ChartSpec(chart_type="bar", title="Partial Autocorrelation (PACF)")
        return [acf, pacf]


class TestACFBridge:
    def test_produces_acf_and_pacf_bars(self):
        charts = charts_from_result(ACFResult())
        assert len(charts) == 2
        assert all(c.chart_type == "bar" for c in charts)

    def test_confidence_bound_drawn_both_sides(self):
        charts = charts_from_result(ACFResult())
        assert len(charts[0].reference_lines) == 2


class CCFResult:
    """CCF self-renders via the contract — cross-correlation bar + bands."""

    def to_render(self):
        spec = ChartSpec(chart_type="bar", title="Cross-Correlation (CCF)")
        spec.add_reference_line(0.4, axis="y", dash="dashed")
        spec.add_reference_line(-0.4, axis="y", dash="dashed")
        return spec


class TestCCFBridge:
    def test_produces_ccf_bar(self):
        charts = charts_from_result(CCFResult())
        assert len(charts) == 1
        assert charts[0].chart_type == "bar"


class GrangerResult:
    """Granger self-renders via the contract — p-value bar + alpha threshold
    (alpha now rides the result, not a bridge kwarg)."""

    def to_render(self):
        spec = ChartSpec(chart_type="bar", title="Granger Causality — p-value by lag")
        spec.add_reference_line(0.05, axis="y", dash="dashed")
        return spec


class TestGrangerBridge:
    def test_produces_pvalue_bar(self):
        charts = charts_from_result(GrangerResult())
        assert len(charts) == 1
        assert charts[0].chart_type == "bar"

    def test_alpha_threshold_drawn(self):
        charts = charts_from_result(GrangerResult())
        assert len(charts[0].reference_lines) == 1


class _CP:
    def __init__(self, index):
        self.index = index


class ChangepointResult:
    """Changepoint self-renders via the contract — it now carries its own
    series (§5b), so the bridge forwards no data= and has no builder."""

    series = [10, 10, 10, 15, 15, 15, 15, 12, 12, 12]
    changepoints = [_CP(3), _CP(7)]

    def to_render(self):
        spec = ChartSpec(chart_type="line", title="Changepoint Detection")
        spec.add_trace(list(range(len(self.series))), self.series, name="series")
        for cp in self.changepoints:
            spec.add_reference_line(cp.index, axis="x", dash="dashed")
        return spec


class TestChangepointBridge:
    def test_self_renders_line_with_markers(self):
        charts = charts_from_result(ChangepointResult())
        assert len(charts) == 1
        assert charts[0].chart_type == "line"
        assert len(charts[0].reference_lines) == 2


class ARIMAResult:
    """ARIMA self-renders via the contract — forecast (3-trace band) +
    residuals. It still carries fitted+residuals, so the bridge's regression
    duck-type fallback must yield to the contract or it'd render a 4-in-1."""

    fitted = [10.0, 10.5, 11.0, 11.2, 11.5]
    residuals = [0.1, -0.2, 0.0, 0.3, -0.1]

    def to_render(self):
        spec = ChartSpec(chart_type="line", title="Forecast")
        spec.add_trace([1, 2, 3], [11.8, 12.0, 12.3], name="Forecast")
        spec.add_trace([1, 2, 3], [11.0, 11.0, 11.1], name="Lower")
        spec.add_trace([1, 2, 3], [12.6, 13.0, 13.5], name="Upper")
        return spec

    def views(self):
        return [self.to_render(), ChartSpec(chart_type="line", title="Residuals")]


class TestARIMABridge:
    def test_produces_forecast_and_residual_charts(self):
        charts = charts_from_result(ARIMAResult())
        assert len(charts) == 2
        assert charts[1].chart_type == "line"  # residuals over time

    def test_forecast_chart_carries_band(self):
        charts = charts_from_result(ARIMAResult())
        # predicted + ci_lower + ci_upper => 3 line traces
        assert len(charts[0].traces) == 3

    def test_arima_not_misrouted_to_regression_panel(self):
        # ARIMAResult exposes fitted+residuals; the regression duck-type
        # fallback must YIELD to the contract (views), not render a 4-in-1.
        charts = charts_from_result(ARIMAResult())
        assert len(charts) == 2  # forecast + residuals, not 4
