"""SPSS-clone compute sidecar — Phase 0.

JSON-RPC 2.0 over newline-delimited stdin/stdout. Logs to stderr only.

Implements exactly two methods:
  - ping()            -> {"ok": true}          (readiness probe)
  - syntax.execute    -> list[output object]   (TITLE only; else Error)

This is NOT a real syntax engine. The only command understood is
`TITLE 'string'.` (single- or double-quoted). Anything else returns a single
Error output object. The real lexer/parser lands in Phase 4.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

# TITLE 'text'. / TITLE "text". — optional trailing period, case-insensitive.
_TITLE_RE = re.compile(
    r"""^\s*TITLE\s+(?P<q>['"])(?P<text>.*?)(?P=q)\s*\.?\s*$""",
    re.IGNORECASE | re.DOTALL,
)


def syntax_execute(params: Any) -> list[dict[str, Any]]:
    text = ""
    if isinstance(params, dict):
        text = str(params.get("text", ""))
    elif isinstance(params, str):
        text = params

    stripped = text.strip()
    m = _TITLE_RE.match(stripped)
    if m:
        return [{"type": "Title", "text": m.group("text")}]

    label = stripped if stripped else "(empty)"
    return [{"type": "Error", "text": f"Unrecognized command: {label}"}]


def ping(_params: Any) -> dict[str, Any]:
    return {"ok": True}


METHODS = {
    "ping": ping,
    "syntax.execute": syntax_execute,
}


def dispatch(req: dict[str, Any]) -> dict[str, Any]:
    """Handle one JSON-RPC request object, return the response object."""
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params")
    resp: dict[str, Any] = {"jsonrpc": "2.0", "id": rid}

    fn = METHODS.get(method) if isinstance(method, str) else None
    if fn is None:
        resp["error"] = {"code": -32601, "message": f"Method not found: {method}"}
        return resp
    try:
        resp["result"] = fn(params)
    except Exception as exc:  # noqa: BLE001 — report any failure as JSON-RPC error
        resp["error"] = {"code": -32603, "message": f"{type(exc).__name__}: {exc}"}
    return resp


def main() -> None:
    print("[sidecar] ready", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"[sidecar] bad JSON: {exc}\n")
            sys.stderr.flush()
            continue
        if not isinstance(req, dict):
            continue
        resp = dispatch(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
