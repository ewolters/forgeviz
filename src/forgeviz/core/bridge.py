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
    - forgestat.core.types.TestResult subclasses → (no chart, returns [])
    - forgestat.core.types.CorrelationResult → scatter matrix
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
    # Pure statistical results don't produce charts by default.
    # The handler or chain layer can request viz separately.

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
