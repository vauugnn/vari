"""Builds the command registry. Classes are registered here (not via module
decorators) to keep imports acyclic."""
from __future__ import annotations

from ..syntax.registry import Registry
from .correlations import Correlations
from .crosstabs import Crosstabs
from .descriptives import Descriptives
from .frequencies import Frequencies
from .nonproc import Get, PivotDemo, Save, Title
from .ttest import TTest


def build_registry() -> Registry:
    reg = Registry()
    reg.register("TITLE")(Title)
    reg.register("GET")(Get)
    reg.register("SAVE")(Save)
    reg.register("PIVOTDEMO")(PivotDemo)
    reg.register("FREQUENCIES")(Frequencies)
    reg.register("DESCRIPTIVES")(Descriptives)
    reg.register("CORRELATIONS")(Correlations)
    reg.register("CROSSTABS")(Crosstabs)
    reg.register("TTEST")(TTest)
    return reg
