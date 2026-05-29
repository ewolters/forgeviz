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
    def __init__(self, feature_importance=None):
        self.feature_importance = feature_importance or {}


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


class TestUnknownResult:
    def test_unknown_type_returns_empty(self):
        class SomethingElse:
            pass
        assert charts_from_result(SomethingElse()) == []
