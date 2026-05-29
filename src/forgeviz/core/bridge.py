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
    - forgespc.models.ControlChartResult → control chart(s)
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

    if type_name == "ControlChartResult":
        return _charts_from_control_chart(result, **kwargs)

    if type_name == "ProcessCapability":
        return _charts_from_capability(result, **kwargs)

    if type_name == "BayesianCapabilityResult":
        return _charts_from_bayesian_capability(result, **kwargs)

    if type_name in ("CUSUMResult", "EWMAResult"):
        return _charts_from_advanced_spc(result, type_name, **kwargs)

    if type_name == "GageRRResult":
        return _charts_from_gage_rr(result, **kwargs)

    # --- forgestat reliability types ---

    if type_name == "WeibullFit":
        return _charts_from_weibull(result, **kwargs)

    if type_name == "BayesianTestResult":
        return _charts_from_bayesian_test(result, **kwargs)

    if type_name == "KaplanMeierResult":
        return _charts_from_kaplan_meier(result, **kwargs)

    # --- forgeml types ---

    if type_name == "MLResult":
        return _charts_from_ml(result, **kwargs)

    # --- forgestat types ---
    # Statistical result objects carry only summary stats, not the raw arrays,
    # so the chart is built from the data context the caller passes as kwargs
    # (groups=dict / data=list / data_dict=dict). Returns [] when no usable
    # context is supplied — the analysis still renders stats + summary.

    if type_name in _DISTRIBUTION_RESULTS:
        return _charts_from_distribution(**kwargs)

    if type_name == "CorrelationResult":
        return _charts_from_correlation(**kwargs)

    # Regression-family results that expose residual diagnostics (fitted +
    # residuals arrays) get the standard 4-in-1 panel, regardless of exact type.
    if hasattr(result, "fitted") and hasattr(result, "residuals"):
        return _charts_from_regression(result, **kwargs)

    return []


# Statistical results whose natural visual is a distribution view — a box plot
# comparing groups (group/paired tests) or a histogram of one sample
# (one-sample tests, normality/outlier checks).
_DISTRIBUTION_RESULTS = {
    "TestResult",  # base class — some rank tests (kruskal, mood) return it directly
    "TTestResult", "AnovaResult", "Anova2Result", "RankTestResult",
    "PostHocResult", "EquivalenceResult", "ProportionResult", "ChiSquareResult",
    "AssumptionCheck",
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


def _charts_from_correlation(data_dict=None, **kwargs) -> list:
    """Correlation → scatter (2 variables) or scatter matrix (>2 variables)."""
    if not data_dict:
        return []
    cols = [c for c in data_dict if data_dict[c]]
    if len(cols) == 2:
        from ..charts.scatter import scatter
        return [scatter(
            _as_list(data_dict[cols[0]]), _as_list(data_dict[cols[1]]),
            title=f"{cols[0]} vs {cols[1]}",
            x_label=cols[0], y_label=cols[1], show_regression=True,
        )]
    if len(cols) > 2:
        from ..charts.statistical import scatter_matrix
        return scatter_matrix({c: _as_list(data_dict[c]) for c in cols})
    return []


def _charts_from_control_chart(result, **kwargs) -> list:
    """ControlChartResult → 1 or 2 ChartSpecs (primary + secondary)."""
    from ..charts.control import from_spc_result_pair
    return from_spc_result_pair(result, title=kwargs.get("title", ""))


def _charts_from_capability(result, **kwargs) -> list:
    """ProcessCapability → capability histogram + normal probability plot.

    Normality is the assumption behind Cp/Cpk, so the probability plot ships
    alongside the histogram whenever the raw sample is available via chart_ctx.
    """
    from dataclasses import asdict

    from ..charts.capability import capability_histogram
    from ..charts.distribution import probability_plot

    d = asdict(result) if hasattr(result, "__dataclass_fields__") else result
    if not isinstance(d, dict):
        return []
    data = kwargs.get("data", [])
    if data is None or (hasattr(data, "__len__") and len(data) == 0):
        return []
    data = list(data)
    return [
        capability_histogram(
            data=data,
            usl=d.get("usl"), lsl=d.get("lsl"), target=d.get("target"),
            cp=d.get("cp"), cpk=d.get("cpk"),
        ),
        probability_plot(data, distribution="normal", title="Normal Probability Plot"),
    ]


def _charts_from_bayesian_capability(result, **kwargs) -> list:
    """BayesianCapabilityResult → bayesian capability chart."""
    try:
        from ..charts.bayesian import bayesian_capability as bc_chart
        return [bc_chart(result)]
    except Exception:
        logger.debug("Bayesian capability chart failed", exc_info=True)
        return []


def _charts_from_advanced_spc(result, type_name, **kwargs) -> list:
    """CUSUMResult / EWMAResult → control chart."""
    from ..charts.control import control_chart
    title = kwargs.get("title")

    if type_name == "EWMAResult":
        values = list(result.ewma_values)
        cl = result.target if result.target is not None else sum(values) / len(values)
        return [control_chart(
            data_points=values,
            ucl=result.ucl_steady, cl=cl, lcl=result.lcl_steady,
            ooc_indices=list(result.out_of_control_indices or []),
            title=title or "EWMA Chart", chart_type_label="EWMA",
        )]

    if type_name == "CUSUMResult":
        h = (result.h or 5.0) * (result.sigma or 1.0)
        return [control_chart(
            data_points=list(result.cusum_pos),
            ucl=h, cl=0.0, lcl=0.0,
            ooc_indices=list(result.signals_up or []),
            title=title or "CUSUM Chart", chart_type_label="CUSUM (C+)",
            secondary_data=list(result.cusum_neg),
            secondary_ucl=h, secondary_cl=0.0, secondary_lcl=0.0,
            secondary_title="CUSUM (C-)",
        )]

    # Legacy control-chart-shaped advanced results
    if hasattr(result, "data_points") and hasattr(result, "limits"):
        from ..charts.control import from_spc_result
        return [from_spc_result(result, title=title or f"{type_name} Chart")]
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


def _charts_from_weibull(result, failure_times=None, **kwargs) -> list:
    """WeibullFit → probability plot + survival curve + hazard function.

    The fit carries only parameters (shape/scale); the raw failure_times come
    from the caller's chart_ctx. With the times we draw the full panel; with
    parameters alone we can still show the hazard (bathtub) curve.
    """
    from ..charts.reliability import hazard_function, survival_curve, weibull_probability_plot
    shape = getattr(result, "shape", 0.0)
    scale = getattr(result, "scale", 0.0)
    if not failure_times:
        if shape and scale:
            return [hazard_function(shape, scale)]
        return []
    times = list(failure_times)
    return [
        weibull_probability_plot(times, shape=shape, scale=scale),
        survival_curve(times),
        hazard_function(shape, scale),
    ]


def _charts_from_regression(result, **kwargs) -> list:
    """Regression result with fitted/residuals → 4-in-1 diagnostic panel."""
    fitted = getattr(result, "fitted", None)
    residuals = getattr(result, "residuals", None)
    if not fitted or not residuals:
        return []
    from ..charts.diagnostic import four_in_one
    return four_in_one(list(fitted), list(residuals))


def _charts_from_kaplan_meier(result, failure_times=None, censored=None, **kwargs) -> list:
    """KaplanMeierResult → Kaplan-Meier survival curve from the raw times the
    handler forwards via chart_ctx (events marked censored)."""
    if not failure_times:
        return []
    from ..charts.reliability import survival_curve
    return [survival_curve(list(failure_times), censored=censored)]


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
