"""Color palettes for ForgeViz."""

# SVEND palette — matches the platform's existing CSS variables
SVEND_COLORS = [
    "#4a9f6e",  # sage green (primary)
    "#e8c547",  # gold
    "#4dc9c0",  # teal
    "#a78bfa",  # purple
    "#f472b6",  # pink
    "#fb923c",  # orange
    "#92400e",  # brown
    "#94a3b8",  # neutral
    "#60a5fa",  # blue
    "#f87171",  # red
]

# Status colors
STATUS_GREEN = "#22c55e"
STATUS_AMBER = "#f59e0b"
STATUS_RED = "#ef4444"
STATUS_BLUE = "#60a5fa"
STATUS_PURPLE = "#a78bfa"
STATUS_DIM = "#64748b"

# Theme definitions
THEMES = {
    "svend_dark": {
        "bg": "#0d120d",
        "plot_bg": "#0d120d",
        "text": "#e8efe8",
        "text_secondary": "#94a3b8",
        "grid": "rgba(255,255,255,0.06)",
        "axis": "rgba(255,255,255,0.15)",
        "accent": "#4a9f6e",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": SVEND_COLORS,
    },
    "light": {
        "bg": "#ffffff",
        "plot_bg": "#ffffff",
        "text": "#1a1a2e",
        "text_secondary": "#64748b",
        "grid": "rgba(0,0,0,0.08)",
        "axis": "rgba(0,0,0,0.2)",
        "accent": "#4a9f6e",
        "font": "Inter, system-ui, sans-serif",
        "font_mono": "JetBrains Mono, monospace",
        "colors": SVEND_COLORS,
    },
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
        "colors": ["#000000", "#444444", "#888888", "#bbbbbb", "#000000", "#444444"],
    },
}


def get_theme(name: str) -> dict:
    return THEMES.get(name, THEMES["svend_dark"])


def get_color(index: int, theme: str = "svend_dark") -> str:
    colors = THEMES.get(theme, THEMES["svend_dark"])["colors"]
    return colors[index % len(colors)]
