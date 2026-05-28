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

    # --- forgestat types ---
    # Statistical result objects carry only summary stats, not the raw arrays,
    # so the chart is built from the data context the caller passes as kwargs
    # (groups=dict / data=list / data_dict=dict). Returns [] when no usable
    # context is supplied — the analysis still renders stats + summary.

    if type_name in _DISTRIBUTION_RESULTS:
        return _charts_from_distribution(**kwargs)

    if type_name == "CorrelationResult":
        return _charts_from_correlation(**kwargs)

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
    """Group test → box plot of the groups; one sample → histogram.

    `groups` is {name: sequence}; `data` is a single sequence (one-sample).
    """
    if groups:
        datasets = {str(k): _as_list(v) for k, v in groups.items() if len(v)}
        if len(datasets) >= 2:
            from ..charts.distribution import box_plot
            return [box_plot(datasets, title=kwargs.get("title", "Group Comparison"))]
        if len(datasets) == 1:
            data = next(iter(datasets.values()))
    if data is not None:
        vals = _as_list(data)
        if vals:
            from ..charts.distribution import histogram
            return [histogram(
                vals, title=kwargs.get("title", "Distribution"),
                target=kwargs.get("target"),
                show_normal=kwargs.get("show_normal", False),
            )]
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
    """ProcessCapability → capability histogram."""
    from ..charts.capability import capability_histogram
    from dataclasses import asdict

    d = asdict(result) if hasattr(result, "__dataclass_fields__") else result
    if isinstance(d, dict):
        data = kwargs.get("data", [])
        if data is None or (hasattr(data, "__len__") and len(data) == 0):
            return []
        return [capability_histogram(
            data=list(data),
            usl=d.get("usl"), lsl=d.get("lsl"), target=d.get("target"),
            cp=d.get("cp"), cpk=d.get("cpk"),
        )]
    return []


def _charts_from_bayesian_capability(result, **kwargs) -> list:
    """BayesianCapabilityResult → bayesian capability chart."""
    try:
        from ..charts.bayesian import bayesian_capability as bc_chart
        return [bc_chart(result)]
    except Exception:
        logger.debug("Bayesian capability chart failed", exc_info=True)
        return []


def _charts_from_advanced_spc(result, type_name, **kwargs) -> list:
    """CUSUM/EWMA result → control chart via from_spc_result if compatible."""
    if hasattr(result, "data_points") and hasattr(result, "limits"):
        from ..charts.control import from_spc_result
        return [from_spc_result(result, title=kwargs.get("title", f"{type_name} Chart"))]
    return []


def _charts_from_gage_rr(result, **kwargs) -> list:
    """GageRRResult → gage R&R component charts."""
    try:
        from ..charts.gage import gage_rr_components
        return [gage_rr_components(result)]
    except Exception:
        logger.debug("Gage R&R chart failed", exc_info=True)
        return []
