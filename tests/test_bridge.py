"""Tests for the result→ChartSpec bridge.

The bridge dispatches by result type *name* (no import coupling), so these
tests use lightweight fakes named to match — keeping forgeviz dependency-free.
"""

from forgeviz.core.bridge import charts_from_result
from forgeviz.core.spec import ChartSpec


class CUSUMResult:
    def __init__(self):
        self.cusum_pos = [0.0, 1.2, 2.4, 3.6, 4.8]
        self.cusum_neg = [0.0, 0.5, 0.0, 0.3, 0.0]
        self.signals_up = [4]
        self.signals_down = []
        self.h = 5.0
        self.sigma = 1.0
        self.n = 5


class EWMAResult:
    def __init__(self):
        self.ewma_values = [10.0, 10.2, 9.8, 10.1, 10.3]
        self.target = 10.0
        self.ucl_steady = 11.0
        self.lcl_steady = 9.0
        self.out_of_control_indices = []
        self.n = 5


class MLResult:
    def __init__(self, feature_importance=None, algorithm="", statistics=None, predictions=None):
        self.feature_importance = feature_importance or {}
        self.algorithm = algorithm
        self.statistics = statistics or {}
        self.predictions = predictions or []


class TestAdvancedSPCBridge:
    def test_cusum_produces_chart(self):
        charts = charts_from_result(CUSUMResult())
        assert len(charts) == 1
        assert isinstance(charts[0], ChartSpec)

    def test_ewma_produces_chart(self):
        charts = charts_from_result(EWMAResult())
        assert len(charts) == 1
        assert isinstance(charts[0], ChartSpec)


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


class TestUnknownResult:
    def test_unknown_type_returns_empty(self):
        class SomethingElse:
            pass
        assert charts_from_result(SomethingElse()) == []
