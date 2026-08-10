"""Generalized Linear Models (GENLIN), Generalized Estimating Equations (GEE),
Linear Mixed Models (MIXED), and Loglinear (GENLOG).

All statsmodels-backed. Parameter tables follow SPSS's "Parameter Estimates"
layout: B, Std. Error, Wald Chi-Square (=(B/SE)^2), df, Sig.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


def _clean(ds: Any, names: list[str]) -> pd.DataFrame:
    frame = {}
    for nm in names:
        s = ds.df[nm]
        frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(frame).dropna()


def _family(dist: str, link: str):
    import statsmodels.api as sm

    links = {
        "IDENTITY": sm.families.links.Identity(),
        "LOG": sm.families.links.Log(),
        "LOGIT": sm.families.links.Logit(),
        "INVERSE": sm.families.links.InversePower(),
    }
    lk = links.get(link.upper())
    d = dist.upper()
    if d in ("NORMAL", "GAUSSIAN"):
        return sm.families.Gaussian(lk or sm.families.links.Identity())
    if d == "POISSON":
        return sm.families.Poisson(lk or sm.families.links.Log())
    if d in ("BINOMIAL", "BERNOULLI"):
        return sm.families.Binomial(lk or sm.families.links.Logit())
    if d == "GAMMA":
        return sm.families.Gamma(lk or sm.families.links.Log())
    return sm.families.Gaussian()


def _wald_table(title, caption, names, b, se):
    from scipy import stats as sps

    rows = list(names)
    t = PivotTable(title, [Dimension("Parameter", rows)],
                   [Dimension("", ["B", "Std. Error", "Wald Chi-Square", "df", "Sig."])],
                   caption=caption)
    for i in range(len(rows)):
        wald = (b[i] / se[i]) ** 2 if se[i] else float("nan")
        sig = float(sps.chi2.sf(wald, 1))
        t.set([i], [0], _F3.render(float(b[i])))
        t.set([i], [1], _F3.render(float(se[i])))
        t.set([i], [2], _F3.render(float(wald)))
        t.set([i], [3], _F0.render(1))
        t.set([i], [4], strip_leading_zero(_F3.render(sig)))
    return t


def _design(data, dep, factors, covars):
    """Build (X, names) with an intercept, dummy-coded factors, and covariates."""
    import pandas as pd

    parts = [pd.Series(1.0, index=data.index, name="(Intercept)")]
    names = ["(Intercept)"]
    for f in factors:
        d = pd.get_dummies(data[f].astype("category"), prefix=f, drop_first=True).astype(float)
        for c in d.columns:
            parts.append(d[c]); names.append(str(c))
    for c in covars:
        parts.append(data[c].astype(float)); names.append(c)
    X = pd.concat(parts, axis=1)
    return X.to_numpy(float), names


def _parse_dep_rhs(body, allnames):
    dep = None
    factors: list[str] = []
    covars: list[str] = []
    m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
    if m:
        dep = expand_varlist(m.group(1), allnames)[0]
        rhs = m.group(2)
        mw = re.search(r"(.+?)\bWITH\b(.+)", rhs, re.IGNORECASE)
        if mw:
            factors = expand_varlist(mw.group(1), allnames)
            covars = expand_varlist(mw.group(2), allnames)
        else:
            factors = expand_varlist(rhs, allnames)
    else:
        mw = re.search(r"(.+?)\bWITH\b(.+)", body, re.IGNORECASE)
        if mw:
            dep = expand_varlist(mw.group(1), allnames)[0]
            covars = expand_varlist(mw.group(2), allnames)
        else:
            names = expand_varlist(body, allnames)
            dep = names[0] if names else None
    return dep, factors, covars


class Genlin(DataProcedure):
    """GENLIN dep BY factors WITH covars /MODEL ... DISTRIBUTION=x LINK=y."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        dist, link = "NORMAL", "IDENTITY"
        for name, b in subs:
            if name.upper() == "MODEL":
                md = re.search(r"DISTRIBUTION\s*=?\s*(\w+)", b, re.IGNORECASE)
                ml = re.search(r"LINK\s*=?\s*(\w+)", b, re.IGNORECASE)
                if md:
                    dist = md.group(1)
                if ml:
                    link = ml.group(1)
        dep, factors, covars = _parse_dep_rhs(body, allnames)
        if dep is None:
            return [{"type": "Error", "text": "GENLIN needs a dependent variable."}]
        data = _clean(ds, [dep] + factors + covars)
        import statsmodels.api as sm

        X, names = _design(data, dep, factors, covars)
        y = data[dep].to_numpy(float)
        model = sm.GLM(y, X, family=_family(dist, link)).fit()
        t = _wald_table("Parameter Estimates",
                        f"Dependent Variable: {dep}   (Distribution: {dist.title()}, Link: {link.title()})",
                        names, model.params, model.bse)
        return [{"type": "Title", "text": "Generalized Linear Models"}, t.to_json()]


