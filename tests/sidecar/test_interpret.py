"""The plain-English interpreter (src/renderer/output/interpret.ts) must agree with SciPy.

The renderer code is bundled with esbuild and run under node on real procedure output."""
import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from test_procedures2 import make_registry, run

ROOT = Path(__file__).resolve().parents[2]
ESBUILD = ROOT / "node_modules" / ".bin" / "esbuild"
pytestmark = pytest.mark.skipif(not (shutil.which("node") and ESBUILD.exists()), reason="node/esbuild not available")


def _interpret(tmp_path, tables):
    entry = tmp_path / "entry.ts"
    (tmp_path / "tables.json").write_text(json.dumps(tables))
    entry.write_text(textwrap.dedent(f"""
        import {{ interpret }} from '{ROOT}/src/renderer/output/interpret'
        import * as fs from 'fs'
        const tables = JSON.parse(fs.readFileSync('{tmp_path}/tables.json', 'utf8'))
        console.log(JSON.stringify(tables.map((t: any) => interpret(t))))
    """))
    out = tmp_path / "bundle.cjs"
    subprocess.run([str(ESBUILD), str(entry), "--bundle", "--platform=node", "--format=cjs", f"--outfile={out}", "--log-level=error"], check=True)
    return json.loads(subprocess.run(["node", str(out)], check=True, capture_output=True, text=True).stdout)


def _tables(cmd, df):
    return [o for o in run(make_registry(df), cmd) if o["type"] == "PivotTable"]


def test_interpretations_agree_with_scipy(tmp_path):
    rng = np.random.RandomState(4)
    n = 120
    g = rng.randint(0, 2, n).astype(float)
    x = rng.normal(10, 2, n) + g * 1.2
    y = 0.5 * x + rng.normal(0, 2, n)
    c = rng.randint(1, 4, n).astype(float)
    h = (rng.rand(n) < 0.3 + 0.3 * g).astype(float)
    df = pd.DataFrame({"g": g, "x": x, "y": y, "c": c, "h": h})

    # t-test
    notes = [s for s in _interpret(tmp_path, _tables("T-TEST GROUPS=g(0 1) /VARIABLES=x.", df)) if s]
    t, p = sps.ttest_ind(x[g == 0], x[g == 1])
    assert len(notes) == 1
    assert f"t({n - 2}) = {t:.2f}" in notes[0] and "statistically significant" in notes[0]
    assert ("p < .001" in notes[0]) or (f"p = {p:.3f}".replace("0.", ".") in notes[0])

    # correlation
    note = next(s for s in _interpret(tmp_path, _tables("CORRELATIONS /VARIABLES=x y.", df)) if s)
    r, rp = sps.pearsonr(x, y)
    assert f"r({n - 2}) = {r:.2f}".replace("0.", ".") in note and "positively" in note

    # chi-square
    note = next(s for s in _interpret(tmp_path, _tables("CROSSTABS /TABLES=g BY h /STATISTICS=CHISQ.", df)) if s)
    chi2, cp, dof, _ = sps.chi2_contingency(pd.crosstab(g, h), correction=False)
    assert f"χ²({dof}, N = {n}) = {chi2:.2f}" in note

    # ANOVA
    note = next(s for s in _interpret(tmp_path, _tables("ONEWAY x BY c.", df)) if s)
    f, ap = sps.f_oneway(*[x[c == k] for k in (1, 2, 3)])
    assert f"F(2, {n - 3}) = {f:.2f}" in note


def test_unknown_tables_get_no_interpretation(tmp_path):
    df = pd.DataFrame({"a": [1.0, 2, 3, 4], "b": [1.0, 2, 2, 3]})
    notes = _interpret(tmp_path, _tables("FREQUENCIES VARIABLES=a.", df))
    assert all(s is None for s in notes)


def test_rounding_is_half_away_from_zero(tmp_path):
    """0.155 must print 0.16, not the binary-float 0.15."""
    table = {"type": "PivotTable", "title": "Independent Samples Test", "caption": None, "corner": "",
             "rowDims": [{"label": "", "categories": ["x"]}, {"label": "", "categories": ["Equal variances assumed"]}],
             "colDims": [], "cells": [], "colLeaves": ["F", "Sig.", "t", "df", "Sig. (2-tailed)", "Mean Difference", "Lower", "Upper"],
             "colSpanners": [[{"label": "Levene's Test for Equality of Variances", "span": 2},
                              {"label": "t-test for Equality of Means", "span": 6}]]}
    for i, v in enumerate(["0.300", ".593", "0.155", "118", ".877", "0.01", "-0.14", "0.17"]):
        table["cells"].append({"r": [0, 0], "c": [i], "v": v, "kind": "num"})
    note = _interpret(tmp_path, [table])[0]
    assert "t(118) = 0.16" in note
