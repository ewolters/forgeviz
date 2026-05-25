"""Self-contained HTML renderer — single file, full interactivity, zero server.

Embeds the ChartSpec JSON + forgeviz.js + forgeviz-interact.js into one HTML
document. Open in any browser. Email as attachment. Diff with git.

This is the "diffable chart" — the HTML file IS the artifact. Version it,
diff it, audit it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..core.spec import ChartSpec

# JS files are shipped alongside the package
_STATIC_DIR = Path(__file__).parent.parent / "static" / "js"


def _load_js(filename: str) -> str:
    """Load embedded JS file. Falls back to stub if not found."""
    path = _STATIC_DIR / filename
    if path.exists():
        return path.read_text()
    return f"// {filename} not found — install forgeviz with static files"


def to_html(
    spec: ChartSpec,
    title: str = "",
    include_interact: bool = True,
    include_toolbar: bool = True,
    theme_override: str = "",
) -> str:
    """Render ChartSpec as a self-contained HTML document.

    The output is a single file with:
    - Embedded chart data (JSON)
    - Embedded forgeviz.js renderer
    - Optional forgeviz-interact.js (zoom/pan/select/crosshair)
    - Content hash for versioning/diffing

    Args:
        spec: The chart to render.
        title: HTML <title>. Defaults to spec.title.
        include_interact: Include zoom/pan/lasso interactivity.
        include_toolbar: Show chart toolbar (export, copy, theme switch).
        theme_override: Override spec theme for this render.
    """
    page_title = title or spec.title or "ForgeViz Chart"
    spec_dict = spec.to_dict()
    if theme_override:
        spec_dict["theme"] = theme_override
    spec_json = json.dumps(spec_dict, indent=2, default=str)

    # Content hash for versioning
    content_hash = hashlib.sha256(spec_json.encode()).hexdigest()[:12]

    # Load JS
    core_js = _load_js("forgeviz.js")
    interact_js = _load_js("forgeviz-interact.js") if include_interact else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<meta name="generator" content="ForgeViz">
<meta name="forgeviz-hash" content="{content_hash}">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0a0f0a;
    color: #e8efe8;
    font-family: Inter, system-ui, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 20px;
  }}
  #chart {{
    width: 100%;
    max-width: {spec.width + 40}px;
  }}
  .forgeviz-meta {{
    text-align: center;
    margin-top: 12px;
    font-size: 10px;
    color: #7a8f7a;
    font-family: 'JetBrains Mono', monospace;
  }}
</style>
</head>
<body>
<div id="chart"></div>
<div class="forgeviz-meta">forgeviz:{content_hash}</div>

<script>
{core_js}
</script>
{f'<script>{interact_js}</script>' if interact_js else ''}
<script>
(function() {{
  var spec = {spec_json};
  ForgeViz.render(document.getElementById('chart'), spec, {{
    interactive: {str(include_interact).lower()},
    toolbar: {str(include_toolbar).lower()}
  }});
}})();
</script>
</body>
</html>"""


def content_hash(spec: ChartSpec) -> str:
    """Compute a deterministic content hash for a ChartSpec.

    Two specs with identical data produce the same hash.
    Use for versioning, diffing, and deduplication.
    """
    spec_json = json.dumps(spec.to_dict(), sort_keys=True, default=str)
    return hashlib.sha256(spec_json.encode()).hexdigest()[:12]


def diff_specs(spec_a: ChartSpec, spec_b: ChartSpec) -> dict[str, Any]:
    """Semantic diff between two ChartSpecs.

    Returns a dict describing what changed: added/removed/modified traces,
    reference line changes, axis changes, etc.
    """
    da = spec_a.to_dict()
    db = spec_b.to_dict()

    changes: dict[str, Any] = {}

    # Top-level scalar fields
    for key in ("title", "subtitle", "chart_type", "width", "height", "theme",
                "background_color", "show_legend", "legend_position"):
        if da.get(key) != db.get(key):
            changes[key] = {"from": da.get(key), "to": db.get(key)}

    # Traces
    traces_a = da.get("traces", [])
    traces_b = db.get("traces", [])
    if len(traces_a) != len(traces_b):
        changes["trace_count"] = {"from": len(traces_a), "to": len(traces_b)}
    else:
        trace_diffs = []
        for i, (ta, tb) in enumerate(zip(traces_a, traces_b)):
            td = {}
            for key in set(list(ta.keys()) + list(tb.keys())):
                if ta.get(key) != tb.get(key):
                    # For data arrays, summarize rather than dump
                    if key in ("x", "y") and isinstance(ta.get(key), list):
                        old_n = len(ta.get(key, []))
                        new_n = len(tb.get(key, []))
                        if old_n != new_n:
                            td[key] = {"length_from": old_n, "length_to": new_n}
                        else:
                            # Count changed values
                            n_changed = sum(1 for a, b in zip(ta[key], tb[key]) if a != b)
                            if n_changed:
                                td[key] = {"values_changed": n_changed, "of": old_n}
                    else:
                        td[key] = {"from": ta.get(key), "to": tb.get(key)}
            if td:
                trace_diffs.append({"trace": i, "changes": td})
        if trace_diffs:
            changes["traces"] = trace_diffs

    # Reference lines
    refs_a = da.get("reference_lines", [])
    refs_b = db.get("reference_lines", [])
    if refs_a != refs_b:
        changes["reference_lines"] = {"from_count": len(refs_a), "to_count": len(refs_b)}

    # Axes
    for axis_key in ("x_axis", "y_axis"):
        ax_a = da.get(axis_key, {})
        ax_b = db.get(axis_key, {})
        if ax_a != ax_b:
            changes[axis_key] = {k: {"from": ax_a.get(k), "to": ax_b.get(k)}
                                 for k in set(list(ax_a.keys()) + list(ax_b.keys()))
                                 if ax_a.get(k) != ax_b.get(k)}

    # Hashes
    changes["hash_from"] = content_hash(spec_a)
    changes["hash_to"] = content_hash(spec_b)
    changes["identical"] = len(changes) == 2  # only hashes present = no real changes

    return changes
