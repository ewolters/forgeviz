"""ForgeViz Color System — THE single source of truth.

Every color in the platform comes from here. SVEND's CSS variables,
chart colors, graph node colors, status badges — all defined once.

When SVEND migrates to ForgeViz, templates read from this via JS
or the Python renderers apply these automatically.
"""

# =========================================================================
# SVEND Platform Colors (match CSS variables in base_app.html)
# =========================================================================

# Background hierarchy
BG_PRIMARY = "#0a0f0a"
BG_SECONDARY = "#0d120d"
BG_TERTIARY = "#121a12"
BG_HOVER = "#1a261a"
CARD_BG = "#121a12"

# Accent colors
ACCENT_PRIMARY = "#4a9f6e"  # sage green — the brand
ACCENT_BLUE = "#4a9faf"
ACCENT_PURPLE = "#8a7fbf"
ACCENT_GOLD = "#e8c547"
ACCENT_ORANGE = "#e89547"

# Text hierarchy
TEXT_PRIMARY = "#e8efe8"
TEXT_SECONDARY = "#9aaa9a"
TEXT_DIM = "#7a8f7a"

# Border
BORDER = "rgba(74, 159, 110, 0.2)"
BORDER_ACCENT = "rgba(74, 159, 110, 0.3)"

# =========================================================================
# Status Colors (semantic — used for badges, indicators, alerts)
# =========================================================================

STATUS_GREEN = "#4a9f6e"   # success, in-control, calibrated (= accent primary)
STATUS_AMBER = "#e89547"   # warning, stale, due-soon
STATUS_RED = "#d06060"     # error, out-of-control, contradicted, overdue
STATUS_BLUE = "#4a9faf"    # info, investigating, active (= accent blue)
STATUS_PURPLE = "#8a7fbf"  # transition, standardize mode (= accent purple)
STATUS_DIM = "#64748b"     # inactive, uncalibrated, neutral

# Dim/border variants for status colors (used in badges, alert backgrounds)
ERROR_DIM = "rgba(208, 96, 96, 0.15)"
ERROR_BORDER = "rgba(208, 96, 96, 0.3)"
WARNING_DIM = "rgba(232, 149, 71, 0.1)"
WARNING_BORDER = "rgba(232, 149, 71, 0.3)"

# =========================================================================
# Chart Data Colors (10-color palette for data series)
# =========================================================================

SVEND_COLORS = [
    "#4a9f6e",  # 0: sage green (primary accent)
    "#e8c547",  # 1: gold
    "#4dc9c0",  # 2: teal
    "#a78bfa",  # 3: purple
    "#f472b6",  # 4: pink
    "#fb923c",  # 5: orange
    "#92400e",  # 6: brown
    "#94a3b8",  # 7: neutral/slate
    "#60a5fa",  # 8: blue
    "#f87171",  # 9: red (light)
]

# Extended palette for when 10 isn't enough (20 colors, no repeats)
SVEND_COLORS_EXTENDED = SVEND_COLORS + [
    "#06b6d4",  # 10: cyan
    "#8b5cf6",  # 11: violet
    "#ec4899",  # 12: hot pink
    "#84cc16",  # 13: lime
    "#14b8a6",  # 14: teal (dark)
    "#f97316",  # 15: orange (dark)
    "#6366f1",  # 16: indigo
    "#d946ef",  # 17: fuchsia
    "#eab308",  # 18: yellow
    "#78716c",  # 19: stone
]

# =========================================================================
# Graph Node Type Colors (Process Map — Cytoscape)
# =========================================================================

NODE_COLORS = {
    "process_parameter": "#4a9f6e",     # sage green
    "quality_characteristic": "#6366f1", # indigo
    "failure_mode": "#ef4444",           # red
    "environmental_factor": "#f59e0b",   # amber
    "material_property": "#8b5cf6",      # violet
    "measurement": "#06b6d4",            # cyan
    "specification": "#0ea5e9",          # sky blue
    "equipment": "#64748b",              # slate
    "human_factor": "#ec4899",           # pink
    "custom": "#94a3b8",                 # neutral
}

# =========================================================================
# Detection Mechanism Level Colors (OLR-001 §9)
# =========================================================================

DETECTION_COLORS = {
    1: STATUS_GREEN,   # source prevention — best
    2: STATUS_GREEN,   # auto arrest
    3: STATUS_GREEN,   # auto detect
    4: STATUS_BLUE,    # auto alert
    5: STATUS_BLUE,    # structured check
    6: STATUS_AMBER,   # observation — weak
    7: STATUS_RED,     # downstream — failure
    8: STATUS_RED,     # undetectable — worst
}

