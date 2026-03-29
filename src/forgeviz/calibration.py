"""Calibration stub for ForgeViz.

ForgeViz is a rendering package — there are no numerical computations
to calibrate against golden references. This module exists to satisfy
the ForgeGov contract (every forge package must have calibration.py)
and returns an empty adapter.
"""

from __future__ import annotations


def get_calibration_adapter():
    """Return a ForgeCal-compatible adapter. Empty — nothing to calibrate."""
    try:
        from forgecal.core import CalibrationAdapter
        from forgeviz import __version__
        return CalibrationAdapter(
            package="forgeviz",
            version=__version__,
            cases=[],  # No calibration cases — rendering is visual, not numerical
            runner=lambda case: ({}, []),
        )
    except ImportError:
        return None


def calibrate():
    """Standalone calibration. No-op for rendering packages."""
    return {"package": "forgeviz", "cases": 0, "passed": 0, "message": "No calibration needed — rendering package"}
