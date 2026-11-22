"""Logistic regression of project abandonment.

Question: once we account for the technology, the size of the project and the
characteristics of the host country, does the identity of the developer still
matter?

Each observation is a power unit in the outcome sample; the dependent variable
equals 1 if the unit was abandoned and 0 if it was built. Three choices:

- **Weights.** The descriptive rates are weighted by capacity. Unweighted, the
  model would mostly describe small solar units (two thirds of the sample), so
  the main specification weights each unit by its capacity (normalised to a
  mean of 1). The unweighted version is reported as a check.
- **Owner categories.** Units with no known owner are mostly small projects,
  rarely abandoned when counted in units. They get their own category
  ('Unknown owner') instead of being mixed with the reference category.
- **Home and abroad.** Gulf sponsors are split between their home country and
  abroad. None of their units at home was abandoned: a logit cannot estimate
  an effect for a category with no failure (perfect prediction), so these units
  are left out of the estimation and discussed descriptively.

Units of the same country share unobserved conditions (grid, politics,
permitting), so standard errors are clustered by country.
"""

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.tools.sm_exceptions import SpecificationWarning


def sponsor_type(ownership: pd.DataFrame) -> pd.Series:
    """Classify each unit by its main identified sponsor, indexed by unit_id:
    'Gulf sponsor at home', 'Gulf sponsor abroad' or 'Global peer'
    (a Gulf sponsor takes precedence when both are present)."""
    sponsors = ownership.dropna(subset=["origin"])
    label = np.where(
        sponsors["origin"] == "Gulf",
        np.where(sponsors["location"] == "Home", "Gulf sponsor at home", "Gulf sponsor abroad"),
        "Global peer",
    )
    priority = {"Gulf sponsor at home": 0, "Gulf sponsor abroad": 1, "Global peer": 2}
    return (
        sponsors.assign(sponsor=label, priority=pd.Series(label).map(priority).to_numpy())
        .sort_values("priority")
        .groupby("unit_id")["sponsor"]
        .first()
    )


def model_table(
    units: pd.DataFrame,
    ownership: pd.DataFrame,
    worldbank: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the estimation sample: one row per unit in the outcome sample."""
    sample = units.loc[units["in_outcome_sample"]]
    known_owner = sample["owners"].notna() | sample["parents"].notna()
    default = pd.Series(np.where(known_owner, "Other owner", "Unknown owner"), index=sample.index)
    table = sample.assign(
        abandoned=sample["abandoned"].astype(int),
        log_capacity=np.log(sample["capacity_mw"]),
        weight=sample["capacity_mw"] / sample["capacity_mw"].mean(),
        sponsor=sample["unit_id"].map(sponsor_type(ownership)).fillna(default),
    )
    if worldbank is not None:
        country_data = worldbank[["iso3", "income_group", "regulatory_quality"]]
        table = table.merge(country_data, on="iso3", how="left")
    return table


def fit_logit(table: pd.DataFrame, formula: str, weighted: bool = True):
    """Fit a logit (binomial GLM) with country-clustered standard errors.

    Rows with a missing variable are dropped beforehand, so that the cluster
    groups line up with the estimation sample. Units of Gulf sponsors at home
    are excluded (perfect prediction, see the module docstring).
    """
    needed = [c for c in ["regulatory_quality", "income_group"] if c in formula]
    sample = (
        table.loc[table["sponsor"] != "Gulf sponsor at home"]
        .dropna(subset=needed + ["abandoned", "iso3"])
    )
    groups = pd.factorize(sample["iso3"])[0]
    with warnings.catch_warnings():
        # statsmodels warns that clustered errors are "not fully supported" with
        # weights. We silence the warning here and discuss it in the report: the
        # unweighted model, where the issue does not arise, gives the same conclusions.
        warnings.simplefilter("ignore", SpecificationWarning)
        return smf.glm(
            formula,
            data=sample,
            family=sm.families.Binomial(),
            var_weights=sample["weight"] if weighted else None,
        ).fit(cov_type="cluster", cov_kwds={"groups": groups})


def odds_ratios(result) -> pd.DataFrame:
    """Odds ratios with 95% confidence intervals and p-values.

    An odds ratio of 2 means that the odds of abandonment are twice as high
    as for the reference category, all other variables being equal.
    """
    ci = np.exp(result.conf_int())
    return (
        pd.DataFrame(
            {
                "odds_ratio": np.exp(result.params),
                "ci_low": ci[0],
                "ci_high": ci[1],
                "p_value": result.pvalues,
            }
        )
        .drop(index="Intercept")
        .rename_axis("variable")
        .reset_index()
    )


def readable_labels(table: pd.DataFrame) -> pd.DataFrame:
    """Turn statsmodels names such as 'C(technology, Treatment("Solar"))[T.Coal]'
    into readable labels such as 'Technology: Coal'."""
    pattern = r'C\((?P<var>\w+)(?:, Treatment\("[^"]+"\))?\)\[T\.(?P<level>[^\]]+)\]'
    extracted = table["variable"].str.extract(pattern)
    names = {"technology": "Technology", "area": "Region", "sponsor": "Owner",
             "income_group": "Income"}
    label = extracted["var"].map(names) + ": " + extracted["level"]
    label = label.fillna(table["variable"].replace({
        "log_capacity": "Capacity (log MW)",
        "regulatory_quality": "Regulatory quality (+1 point)",
        "I(regulatory_quality ** 2)": "Regulatory quality, squared",
    }))
    return table.assign(label=label)


def compare_models(results: dict) -> pd.DataFrame:
    """Side-by-side odds ratios and p-values of several fitted models.

    ``results`` maps a model name to a fitted result."""
    tables = [
        readable_labels(odds_ratios(result))
        .set_index("label")[["odds_ratio", "p_value"]]
        .rename(columns=lambda column: f"{column} ({name})")
        for name, result in results.items()
    ]
    return pd.concat(tables, axis=1).reset_index()


def model_summary(results: dict) -> pd.DataFrame:
    """Number of units and McFadden pseudo R² of each model."""
    return pd.DataFrame(
        {
            "units": [int(r.nobs) for r in results.values()],
            "pseudo_r2": [r.pseudo_rsquared(kind="mcf") for r in results.values()],
        },
        index=list(results),
    )




