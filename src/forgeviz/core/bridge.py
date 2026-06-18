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

    # forgestat reliability (WeibullFit/KaplanMeierResult), bayesian
    # (BayesianTestResult posterior density), and forgeml MLResult all
    # self-render via the contract fallback below — they carry their own data
    # (§5b). No builders, no dispatch arms.

    # --- forgestat timeseries types ---
    # The whole timeseries family (ACF/CCF/decomposition/ARIMA/Granger/
    # changepoint) self-renders via the contract fallback below — no dispatch
    # arms, no bridge builders. ChangepointResult now carries its own series
    # (§5b), so it no longer needs a data= kwarg.

    # forgestat power: PowerResult sweeps its own power-vs-n curve onto a
    # power_curve field (§5b) and self-renders via the contract fallback below.

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
