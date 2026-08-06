"""Tokenizer for the SPSS expression language (HLD 7)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Multi-char operators first so they win over single-char.
_TOKEN_RE = re.compile(
    r"""
    \s+
  | (?P<number>\d+\.\d+(?:[eE][+-]?\d+)?|\.\d+|\d+(?:[eE][+-]?\d+)?)
  | (?P<string>'[^']*'|"[^"]*")
  | (?P<op>\*\*|<=|>=|~=|<>|=|<|>|\+|-|\*|/|&|\||~)
  | (?P<lparen>\()
  | (?P<rparen>\))
  | (?P<comma>,)
  | (?P<name>[A-Za-z@#$][A-Za-z0-9@#$._]*)
    """,
    re.VERBOSE,
)

# Word forms of operators/keywords.
_WORD_OPS = {"EQ": "=", "NE": "~=", "LT": "<", "GT": ">", "LE": "<=", "GE": ">=",
             "AND": "AND", "OR": "OR", "NOT": "NOT"}


@dataclass
class Token:
    kind: str  # number, string, op, name, func, lparen, rparen, comma, and, or, not, to
    value: str


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"Unexpected character at {pos}: {text[pos:pos+10]!r}")
        pos = m.end()
        if m.lastgroup is None:
            continue  # whitespace
        kind = m.lastgroup
        val = m.group()
        if kind == "name":
            up = val.upper()
            if up in _WORD_OPS:
                mapped = _WORD_OPS[up]
                if mapped in ("AND", "OR", "NOT"):
                    tokens.append(Token(mapped.lower(), mapped))
                else:
                    tokens.append(Token("op", mapped))
            elif up == "TO":
                tokens.append(Token("to", "TO"))
            else:
                tokens.append(Token("name", val))
        elif kind == "op":
            tokens.append(Token("op", "~=" if val == "<>" else val))
        else:
            tokens.append(Token(kind, val))
    return tokens


def peek_is_lparen(tokens: list[Token], i: int) -> bool:
    return i < len(tokens) and tokens[i].kind == "lparen"


def unquote(s: str) -> Optional[str]:
    if len(s) >= 2 and s[0] in "'\"" and s[-1] == s[0]:
        return s[1:-1].replace(s[0] * 2, s[0])
    return None
