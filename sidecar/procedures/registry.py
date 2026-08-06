"""Builds the command registry. Classes are registered here (not via module
decorators) to keep imports acyclic."""
from __future__ import annotations

from ..syntax.registry import Registry
from .correlations import Correlations
from .crosstabs import Crosstabs
from .data_ops import Filter, SelectIf, SortCases, SplitFile, UseCommand, Weight
from .descriptives import Descriptives
from .examine import Examine
from .metadata import Formats, MissingValues, RenameVariables, ValueLabels, VariableCmd
from .partial import PartialCorr
from .frequencies import Frequencies
from .graph import Graph
from .means import Means
from .nonparcorr import NonparCorr
from .nonproc import Get, PivotDemo, Save, Title
from .npar import NparTests
from .oneway import Oneway
from .regression import Regression
from .reliability import Reliability
from .transforms import AutoRecode, Compute, Count, Execute, If, Rank, Recode, Rmv
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
    reg.register("ONEWAY")(Oneway)
    reg.register("RELIABILITY")(Reliability)
    reg.register("REGRESSION")(Regression)
    reg.register("MEANS")(Means)
    reg.register("NONPAR")(NonparCorr)
    reg.register("NPAR")(NparTests)
    reg.register("COMPUTE")(Compute)
    reg.register("IF")(If)
    reg.register("RECODE")(Recode)
    reg.register("COUNT")(Count)
    reg.register("EXECUTE")(Execute)
    reg.register("GRAPH")(Graph)
    reg.register("SORT")(SortCases)
    reg.register("SELECT")(SelectIf)
    reg.register("FILTER")(Filter)
    reg.register("WEIGHT")(Weight)
    reg.register("SPLIT")(SplitFile)
    reg.register("USE")(UseCommand)
    reg.register("EXAMINE")(Examine)
    reg.register("PARTIAL")(PartialCorr)
    reg.register("RANK")(Rank)
    reg.register("AUTORECODE")(AutoRecode)
    reg.register("RMV")(Rmv)
    reg.register("VARIABLE")(VariableCmd)
    reg.register("VALUE")(ValueLabels)
    reg.register("ADD")(lambda: ValueLabels(add=True))
    reg.register("MISSING")(MissingValues)
    reg.register("RENAME")(RenameVariables)
    reg.register("FORMATS")(Formats)
    return reg
