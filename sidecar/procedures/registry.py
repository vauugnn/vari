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
from .nonproc import DatasetName, Display, Get, PivotDemo, Save, Title
from .npar import NparTests
from .oneway import Oneway
from .regression import Regression
from .reliability import Reliability
from .transforms import AutoRecode, Compute, Count, Create, Execute, If, Rank, Recode, Rmv, SetCmd
from .multivariate import CanCorr, Manova, Proximities
from .regression2 import GlmRepeated, Pls, Probit, Tsls, Varcomp
from .glm3 import Gee, Genlin, Genlog, Mixed
from .survival import CoxReg, KaplanMeier, LifeTable
from .forecasting import Arima, Season, Spectra
from .complex_samples import CsDescriptives, CsTabulate
from .classify2 import NearestNeighbor, TwoStep
from .dimension import Alscal, Correspondence, Mds
from .neural import Mlp, Rbf
from .reports2 import Ctables, MultResponse, Olap
from .qc import Pareto, SpChart
from .bayesian import Bayes
from .dataops3 import CasesToVars, VarsToCases, VisualBin
from .advanced import MetaAnalysis, Mediation, MissingValue, MultipleImputation, PowerAnalysis
from .ttest import TTest


def build_registry() -> Registry:
    reg = Registry()
    reg.register("TITLE")(Title)
    reg.register("GET")(Get)
    reg.register("SAVE")(Save)
    reg.register("DISPLAY")(Display)
    reg.register("DATASET")(DatasetName)
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
    reg.register("KM")(KaplanMeier)
    reg.register("COXREG")(CoxReg)
    reg.register("SURVIVAL")(LifeTable)
    reg.register("TSMODEL")(Arima)
    reg.register("SEASON")(Season)
    reg.register("SPECTRA")(Spectra)
    reg.register("CSDESCRIPTIVES")(CsDescriptives)
    reg.register("CSTABULATE")(CsTabulate)
    reg.register("TWOSTEP")(TwoStep)
    reg.register("KNN")(NearestNeighbor)
    reg.register("CORRESPONDENCE")(Correspondence)
    reg.register("PROXSCAL")(Mds)
    reg.register("ALSCAL")(Alscal)
    reg.register("PREFSCAL")(Alscal)
    reg.register("MLP")(Mlp)
    reg.register("RBF")(Rbf)
    reg.register("OLAP")(Olap)
    reg.register("CTABLES")(Ctables)
    reg.register("MULTRESPONSE")(MultResponse)
    reg.register("SPCHART")(SpChart)
    reg.register("PARETO")(Pareto)
    reg.register("BAYES")(Bayes)
    reg.register("VARSTOCASES")(VarsToCases)
    reg.register("CASESTOVARS")(CasesToVars)
    reg.register("VBIN")(VisualBin)
    reg.register("POWER")(PowerAnalysis)
    reg.register("MVA")(MissingValue)
    reg.register("MI")(MultipleImputation)
    reg.register("MEDIATION")(Mediation)
    reg.register("META")(MetaAnalysis)
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
