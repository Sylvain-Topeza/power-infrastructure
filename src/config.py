"""Project-wide settings: data locations, definitions and constants.

Every analytical choice that could change a result (the cohort start year,
the regional groupings, the mapping of statuses to stages) is defined here,
so that it is visible in one place and easy to change.
"""

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"          # local copies, ignored by Git
FIGURES_DIR = ROOT / "figures"

# --------------------------------------------------------------------------
# Main source: Global Energy Monitor, Global Integrated Power Tracker
# --------------------------------------------------------------------------
# The tracker is distributed through a download form, so it cannot be fetched
# by code from Global Energy Monitor directly. We mirror the raw file,
# unchanged, in the public "diffusion" folder of our SSP Cloud storage
# (licence CC BY 4.0, which allows redistribution with attribution).
# It is downloaded over plain HTTPS, so the project runs on any computer.
GEM_FILE_NAME = "Global Integrated Power September 2026 V2.xlsx"
GEM_SHEET = "Power facilities"
# SSP Cloud username of the group member who hosts the data (see README).
S3_BUCKET = os.environ.get("PDR_S3_BUCKET", "maximerolland")
GEM_URL = (
    f"https://minio.lab.sspcloud.fr/{S3_BUCKET}/diffusion/power-projects/{GEM_FILE_NAME}"
)

# Secondary sources
COUNTRY_CODES_URL = (
    "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
)
WORLD_BANK_API = "https://api.worldbank.org/v2"
WORLD_BANK_SNAPSHOT = DATA_DIR / "worldbank_snapshot.csv"
SPONSORS_FILE = DATA_DIR / "sponsors.csv"

# --------------------------------------------------------------------------
# Definitions
# --------------------------------------------------------------------------
# GEM statuses grouped into the four stages of a project's life.
STATUS_TO_STAGE = {
    "announced": "pipeline",
    "pre-construction": "pipeline",
    "construction": "construction",
    "operating": "operating",
    "cancelled": "abandoned",
    "cancelled - inferred 4 y": "abandoned",
    "shelved": "abandoned",
    "shelved - inferred 2 y": "abandoned",
    "mothballed": "other",
    "retired": "other",
}
# Statuses that GEM infers from the absence of news (used in robustness checks).
INFERRED_STATUSES = {"cancelled - inferred 4 y", "shelved - inferred 2 y"}

# A project "reached an outcome" if it was abandoned, is under construction,
# or entered operation in or after this year (see the notebook, section 2.4).
COHORT_START_YEAR = 2010

# Regional groupings used throughout the report.
GCC = ["Bahrain", "Kuwait", "Oman", "Qatar", "Saudi Arabia", "United Arab Emirates"]
REST_OF_MIDDLE_EAST = [
    "Egypt", "Iran", "Iraq", "Israel", "Jordan", "Lebanon",
    "Palestine", "Syria", "Yemen",
]

# Readable labels for GEM technology types.
# Readable labels for GEM technology types.
TECHNOLOGY_LABELS = {
    "utility-scale solar": "Solar",
    "wind": "Wind",
    "oil/gas": "Gas & oil",
    "coal": "Coal",
    "hydropower": "Hydropower",
    "nuclear": "Nuclear",
    "bioenergy": "Bioenergy",
    "geothermal": "Geothermal",
}

# Country names used by GEM that differ from the reference ISO table.
COUNTRY_NAME_FIXES = {
    "Antigua and Barbuda": "ATG",
    "Bonaire, Sint Eustatius, and Saba": "BES",
    "Bosnia and Herzegovina": "BIH",
    "Cabo Verde": "CPV",
    "Czech Republic": "CZE",
    "Côte d'Ivoire": "CIV",
    "DR Congo": "COD",
    "Kosovo": "XKX",  # World Bank code; Kosovo has no ISO 3166 code
    "Republic of the Congo": "COG",
    "Saint Helena, Ascension, and Tristan da Cunha": "SHN",
    "Saint Kitts and Nevis": "KNA",
    "Saint Lucia": "LCA",
    "Saint Pierre and Miquelon": "SPM",
    "Saint Vincent and the Grenadines": "VCT",
    "Sao Tome and Principe": "STP",
    "The Gambia": "GMB",
    "Trinidad and Tobago": "TTO",
    "United Kingdom": "GBR",
    "United States": "USA",
    "Virgin Islands (U.S.)": "VIR",
}

# World Bank indicators. The Worldwide Governance Indicators changed codes in
# their 2024 revision, so several candidate codes are tried in order.
