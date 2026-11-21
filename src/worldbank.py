"""Country characteristics from the World Bank API (v2).

We collect, for every country:
- its income group (World Bank classification);
- GDP per capita (World Development Indicators);
- the Regulatory Quality score of the Worldwide Governance Indicators, which
  measures how far governments allow and support private sector development
  (roughly from -2.5, weak, to +2.5, strong).

The API is free and needs no key. Results are paged: we loop over pages.
A snapshot of the result is saved in data/worldbank_snapshot.csv and
committed to the repository, so that the analysis still runs if the API
is unavailable on the day of grading (see the README).
"""

import pandas as pd
import requests

from src import config

TIMEOUT = 30


def _get_all_pages(url: str, params: dict) -> list:
    """Call a World Bank API endpoint and return the records of every page.

    The API answers a JSON list: [metadata, records]. On an unknown indicator
    it answers [{"message": [...]}] instead, which we turn into an empty list.
    """
    params = {"format": "json", "per_page": 1000, **params}
    records, page, pages = [], 1, 1
    while page <= pages:
        response = requests.get(url, params={**params, "page": page}, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        if len(payload) < 2 or payload[1] is None:
            return []
        pages = payload[0]["pages"]
        records.extend(payload[1])
        page += 1
    return records


def fetch_countries() -> pd.DataFrame:
    """Return the list of countries with their income group.

    The endpoint also lists aggregates (e.g. 'World', 'Arab World'),
    recognisable by their region 'Aggregates': we drop them.
    """
    records = _get_all_pages(f"{config.WORLD_BANK_API}/country", {})
    return (
        pd.DataFrame(
            {
                "iso3": [r["id"] for r in records],
                "wb_name": [r["name"] for r in records],
                "wb_region": [r["region"]["value"] for r in records],
                "income_group": [r["incomeLevel"]["value"] for r in records],
            }
        )
        .loc[lambda df: df["wb_region"] != "Aggregates"]
        .reset_index(drop=True)
    )


def fetch_indicator(name: str) -> pd.DataFrame:
    """Return the most recent value of an indicator for every country.

    Several codes may be listed for one indicator in config.WB_INDICATORS
    (codes changed over time): the first one that returns data is used.
    """
    spec = config.WB_INDICATORS[name]
    start, end = config.WB_YEARS
    for code in spec["codes"]:
        records = _get_all_pages(
            f"{config.WORLD_BANK_API}/country/all/indicator/{code}",
            {"date": f"{start}:{end}", "source": spec["source"]},
        )
        values = pd.DataFrame(
            {
                "iso3": [r["countryiso3code"] for r in records],
                "year": [r["date"] for r in records],
                "value": [r["value"] for r in records],
            }
        ).dropna(subset=["value"])
        if not values.empty:
            return (
                values
                .assign(year=lambda df: df["year"].astype(int))
                .sort_values("year")
                .groupby("iso3", as_index=False)
                .last()
                .rename(columns={"value": name, "year": f"{name}_year"})
                .assign(**{f"{name}_code": code})
            )
    raise RuntimeError(f"No data returned by the World Bank API for '{name}'.")


def fetch_worldbank() -> pd.DataFrame:
    """Query the API and assemble one row per country."""
    table = fetch_countries()
    for name in config.WB_INDICATORS:
        table = table.merge(fetch_indicator(name), on="iso3", how="left")
    return table


def load_worldbank(refresh: bool = False) -> pd.DataFrame:
    """Return the World Bank table, from the API or from the saved snapshot.

    With ``refresh=True``, or when no snapshot exists, the API is queried and
    the snapshot is rewritten. If the API cannot be reached, the snapshot is
    used and a message says so.
    """
    snapshot = config.WORLD_BANK_SNAPSHOT
    if refresh or not snapshot.exists():
        try:
            table = fetch_worldbank()
        except requests.RequestException as error:
            if not snapshot.exists():
                raise RuntimeError(
                    "The World Bank API could not be reached and no snapshot "
                    f"exists yet ({snapshot})."
                ) from error
            print(f"World Bank API unavailable ({error}); using the saved snapshot.")
        else:
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            table.to_csv(snapshot, index=False)
            return table
    return pd.read_csv(snapshot, keep_default_na=False, na_values=[""])
