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



