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


def parse_owners(text) -> list:
    """Split an ownership field into a list of (owner, share in %) pairs.

    When no share is reported (most wind and solar projects), capacity is split
    equally between the listed owners. When only some shares are reported,
    owners without a share get zero, so that the total never exceeds 100%.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    entries = []
    for part in text.split(";"):
        match = OWNER_PATTERN.match(part.strip())
        share = match.group("share")
        entries.append((match.group("owner"), float(share) if share else None))
    if all(share is None for _, share in entries):
        return [(owner, 100 / len(entries)) for owner, _ in entries]
    return [(owner, share or 0.0) for owner, share in entries]


def build_ownership(units: pd.DataFrame) -> pd.DataFrame:
    """Long table with one row per unit and owner.

    We use the ultimate parent companies when GEM reports them (coal and gas
    plants) and the direct owners otherwise. ``equity_mw`` is the capacity
    attributable to each owner (capacity x share).
    """
    source = units["parents"].where(units["parents"].notna(), units["owners"])
    ownership = (
        units[["unit_id"]]
        .assign(
            entries=source.map(parse_owners),
            share_reported=source.fillna("").str.contains("%"),
            owner_level=np.where(units["parents"].notna(), "parent", "owner"),
        )
        .explode("entries")
        .dropna(subset=["entries"])
    )
    ownership[["owner", "share_pct"]] = pd.DataFrame(
        ownership["entries"].tolist(), index=ownership.index
    )
    ownership = (
        ownership
        .drop(columns="entries")
        .merge(units, on="unit_id", how="left")
        .assign(equity_mw=lambda df: df["capacity_mw"] * df["share_pct"] / 100)
        .reset_index(drop=True)
    )
    return ownership


def assign_sponsor_groups(ownership: pd.DataFrame, sponsors: pd.DataFrame) -> pd.DataFrame:
    """Link each owner to a sponsor group, using the regular expressions of
    data/sponsors.csv (first match wins). Also flags whether the asset is in
    the sponsor's home country or abroad."""
    group = pd.Series(pd.NA, index=ownership.index, dtype="object")
    for row in sponsors.itertuples():
        matches = group.isna() & ownership["owner"].str.contains(row.pattern, regex=True)
        group[matches] = row.sponsor_group
    sponsor_info = sponsors.set_index("sponsor_group")[["home_country", "origin"]]
    ownership = ownership.assign(sponsor_group=group).join(sponsor_info, on="sponsor_group")
    is_home = ownership["home_country"].eq(ownership["country"]).fillna(False)
    location = pd.Series("Abroad", index=ownership.index, dtype="object")
    location[is_home.to_numpy(dtype=bool)] = "Home"
    location[ownership["home_country"].isna().to_numpy()] = None
    return ownership.assign(location=location)