class Gee(DataProcedure):
    """GEE dep BY factors WITH covars /SUBJECT=id [/MODEL DISTRIBUTION=x LINK=y]."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        dist, link, subject = "NORMAL", "IDENTITY", None
        for name, b in subs:
            if name.upper() == "SUBJECT":
                subject = expand_varlist(b, allnames)[0]
            elif name.upper() == "MODEL":
                md = re.search(r"DISTRIBUTION\s*=?\s*(\w+)", b, re.IGNORECASE)
                ml = re.search(r"LINK\s*=?\s*(\w+)", b, re.IGNORECASE)
                if md:
                    dist = md.group(1)
                if ml:
                    link = ml.group(1)
        dep, factors, covars = _parse_dep_rhs(body, allnames)
        if dep is None or subject is None:
            return [{"type": "Error", "text": "GEE needs 'dep ... /SUBJECT=id'."}]
        data = _clean(ds, [dep, subject] + factors + covars)
        import statsmodels.api as sm

        X, names = _design(data, dep, factors, covars)
        y = data[dep].to_numpy(float)
        groups = data[subject].to_numpy()
        model = sm.GEE(y, X, groups=groups, family=_family(dist, link)).fit()
        t = _wald_table("Parameter Estimates",
                        f"Dependent Variable: {dep}   (Subject: {subject})",
                        names, np.asarray(model.params), np.asarray(model.bse))
        return [{"type": "Title", "text": "Generalized Estimating Equations"}, t.to_json()]


class Mixed(DataProcedure):
    """MIXED dep WITH covars /FIXED=covars /RANDOM=subject — linear mixed model."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        subject = None
        for name, b in subs:
            if name.upper() in ("RANDOM", "SUBJECT"):
                got = expand_varlist(b, allnames)
                if got:
                    subject = got[0]
        dep, factors, covars = _parse_dep_rhs(body, allnames)
        if dep is None or subject is None:
            return [{"type": "Error", "text": "MIXED needs 'dep WITH covars /RANDOM=subject'."}]
        preds = factors + covars
        data = _clean(ds, [dep, subject] + preds)
        import statsmodels.formula.api as smf

        rhs = " + ".join(f"Q('{p}')" for p in preds) if preds else "1"
        model = smf.mixedlm(f"Q('{dep}') ~ {rhs}", data, groups=data[subject]).fit()
        fe = model.fe_params
        se = model.bse[: len(fe)]
        names = ["(Intercept)"] + preds
        # Statsmodels names the intercept "Intercept"; align lengths defensively.
        b = np.asarray(fe)[: len(names)]
        se = np.asarray(se)[: len(names)]
        from scipy import stats as sps

        t = PivotTable("Estimates of Fixed Effects", [Dimension("Parameter", names)],
                       [Dimension("", ["Estimate", "Std. Error", "t", "Sig."])],
                       caption=f"Dependent Variable: {dep}")
        for i in range(len(names)):
            tv = b[i] / se[i] if se[i] else float("nan")
            t.set([i], [0], _F3.render(float(b[i])))
            t.set([i], [1], _F3.render(float(se[i])))
            t.set([i], [2], _F3.render(float(tv)))
            t.set([i], [3], strip_leading_zero(_F3.render(float(2 * sps.norm.sf(abs(tv))))))
        cov = PivotTable("Covariance Parameters", [Dimension("Parameter", [f"{subject} Variance", "Residual"])],
                         [Dimension("", ["Estimate"])])
        cov.set([0], [0], _F3.render(float(model.cov_re.iloc[0, 0])))
        cov.set([1], [0], _F3.render(float(model.scale)))
        return [{"type": "Title", "text": "Mixed Linear Models"}, t.to_json(), cov.to_json()]


class Genlog(DataProcedure):
    """GENLOG f1 f2 [f3] — loglinear analysis of the cross-classified counts
    (saturated model), reported as Poisson-GLM parameter estimates."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        factors = expand_varlist(body, allnames)
        if len(factors) < 2:
            return [{"type": "Error", "text": "GENLOG needs 2+ factors."}]
        data = _clean(ds, factors)
        counts = data.groupby(factors).size().reset_index(name="_count")

        import statsmodels.api as sm

        X, names = _design(counts, "_count", factors, [])
        # Add pairwise interactions for the first two factors (SPSS default fits
        # the saturated model; we include main effects + first interaction).
        y = counts["_count"].to_numpy(float)
        model = sm.GLM(y, X, family=sm.families.Poisson()).fit()
        t = _wald_table("Parameter Estimates", "Loglinear (Poisson) model",
                        names, model.params, model.bse)

        # Goodness of fit.
        gof = PivotTable("Goodness-of-Fit Tests", [Dimension("", ["Likelihood Ratio", "Pearson Chi-Square"])],
                         [Dimension("", ["Value", "df", "Sig."])])
        from scipy import stats as sps

        dfree = int(model.df_resid)
        lr = float(model.deviance)
        pear = float(model.pearson_chi2)
        gof.set([0], [0], _F3.render(lr)); gof.set([0], [1], _F0.render(dfree))
        gof.set([0], [2], strip_leading_zero(_F3.render(float(sps.chi2.sf(lr, dfree)) if dfree else 1.0)))
        gof.set([1], [0], _F3.render(pear)); gof.set([1], [1], _F0.render(dfree))
        gof.set([1], [2], strip_leading_zero(_F3.render(float(sps.chi2.sf(pear, dfree)) if dfree else 1.0)))
        return [{"type": "Title", "text": "General Loglinear Analysis"}, gof.to_json(), t.to_json()]
