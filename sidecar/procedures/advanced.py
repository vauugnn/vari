"""Additional Analyze modules to match SPSS's menu: Power Analysis (POWER),
Missing Value Analysis (MVA), Multiple Imputation (MI), Mediation (MEDIATION),
and Meta-Analysis (META)."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure, Procedure, Context
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F1 = Format("F", 8, 1)
_F0 = Format("F", 8, 0)


def _clean(ds: Any, names: list[str]) -> pd.DataFrame:
    frame = {}
    for nm in names:
        s = ds.df[nm]
        frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(frame).dropna()


class PowerAnalysis(Procedure):
    """POWER /TEST=TTEST|ANOVA|CORR /EFFECT=d /ALPHA=a [/N=n | /POWER=p [/GROUPS=k]]
    Solves for power (given N) or required N (given power)."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        from ..syntax.lexer import split_subcommands
        from statsmodels.stats.power import TTestIndPower, FTestAnovaPower

        subs = split_subcommands(rest)
        opts = {}
        for name, b in subs:
            m = re.match(r"\s*(\w+)\s*=?\s*([\d.]+|\w+)", b) if name in ("", "VARIABLES") else None
            if m:
                opts[m.group(1).upper()] = m.group(2)
            u = name.upper()
            mv = re.search(r"([\d.]+|\w+)", b)
            if u in ("TEST", "EFFECT", "ALPHA", "N", "POWER", "GROUPS") and mv:
                opts[u] = mv.group(1)
        test = str(opts.get("TEST", "TTEST")).upper()
        effect = float(opts.get("EFFECT", 0.5))
        alpha = float(opts.get("ALPHA", 0.05))
        k = int(float(opts.get("GROUPS", 2)))
        rows, vals = [], []
        if test == "ANOVA":
            eng = FTestAnovaPower()
            if "N" in opts:
                n = float(opts["N"])
                p = eng.power(effect_size=effect, nobs=n, alpha=alpha, k_groups=k)
                rows, vals = ["Effect size (f)", "Alpha", "Groups", "N", "Power"], [effect, alpha, k, n, p]
            else:
                target = float(opts.get("POWER", 0.8))
                n = eng.solve_power(effect_size=effect, alpha=alpha, power=target, k_groups=k)
                rows, vals = ["Effect size (f)", "Alpha", "Groups", "Power", "N per group"], [effect, alpha, k, target, n]
        else:
            eng = TTestIndPower()
            if "N" in opts:
                n = float(opts["N"])
                p = eng.power(effect_size=effect, nobs1=n, alpha=alpha)
                rows, vals = ["Effect size (d)", "Alpha", "N per group", "Power"], [effect, alpha, n, p]
            else:
                target = float(opts.get("POWER", 0.8))
                n = eng.solve_power(effect_size=effect, alpha=alpha, power=target)
                rows, vals = ["Effect size (d)", "Alpha", "Power", "N per group"], [effect, alpha, target, n]
        t = PivotTable("Power Analysis", [Dimension("", rows)], [Dimension("", ["Value"])])
        for i, v in enumerate(vals):
            t.set([i], [0], _F3.render(float(v)))
        return [{"type": "Title", "text": "Power Analysis"}, t.to_json()]


