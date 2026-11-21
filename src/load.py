"""Import of the raw data.

The Global Energy Monitor file is a 30 MB Excel workbook, downloaded once from
its public URL into data/raw/. Reading it takes about a minute, so the first
read is cached as Parquet (a compressed columnar format, see the course
chapter on Parquet). Later runs read the cache. Both folders are ignored by Git.
"""

from pathlib import Path

import pandas as pd
import requests

from src import config


def download(url: str, destination: Path) -> Path:
    """Download a file once; do nothing if it is already there."""
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        destination.write_bytes(response.content)
    return destination


def load_gem(use_cache: bool = True) -> pd.DataFrame:
    """Return the raw Global Integrated Power Tracker, one row per power unit.

    Look-up order: the Parquet cache (data/cache/), then the Excel file in
    data/raw/, downloaded from ``config.GEM_URL`` if it is not there yet.
    """
    cache = config.CACHE_DIR / "gem.parquet"
    if use_cache and cache.exists():
        return pd.read_parquet(cache)

    raw_file = download(config.GEM_URL, config.DATA_DIR / "raw" / config.GEM_FILE_NAME)
    gem = pd.read_excel(raw_file, sheet_name=config.GEM_SHEET)

    # Some text columns mix strings and numbers (e.g. unit names "GEN9" and 2):
    # Parquet needs one type per column, so text columns are stored as strings.
    text_columns = gem.select_dtypes(include="object").columns
    gem[text_columns] = gem[text_columns].astype("string")

    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    gem.to_parquet(cache, index=False)
    return gem


def load_country_codes() -> pd.DataFrame:
    """Return the ISO 3166 reference table (country names and codes).

    ``keep_default_na=False`` matters: otherwise Namibia's two-letter code
    "NA" would be read as a missing value.
    """
    cache = config.CACHE_DIR / "country_codes.csv"
    if cache.exists():
        return pd.read_csv(cache, keep_default_na=False)
    codes = pd.read_csv(config.COUNTRY_CODES_URL, keep_default_na=False)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    codes.to_csv(cache, index=False)
    return codes


def load_sponsors(path: Path = config.SPONSORS_FILE) -> pd.DataFrame:
    """Return the hand-built dictionary of sponsor groups (data/sponsors.csv)."""
    return pd.read_csv(path)

