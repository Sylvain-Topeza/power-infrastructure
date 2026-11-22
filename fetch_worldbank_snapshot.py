"""One-off helper: create data/worldbank_snapshot.csv from the World Bank API.

Run it once from the root of the repository (on the SSP Cloud or any computer
with internet access):

    python fetch_worldbank_snapshot.py

It calls the same functions as the notebook (src/worldbank.py) and saves the
result, which is then committed so that the analysis runs even if the API is
down on the day of grading.
"""

from src import worldbank

if __name__ == "__main__":
    table = worldbank.load_worldbank(refresh=True)
    print(table.head())
    print(f"{len(table)} countries saved.")
    for column in ["income_group", "regulatory_quality", "gdp_per_capita"]:
        print(f"{column}: {table[column].notna().sum()} countries with data")

