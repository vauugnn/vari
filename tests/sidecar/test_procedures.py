"""FREQUENCIES and DESCRIPTIVES through the full syntax pipeline (PHASE 4/6).

User-missing values must be excluded from statistics but reported as Missing in
the frequency table (HLD 3.3)."""
from sidecar.server import dispatch


def run(method, params=None):
    resp = dispatch({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    assert "error" not in resp, resp.get("error")
    return resp["result"]


def cellmap(table):
    return {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in table["cells"]}


def rowidx(table, label):
    return table["rowDims"][0]["categories"].index(label)


def test_descriptives_excludes_missing(sav_path):
    run("dataset.open", {"path": sav_path})
    res = run("syntax.execute", {"text": "DESCRIPTIVES VARIABLES=income."})
    t = [o for o in res if o["type"] == "PivotTable"][0]
    assert t["title"] == "Descriptive Statistics"
    assert t["colDims"][0]["categories"] == ["N", "Minimum", "Maximum", "Mean", "Std. Deviation"]
    c = cellmap(t)
    # income = [50000, 60000, 999999(missing), 45000] -> valid [50000,60000,45000]
    assert c[((0,), (0,))] == "3"       # N
    assert c[((0,), (1,))] == "45000"   # Minimum
    assert c[((0,), (2,))] == "60000"   # Maximum
    assert c[((0,), (3,))] == "51666.67"  # Mean (2 dp)


def test_descriptives_abbreviation_and_default_stats(sav_path):
    run("dataset.open", {"path": sav_path})
    res = run("syntax.execute", {"text": "DESC income agree."})  # DESC -> DESCRIPTIVES
    t = [o for o in res if o["type"] == "PivotTable"][0]
    assert t["rowDims"][0]["categories"] == ["income", "agree", "Valid N (listwise)"]


def test_frequencies_statistics_and_table(sav_path):
    run("dataset.open", {"path": sav_path})
    res = run("syntax.execute", {"text": "FREQUENCIES VARIABLES=gender /STATISTICS=MEAN."})
    tables = [o for o in res if o["type"] == "PivotTable"]
    stats_t = tables[0]
    assert stats_t["title"] == "Statistics"
    sc = cellmap(stats_t)
    # gender = [1,2,1,9(missing)] -> valid 3, missing 1
    assert sc[((0,), (0,))] == "3"   # Valid
    assert sc[((1,), (0,))] == "1"   # Missing

    freq_t = tables[1]
    fc = cellmap(freq_t)
    male = rowidx(freq_t, "Male")
    female = rowidx(freq_t, "Female")
    assert fc[((male,), (0,))] == "2"      # Frequency of Male
    assert fc[((male,), (1,))] == "50.0"   # Percent (of 4)
    assert fc[((male,), (2,))] == "66.7"   # Valid Percent (of 3)
    assert fc[((female,), (2,))] == "33.3"


def test_frequencies_missing_row_present(sav_path):
    run("dataset.open", {"path": sav_path})
    res = run("syntax.execute", {"text": "FREQ gender."})  # FREQ -> FREQUENCIES
    freq_t = [o for o in res if o["type"] == "PivotTable"][1]
    cats = freq_t["rowDims"][0]["categories"]
    assert "No answer" in cats   # the user-missing code 9 shown as its label
    assert cats.count("Total") == 2  # valid subtotal + grand total
