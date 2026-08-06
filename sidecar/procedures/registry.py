"""Builds the command registry. Classes are registered here (not via module
decorators) to keep imports acyclic."""
from __future__ import annotations

from ..syntax.registry import Registry
from .descriptives import Descriptives
from .frequencies import Frequencies
from .nonproc import Get, PivotDemo, Save, Title


def build_registry() -> Registry:
    reg = Registry()
    reg.register("TITLE")(Title)
    reg.register("GET")(Get)
    reg.register("SAVE")(Save)
    reg.register("PIVOTDEMO")(PivotDemo)
    reg.register("FREQUENCIES")(Frequencies)
    reg.register("DESCRIPTIVES")(Descriptives)
    return reg
