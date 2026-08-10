"""Builds the command registry. Classes are registered here (not via module
decorators) to keep imports acyclic."""
from __future__ import annotations

from ..syntax.registry import Registry
from .cluster import Cluster, QuickCluster
from .correlations import Correlations
from .crosstabs import Crosstabs
from .curvefit import CurveFit
from .discriminant import Discriminant
from .misc_procs import Kappa, Pplot, RatioStats
from .reports import Codebook, Summarize
from .roc import Roc
from .data_ops import Filter, SelectIf, SortCases, SplitFile, UseCommand, Weight
from .data_ops2 import AddCmd, Aggregate, Flip, MatchFiles
from .descriptives import Descriptives
from .examine import Examine
from .factor import Factor
from .glm import Unianova
from .logistic import LogisticRegression, Nomreg, Plum
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
from .transforms import AutoRecode, Compute, Count, Create, Execute, If, Rank, Recode, Rmv, SetCmd
from .multivariate import CanCorr, Manova, Proximities
from .regression2 import GlmRepeated, Pls, Probit, Tsls, Varcomp
from .glm3 import Gee, Genlin, Genlog, Mixed
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
    reg.register("CREATE")(Create)
    reg.register("SET")(SetCmd)
    reg.register("GLM")(Manova)
    reg.register("PROXIMITIES")(Proximities)
    reg.register("CANCORR")(CanCorr)
    reg.register("PROBIT")(Probit)
    reg.register("PLS")(Pls)
    reg.register("2SLS")(Tsls)
    reg.register("VARCOMP")(Varcomp)
    reg.register("GLMRM")(GlmRepeated)
    reg.register("GENLIN")(Genlin)
    reg.register("GEE")(Gee)
    reg.register("MIXED")(Mixed)
    reg.register("GENLOG")(Genlog)
    reg.register("VARIABLE")(VariableCmd)
    reg.register("VALUE")(ValueLabels)
    reg.register("ADD")(lambda: ValueLabels(add=True))
    reg.register("MISSING")(MissingValues)
    reg.register("RENAME")(RenameVariables)
    reg.register("ADD")(AddCmd)
    reg.register("FORMATS")(Formats)
    reg.register("AGGREGATE")(Aggregate)
    reg.register("FLIP")(Flip)
    reg.register("MATCH")(MatchFiles)
    reg.register("UNIANOVA")(Unianova)
    reg.register("FACTOR")(Factor)
    reg.register("LOGISTIC")(LogisticRegression)
    reg.register("NOMREG")(Nomreg)
    reg.register("PLUM")(Plum)
    reg.register("QUICK")(QuickCluster)
    reg.register("CLUSTER")(Cluster)
    reg.register("DISCRIMINANT")(Discriminant)
    reg.register("ROC")(Roc)
    reg.register("CURVEFIT")(CurveFit)
    reg.register("SUMMARIZE")(Summarize)
    reg.register("CODEBOOK")(Codebook)
    reg.register("PPLOT")(Pplot)
    reg.register("RATIO")(RatioStats)
    reg.register("KAPPA")(Kappa)
    return reg
