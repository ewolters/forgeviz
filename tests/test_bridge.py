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
    def __init__(self, fitted=None, residuals=None):
        self.fitted = fitted or []
        self.residuals = residuals or []
        self.coefficients = {"x1": 1.2}
        self.r_squared = 0.8


class TestRegressionBridge:
    def test_regression_produces_four_in_one(self):
        r = RegressionResult(
            fitted=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            residuals=[0.1, -0.2, 0.05, -0.1, 0.2, -0.05],
        )
        charts = charts_from_result(r)
        assert len(charts) == 4
        assert all(isinstance(c, ChartSpec) for c in charts)
        types = {c.chart_type for c in charts}
        assert "residual" in types
        assert "qq_plot" in types
        assert "residual_order" in types

    def test_regression_without_arrays_yields_no_chart(self):
        assert charts_from_result(RegressionResult()) == []


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
    def __init__(self):
        self.observed = [10.0, 12.0, 11.0, 13.0, 12.0, 14.0]
        self.trend = [10.5, 11.0, 11.5, 12.0, 12.5, 13.0]
        self.seasonal = [-0.5, 0.5, -0.5, 0.5, -0.5, 0.5]
        self.residual = [0.0, 0.5, 0.0, 0.5, 0.0, 0.5]
        self.model = "additive"
        self.period = 2


class TestDecompositionBridge:
    def test_produces_four_line_panels(self):
        charts = charts_from_result(DecompositionResult())
        assert len(charts) == 4
        assert all(c.chart_type == "line" for c in charts)

    def test_empty_components_yield_no_chart(self):
        r = DecompositionResult()
        r.observed = r.trend = r.seasonal = r.residual = []
        assert charts_from_result(r) == []


class ACFResult:
    def __init__(self):
        self.acf_values = [1.0, 0.6, 0.3, 0.1]
        self.pacf_values = [1.0, 0.5, 0.1, -0.1]
        self.confidence_bound = 0.35


class TestACFBridge:
    def test_produces_acf_and_pacf_bars(self):
        charts = charts_from_result(ACFResult())
        assert len(charts) == 2
        assert all(c.chart_type == "bar" for c in charts)

    def test_confidence_bound_drawn_both_sides(self):
        charts = charts_from_result(ACFResult())
        assert len(charts[0].reference_lines) == 2


class CCFResult:
    def __init__(self):
        self.lags = [-2, -1, 0, 1, 2]
        self.ccf_values = [0.1, 0.3, 0.6, 0.2, -0.1]
        self.confidence_bound = 0.4
        self.peak_lag = 0


class TestCCFBridge:
    def test_produces_ccf_bar(self):
        charts = charts_from_result(CCFResult())
        assert len(charts) == 1
        assert charts[0].chart_type == "bar"


class GrangerResult:
    def __init__(self):
        self.results_by_lag = [
            {"lag": 1, "f_stat": 5.0, "p_value": 0.02},
            {"lag": 2, "f_stat": 3.0, "p_value": 0.08},
        ]
        self.best_lag = 1
        self.best_p_value = 0.02
        self.x_causes_y = True


class TestGrangerBridge:
    def test_produces_pvalue_bar(self):
        charts = charts_from_result(GrangerResult())
        assert len(charts) == 1
        assert charts[0].chart_type == "bar"

    def test_alpha_threshold_drawn(self):
        charts = charts_from_result(GrangerResult(), alpha=0.05)
        assert len(charts[0].reference_lines) == 1


class _CP:
    def __init__(self, index):
        self.index = index


class ChangepointResult:
    def __init__(self):
        self.method = "pelt"
        self.changepoints = [_CP(3), _CP(7)]
        self.segment_means = [10.0, 15.0, 12.0]
        self.segment_boundaries = [0, 3, 7]
        self.n_segments = 3


class TestChangepointBridge:
    def test_with_data_produces_line_with_markers(self):
        data = [10, 10, 10, 15, 15, 15, 15, 12, 12, 12]
        charts = charts_from_result(ChangepointResult(), data=data)
        assert len(charts) == 1
        assert charts[0].chart_type == "line"
        assert len(charts[0].reference_lines) == 2

    def test_without_data_yields_no_chart(self):
        assert charts_from_result(ChangepointResult()) == []


class _FP:
    def __init__(self, step, predicted, ci_lower, ci_upper):
        self.step = step
        self.predicted = predicted
        self.ci_lower = ci_lower
        self.ci_upper = ci_upper


class ARIMAResult:
    def __init__(self):
        self.fitted = [10.0, 10.5, 11.0, 11.2, 11.5]
        self.residuals = [0.1, -0.2, 0.0, 0.3, -0.1]
        self.forecast = [_FP(1, 11.8, 11.0, 12.6), _FP(2, 12.0, 11.0, 13.0),
                         _FP(3, 12.3, 11.1, 13.5)]
        self.ljung_box_p = 0.4


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
        # ARIMAResult exposes fitted+residuals; must match by name, NOT the
        # duck-typed regression fallback (which would yield a 4-in-1 panel).
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
