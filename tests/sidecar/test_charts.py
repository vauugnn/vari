"""Charts: FREQUENCIES chart subcommands and the GRAPH command emit SVG."""
import numpy as np
import pandas as pd

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def make_registry(df):
    variables = [VariableMeta(name=c, print_format=Format("F", 8, 2)) for c in df.columns]
    reg = DatasetRegistry()
    reg.add(Dataset(df.copy(), variables))
    return reg


def run(reg, text):
    return execute_syntax(text, build_registry(), Context(reg))


def test_frequencies_histogram_emits_chart():
    rng = np.random.RandomState(1)
    reg = make_registry(pd.DataFrame({"x": rng.normal(0, 1, 100)}))
    out = run(reg, "FREQUENCIES VARIABLES=x /FORMAT=NOTABLE /HISTOGRAM.")
    charts = [o for o in out if o["type"] == "Chart"]
    assert len(charts) == 1
    assert charts[0]["svg"].startswith("<svg")


def test_frequencies_barchart():
    reg = make_registry(pd.DataFrame({"g": [1.0, 1, 2, 2, 2, 3]}))
    out = run(reg, "FREQUENCIES VARIABLES=g /BARCHART.")
    assert any(o["type"] == "Chart" and "<svg" in o["svg"] for o in out)


def test_graph_scatter():
    rng = np.random.RandomState(2)
    x = rng.normal(0, 1, 50)
    reg = make_registry(pd.DataFrame({"x": x, "y": x + rng.normal(0, 0.5, 50)}))
    out = run(reg, "GRAPH /SCATTERPLOT(BIVAR)=x WITH y.")
    charts = [o for o in out if o["type"] == "Chart"]
    assert len(charts) == 1 and charts[0]["svg"].startswith("<svg")


def test_graph_histogram_and_pie():
    reg = make_registry(pd.DataFrame({"v": [1.0, 2, 2, 3, 3, 3]}))
    assert any(o["type"] == "Chart" for o in run(reg, "GRAPH /HISTOGRAM=v."))
    assert any(o["type"] == "Chart" for o in run(reg, "GRAPH /PIE=v."))
