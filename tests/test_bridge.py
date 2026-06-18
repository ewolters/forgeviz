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


class MLResult:
    def __init__(self, feature_importance=None, algorithm="", statistics=None, predictions=None):
        self.feature_importance = feature_importance or {}
        self.algorithm = algorithm
        self.statistics = statistics or {}
        self.predictions = predictions or []


class TestAdvancedSPCBridge:
    def test_cusum_self_renders_via_contract_fallback(self):
        charts = charts_from_result(CUSUMResult())
        assert len(charts) == 1
        assert charts[0].subtitle == "CUSUM"  # the result's own spec, untouched

    def test_ewma_self_renders_via_contract_fallback(self):
        charts = charts_from_result(EWMAResult())
        assert len(charts) == 1
        assert charts[0].subtitle == "EWMA"


class TestMLBridge:
    def test_feature_importance_produces_bar(self):
        charts = charts_from_result(MLResult({"f1": 0.6, "f2": 0.3, "f3": 0.1}))
        assert len(charts) == 1
        assert isinstance(charts[0], ChartSpec)

    def test_no_feature_importance_yields_no_chart(self):
        assert charts_from_result(MLResult({})) == []

    def test_pca_produces_scree_and_loadings(self):
        r = MLResult(algorithm="pca", statistics={
            "explained_variance_ratio": [0.6, 0.25, 0.15],
            "loadings": {"PC1": {"a": 0.7, "b": 0.5, "c": 0.1}},
        })
        charts = charts_from_result(r)
        assert len(charts) == 2
        assert all(isinstance(c, ChartSpec) for c in charts)

    def test_cluster_with_coords_produces_scatter_and_sizes(self):
        r = MLResult(algorithm="kmeans",
                     statistics={"cluster_sizes": {"cluster_0": 3, "cluster_1": 2}},
                     predictions=[0, 1, 0, 1, 0])
        X = [[1, 2], [8, 9], [1.5, 2.5], [8.5, 9.5], [1, 2.2]]
        charts = charts_from_result(r, X=X)
        assert len(charts) == 2
        assert all(isinstance(c, ChartSpec) for c in charts)

    def test_cluster_without_coords_falls_back_to_size_bar(self):
        r = MLResult(algorithm="kmeans",
                     statistics={"cluster_sizes": {"cluster_0": 3, "cluster_1": 2}},
                     predictions=[0, 1, 0])
        charts = charts_from_result(r)
        assert len(charts) == 1


class WeibullFit:
    def __init__(self):
        self.shape = 2.0
        self.scale = 100.0
        self.location = 0.0
        self.failure_mode = "wear_out"


class TestWeibullBridge:
    def test_weibull_with_failure_times_produces_panel(self):
        charts = charts_from_result(
            WeibullFit(), failure_times=[10, 20, 35, 50, 70, 90, 120]
        )
        assert len(charts) == 3
        assert all(isinstance(c, ChartSpec) for c in charts)
        assert {c.chart_type for c in charts} == {"weibull_prob", "survival", "hazard"}

    def test_weibull_without_failure_times_falls_back_to_hazard(self):
        charts = charts_from_result(WeibullFit())
        assert len(charts) == 1
        assert charts[0].chart_type == "hazard"


class BayesianTestResult:
    def __init__(self, posterior_mean=None, posterior_std=None,
                 credible_interval=None, p_rope=None):
        self.test_name = "bayes"
        self.posterior_mean = posterior_mean
        self.posterior_std = posterior_std
        self.credible_interval = credible_interval
        self.p_rope = p_rope


class TestBayesianBridge:
    def test_posterior_with_moments_produces_density(self):
        r = BayesianTestResult(posterior_mean=1.5, posterior_std=0.4,
                               credible_interval=(0.7, 2.3), p_rope=0.05)
        charts = charts_from_result(r)
        assert len(charts) == 1
        assert isinstance(charts[0], ChartSpec)
        assert charts[0].chart_type == "posterior_density"

    def test_posterior_without_std_yields_no_chart(self):
        # eta-squared / R² results carry a mean but no posterior std
        r = BayesianTestResult(posterior_mean=0.42)
        assert charts_from_result(r) == []


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


