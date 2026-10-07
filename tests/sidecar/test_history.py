"""Version history: snapshots, dedupe, restore fidelity, diff, retention, recovery."""
import numpy as np
import pandas as pd
import pytest

from sidecar.data.dataset import Dataset
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.history import DAY, HOUR, HistoryError, HistoryStore, diff_states, doc_id_for


def make_ds(values=(1.0, 2.0, 3.0), label="Score"):
    v = VariableMeta(name="x", print_format=Format("F", 8, 2), label=label)
    v.value_labels = {1.0: "one"}
    return Dataset(pd.DataFrame({"x": np.array(values, float)}), [v], name="DataSet1")


@pytest.fixture
def store(tmp_path):
    return HistoryStore(tmp_path / "history")


def test_create_list_and_dedupe(store):
    ds = make_ds()
    v1 = store.create("doc", ds, "FREQ.", [{"type": "Title", "text": "a"}], kind="manual", name="First")
    assert v1["name"] == "First" and v1["rows"] == 3 and v1["bytes"] > 0
    assert store.create("doc", ds, "FREQ.", [{"type": "Title", "text": "a"}], kind="auto") is None  # unchanged
    ds.df.loc[0, "x"] = 99.0
    v2 = store.create("doc", ds, "FREQ.", [{"type": "Title", "text": "a"}], kind="auto")
    assert v2 is not None
    assert [v["id"] for v in store.list("doc")] == [v2["id"], v1["id"]]  # newest first
    # a manual snapshot is always stored, even when nothing changed
    assert store.create("doc", ds, "FREQ.", [{"type": "Title", "text": "a"}], kind="manual") is not None


def test_load_restores_data_variables_syntax_and_output(store):
    ds = make_ds()
    v = store.create("doc", ds, "COMPUTE y=x.", [{"type": "TextBlock", "text": "hi"}], kind="save")
    got = store.load("doc", v["id"])
    pd.testing.assert_frame_equal(got["payload"]["df"], ds.df)
    var = got["payload"]["variables"][0]
    assert var.label == "Score" and var.value_labels == {1.0: "one"} and var.print_format == Format("F", 8, 2)
    assert got["syntax"] == "COMPUTE y=x." and got["output"] == [{"type": "TextBlock", "text": "hi"}]


def test_rename_delete_and_missing_version(store):
    v = store.create("doc", make_ds(), kind="auto")
    assert store.rename("doc", v["id"], "  Final  ")["name"] == "Final"
    store.delete("doc", v["id"])
    assert store.list("doc") == []
    with pytest.raises(HistoryError):
        store.load("doc", v["id"])
    with pytest.raises(HistoryError):
        store.rename("doc", "nope", "x")


def test_invalid_document_ids_are_rejected(store):
    for bad in ("../evil", "a/b", "", "x" * 200):
        with pytest.raises(HistoryError):
            store.list(bad)


def test_diff_reports_what_changed(store):
    a = make_ds()
    va = store.create("doc", a, "A", kind="manual")
    b = make_ds((1.0, 5.0, 3.0), label="Renamed score")
    b.variables.append(VariableMeta(name="z", print_format=Format("F", 8, 0)))
    b.df["z"] = 0.0
    b.variables[0].measure = "nominal"
    vb = store.create("doc", b, "A\nB", [{"type": "Title", "text": "t"}], kind="manual")
    d = store.diff("doc", va["id"], vb["id"])
    assert d["variables"]["added"] == ["z"] and d["variables"]["removed"] == []
    assert {"variable": "x", "field": "label", "from": "Score", "to": "Renamed score"} in d["variables"]["changed"]
    assert d["cells"]["changed"] == 1 and d["cells"]["examples"][0] == {"case": 2, "variable": "x", "from": 2.0, "to": 5.0}
    assert any(line.startswith("+B") for line in d["syntaxDiff"])
    assert d["outputItems"] == {"from": 0, "to": 1} and not d["identical"]
    assert store.diff("doc", va["id"], va["id"])["identical"]


