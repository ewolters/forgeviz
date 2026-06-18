"""Bridge — forge result objects → ForgeViz ChartSpec list.

Auto-dispatches based on result type. Handlers call this instead of
manually building ChartSpecs. Each forge package returns typed results;
this module knows which ForgeViz chart builder to call for each.

Usage:
    from forgeviz.core.bridge import charts_from_result
    charts = charts_from_result(result)  # list[ChartSpec]
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def charts_from_result(result: Any, **kwargs) -> list:
    """Convert a forge result object to a list of ChartSpec.

    Inspects the result type and delegates to the appropriate chart builder.
    Returns an empty list if the type is not recognized (no error).

    Supported types:
    - forgespc.models.ProcessCapability → capability histogram
    - forgespc.bayesian.BayesianCapabilityResult → bayesian capability chart
    - forgestat group tests (TTest/Anova/RankTest/PostHoc/...) → box plot or
      histogram, built from `groups=`/`data=` kwargs (result carries no raw data)
    - forgestat.core.types.CorrelationResult → scatter / scatter matrix from `data_dict=`
    - dict with 'chart_type' key → already a spec, pass through
    """
    if result is None:
        return []

    # Already a ChartSpec or dict spec — pass through
    if hasattr(result, "chart_type") and hasattr(result, "traces"):
        return [result]
    if isinstance(result, dict) and "chart_type" in result:
        return [result]

    # List of specs/results
    if isinstance(result, list):
        out = []
        for item in result:
            out.extend(charts_from_result(item, **kwargs))
        return out

    type_name = type(result).__name__
    module = type(result).__module__ or ""

    # --- forgespc types ---

    if type_name == "BayesianCapabilityResult":
        return _charts_from_bayesian_capability(result, **kwargs)

    if type_name == "GageRRResult":
        return _charts_from_gage_rr(result, **kwargs)

    # --- forgestat reliability types ---
    # WeibullFit (carries failure_times, §5b) + KaplanMeierResult (carries its
    # computed curve) self-render via the contract fallback. BayesianTestResult
    # stays — it has no contract render yet.

    if type_name == "BayesianTestResult":
        return _charts_from_bayesian_test(result, **kwargs)

    # --- forgeml types ---

    if type_name == "MLResult":
        return _charts_from_ml(result, **kwargs)

    # --- forgestat timeseries types ---
    # The whole timeseries family (ACF/CCF/decomposition/ARIMA/Granger/
    # changepoint) self-renders via the contract fallback below — no dispatch
    # arms, no bridge builders. ChangepointResult now carries its own series
    # (§5b), so it no longer needs a data= kwarg.

    # --- forgestat power types ---

    if type_name == "PowerResult":
        return _charts_from_power(result, **kwargs)

    # --- forgestat types ---
    # Statistical result objects carry only summary stats, not the raw arrays,
    # so the chart is built from the data context the caller passes as kwargs
    # (groups=dict / data=list / data_dict=dict). Returns [] when no usable
    # context is supplied — the analysis still renders stats + summary.

    if type_name in _DISTRIBUTION_RESULTS:
        return _charts_from_distribution(**kwargs)

    # Contract fallback, tried LAST: a result the bridge doesn't know that
    # speaks the forgecore Result protocol renders its complete portrait —
    # views() when present (multi-chart results), to_render() otherwise.
    # Remaining builders keep priority above because they compose data-context
    # charts a result cannot draw from its own fields.
    portrait = getattr(result, "views", None) or getattr(result, "to_render", None)
    if callable(portrait):
        try:
            specs = portrait()
            return list(specs) if isinstance(specs, list) else [specs]
        except Exception:
            logger.warning("contract render failed for %s", type_name, exc_info=True)
            return []

    return []


# Statistical results whose natural visual is a distribution view — a box plot
# comparing groups (group/paired tests) or a histogram of one sample
# (one-sample tests, normality/outlier checks).
_DISTRIBUTION_RESULTS = {
    "TestResult",  # base class — some rank tests (kruskal, mood) return it directly
    "Anova2Result",
    "ProportionResult", "ChiSquareResult",
    "AssumptionCheck",
    # Retired (§5b — carry raw samples, self-render box/histogram via the contract):
    # AnovaResult, TTestResult, RankTestResult, EquivalenceResult, PostHocResult.
}


def _as_list(values) -> list:
    """Coerce a numpy array / sequence to a plain list of floats."""
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError):
        return list(values)


def _charts_from_distribution(groups=None, data=None, **kwargs) -> list:
    """Group test → box plot + a normal Q-Q per group; one sample → histogram
    + a normal Q-Q. The Q-Q plot surfaces the normality assumption these tests
    rest on. `groups` is {name: sequence}; `data` is a single sequence.
    """
    from ..charts.diagnostic import qq_plot

    if groups:
        datasets = {str(k): _as_list(v) for k, v in groups.items() if len(v)}
        if len(datasets) >= 2:
            from ..charts.distribution import box_plot
            charts = [box_plot(datasets, title=kwargs.get("title", "Group Comparison"))]
            for name, vals in datasets.items():
                if len(vals) >= 3:
                    charts.append(qq_plot(vals, title=f"Normal Q-Q — {name}"))
            return charts
        if len(datasets) == 1:
            data = next(iter(datasets.values()))
    if data is not None:
        vals = _as_list(data)
        if vals:
            from ..charts.distribution import histogram
            charts = [histogram(
                vals, title=kwargs.get("title", "Distribution"),
                target=kwargs.get("target"),
                show_normal=kwargs.get("show_normal", False),
            )]
            if len(vals) >= 3:
                charts.append(qq_plot(vals, title="Normal Q-Q Plot"))
            return charts
    return []


def _charts_from_bayesian_capability(result, **kwargs) -> list:
    """BayesianCapabilityResult → bayesian capability chart."""
    try:
        from ..charts.bayesian import bayesian_capability as bc_chart
        return [bc_chart(result)]
    except Exception:
        logger.debug("Bayesian capability chart failed", exc_info=True)
        return []


def _charts_from_ml(result, X=None, **kwargs) -> list:
    """MLResult → charts by algorithm.

    Feature-importance models → importance bar; PCA → scree + PC1 loadings;
    clustering → 2-D cluster scatter (needs the raw points X via chart_ctx) plus
    a cluster-size bar. Returns [] for ML results with nothing plottable.
    """
    from ..charts.generic import bar
    fi = getattr(result, "feature_importance", None)
    if fi:
        items = sorted(fi.items(), key=lambda kv: kv[1], reverse=True)
        return [bar(
            [str(k) for k, _ in items],
            [float(v) for _, v in items],
            title="Feature Importance",
            horizontal=True,
        )]

    stats = getattr(result, "statistics", {}) or {}
    if getattr(result, "algorithm", "") == "pca":
        return _charts_from_pca(stats)
    if "cluster_sizes" in stats:
        return _charts_from_cluster(result, stats, X)
    return []


def _charts_from_pca(stats) -> list:
    """PCA statistics → scree plot + PC1 loadings bar."""
    from ..charts.generic import bar
    charts = []
    evr = stats.get("explained_variance_ratio") or []
    if evr:
        charts.append(bar(
            [f"PC{i + 1}" for i in range(len(evr))],
            [float(v) for v in evr],
            title="Scree Plot — Explained Variance",
            x_label="Component", y_label="Variance Ratio",
        ))
    pc1 = (stats.get("loadings") or {}).get("PC1") or {}
    if pc1:
        charts.append(bar(
            list(pc1.keys()),
            [float(v) for v in pc1.values()],
            title="PC1 Loadings", x_label="Feature", y_label="Loading",
            horizontal=True,
        ))
    return charts


def _charts_from_cluster(result, stats, X) -> list:
    """Clustering result → 2-D scatter coloured by label + cluster-size bar."""
    from ..charts.generic import bar
    from ..charts.scatter import scatter
    charts = []
    labels = getattr(result, "predictions", []) or []
    if X is not None and labels and len(X) == len(labels):
        xs = [float(row[0]) for row in X]
        ys = [float(row[1]) if len(row) > 1 else 0.0 for row in X]
        groups: dict = {}
        for i, lab in enumerate(labels):
            groups.setdefault(f"Cluster {lab}", []).append(i)
        charts.append(scatter(
            xs, ys, title="Cluster Assignments",
            x_label="Feature 1", y_label="Feature 2", groups=groups,
        ))
    sizes = stats.get("cluster_sizes") or {}
    if sizes:
        charts.append(bar(
            list(sizes.keys()), [float(v) for v in sizes.values()],
            title="Cluster Sizes", x_label="Cluster", y_label="Count",
        ))
    return charts


def _charts_from_bayesian_test(result, **kwargs) -> list:
    """BayesianTestResult → Normal-approximation posterior density.

    The result is summary-only (no draws); a density needs both posterior
    moments. Mean-only results (η²/R²) have nothing to plot, so return [].
    """
    mean = getattr(result, "posterior_mean", None)
    std = getattr(result, "posterior_std", None)
    if mean is None or not std or std <= 0:
        return []
    from ..charts.bayesian import posterior_density
    return [posterior_density(
        mean, std,
        credible_interval=getattr(result, "credible_interval", None),
        p_rope=getattr(result, "p_rope", None),
    )]


def _charts_from_gage_rr(result, measurements=None, parts=None, operators=None, **kwargs) -> list:
    """GageRRResult → variance-component bar, plus by-part and by-operator
    spread plots when the raw measurements are supplied via chart_ctx.
    """
    from ..charts.gage import gage_rr_by_operator, gage_rr_by_part, gage_rr_components

    pct = {
        "gage_rr": getattr(result, "pct_gage_rr", 0),
        "repeatability": getattr(result, "pct_repeatability", 0),
        "reproducibility": getattr(result, "pct_reproducibility", 0),
        "part_to_part": getattr(result, "pct_part", 0),
    }
    charts = [gage_rr_components(pct)]

    if measurements is not None and parts is not None:
        by_part: dict = {}
        for m, p in zip(measurements, parts):
            by_part.setdefault(str(p), []).append(float(m))
        charts.append(gage_rr_by_part(list(by_part.keys()), by_part))

    if measurements is not None and operators is not None:
        by_op: dict = {}
        for m, o in zip(measurements, operators):
            by_op.setdefault(str(o), []).append(float(m))
        charts.append(gage_rr_by_operator(list(by_op.keys()), by_op))

    return charts


# --- forgestat power builder ---


def _charts_from_power(result, power_curve=None, **kwargs) -> list:
    """PowerResult → power-vs-sample-size curve.

    The result is a single solved point, which is no chart on its own; the
    handler sweeps the power calculation across a range of n and forwards the
    swept curve via chart_ctx (power_curve={"n": [...], "power": [...]}). The
    target-power and solved-n are drawn as reference lines.
    """
    if not power_curve:
        return []
    ns = _as_list(power_curve.get("n", []))
    powers = _as_list(power_curve.get("power", []))
    if not ns or not powers:
        return []
    from ..charts.generic import line
    spec = line(ns, powers, title="Power Curve",
                x_label="Sample size (n)", y_label="Power")
    target = power_curve.get("target_power")
    if target:
        spec.add_reference_line(float(target), axis="y", color="#888",
                                dash="dashed", label=f"target {float(target):.0%}")
    solved = power_curve.get("solved_n")
    if solved:
        spec.add_reference_line(float(solved), axis="x", color="#888",
                                dash="dotted", label=f"n = {int(solved)}")
    return [spec]
