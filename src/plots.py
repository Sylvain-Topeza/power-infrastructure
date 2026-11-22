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


# --------------------------------------------------------------------------
# Descriptive charts
# --------------------------------------------------------------------------
def plot_capacity_by_stage(table: pd.DataFrame, title: str, subtitle: str = ""):
    """Small multiples: GW by technology (rows) for each stage (panels).

    ``table``: columns technology, stage, gw (from indicators.capacity_by_stage).
    """
    stages = ["operating", "construction", "pipeline"]
    data = table.loc[table["stage"].isin(stages)].copy()
    order = (data.loc[data["stage"] == "operating"]
             .sort_values("gw")["technology"].tolist())
    order += [t for t in data["technology"].unique() if t not in order]
    data["technology"] = pd.Categorical(data["technology"], order, ordered=True)
    data["stage"] = pd.Categorical(
        data["stage"].astype(str).str.capitalize(),
        [s.capitalize() for s in stages], ordered=True,
    )
    data["label"] = data["gw"].map(lambda v: f"{v:,.0f}" if v >= 1 else "")
    colors = {k.capitalize(): v for k, v in STAGE_COLORS.items()}
    return (
        ggplot(data, aes("technology", "gw", fill="stage"))
        + geom_col(width=0.7, show_legend=False)
        + geom_text(aes(label="label"), ha="left", nudge_y=2, size=7, color="#52514e")
        + coord_flip()
        + facet_wrap("stage", nrow=1)
        + scale_fill_manual(values=colors)
        + scale_y_continuous(expand=(0, 0, 0.25, 0))
        + labs(x="", y="Capacity (GW)", title=title, subtitle=subtitle)
        + theme_report(9, 4)
    )


def plot_rates(
    table: pd.DataFrame,
    label: str,
    title: str,
    subtitle: str = "",
    color: str | None = None,
    reference: float | None = None,
    caption: str = "",
    height: float = 4.5,
):
    """Lollipop chart of abandonment rates, sorted from highest to lowest.

    ``reference`` draws a dashed line, e.g. the world average.
    """
    data = table.sort_values("abandonment_rate").copy()
    data[label] = pd.Categorical(data[label], data[label], ordered=True)
    data["text"] = data["abandonment_rate"].map(lambda v: f"{v:.0%}")
    if color:
        segment = geom_segment(aes(x=label, xend=label, y=0, yend="abandonment_rate",
                                   color=color), size=0.8)
        point = geom_point(aes(label, "abandonment_rate", color=color), size=3)
    else:
        segment = geom_segment(aes(x=label, xend=label, y=0, yend="abandonment_rate"),
                               size=0.8, color=BLUE)
        point = geom_point(aes(label, "abandonment_rate"), size=3, color=BLUE)
    plot = (
        ggplot(data)
        + segment
        + point
        + geom_text(aes(label, "abandonment_rate", label="text"),
                    nudge_y=0.035, size=7.5, ha="left", color="#52514e")
        + coord_flip()
        + scale_y_continuous(labels=percent, limits=(0, 1.08))
        + labs(x="", y="Abandonment rate (share of capacity)",
               title=title, subtitle=subtitle, caption=caption)
        + theme_report(8, height)
    )
    if color:
        palette = AREA_COLORS if color == "area" else ORIGIN_COLORS
        plot += scale_color_manual(values=palette)
    if reference is not None:
        plot += geom_hline(yintercept=reference, linetype="dashed", color=GREY)
    return plot


def plot_sponsor_models(profiles: pd.DataFrame, title: str, subtitle: str = ""):
    """Scatter of sponsors: pipeline ratio (x, log scale) against abandonment
    rate (y), bubble size = portfolio abroad, colour = Gulf or global peer."""
    data = profiles.loc[
        np.isfinite(profiles["pipeline_ratio"]) & (profiles["pipeline_ratio"] > 0)
        & profiles["abandonment_rate"].notna() & (profiles["portfolio_gw"] >= 2)
    ]
    return (
        ggplot(data, aes("pipeline_ratio", "abandonment_rate"))
        + geom_vline(xintercept=1, linetype="dashed", color=GREY)
        + geom_point(aes(size="portfolio_gw", color="origin"), alpha=0.8)
        + geom_text(aes(label="sponsor_group"), size=7, color="#2b2b2b",
                    adjust_text={"expand": (1.4, 1.8),
                                 "arrowprops": {"arrowstyle": "-", "color": "#c3c2b7"}})
        + scale_x_log10(breaks=[0.05, 0.1, 0.25, 0.5, 1, 2, 5],
                        labels=["0.05", "0.1", "0.25", "0.5", "1", "2", "5"])
        + scale_y_continuous(labels=percent)
        + scale_color_manual(values=ORIGIN_COLORS, breaks=["Gulf", "Global peer"])
        + scale_size_area(max_size=12, guide=None)
        + guides(color=guide_legend(override_aes={"size": 4}))
        + labs(x="Pipeline ratio: (pipeline + construction) / operating capacity, log scale",
               y="Abandonment rate", title=title, subtitle=subtitle)
        + theme_report(9, 5.5)
    )