def test_diff_against_current_state(store):
    a = make_ds()
    va = store.create("doc", a, kind="manual")
    cur = {"payload": {"df": make_ds((1.0, 2.0)).df, "variables": make_ds().variables}, "syntax": "", "output": []}
    d = store.diff("doc", va["id"], None, current=cur)
    assert d["rows"] == {"from": 3, "to": 2}


def test_retention_thins_old_autosaves_but_keeps_named_and_saves(store):
    now = 1_000_000_000.0
    ds = make_ds()
    made = {}
    # 12 autosaves, 5 minutes apart, ending 3 hours ago -> all in older-than-1h hourly buckets
    for i in range(12):
        ds.df.loc[0, "x"] = float(i)
        made[i] = store.create("doc", ds, kind="auto", now=now - 3 * HOUR - (11 - i) * 300)
    ds.df.loc[0, "x"] = 100.0
    named = store.create("doc", ds, kind="manual", name="Keep me", now=now - 3 * HOUR - 1000)
    ds.df.loc[0, "x"] = 101.0
    saved = store.create("doc", ds, kind="save", now=now - 40 * DAY)
    ds.df.loc[0, "x"] = 102.0
    recent = [store.create("doc", ds, kind="auto", now=now - 120), None]
    ds.df.loc[0, "x"] = 103.0
    recent[1] = store.create("doc", ds, kind="auto", now=now - 60)
    store.prune("doc", now=now)
    ids = {v["id"] for v in store.list("doc")}
    assert named["id"] in ids and saved["id"] in ids                      # never pruned
    assert recent[0]["id"] in ids and recent[1]["id"] in ids              # last hour: everything
    old_auto = [made[i]["id"] for i in range(12) if made[i]["id"] in ids]
    assert 1 <= len(old_auto) <= 2                                        # 12 autosaves thinned to ~1 per hour


def test_size_cap_drops_oldest_unnamed_first(tmp_path):
    store = HistoryStore(tmp_path / "h", cap_bytes=1)  # absurdly small: only protected versions survive
    ds = make_ds()
    store.create("doc", ds, kind="manual", name="Named", now=1.0)
    ds.df.loc[0, "x"] = 7.0
    store.create("doc", ds, kind="auto", now=2.0)
    kinds = [(v["kind"], v["name"]) for v in store.list("doc")]
    assert ("manual", "Named") in kinds and not any(k == "auto" for k, _ in kinds)


def test_adopt_moves_an_unsaved_documents_history_to_the_file(store):
    ds = make_ds()
    store.create("untitled-abc", ds, kind="manual", name="Draft")
    new_id = doc_id_for("/tmp/some/file.sav")
    store.adopt("untitled-abc", new_id)
    assert store.list("untitled-abc") == []
    assert [v["name"] for v in store.list(new_id)] == ["Draft"]


def test_damaged_index_is_rebuilt_from_snapshots(store, tmp_path):
    ds = make_ds()
    v = store.create("doc", ds, kind="manual", name="N")
    (tmp_path / "history" / "doc" / "index.json").write_text("{not json")
    got = store.list("doc")
    assert [x["id"] for x in got] == [v["id"]] and got[0]["name"] == "N"


def test_corrupt_snapshot_gives_a_clear_error(store, tmp_path):
    v = store.create("doc", make_ds(), kind="manual")
    (tmp_path / "history" / "doc" / f"{v['id']}.vsnap").write_bytes(b"garbage")
    with pytest.raises(HistoryError):
        store.load("doc", v["id"])


def test_doc_ids_are_stable_for_a_path_and_unique_for_unsaved():
    assert doc_id_for("/a/b/data.sav") == doc_id_for("/a/b/data.sav")
    assert doc_id_for("/a/b/data.sav") != doc_id_for("/c/data.sav")
    assert doc_id_for(None) != doc_id_for(None)


# ---- through the JSON-RPC server -------------------------------------------------
def _rpc(method, params=None):
    from sidecar import server

    r = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    assert "error" not in r, r
    return r["result"]


@pytest.fixture
def server_ds(tmp_path, monkeypatch):
    from sidecar import server

    monkeypatch.setenv("VARI_HISTORY_DIR", str(tmp_path / "hist"))
    server._HISTORY = None
    server.REGISTRY = type(server.REGISTRY)()
    server._UNDO.clear()
    server._REDO.clear()
    server._CONTEXT.update(syntax="", output=[])
    ds = make_ds((1.0, 2.0, 3.0, 4.0))
    server.REGISTRY.add(ds)
    yield server
    server._HISTORY = None


