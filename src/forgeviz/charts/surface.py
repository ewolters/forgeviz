"""Response surface visualization — contour plots and response surface data.

Note: 3D rendering is a client-side concern. This module produces the data
grid that the JS renderer or Plotly can consume as a contour/heatmap.
"""

from __future__ import annotations

from ..core.colors import get_color
from ..core.spec import ChartSpec, Trace


def contour_plot(
    x_values: list[float],
    y_values: list[float],
    z_matrix: list[list[float]],
    x_label: str = "Factor A",
    y_label: str = "Factor B",
    z_label: str = "Response",
    title: str = "Contour Plot",
    levels: int = 10,
) -> ChartSpec:
    """2D contour plot from a response surface.

    z_matrix[i][j] = response at x_values[j], y_values[i]
    """
    spec = ChartSpec(
        title=title,
        chart_type="contour",
        x_axis={"label": x_label},
        y_axis={"label": y_label},
        height=500,
        width=600,
    )

    # Store contour data as a special trace type
    spec.traces.append({
        "type": "contour",
        "x": x_values,
        "y": y_values,
        "z": z_matrix,
        "z_label": z_label,
        "levels": levels,
        "colorscale": "viridis",
    })

    return spec


def response_surface_from_model(
    coefficients: dict[str, float],
    factor_a: str,
    factor_b: str,
    a_range: tuple[float, float] = (-1, 1),
    b_range: tuple[float, float] = (-1, 1),
    grid_points: int = 25,
    hold_values: dict[str, float] | None = None,
    title: str = "",
) -> ChartSpec:
    """Generate contour plot from a DOE regression model.

    Evaluates the model across a grid of two factors while holding
    all other factors at specified values (default: 0 = center).
    """
    hold = hold_values or {}

    # Build grid
    a_step = (a_range[1] - a_range[0]) / (grid_points - 1)
    b_step = (b_range[1] - b_range[0]) / (grid_points - 1)
    x_values = [a_range[0] + i * a_step for i in range(grid_points)]
    y_values = [b_range[0] + i * b_step for i in range(grid_points)]

    z_matrix = []
    for b_val in y_values:
        row = []
        for a_val in x_values:
            # Evaluate model
            pred = coefficients.get("Intercept", 0)
            values = dict(hold)
            values[factor_a] = a_val
            values[factor_b] = b_val

            # Main effects
            for name, val in values.items():
                pred += coefficients.get(name, 0) * val

            # Interactions
            names = list(values.keys())
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    term = f"{names[i]}*{names[j]}"
                    pred += coefficients.get(term, 0) * values[names[i]] * values[names[j]]

            # Quadratic
            for name, val in values.items():
                term = f"{name}^2"
                pred += coefficients.get(term, 0) * val ** 2

            row.append(round(pred, 4))
        z_matrix.append(row)

    return contour_plot(
        x_values, y_values, z_matrix,
        x_label=factor_a, y_label=factor_b,
        title=title or f"Response Surface: {factor_a} × {factor_b}",
    )


def overlay_optimal_point(
    spec: ChartSpec,
    optimal_a: float,
    optimal_b: float,
    label: str = "Optimal",
) -> ChartSpec:
    """Add optimal point marker to a contour plot."""
    spec.add_trace(
        [optimal_a], [optimal_b],
        name=label, trace_type="scatter",
        color="#ffffff", marker_size=10,
    )
    spec.annotations.append({
        "x": optimal_a, "y": optimal_b,
        "text": label, "color": "#ffffff", "font_size": 10,
    })
    return spec
