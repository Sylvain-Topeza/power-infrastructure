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


def add_iso3(units: pd.DataFrame, country_codes: pd.DataFrame) -> pd.DataFrame:
    """Add the ISO 3166 alpha-3 code of each country, needed to join the
    World Bank data. GEM uses short English names: we match them first on the
    CLDR display names, then on official names, then on a manual table."""
    lookup = {}
    for column in ["official_name_en", "CLDR display name"]:  # CLDR wins on ties
        lookup.update(
            country_codes
            .loc[country_codes[column] != "", [column, "ISO3166-1-Alpha-3"]]
            .set_index(column)["ISO3166-1-Alpha-3"]
            .to_dict()
        )
    lookup.update(config.COUNTRY_NAME_FIXES)
    return units.assign(iso3=units["country"].map(lookup))


def add_outcome(units: pd.DataFrame, start_year: int = config.COHORT_START_YEAR) -> pd.DataFrame:
    """Flag the units whose development reached an outcome.

    GEM gives no announcement date, so we cannot follow projects over time.
    We compare, instead, the projects that were abandoned with those that were
    built recently: under construction, or in operation since ``start_year``.
    Older operating plants are left out, because the projects abandoned before
    ``start_year`` have mostly disappeared from the tracker.
    """
    built = (units["stage"] == "construction") | (
        (units["stage"] == "operating") & (units["start_year"] >= start_year)
    )
    abandoned = units["stage"] == "abandoned"
    return units.assign(
        in_outcome_sample=built | abandoned,
        abandoned=abandoned,
    )


def build_units(gem: pd.DataFrame, country_codes: pd.DataFrame) -> pd.DataFrame:
    """Full cleaning pipeline for the unit-level table."""
    units = (
        gem
        .pipe(select_columns)
        .loc[lambda df: df["capacity_mw"] > 0]
        .pipe(add_stage)
        .pipe(add_labels)
        .pipe(add_iso3, country_codes=country_codes)
        .pipe(add_outcome)
        .reset_index(drop=True)
    )
    if not units["unit_id"].is_unique:
        raise ValueError("Duplicated unit identifiers in the GEM data.")
    return units


# --------------------------------------------------------------------------
# Ownership
# --------------------------------------------------------------------------
# "Company A [51%]; Company B [49%]" -> owner name and share, per entry.
OWNER_PATTERN = re.compile(r"^(?P<owner>.*?)\s*(?:\[(?P<share>[\d.]+)%\])?\s*$")