# =========================================================================
# Classification Tier Colors
# =========================================================================

TIER_COLORS = {
    "critical": STATUS_RED,
    "major": STATUS_AMBER,
    "minor": STATUS_DIM,
}

# =========================================================================
# Maturity Level Colors (OLR-001 §14)
# =========================================================================

MATURITY_COLORS = {
    1: STATUS_RED,     # structured
    2: STATUS_AMBER,   # learning
    3: STATUS_GREEN,   # sustaining
    4: "#6366f1",      # predictive (indigo)
}

# =========================================================================
# Theme Definitions
# =========================================================================

THEMES = {
    # ── Forest at Night (default dark) ─────────────────────────────
    "svend_dark": {
        "bg": "#0a0f0a",
        "plot_bg": "#0d120d",
        "text": "#e8efe8",
        "text_secondary": "#9aaa9a",
        "grid": "rgba(255,255,255,0.06)",
        "axis": "rgba(255,255,255,0.15)",
        "accent": "#4a9f6e",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": SVEND_COLORS,
    },
    # ── Light (green-tinted, matches production) ───────────────────
    "light": {
        "bg": "#f5f7f5",
        "plot_bg": "#f5f7f5",
        "text": "#1a2a1a",
        "text_secondary": "#4a5a4a",
        "grid": "rgba(0,0,0,0.08)",
        "axis": "rgba(0,0,0,0.2)",
        "accent": "#2d7a4a",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": ["#2d7a4a", "#2a6070", "#846a0a", "#9a580a", "#4a3f6f",
                   "#a03030", "#4a5a4a", "#5f705f", "#2a6070", "#9a580a"],
    },
    # ── Nordic Frost (light, cool) ─────────────────────────────────
    "nordic": {
        "bg": "#f2f5f8",
        "plot_bg": "#f2f5f8",
        "text": "#1a2030",
        "text_secondary": "#485060",
        "grid": "rgba(26,32,48,0.07)",
        "axis": "rgba(26,32,48,0.18)",
        "accent": "#2a6b50",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": ["#2a6b50", "#1a5f80", "#7a6505", "#9a5808", "#4a3f70",
                   "#b02828", "#485060", "#5f6878", "#1a5f80", "#9a5808"],
    },
    # ── Sandstone (light, warm) ────────────────────────────────────
    "sandstone": {
        "bg": "#f7f4f0",
        "plot_bg": "#f7f4f0",
        "text": "#2a2420",
        "text_secondary": "#5a524a",
        "grid": "rgba(42,36,32,0.07)",
        "axis": "rgba(42,36,32,0.18)",
        "accent": "#2d7a4a",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": ["#2d7a4a", "#2a607a", "#7a6208", "#a06010", "#5a4070",
                   "#a82a2a", "#5a524a", "#6f675f", "#2a607a", "#a06010"],
    },
    # ── Midnight (dark, vivid) ─────────────────────────────────────
    "midnight": {
        "bg": "#0a0a14",
        "plot_bg": "#0d0d1a",
        "text": "#e8e8f8",
        "text_secondary": "#9a9aaa",
        "grid": "rgba(232,232,248,0.06)",
        "axis": "rgba(232,232,248,0.15)",
        "accent": "#6a7fff",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": ["#6a7fff", "#4a9fdf", "#ffd54f", "#ff9547", "#9a6fff",
                   "#ff5a5a", "#4a9f6e", "#9a9aaa", "#4a9fdf", "#ff9547"],
    },
    # ── High Contrast (accessibility, WCAG AAA) ────────────────────
    "high_contrast": {
        "bg": "#000000",
        "plot_bg": "#000000",
        "text": "#ffffff",
        "text_secondary": "#c0c0c0",
        "grid": "rgba(255,255,255,0.1)",
        "axis": "rgba(255,255,255,0.3)",
        "accent": "#50c080",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": ["#50c080", "#50b0e0", "#f0d050", "#f0a050", "#b090f0",
                   "#f06060", "#ffffff", "#c0c0c0", "#50b0e0", "#f0a050"],
    },
    # ── Print (grayscale, paper-optimized) ─────────────────────────
    "print": {
        "bg": "#ffffff",
        "plot_bg": "#ffffff",
        "text": "#000000",
        "text_secondary": "#333333",
        "grid": "rgba(0,0,0,0.1)",
        "axis": "#000000",
        "accent": "#000000",
        "font": "Helvetica, Arial, sans-serif",
        "font_mono": "Courier, monospace",
        "colors": ["#000000", "#444444", "#888888", "#bbbbbb", "#000000", "#444444",
                   "#222222", "#666666", "#aaaaaa", "#333333"],
    },
    # ── Precision Document (warm paper, ink on paper aesthetic) ────
    "precision": {
        "bg": "#f5f0e8",
        "plot_bg": "#f5f0e8",
        "text": "#1a1a1a",
        "text_secondary": "#4a4a46",
        "grid": "rgba(26,26,26,0.07)",
        "axis": "rgba(26,26,26,0.2)",
        "accent": "#2a5f8f",
        "font": "Georgia, 'Times New Roman', serif",
        "font_mono": "Courier, monospace",
        "colors": ["#2a5f8f", "#4a7a5a", "#9a7a2a", "#c04040", "#1a1a1a",
                   "#4a4a46", "#8a8880", "#2a5f8f", "#4a7a5a", "#9a7a2a"],
    },
    # ── Tufte (cream, serif, zero chartjunk) ───────────────────────
    "tufte": {
        "bg": "#fffff8",
        "plot_bg": "#fffff8",
        "text": "#111111",
        "text_secondary": "#555555",
        "grid": "rgba(0,0,0,0)",
        "axis": "#333333",
        "accent": "#333333",
        "font": "Georgia, 'Times New Roman', serif",
        "font_mono": "Courier, monospace",
        "colors": ["#333333", "#888888", "#c0392b", "#2980b9", "#27ae60",
                   "#8e44ad", "#d35400", "#16a085", "#555555", "#aaaaaa"],
        "range_frame": True,
        "bar_width_ratio": 0.4,
    },
}


