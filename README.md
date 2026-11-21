# Which Power Projects Actually Get Built?
### Development Risk in the Middle East and Beyond

*ENSAE Paris – Python for Data Science (2026-2027)*
*Authors: Sylvain Topeza, Maxime Rolland, Arcadius Kouwagou*

## The question

Governments and developers regularly announce gigawatts of new power capacity.
Yet a large share of announced projects is never built: permits fall through,
financing fails, or priorities change. For anyone financing or investing in
infrastructure, this gap between announcement and construction is the core of
**development risk**.

This project asks: **which power projects actually get built, and why?**

We answer three questions:

1. **How much of what is announced gets built?** Abandonment rates by technology.
2. **Where is development risk highest?** A country-level comparison, with a
   focus on the Middle East, where state-led procurement makes the region a
   striking case.
3. **Is it the market or the developer?** We follow the same Gulf developers
   (ACWA Power, Masdar, TAQA, etc.) at home and abroad, and compare them with
   global peers (ENGIE, EDF, Ørsted, Brookfield, etc.).

## Key findings (preliminary)

- [X]% of the capacity that progressed past the pipeline stage since 2010 was abandoned
  rather than built; rates range from [20]% for solar to [75]% for nuclear.
- In Gulf countries, almost no announced project is abandoned ([~3]% in Saudi
  Arabia), against [56]% in India and [69]% in Greece.
- Gulf developers abandon almost nothing at home but [34]% of their projects
  abroad, close to their Western and Asian peers ([40]%): development risk
  seems to follow the market, not the developer.

## Data

| Source | Content | Access |
|---|---|---|
| [Global Integrated Power Tracker](https://globalenergymonitor.org/projects/global-integrated-power-tracker/), Global Energy Monitor (September 2026, V2) | 183,404 power units: capacity, technology, country, status, owners | CC BY 4.0, mirrored on SSP Cloud storage |
| [World Bank API] *(optional)* | Income group, regulatory quality by country | Public API |

The raw file is downloaded from Global Energy Monitor through a form, so it
cannot be fetched by code. We mirror it, unchanged, on the SSP Cloud public
storage; the notebook reads it from there.

## Method

1. **Cleaning**: extract owners and ownership shares from text fields with
   regular expressions; group subsidiaries under their parent company;
   harmonise statuses into four stages (pipeline, construction, operating,
   abandoned).
2. **Development risk indicator**: abandonment rate = abandoned capacity /
   (abandoned + under construction + commissioned since 2010).
3. **Descriptive analysis and maps** by technology, country and developer.
4. **Logistic regression** to separate technology, country and developer effects.

## Limits

- The dataset is a snapshot: it has no announcement dates, so we cannot follow
  each project over time.
- In tender-based markets (e.g. the Gulf), projects often appear in the data
  only once awarded, which mechanically lowers abandonment rates.
- Ownership shares are only reported for coal and gas plants; for other
  technologies, capacity is split equally between listed owners.
- Small installations below the tracker's thresholds (e.g. 1-20 MW for solar)
  are not covered.

## Repository structure

    ├── main.ipynb           # Final report: run all cells to reproduce
    ├── src/
    │   ├── load.py          # Data import from SSP Cloud
    │   ├── clean.py         # Ownership parsing, statuses, sponsor mapping
    │   ├── indicators.py    # Development risk indicators
    │   └── plots.py         # Charts and maps
    ├── requirements.txt
    └── README.md

## How to run

1. Open a Python service on the [SSP Cloud](https://datalab.sspcloud.fr).
2. Clone the repository and install dependencies:
   `pip install -r requirements.txt`
3. Open `main.ipynb` and run all cells.

## Data attribution

Global Energy Monitor, Global Integrated Power Tracker, September 2026 release (V2), licensed under CC BY 4.0.
