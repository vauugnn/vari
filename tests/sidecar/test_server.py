"""Phase 0 sidecar tests: ping + syntax.execute round trip via dispatch()."""
from sidecar.server import dispatch, syntax_execute


def test_ping():
    resp = dispatch({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}})
    assert resp["id"] == 1
    assert resp["result"] == {"ok": True}
    assert "error" not in resp


def test_title_single_quote():
    resp = dispatch(
        {"jsonrpc": "2.0", "id": 2, "method": "syntax.execute",
         "params": {"text": "TITLE 'hello'."}}
    )
    assert resp["result"] == [{"type": "Title", "text": "hello"}]


def test_title_double_quote_no_period():
    assert syntax_execute({"text": 'TITLE "world"'}) == [
        {"type": "Title", "text": "world"}
    ]


def test_title_case_insensitive():
    assert syntax_execute({"text": "title 'Case'."}) == [
        {"type": "Title", "text": "Case"}
    ]


def test_unrecognized_returns_error():
    out = syntax_execute({"text": "BOGUSCMD x."})
    assert len(out) == 1
    assert out[0]["type"] == "Error"
    assert "BOGUSCMD" in out[0]["text"]


def test_frequencies_without_dataset_errors():
    out = syntax_execute({"text": "FREQUENCIES VARIABLES=x."})
    assert out[0]["type"] == "Error"


def test_empty_yields_no_output():
    assert syntax_execute({"text": "   "}) == []


def test_unknown_method():
    resp = dispatch({"jsonrpc": "2.0", "id": 9, "method": "nope", "params": {}})
    assert resp["error"]["code"] == -32601
