"""Recursive-descent parser for SPSS expressions (HLD 7.1 precedence).

Produces a small AST of tuples. Precedence, lowest to highest:
  OR < AND < NOT < comparisons < +,- < *,/ < unary- < ** < ()
"""
from __future__ import annotations

from typing import Any

from .lexer import Token, tokenize, unquote

Node = tuple


class Parser:
    def __init__(self, tokens: list[Token]):
        self.toks = tokens
        self.i = 0

    def peek(self) -> Token | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self) -> Token:
        t = self.toks[self.i]
        self.i += 1
        return t

    def accept(self, kind: str, value: str | None = None) -> Token | None:
        t = self.peek()
        if t and t.kind == kind and (value is None or t.value == value):
            return self.next()
        return None

    # ---- grammar ----
    def parse(self) -> Node:
        node = self.parse_or()
        if self.peek() is not None:
            raise ValueError(f"Unexpected token: {self.peek().value}")
        return node

    def parse_or(self) -> Node:
        node = self.parse_and()
        while self.accept("or"):
            node = ("or", node, self.parse_and())
        return node

    def parse_and(self) -> Node:
        node = self.parse_not()
        while self.accept("and"):
            node = ("and", node, self.parse_not())
        return node

    def parse_not(self) -> Node:
        if self.accept("not"):
            return ("not", self.parse_not())
        return self.parse_cmp()

    def parse_cmp(self) -> Node:
        node = self.parse_add()
        t = self.peek()
        while t and t.kind == "op" and t.value in ("<", ">", "<=", ">=", "=", "~="):
            self.next()
            node = ("bin", t.value, node, self.parse_add())
            t = self.peek()
        return node

    def parse_add(self) -> Node:
        node = self.parse_mul()
        t = self.peek()
        while t and t.kind == "op" and t.value in ("+", "-"):
            self.next()
            node = ("bin", t.value, node, self.parse_mul())
            t = self.peek()
        return node

    def parse_mul(self) -> Node:
        node = self.parse_unary()
        t = self.peek()
        while t and t.kind == "op" and t.value in ("*", "/"):
            self.next()
            node = ("bin", t.value, node, self.parse_unary())
            t = self.peek()
        return node

    def parse_unary(self) -> Node:
        if self.accept("op", "-"):
            return ("neg", self.parse_unary())
        if self.accept("op", "+"):
            return self.parse_unary()
        return self.parse_pow()

    def parse_pow(self) -> Node:
        node = self.parse_primary()
        if self.accept("op", "**"):
            return ("bin", "**", node, self.parse_unary())
        return node

    def parse_primary(self) -> Node:
        t = self.peek()
        if t is None:
            raise ValueError("Unexpected end of expression.")
        if t.kind == "number":
            self.next()
            return ("num", float(t.value))
        if t.kind == "string":
            self.next()
            return ("str", unquote(t.value) or "")
        if t.kind == "lparen":
            self.next()
            node = self.parse_or()
            if not self.accept("rparen"):
                raise ValueError("Expected ')'.")
            return node
        if t.kind == "name":
            self.next()
            if self.accept("lparen"):
                args = self.parse_args()
                if not self.accept("rparen"):
                    raise ValueError("Expected ')'.")
                return ("call", t.value.upper(), args)
            return ("var", t.value)
        raise ValueError(f"Unexpected token: {t.value}")

    def parse_args(self) -> list[Node]:
        args: list[Node] = []
        if self.peek() and self.peek().kind == "rparen":
            return args
        while True:
            node = self.parse_or()
            if self.accept("to"):
                hi = self.parse_or()
                node = ("range", node, hi)
            args.append(node)
            if not self.accept("comma"):
                break
        return args


def parse_expression(text: str) -> Node:
    return Parser(tokenize(text)).parse()