class TTestResult:
    pass


class TestDistributionBridge:
    def test_two_group_test_adds_per_group_qq(self):
        groups = {"A": [1.0, 2.0, 1.5, 2.2, 1.8, 2.1],
                  "B": [3.0, 3.5, 2.9, 3.2, 3.8, 3.1]}
        charts = charts_from_result(TTestResult(), groups=groups)
        assert len(charts) == 3  # box plot + one Q-Q per group
        types = [c.chart_type for c in charts]
        assert types.count("qq_plot") == 2

    def test_one_sample_adds_qq(self):
        charts = charts_from_result(TTestResult(), data=[1.0, 2.0, 1.5, 2.2, 1.8, 2.1, 1.9])
        assert len(charts) == 2  # histogram + Q-Q
        assert any(c.chart_type == "qq_plot" for c in charts)


class GageRRResult:
    def __init__(self):
        self.design = "crossed"
        self.pct_gage_rr = 18.0
        self.pct_repeatability = 12.0
        self.pct_reproducibility = 6.0
        self.pct_part = 82.0
        self.ndc = 4


class TestGageRRBridge:
    def test_components_only_without_raw_data(self):
        charts = charts_from_result(GageRRResult())
        assert len(charts) == 1
        assert charts[0].chart_type == "gage_components"

    def test_full_panel_with_measurements(self):
        meas = [10.1, 10.2, 9.9, 10.0, 10.3, 10.1]
        parts = ["P1", "P1", "P2", "P2", "P3", "P3"]
        ops = ["A", "B", "A", "B", "A", "B"]
        charts = charts_from_result(GageRRResult(), measurements=meas, parts=parts, operators=ops)
        assert len(charts) == 3
        assert {c.chart_type for c in charts} == {"gage_components", "gage_by_part", "gage_by_operator"}


class KaplanMeierResult:
    def __init__(self):
        self.median_survival = 50.0
        self.mean_survival = 55.0
        self.n_censored = 2


class TestKaplanMeierBridge:
    def test_km_with_times_produces_survival_curve(self):
        charts = charts_from_result(
            KaplanMeierResult(),
            failure_times=[5, 10, 15, 20, 25, 30, 40, 50],
            censored=[False, False, False, True, False, False, True, False],
        )
        assert len(charts) == 1
        assert charts[0].chart_type == "survival"

    def test_km_without_times_yields_no_chart(self):
        assert charts_from_result(KaplanMeierResult()) == []


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


# ---------------------------------------------------------------------------
# Power family. PowerResult is a single solved point; the handler sweeps the
# calculation across sample sizes and forwards the curve via chart_ctx.
# ---------------------------------------------------------------------------


class PowerResult:
    def __init__(self):
        self.test = "z-test"
        self.power = 0.8
        self.sample_size = 32
        self.alpha = 0.05
        self.effect_size = 0.5


class TestPowerBridge:
    def test_with_curve_produces_line(self):
        curve = {"n": [10, 20, 30, 40, 50],
                 "power": [0.4, 0.6, 0.78, 0.88, 0.94],
                 "solved_n": 32, "target_power": 0.8}
        charts = charts_from_result(PowerResult(), power_curve=curve)
        assert len(charts) == 1
        assert charts[0].chart_type == "line"

    def test_curve_draws_target_and_solved_markers(self):
        curve = {"n": [10, 20, 30], "power": [0.4, 0.6, 0.78],
                 "solved_n": 30, "target_power": 0.8}
        charts = charts_from_result(PowerResult(), power_curve=curve)
        assert len(charts[0].reference_lines) == 2

    def test_without_curve_yields_no_chart(self):
        assert charts_from_result(PowerResult()) == []
