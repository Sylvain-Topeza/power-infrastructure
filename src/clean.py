"""Cleaning and structuring of the Global Energy Monitor data.

Main steps, each in its own function:
- keep and rename the useful columns (snake_case);
- group the ten GEM statuses into four stages;
- add readable technology labels, regional groupings and ISO country codes;
- turn the ownership text fields into a long table (one row per unit and owner),
  with each owner's equity share of the capacity;
- link owners to sponsor groups (Masdar, ACWA Power, ENGIE...).
"""

import re

import numpy as np
import pandas as pd

from src import config

COLUMNS = {
    "GEM unit/phase ID": "unit_id",
    "Plant / Project name": "project",
    "Type": "type",
    "Country/area": "country",
    "Region": "region",
    "Subregion": "subregion",
    "Capacity (MW)": "capacity_mw",
    "Status": "status",
    "Start year": "start_year",
    "Owner(s)": "owners",
    "Parent(s)": "parents",
    "Latitude": "latitude",
    "Longitude": "longitude",
}


# --------------------------------------------------------------------------
# Unit-level table
# --------------------------------------------------------------------------
def select_columns(gem: pd.DataFrame) -> pd.DataFrame:
    """Keep the columns used in the project, with short snake_case names."""
    return gem[list(COLUMNS)].rename(columns=COLUMNS)


def add_stage(units: pd.DataFrame) -> pd.DataFrame:
    """Group GEM statuses into four stages: pipeline, construction,
    operating and abandoned (plus 'other' for retired and mothballed units)."""
    unknown = set(units["status"].dropna()) - set(config.STATUS_TO_STAGE)
    if unknown:
        raise ValueError(f"Statuses missing from config.STATUS_TO_STAGE: {unknown}")
    return units.assign(
        stage=units["status"].map(config.STATUS_TO_STAGE),
        status_inferred=units["status"].isin(config.INFERRED_STATUSES),
    )


def add_labels(units: pd.DataFrame) -> pd.DataFrame:
    """Add a readable technology label and a three-level regional grouping."""
    area = np.select(
        [units["country"].isin(config.GCC),
         units["country"].isin(config.REST_OF_MIDDLE_EAST)],
        ["GCC", "Rest of Middle East"],
        default="Rest of world",
    )
    return units.assign(
        technology=units["type"].map(config.TECHNOLOGY_LABELS),
        area=area,
    )

