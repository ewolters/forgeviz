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
    - dict with 'chart_type' key → already a spec, pass through
    - any forgecore Result protocol conformer → its own views()/to_render()

    The forgestat statistical families (t-test/ANOVA/rank/post-hoc/equivalence/
    chi-square/proportion/correlation/...) now carry their own data and
    self-render via the contract fallback — no per-type builder, no data kwargs.
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

    # forgestat reliability (WeibullFit/KaplanMeierResult), bayesian
    # (BayesianTestResult posterior density), and forgeml MLResult all
    # self-render via the contract fallback below — they carry their own data
    # (§5b). No builders, no dispatch arms.

    # --- forgestat timeseries types ---
    # The whole timeseries family (ACF/CCF/decomposition/ARIMA/Granger/
    # changepoint) self-renders via the contract fallback below — no dispatch
    # arms, no bridge builders. ChangepointResult now carries its own series
    # (§5b), so it no longer needs a data= kwarg.

    # --- forgestat power types ---

    if type_name == "PowerResult":
        return _charts_from_power(result, **kwargs)

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


def _as_list(values) -> list:
    """Coerce a numpy array / sequence to a plain list of floats."""
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError):
        return list(values)


def _charts_from_bayesian_capability(result, **kwargs) -> list:
    """BayesianCapabilityResult → bayesian capability chart."""
    try:
        from ..charts.bayesian import bayesian_capability as bc_chart
        return [bc_chart(result)]
    except Exception:
        logger.debug("Bayesian capability chart failed", exc_info=True)
        return []


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