def plot_home_abroad(table: pd.DataFrame, title: str, subtitle: str = ""):
    """Dumbbell chart: abandonment rate at home and abroad, per group."""
    wide = table.pivot(index="group", columns="location", values="abandonment_rate").reset_index()
    wide = wide.sort_values("Abroad")
    order = wide["group"].tolist()
    long = table.assign(group=lambda df: pd.Categorical(df["group"], order, ordered=True))
    wide["group"] = pd.Categorical(wide["group"], order, ordered=True)
    return (
        ggplot()
        + geom_segment(wide, aes(x="group", xend="group", y="Home", yend="Abroad"),
                       color="#c3c2b7", size=1.5)
        + geom_point(long, aes("group", "abandonment_rate", color="location"), size=4)
        + coord_flip()
        + scale_y_continuous(labels=percent, limits=(0, 1))
        + scale_color_manual(values={"Home": BLUE, "Abroad": ORANGE}, breaks=["Home", "Abroad"])
        + labs(x="", y="Abandonment rate (share of equity capacity)",
               title=title, subtitle=subtitle)
        + theme_report(8, 3.2)
    )


def plot_odds_ratios(table: pd.DataFrame, title: str, subtitle: str = ""):
    """Forest plot of odds ratios with 95% confidence intervals (log scale)."""
    data = table.sort_values("odds_ratio").copy()
    data["label"] = pd.Categorical(data["label"], data["label"], ordered=True)
    return (
        ggplot(data, aes("label", "odds_ratio"))
        + geom_hline(yintercept=1, color=GREY)
        + geom_segment(aes(x="label", xend="label", y="ci_low", yend="ci_high"),
                       color="#86b6ef", size=1.2)
        + geom_point(color=BLUE, size=3)
        + coord_flip()
        + scale_y_continuous(trans="log10",
                             breaks=[0.1, 0.25, 0.5, 1, 2, 4, 8, 16],
                             labels=["0.1", "0.25", "0.5", "1", "2", "4", "8", "16"])
        + labs(x="", y="Odds ratio (log scale; 1 = no effect)",
               title=title, subtitle=subtitle)
        + theme_report(8, 5)
    )


def plot_rate_vs_governance(countries: pd.DataFrame, title: str, subtitle: str = ""):
    """Countries: regulatory quality (x) against abandonment rate (y)."""
    labelled = countries.loc[
        (countries["area"] != "Rest of world") | (countries["outcome_gw"] >= 150)
    ]
    return (
        ggplot(countries, aes("regulatory_quality", "abandonment_rate"))
        + geom_point(aes(size="outcome_gw", color="area"), alpha=0.75)
        + geom_text(labelled, aes(label="country"), size=6.5, color="#2b2b2b",
                    adjust_text={"arrowprops": {"arrowstyle": "-", "color": "#c3c2b7"}})
        + scale_color_manual(values=AREA_COLORS)
        + scale_size_area(max_size=14, guide=None)
        + scale_y_continuous(labels=percent)
        + guides(color=guide_legend(override_aes={"size": 4}))
        + labs(x="Regulatory quality (World Bank, higher = more supportive of private investment)",
               y="Abandonment rate", title=title, subtitle=subtitle)
        + theme_report(9, 5.5)
    )


# --------------------------------------------------------------------------
# Maps (plotly)
# --------------------------------------------------------------------------
def map_abandonment(countries: pd.DataFrame):
    """World choropleth of abandonment rates, in five classes.

    A rate is already normalised, so a choropleth is appropriate (raw
    totals would mostly reflect country size). Classes make it readable.
    """
    data = countries.assign(
        rate_class=pd.cut(countries["abandonment_rate"], [0, .2, .4, .6, .8, 1.0001],
                          labels=MAP_CLASSES, right=False),
        hover=lambda df: (
            df["country"] + "<br>Abandonment rate: "
            + df["abandonment_rate"].map(lambda v: f"{v:.0%}")
            + "<br>Capacity with an outcome: "
            + df["outcome_gw"].map(lambda v: f"{v:,.0f} GW")
        ),
    ).sort_values("rate_class")
    fig = px.choropleth(
        data, locations="iso3", color="rate_class",
        color_discrete_sequence=MAP_COLORS,
        category_orders={"rate_class": MAP_CLASSES},
        hover_name="hover", hover_data={"iso3": False, "rate_class": False},
    )
    fig.update_traces(hovertemplate="%{hovertext}<extra></extra>", marker_line_width=0.3)
    fig.update_layout(
        title="Share of power capacity abandoned rather than built, by country",
        legend_title_text="Abandonment rate",
        geo=dict(showframe=False, showcoastlines=False, projection_type="natural earth"),
        margin=dict(l=0, r=0, t=50, b=0), height=480,
    )
    return fig


def map_projects(units: pd.DataFrame, title: str):
    """Proportional-symbol map of projects with an outcome: one circle per
    project, area proportional to capacity, colour = built or abandoned."""
    projects = (
        units.loc[units["in_outcome_sample"]]
        .assign(outcome=lambda df: np.where(df["abandoned"], "Abandoned", "Built"))
        .groupby(["project", "country", "technology", "outcome"], as_index=False)
        .agg(capacity_mw=("capacity_mw", "sum"), latitude=("latitude", "mean"),
             longitude=("longitude", "mean"))
        .sort_values("capacity_mw", ascending=False)
    )
    fig = px.scatter_geo(
        projects, lat="latitude", lon="longitude", size="capacity_mw",
        color="outcome", color_discrete_map={"Built": BLUE, "Abandoned": ORANGE},
        hover_name="project",
        hover_data={"country": True, "technology": True, "capacity_mw": ":,.0f",
                    "latitude": False, "longitude": False, "outcome": False},
        size_max=28, opacity=0.6,
    )
    fig.update_layout(
        title=title, legend_title_text="",
        geo=dict(projection_type="mercator", lataxis_range=[12, 42],
                 lonaxis_range=[24, 63], showcountries=True, countrycolor="#c3c2b7",
                 showland=True, landcolor="#f4f3f0"),
        margin=dict(l=0, r=0, t=50, b=0), height=520,
    )
    return fig