def test_restore_returns_data_syntax_and_output_and_is_undoable(server_ds):
    server = server_ds
    _rpc("history.create", {"kind": "manual", "name": "Good", "syntax": "FREQ x.", "output": [{"type": "Title", "text": "T"}]})
    good = _rpc("history.list")["versions"][0]
    server.REGISTRY.active.df.loc[0, "x"] = 10.0                  # an unsaved edit since the last snapshot
    _rpc("syntax.execute", {"text": "SELECT IF (x > 2)."})        # destructive: a pre-op snapshot is taken first
    assert server.REGISTRY.active.n_rows == 3
    kinds = [v["kind"] for v in _rpc("history.list")["versions"]]
    assert "pre-op" in kinds
    out = _rpc("history.restore", {"id": good["id"], "syntax": "SELECT IF (x > 2).", "output": []})
    assert server.REGISTRY.active.n_rows == 4 and server.REGISTRY.active.df["x"].tolist() == [1.0, 2.0, 3.0, 4.0]
    assert out["syntax"] == "FREQ x." and out["output"] == [{"type": "Title", "text": "T"}]
    assert "restore" in [v["kind"] for v in _rpc("history.list")["versions"]]
    _rpc("dataset.undo")                                          # restore can be undone
    assert server.REGISTRY.active.n_rows == 3


def test_diff_against_current_through_the_server(server_ds):
    server = server_ds
    _rpc("history.create", {"kind": "manual", "name": "Before"})
    v = _rpc("history.list")["versions"][0]
    server.REGISTRY.active.df.loc[0, "x"] = 50.0
    d = _rpc("history.diff", {"a": v["id"], "b": "current"})
    assert d["cells"]["changed"] == 1 and not d["identical"]


def test_autosave_is_a_noop_until_something_changes(server_ds):
    server = server_ds
    assert _rpc("history.create", {"kind": "auto"})["version"] is not None
    assert _rpc("history.create", {"kind": "auto"})["version"] is None
    server.REGISTRY.active.df.loc[1, "x"] = 9.0
    assert _rpc("history.create", {"kind": "auto"})["version"] is not None


def test_saving_adopts_history_and_records_a_save_version(server_ds, tmp_path):
    server = server_ds
    _rpc("history.create", {"kind": "manual", "name": "Draft"})
    untitled = _rpc("history.list")["docId"]
    assert untitled.startswith("untitled-")
    _rpc("dataset.save", {"path": str(tmp_path / "mydata.sav")})
    after = _rpc("history.list")
    assert after["docId"].startswith("mydata-")
    names = [v["name"] for v in after["versions"]]
    assert "Draft" in names and "Saved" in names


def test_opening_a_file_records_the_original(server_ds, tmp_path):
    from sidecar.io.files import save_file

    p = str(tmp_path / "orig.sav")
    save_file(make_ds(), p)
    _rpc("dataset.open", {"path": p})
    vs = _rpc("history.list")["versions"]
    assert vs[-1]["kind"] == "open" and vs[-1]["name"] == "Opened file"


def test_recover_finds_the_newest_version_and_opens_it_as_a_new_dataset(server_ds):
    server = server_ds
    assert _rpc("history.recover") == {"found": False}
    _rpc("history.create", {"kind": "auto", "syntax": "SYN", "output": [{"type": "Title", "text": "T"}]})
    server.REGISTRY.active.df.loc[0, "x"] = 77.0
    _rpc("history.create", {"kind": "auto", "syntax": "SYN2"})
    rec = _rpc("history.recover")
    assert rec["found"] and rec["version"]["rows"] == 4
    before = server.REGISTRY.active.name
    out = _rpc("history.openVersion", {"docId": rec["docId"], "id": rec["version"]["id"]})
    assert out["syntax"] == "SYN2" and server.REGISTRY.active.df["x"].tolist()[0] == 77.0
    assert server.REGISTRY.active.name != before and server.REGISTRY.get(before) is not None
