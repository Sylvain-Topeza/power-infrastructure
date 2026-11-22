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
