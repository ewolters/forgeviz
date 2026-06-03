"""Theme-neutral rendering.

Solvers (forgespc, etc.) emit theme-neutral ChartSpecs: every element color is
left empty (color="") and tagged with a semantic role. The renderer must resolve
each role to a visible theme color. Without resolution, reference lines, zones,
and markers render with stroke=""/fill="" — invisible.
"""

from forgeviz.core.colors import STATUS_RED, role_color
from forgeviz.core.spec import ChartSpec
from forgeviz.renderers.svg import to_svg


def _neutral_control_chart() -> ChartSpec:
    """A control chart spec exactly as a solver emits it: colors empty, roles set."""
    spec = ChartSpec(title="Neutral", chart_type="control_chart")
    spec.add_trace([0, 1, 2, 3], [5, 9, 4, 6], name="Data", color="", role="data")
    spec.add_reference_line(8, color="", label="UCL", role="control_limit")
    spec.add_reference_line(2, color="", label="LCL", role="control_limit")
    spec.add_zone(6, 8, color="", role="sigma_zone")
    spec.add_marker([1], color="", label="OOC", role="out_of_control")
    return spec


class TestRoleColor:
    def test_resolves_known_roles_to_nonempty(self):
        for role in ("control_limit", "centerline", "out_of_control",
                     "spec_limit", "run_rule", "sigma_zone", "data"):
            assert role_color(role, "svend_dark"), f"role {role!r} resolved empty"

    def test_unknown_role_returns_empty(self):
        assert role_color("nonsense", "svend_dark") == ""

    def test_empty_role_returns_empty(self):
        assert role_color("", "svend_dark") == ""

    def test_control_limit_is_alarm_color(self):
        assert role_color("control_limit", "svend_dark") == STATUS_RED

    def test_accepts_theme_dict_or_name(self):
        from forgeviz.core.colors import get_theme
        assert role_color("data", "svend_dark") == role_color("data", get_theme("svend_dark"))


class TestNeutralRender:
    def test_no_invisible_strokes(self):
        svg = to_svg(_neutral_control_chart())
        assert 'stroke=""' not in svg

    def test_no_invisible_fills(self):
        svg = to_svg(_neutral_control_chart())
        assert 'fill=""' not in svg

    def test_control_limits_render_with_alarm_color(self):
        svg = to_svg(_neutral_control_chart())
        assert STATUS_RED in svg

    def test_sigma_zone_renders_with_role_fill(self):
        svg = to_svg(_neutral_control_chart())
        assert role_color("sigma_zone", "svend_dark") in svg
