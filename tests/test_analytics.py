"""Tests for the auto-analytics engine."""

import math
import random

from forgeviz.analytics.auto import (
    add_confidence_band,
    add_moving_average,
    add_trend_line,
    auto_annotate,
    detect_changepoints,
    detect_clusters,
    detect_outliers,
    detect_seasonality,
    detect_trends,
    enrich,
    suggest_chart_type,
)
from forgeviz.analytics.recommend import auto_dashboard, recommend
from forgeviz.charts.generic import line
from forgeviz.core.spec import ChartSpec


class TestDetectTrends:
    def test_linear_upward(self):
        y = [i * 2 + 1 for i in range(20)]
        trends = detect_trends(y)
        assert len(trends) >= 1
        assert trends[0]["direction"] == "up"
        assert trends[0]["r_squared"] > 0.95

    def test_flat(self):
        y = [5.0] * 20
        trends = detect_trends(y)
        # Flat data — r² is undefined or 0
        if trends:
            assert trends[0]["direction"] == "flat"

    def test_too_short(self):
        assert detect_trends([1, 2]) == []

    def test_downward(self):
        y = [100 - i * 3 for i in range(20)]
        trends = detect_trends(y)
        assert any(t["direction"] == "down" for t in trends)


class TestDetectOutliers:
    def test_planted_outliers(self):
        y = [10.0] * 50
        y[25] = 100.0  # obvious outlier
        y[30] = -80.0  # another
        outliers = detect_outliers(y)
        assert 25 in outliers
        assert 30 in outliers

    def test_no_outliers(self):
        y = list(range(20))
        outliers = detect_outliers(y)
        assert len(outliers) == 0

    def test_zscore_method(self):
        random.seed(42)
        y = [random.gauss(0, 1) for _ in range(100)]
        y.append(10.0)  # plant outlier
        outliers = detect_outliers(y, method="zscore")
        assert 100 in outliers

    def test_empty(self):
        assert detect_outliers([]) == []


class TestDetectChangepoints:
    def test_planted_shift(self):
        y = [10.0] * 20 + [20.0] * 20
        cps = detect_changepoints(y, min_segment=5)
        assert len(cps) >= 1
        # Changepoint should be near index 20
        assert any(15 <= cp <= 25 for cp in cps)

    def test_no_shift(self):
        y = [5.0] * 40
        cps = detect_changepoints(y)
        assert len(cps) == 0

    def test_too_short(self):
        assert detect_changepoints([1, 2, 3]) == []


class TestDetectSeasonality:
    def test_periodic(self):
        y = [math.sin(2 * math.pi * i / 7) for i in range(70)]
        result = detect_seasonality(y)
        assert result is not None
        assert abs(result["period"] - 7) <= 1

    def test_no_seasonality(self):
        # Random noise — no periodic pattern
        random.seed(99)
        y = [random.gauss(0, 1) for _ in range(50)]
        result = detect_seasonality(y)
        # Should return None or very weak seasonality
        if result:
            assert result["strength"] < 0.5

    def test_too_short(self):
        assert detect_seasonality([1, 2, 3]) is None


class TestDetectClusters:
    def test_two_clusters(self):
        x = [1.0, 1.1, 1.2, 0.9, 0.8, 10.0, 10.1, 10.2, 9.9, 9.8]
        y = [1.0, 1.1, 0.9, 1.2, 0.8, 10.0, 10.1, 9.9, 10.2, 9.8]
        clusters = detect_clusters(x, y, max_clusters=3)
        assert len(clusters) >= 2

    def test_too_few_points(self):
        assert detect_clusters([1], [1]) == []


class TestSuggestChartType:
    def test_categorical_numeric(self):
        assert suggest_chart_type({"categories": ["A", "B", "C"], "y": [1, 2, 3]}) == "pie"

    def test_many_categories(self):
        cats = [f"Cat{i}" for i in range(20)]
        assert suggest_chart_type({"categories": cats, "y": list(range(20))}) == "bar"

    def test_time_series(self):
        assert suggest_chart_type({"y": [1, 2, 3], "time_series": True}) == "line"

    def test_two_numeric(self):
        assert suggest_chart_type({"x": [1, 2], "y": [3, 4]}) == "scatter"

    def test_single_numeric(self):
        assert suggest_chart_type({"y": [1, 2, 3, 4, 5]}) == "histogram"


class TestAddTrendLine:
    def test_adds_trace(self):
        spec = line(list(range(10)), [i * 2 for i in range(10)])
        enriched = add_trend_line(spec)
        # Should have original trace + trend line
        assert len(enriched.traces) > len(spec.traces)
        # Should not mutate original
        assert len(spec.traces) == 1

    def test_no_mutation(self):
        spec = line([1, 2, 3], [4, 5, 6])
        original_n = len(spec.traces)
        add_trend_line(spec)
        assert len(spec.traces) == original_n


class TestAddMovingAverage:
    def test_adds_ma_trace(self):
        spec = line(list(range(20)), [i + random.random() for i in range(20)])
        enriched = add_moving_average(spec, window=5)
        assert len(enriched.traces) == 2


class TestAddConfidenceBand:
    def test_adds_zone(self):
        spec = line(list(range(10)), [i * 2 for i in range(10)])
        enriched = add_confidence_band(spec)
        assert len(enriched.zones) > len(spec.zones)


class TestAutoAnnotate:
    def test_adds_min_max(self):
        spec = line(list(range(10)), [5, 3, 7, 1, 9, 2, 8, 4, 6, 0])
        annotated = auto_annotate(spec)
        texts = [a["text"] for a in annotated.annotations]
        assert any("Min" in t for t in texts)
        assert any("Max" in t for t in texts)


class TestEnrich:
    def test_default_enrichment(self):
        random.seed(42)
        y = [i + random.gauss(0, 0.5) for i in range(30)]
        spec = line(list(range(30)), y)
        enriched = enrich(spec)
        # Should have more elements than original
        total_new = (
            len(enriched.traces) + len(enriched.annotations) +
            len(enriched.markers) + len(enriched.zones)
        )
        total_orig = (
            len(spec.traces) + len(spec.annotations) +
            len(spec.markers) + len(spec.zones)
        )
        assert total_new > total_orig

    def test_specific_features(self):
        spec = line(list(range(20)), list(range(20)))
        enriched = enrich(spec, features=["trends"])
        assert len(enriched.traces) == 2  # original + trend

    def test_empty_spec(self):
        spec = ChartSpec()
        enriched = enrich(spec)
        assert isinstance(enriched, ChartSpec)


class TestRecommend:
    def test_returns_suggestions(self):
        data = {"x": [1, 2, 3], "y": [4, 5, 6]}
        results = recommend(data)
        assert len(results) >= 1
        assert "chart_type" in results[0]
        assert "score" in results[0]
        assert "spec" in results[0]

    def test_categorical(self):
        data = {"categories": ["A", "B", "C"], "y": [10, 20, 30]}
        results = recommend(data)
        assert results[0]["chart_type"] in ("pie", "bar")


class TestAutoDashboard:
    def test_creates_dashboard(self):
        sources = {
            "Revenue": {"x": [1, 2, 3], "y": [100, 200, 300], "time_series": True},
            "By Region": {"categories": ["East", "West"], "y": [60, 40]},
        }
        dashboard = auto_dashboard(sources, title="Test")
        assert dashboard.title == "Test"
        assert len(dashboard.panels) == 2
