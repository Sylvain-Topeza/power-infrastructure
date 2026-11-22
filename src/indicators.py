"""Indicators of development risk.

The central indicator is the **abandonment rate**: among the projects that
reached an outcome (see ``clean.add_outcome``), the share of capacity that was
abandoned rather than built:

    abandonment rate = abandoned MW / (abandoned MW + built MW)

Rates are weighted by capacity (a 2 GW project counts more than a 20 MW one),
which is what matters to an investor or a grid operator.
"""

import pandas as pd

STAGE_ORDER = ["pipeline", "construction", "operating", "abandoned", "other"]

# Classes of the World Bank Regulatory Quality score (section 5 of the report).
REGULATION_BINS = [-3, -0.5, 0.5, 1.2, 3]
REGULATION_LABELS = [
    "Weak (below -0.5)", "Average (-0.5 to 0.5)", "Good (0.5 to 1.2)", "Very good (above 1.2)",
]


def abandonment_rate(
    data: pd.DataFrame,
    by,
    weight: str = "capacity_mw",
    min_gw: float = 0.0,
) -> pd.DataFrame:
    """Abandonment rate by group, for units in the outcome sample.

    ``data`` is either the unit table (weight 'capacity_mw') or the ownership
    table (weight 'equity_mw'). Groups with less than ``min_gw`` of capacity
    in the sample are dropped, because their rates are too noisy to compare.
    """
    by = [by] if isinstance(by, str) else list(by)
    return (
        data
        .loc[data["in_outcome_sample"]]
        .assign(
            abandoned_mw=lambda df: df[weight].where(df["abandoned"], 0),
            built_mw=lambda df: df[weight].where(~df["abandoned"], 0),
        )
        .groupby(by, as_index=False, observed=True)
        .agg(
            abandoned_gw=("abandoned_mw", "sum"),
            built_gw=("built_mw", "sum"),
            n_units=("unit_id", "nunique"),
        )
        .assign(
            abandoned_gw=lambda df: df["abandoned_gw"] / 1000,
            built_gw=lambda df: df["built_gw"] / 1000,
            outcome_gw=lambda df: df["abandoned_gw"] + df["built_gw"],
            abandonment_rate=lambda df: df["abandoned_gw"] / df["outcome_gw"],
        )
        .loc[lambda df: df["outcome_gw"] >= min_gw]
        .reset_index(drop=True)
    )


def capacity_by_stage(data: pd.DataFrame, by, weight: str = "capacity_mw") -> pd.DataFrame:
    """Capacity (GW) by group and stage, in long format."""
    by = [by] if isinstance(by, str) else list(by)
    return (
        data
        .groupby(by + ["stage"], as_index=False, observed=True)[weight]
        .sum()
        .assign(gw=lambda df: df[weight] / 1000)
        .drop(columns=weight)
        .assign(stage=lambda df: pd.Categorical(df["stage"], STAGE_ORDER, ordered=True))
        .sort_values(by + ["stage"])
        .reset_index(drop=True)
    )


def sponsor_profiles(ownership: pd.DataFrame, location: str | None = "Abroad") -> pd.DataFrame:
    """One row per sponsor group: portfolio by stage and two ratios.

    - ``pipeline_ratio`` = (pipeline + construction) / operating capacity.
      Above 1, the sponsor is mainly developing new projects; well below 1,
      it mainly owns plants that are already running (an acquirer or operator).
    - ``abandonment_rate``, on the sponsor's equity capacity.

    ``location`` restricts to assets abroad ('Abroad'), at home ('Home'),
    or keeps both (None).
    """
    sponsors = ownership.loc[ownership["sponsor_group"].notna()]
    if location is not None:
        sponsors = sponsors.loc[sponsors["location"] == location]
    portfolio = (
        sponsors
        .pivot_table(index=["sponsor_group", "origin"], columns="stage",
                     values="equity_mw", aggfunc="sum", fill_value=0)
        .div(1000)
        .reindex(columns=STAGE_ORDER, fill_value=0)
        .reset_index()
        .rename_axis(columns=None)
    )
    rates = abandonment_rate(sponsors, "sponsor_group", weight="equity_mw")[
        ["sponsor_group", "abandonment_rate"]
    ]
    return (
        portfolio
        .assign(
            portfolio_gw=lambda df: df[STAGE_ORDER].sum(axis=1),
            # Undefined (missing) for sponsors with no operating plant abroad.
            pipeline_ratio=lambda df: ((df["pipeline"] + df["construction"])
                                       / df["operating"].where(df["operating"] > 0)),
        )
        .merge(rates, on="sponsor_group", how="left")
        .sort_values("portfolio_gw", ascending=False)
        .reset_index(drop=True)
    )


def home_vs_abroad(ownership: pd.DataFrame, by: str = "origin") -> pd.DataFrame:
    """Abandonment rates of sponsors at home and abroad, by ``by``
    ('origin' for Gulf vs global peers, or 'sponsor_group')."""
    return abandonment_rate(
        ownership.loc[ownership["sponsor_group"].notna()],
        [by, "location"],
        weight="equity_mw",
    )


def robustness_checks(units: pd.DataFrame, by: str = "area") -> pd.DataFrame:
    """Abandonment rates by ``by`` under alternative definitions.

    - 'Baseline': abandoned vs under construction or operating since 2010;
    - 'Excluding inferred statuses': drops units that GEM classifies as
      cancelled or shelved only because no news was found for 2-4 years
      (a lower bound for the rate);
    - 'Excluding construction': counts as built only the plants already in
      operation, since projects under construction can still be abandoned
      (an upper bound for the rate).
    """
    variants = {
        "Excluding inferred statuses": units.loc[~units["status_inferred"]],
        "Baseline": units,
        "Excluding construction": units.assign(
            in_outcome_sample=units["in_outcome_sample"] & (units["stage"] != "construction")
        ),
    }
    return pd.concat(
        [abandonment_rate(data, by).assign(definition=name) for name, data in variants.items()]
    ).pivot(index=by, columns="definition", values="abandonment_rate")[list(variants)]

