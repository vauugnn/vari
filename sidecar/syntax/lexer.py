"""Minimal SPSS command lexing helpers (HLD 8.1).

Not a full tokenizer yet — enough to split a syntax buffer into commands, split
a command into subcommands, and expand variable lists (TO / ALL). The general
recursive-descent parser comes with the wider command registry.
"""
from __future__ import annotations

import re
from typing import Optional


def strip_comments(text: str) -> str:
    # /* ... */ block comments (may span lines)
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)


def _balanced_quotes(s: str) -> bool:
    return s.count("'") % 2 == 0 and s.count('"') % 2 == 0


def split_commands(text: str) -> list[str]:
    """Split a syntax buffer into individual command strings. A command ends at
    a period at end of line, or at a blank line."""
    text = strip_comments(text)
    commands: list[str] = []
    cur: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not cur and stripped.startswith("*"):
            continue  # whole-line comment command
        if stripped == "":
            if cur:
                commands.append("\n".join(cur))
                cur = []
            continue
        cur.append(raw)
        joined = "\n".join(cur)
        if stripped.endswith(".") and _balanced_quotes(joined):
            commands.append(joined)
            cur = []
    if cur:
        commands.append("\n".join(cur))
    out = []
    for c in commands:
        c = c.strip()
        if c.endswith("."):
            c = c[:-1]
        if c.strip():
            out.append(c.strip())
    return out


def command_name(cmd: str) -> tuple[str, str]:
    """Return (NAME, rest). NAME may be two words for commands like GET DATA."""
    # First char may be a digit for commands like 2SLS / 3SLS.
    m = re.match(r"\s*([A-Za-z0-9][A-Za-z-]*)(.*)$", cmd, re.DOTALL)
    if not m:
        return "", ""
    return m.group(1).upper(), m.group(2)


def split_subcommands(rest: str) -> list[tuple[str, str]]:
    """Split the remainder of a command into (SUBNAME, body) pairs on top-level
    '/'. The text before the first '/' is attached to an implicit '' subname."""
    parts = _split_top_level(rest, "/")
    out: list[tuple[str, str]] = []
    for i, part in enumerate(parts):
        part = part.strip()
        if part == "" and i == 0:
            continue
        m = re.match(r"([A-Za-z][A-Za-z0-9-]*)\s*=?\s*(.*)$", part, re.DOTALL)
        if m and (i > 0 or _looks_like_subcommand(m.group(1))):
            out.append((m.group(1).upper(), m.group(2).strip()))
        else:
            out.append(("", part))
    return out


# Subcommand keywords that can appear before the first slash (rare); default:
# leading text is the implicit variable list.
def _looks_like_subcommand(_word: str) -> bool:
    return False


def _split_top_level(s: str, sep: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    quote: Optional[str] = None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def tokenize_values(body: str) -> list[str]:
    """Whitespace/comma separated tokens, respecting quotes and parentheses."""
    tokens = re.findall(r"\"[^\"]*\"|'[^']*'|\([^)]*\)|[^\s,]+", body)
    return [t for t in tokens if t.strip()]


def unquote(tok: str) -> str:
    if len(tok) >= 2 and tok[0] in "'\"" and tok[-1] == tok[0]:
        return tok[1:-1].replace(tok[0] * 2, tok[0])
    return tok


def expand_varlist(body: str, all_names: list[str]) -> list[str]:
    """Expand a variable list: names, ALL, and `a TO b` ranges (by file order).
    Matching is case-insensitive; returned names use the dataset's casing."""
    lower = {n.lower(): n for n in all_names}
    toks = tokenize_values(body)
    out: list[str] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        up = tok.upper()
        if up == "ALL":
            out.extend(all_names)
            i += 1
        elif i + 2 < len(toks) and toks[i + 1].upper() == "TO":
            a, b = tok.lower(), toks[i + 2].lower()
            if a in lower and b in lower:
                ia, ib = all_names.index(lower[a]), all_names.index(lower[b])
                lo, hi = (ia, ib) if ia <= ib else (ib, ia)
                out.extend(all_names[lo : hi + 1])
            i += 3
        else:
            if tok.lower() in lower:
                out.append(lower[tok.lower()])
            else:
                raise ValueError(f"Undefined variable: {tok}")
            i += 1
    return out