# =========================================================================
# Helper Functions
# =========================================================================

def get_theme(name: str) -> dict:
    """Get theme definition by name. Falls back to svend_dark."""
    return THEMES.get(name, THEMES["svend_dark"])


def get_color(index: int, theme: str = "svend_dark") -> str:
    """Get data color by index from theme palette. Cycles if index > palette size."""
    colors = THEMES.get(theme, THEMES["svend_dark"])["colors"]
    return colors[index % len(colors)]


def get_node_color(node_type: str) -> str:
    """Get color for a process graph node type."""
    return NODE_COLORS.get(node_type, NODE_COLORS["custom"])


def get_detection_color(level: int) -> str:
    """Get color for a detection mechanism level (1-8)."""
    return DETECTION_COLORS.get(level, STATUS_DIM)


def get_tier_color(tier: str) -> str:
    """Get color for a classification tier."""
    return TIER_COLORS.get(tier, STATUS_DIM)


def get_maturity_color(level: int) -> str:
    """Get color for a maturity level (1-4)."""
    return MATURITY_COLORS.get(level, STATUS_DIM)


def rgba(hex_color: str, alpha: float) -> str:
    """Convert hex color to rgba string."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def css_variables() -> dict[str, str]:
    """Export as CSS custom properties for template injection.

    Returns dict like {"--accent-primary": "#4a9f6e", ...}
    """
    return {
        "--bg-primary": BG_PRIMARY,
        "--bg-secondary": BG_SECONDARY,
        "--bg-tertiary": BG_TERTIARY,
        "--bg-hover": BG_HOVER,
        "--bg": BG_PRIMARY,
        "--card-bg": CARD_BG,
        "--accent-primary": ACCENT_PRIMARY,
        "--accent-primary-dim": rgba(ACCENT_PRIMARY, 0.15),
        "--accent-primary-border": rgba(ACCENT_PRIMARY, 0.3),
        "--accent": ACCENT_PRIMARY,
        "--accent-blue": ACCENT_BLUE,
        "--accent-purple": ACCENT_PURPLE,
        "--accent-gold": ACCENT_GOLD,
        "--accent-orange": ACCENT_ORANGE,
        "--text-primary": TEXT_PRIMARY,
        "--text-secondary": TEXT_SECONDARY,
        "--text-dim": TEXT_DIM,
        "--text": TEXT_PRIMARY,
        "--success": STATUS_GREEN,
        "--warning": STATUS_AMBER,
        "--error": STATUS_RED,
        "--info": STATUS_BLUE,
        "--border": BORDER,
        "--border-accent": BORDER_ACCENT,
        "--error-dim": ERROR_DIM,
        "--error-border": ERROR_BORDER,
        "--warning-dim": WARNING_DIM,
        "--warning-border": WARNING_BORDER,
    }
