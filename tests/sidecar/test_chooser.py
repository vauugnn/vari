"""The test-chooser decision tree (src/renderer/dialogs/testChooser.ts) must be sound."""
import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ESBUILD = ROOT / "node_modules" / ".bin" / "esbuild"
pytestmark = pytest.mark.skipif(not (shutil.which("node") and ESBUILD.exists()), reason="node/esbuild not available")


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
    d = tmp_path_factory.mktemp("chooser")
    (d / "entry.ts").write_text(textwrap.dedent(f"""
        import {{ NODES, ROOT }} from '{ROOT}/src/renderer/dialogs/testChooser'
        console.log(JSON.stringify({{ NODES, ROOT }}))
    """))
    subprocess.run([str(ESBUILD), str(d / "entry.ts"), "--bundle", "--platform=node", "--format=cjs",
                    f"--outfile={d / 'b.cjs'}", "--log-level=error"], check=True)
    return json.loads(subprocess.run(["node", str(d / "b.cjs")], check=True, capture_output=True, text=True).stdout)


def test_every_link_resolves_and_every_node_is_reachable(tree):
    nodes, root = tree["NODES"], tree["ROOT"]
    seen, stack = set(), [root]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        assert n in nodes, f"dangling link to {n!r}"
        seen.add(n)
        node = nodes[n]
        if node["kind"] == "question":
            stack += [o["next"] for o in node["options"]]
        elif node.get("fallback"):
            stack.append(node["fallback"]["next"])
    assert seen == set(nodes), f"unreachable nodes: {set(nodes) - seen}"


def test_questions_always_lead_toward_a_result_without_cycles(tree):
    nodes = tree["NODES"]

    def depth(n, path):
        assert n not in path, f"cycle through {n!r}"
        node = nodes[n]
        if node["kind"] == "result":
            return 1
        return 1 + max(depth(o["next"], path | {n}) for o in node["options"])

    assert 2 <= depth(tree["ROOT"], frozenset()) <= 5  # a handful of questions, never a maze


def test_questions_and_results_are_complete(tree):
    for key, node in tree["NODES"].items():
        if node["kind"] == "question":
            assert len(node["options"]) >= 2 and node["text"].endswith("?"), key
            assert all(o["label"].strip() for o in node["options"]), key
        else:
            assert node["title"] and node["why"] and node["report"] and node["check"], key


def test_every_result_opens_a_dialog_that_exists(tree):
    src = (ROOT / "src/renderer/dataeditor/DataEditor.tsx").read_text()
    known = set(re.findall(r"case '([\w-]+)':", src))
    for key, node in tree["NODES"].items():
        if node["kind"] == "result":
            assert node["dialog"] in known, f"{key} opens unknown dialog {node['dialog']!r}"