class MissingValue(DataProcedure):
    """MVA VARIABLES=var list — univariate missing-value summary."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(re.sub(r"^\s*VARIABLES?\s*=?\s*", "", body, flags=re.IGNORECASE), allnames)
        if not names:
            names = allnames
        rows = list(names)
        t = PivotTable("Univariate Statistics", [Dimension("", rows)],
                       [Dimension("", ["N", "Mean", "Missing Count", "Missing Percent"])])
        n_total = ds.n_rows
        for i, nm in enumerate(names):
            s = ds.df[nm]
            mask = missing_mask(s, ds.variables[ds._index_of(nm)]).to_numpy()
            valid = s.where(~mask).dropna()
            miss = n_total - len(valid)
            t.set([i], [0], _F0.render(len(valid)))
            t.set([i], [1], _F3.render(float(valid.astype(float).mean())) if len(valid) and not ds.variables[ds._index_of(nm)].is_string else "")
            t.set([i], [2], _F0.render(miss))
            t.set([i], [3], _F1.render(100.0 * miss / n_total) if n_total else "")
        complete = int(ds.df[names].apply(lambda r: r.notna().all(), axis=1).sum())
        note = {"type": "Notes", "text": f"Complete cases (listwise): {complete} of {n_total}."}
        return [{"type": "Title", "text": "Missing Value Analysis"}, note, t.to_json()]


class MultipleImputation(Procedure):
    """MI VARIABLES=var list — impute missing values (IterativeImputer) into a
    new active dataset."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        from sklearn.experimental import enable_iterative_imputer  # noqa: F401
        from sklearn.impute import IterativeImputer
        from ..data.dataset import Dataset
        from ..syntax.lexer import split_subcommands

        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        body = " ".join(b for name, b in split_subcommands(rest) if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(re.sub(r"^\s*VARIABLES?\s*=?\s*", "", body, flags=re.IGNORECASE), allnames)
        num_names = [n for n in (names or allnames) if not ds.variables[ds._index_of(n)].is_string]
        if not num_names:
            return [{"type": "Error", "text": "MI needs numeric variables."}]
        frames = {}
        before = 0
        for nm in num_names:
            s = ds.df[nm]
            m = missing_mask(s, ds.variables[ds._index_of(nm)]).to_numpy()
            before += int(m.sum() + s.isna().sum())
            frames[nm] = s.where(~m)
        block = pd.DataFrame(frames)
        imp = IterativeImputer(max_iter=10, random_state=0)
        filled = imp.fit_transform(block)
        new_df = ds.df.copy()
        for j, nm in enumerate(num_names):
            new_df[nm] = filled[:, j]
        new = Dataset(new_df, [v.copy() for v in ds.variables], name=ctx.ds_registry.next_name())
        ctx.ds_registry.add(new, activate=True)
        ctx.mark_changed()
        t = PivotTable("Imputation Results", [Dimension("", ["Values imputed", "Variables", "Cases"])],
                       [Dimension("", ["Count"])])
        t.set([0], [0], _F0.render(before))
        t.set([1], [0], _F0.render(len(num_names)))
        t.set([2], [0], _F0.render(new.n_rows))
        return [{"type": "Title", "text": "Multiple Imputation"}, t.to_json()]


class Mediation(DataProcedure):
    """MEDIATION y WITH x MED m — simple mediation (indirect/direct effects)."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        med = None
        for name, b in subs:
            if name.upper() in ("MED", "MEDIATOR"):
                med = expand_varlist(b, allnames)[0]
        m = re.search(r"(\w+)\s+WITH\s+(\w+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "MEDIATION needs 'y WITH x /MED m'."}]
        y, x = m.group(1), m.group(2)
        if med is None:
            mm = re.search(r"\bMED\b\s+(\w+)", body, re.IGNORECASE)
            med = mm.group(1) if mm else None
        if med is None:
            return [{"type": "Error", "text": "MEDIATION needs a /MED mediator."}]
        data = _clean(ds, [y, x, med])
        import statsmodels.api as sm

        # a: x->m ; b,c': m,x->y
        a = sm.OLS(data[med], sm.add_constant(data[[x]])).fit().params.iloc[1]
        ymod = sm.OLS(data[y], sm.add_constant(data[[x, med]])).fit()
        b = ymod.params.loc[med]
        cprime = ymod.params.loc[x]
        total = sm.OLS(data[y], sm.add_constant(data[[x]])).fit().params.iloc[1]
        indirect = a * b
        rows = ["Total effect (c)", "Direct effect (c')", "Indirect effect (a*b)", "a (X→M)", "b (M→Y)"]
        vals = [total, cprime, indirect, a, b]
        t = PivotTable("Mediation Effects", [Dimension("", rows)], [Dimension("", ["Estimate"])],
                       caption=f"{x} → {med} → {y}")
        for i, v in enumerate(vals):
            t.set([i], [0], _F3.render(float(v)))
        return [{"type": "Title", "text": "Mediation Analysis"}, t.to_json()]


class MetaAnalysis(DataProcedure):
    """META EFFECT=es SE=se [/MODEL=FIXED|RANDOM] — inverse-variance pooling."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        allnames = [v.name for v in ds.variables]
        es = se = None
        model = "RANDOM"
        for name, b in subs:
            u = name.upper()
            if u in ("", "VARIABLES"):
                me = re.search(r"EFFECT\s*=?\s*(\w+)", b, re.IGNORECASE)
                ms = re.search(r"SE\s*=?\s*(\w+)", b, re.IGNORECASE)
                if me:
                    es = me.group(1)
                if ms:
                    se = ms.group(1)
            elif u == "EFFECT":
                es = expand_varlist(b, allnames)[0]
            elif u == "SE":
                se = expand_varlist(b, allnames)[0]
            elif u == "MODEL":
                model = b.strip().upper() or "RANDOM"
        if es is None or se is None:
            return [{"type": "Error", "text": "META needs EFFECT=es SE=se."}]
        data = _clean(ds, [es, se])
        y = data[es].to_numpy(float)
        s = data[se].to_numpy(float)
        v = s ** 2
        w = 1.0 / v
        pooled_fixed = float((w * y).sum() / w.sum())
        q = float((w * (y - pooled_fixed) ** 2).sum())
        dfree = len(y) - 1
        c = w.sum() - (w ** 2).sum() / w.sum()
        tau2 = max(0.0, (q - dfree) / c) if c else 0.0
        if model == "FIXED":
            pooled, wv = pooled_fixed, w
        else:
            wv = 1.0 / (v + tau2)
            pooled = float((wv * y).sum() / wv.sum())
        se_pooled = float(np.sqrt(1.0 / wv.sum()))
        i2 = max(0.0, (q - dfree) / q * 100) if q > 0 else 0.0
        rows = ["Pooled effect", "Std. Error", "95% Lower", "95% Upper", "Q", "I² (%)", "Tau²"]
        vals = [pooled, se_pooled, pooled - 1.96 * se_pooled, pooled + 1.96 * se_pooled, q, i2, tau2]
        t = PivotTable(f"Meta-Analysis ({model.title()} Effects)", [Dimension("", rows)],
                       [Dimension("", ["Value"])], caption=f"k = {len(y)} studies")
        for i, val in enumerate(vals):
            t.set([i], [0], _F3.render(float(val)))
        return [{"type": "Title", "text": "Meta-Analysis"}, t.to_json()]
