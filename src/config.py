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
