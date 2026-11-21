"""Charts and maps of the report.

Static charts use plotnine (the grammar of graphics taught in the course);
maps use plotly, which is interactive and draws country borders without
extra files. Colours follow one rule throughout: a category always keeps the
same colour (e.g. 'abandoned' is always orange), and categories are sorted
from the largest to the smallest value so that rankings are readable.
"""

import numpy as np
import pandas as pd
import plotly.express as px
from plotnine import (
    aes, coord_flip, element_blank, element_line, element_rect, element_text,
    facet_wrap, geom_col, geom_hline, geom_label, geom_point, geom_segment,
    geom_text, geom_vline, ggplot, guides, guide_legend, labs, scale_color_manual,
    scale_fill_manual, scale_size_area, scale_x_continuous, scale_x_log10,
    scale_y_continuous, theme, theme_minimal,
)

from src import config

# Validated colour-blind-safe palette (adjacent and all-pairs checks pass).
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GREY = "#8a8985"
STAGE_COLORS = {"pipeline": YELLOW, "construction": AQUA, "operating": BLUE, "abandoned": ORANGE}
ORIGIN_COLORS = {"Gulf": BLUE, "Global peer": ORANGE}
AREA_COLORS = {"GCC": BLUE, "Rest of Middle East": AQUA, "Rest of world": GREY}
MAP_CLASSES = ["< 20%", "20–40%", "40–60%", "60–80%", "≥ 80%"]
MAP_COLORS = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # sequential blue


def percent(values) -> list:
    """Axis labels in percent."""
    return [f"{v:.0%}" for v in values]


def theme_report(width: float = 8, height: float = 4.5):
    """Sober theme: white background, light grid, no vertical text."""
    return theme_minimal() + theme(
        figure_size=(width, height),
        plot_background=element_rect(fill="white", color="white"),
        panel_grid_minor=element_blank(),
        panel_grid_major=element_line(color="#ecebe8"),
        plot_title=element_text(size=12, weight="bold"),
        plot_subtitle=element_text(size=9, color="#52514e"),
        plot_caption=element_text(size=8, color="#52514e", ha="left"),
        axis_title=element_text(size=9, color="#52514e"),
        legend_position="top",
        legend_title=element_blank(),
    )


def save(plot, name: str, width: float = 8, height: float = 4.5):
    """Save a plotnine chart in figures/ (used by the README)."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plot.save(config.FIGURES_DIR / f"{name}.png", width=width, height=height,
              dpi=150, verbose=False)


