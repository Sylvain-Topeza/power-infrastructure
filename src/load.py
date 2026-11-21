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

