// "Which test should I use?": a short question flow that ends at a recommended test, why it fits,
// what to check first, and how it is written up. Plain data on purpose, so it is easy to review.
// `dialog` is the id of the existing Analyze dialog the result opens.

export interface Option {
  label: string
  hint?: string
  next: string
}

export interface Question {
  kind: 'question'
  text: string
  help?: string
  options: Option[]
}

export interface Result {
  kind: 'result'
  title: string
  dialog: string
  dialogLabel: string
  why: string
  check: string[]
  report: string
  // If the checks fail, this node is the usual fallback.
  fallback?: { label: string; next: string }
}

export type Node = Question | Result

export const ROOT = 'root'

export const NODES: Record<string, Node> = {
  root: {
    kind: 'question',
    text: 'What do you want to find out?',
    options: [
      { label: 'Whether groups are different', hint: 'e.g. do boys and girls score differently?', next: 'groups' },
      { label: 'Whether two things are related', hint: 'e.g. does study time go with grades?', next: 'relate' },
      { label: 'How well I can predict something', hint: 'e.g. predict grades from study time', next: 'predict' },
      { label: 'What my data looks like', hint: 'counts, averages, spread', next: 'describe' }
    ]
  },

  // ---- comparing groups ----
  groups: {
    kind: 'question',
    text: 'What kind of measurement is the outcome you are comparing?',
    options: [
      { label: 'A number', hint: 'score, height, income, age', next: 'g-scale' },
      { label: 'A category', hint: 'yes/no, type, passed/failed', next: 'g-cat' },
      { label: 'A rank or rating', hint: 'agree–disagree scale, 1st/2nd/3rd, or numbers that are very skewed', next: 'g-rank' }
    ]
  },
  'g-scale': {
    kind: 'question',
    text: 'How are the groups set up?',
    options: [
      { label: 'One group, compared with a known value', next: 'r-ttest-one' },
      { label: 'Two separate groups of people', hint: 'e.g. boys vs girls', next: 'r-ttest-ind' },
      { label: 'The same people measured twice', hint: 'before and after', next: 'r-ttest-paired' },
      { label: 'Three or more separate groups', hint: 'e.g. grade 7, 8 and 9', next: 'r-anova' },
      { label: 'The same people measured three or more times', next: 'r-rm' }
    ]
  },
  'g-cat': {
    kind: 'question',
    text: 'What is the design?',
    options: [
      { label: 'Two categorical variables', hint: 'e.g. gender and passed/failed', next: 'r-chisq' },
      { label: 'One categorical variable against expected proportions', hint: 'e.g. is the split really 50/50?', next: 'r-chisq-gof' },
      { label: 'The same people, yes/no before and after', next: 'r-mcnemar' }
    ]
  },
  'g-rank': {
    kind: 'question',
    text: 'How are the groups set up?',
    options: [
      { label: 'Two separate groups', next: 'r-mannwhitney' },
      { label: 'The same people measured twice', next: 'r-wilcoxon' },
      { label: 'Three or more separate groups', next: 'r-kruskal' },
      { label: 'The same people measured three or more times', next: 'r-friedman' }
    ]
  },

  // ---- relationships ----
  relate: {
    kind: 'question',
    text: 'What kind of variables are they?',
    options: [
      { label: 'Both are numbers', hint: 'study hours and test score', next: 'r-pearson' },
      { label: 'Ranks, or numbers with outliers / heavy skew', next: 'r-spearman' },
      { label: 'Both are categories', hint: 'gender and yes/no', next: 'r-chisq' }
    ]
  },

  // ---- prediction ----
  predict: {
    kind: 'question',
    text: 'What are you trying to predict?',
    options: [
      { label: 'A number', hint: 'a score, an amount', next: 'r-linreg' },
      { label: 'A yes/no outcome', next: 'r-logit' },
      { label: 'A category with three or more options', next: 'r-multinom' },
      { label: 'An ordered rating', hint: 'low / medium / high', next: 'r-ordinal' }
    ]
  },

  // ---- describing ----
  describe: {
    kind: 'question',
    text: 'What do you want to describe?',
    options: [
      { label: 'A category: how many fall in each', next: 'r-freq' },
      { label: 'A number: average and spread', next: 'r-desc' },
      { label: 'A number: its shape, outliers and normality', next: 'r-explore' }
    ]
  },

  // ---- results ----
  'r-ttest-one': {
    kind: 'result',
    title: 'One-sample t test',
    dialog: 'ttest-one',
    dialogLabel: 'One-Sample T Test',
    why: 'You have one group and want to know whether its average differs from a value you already know (a norm, a target, a population figure).',
    check: ['The outcome is a number.', 'The scores are roughly normal, or you have about 30 or more cases.', 'Cases are independent of each other.'],
    report: 't(df) = …, p = …, with the mean and the test value.',
    fallback: { label: 'Scores are very skewed with few cases', next: 'r-wilcoxon' }
  },
  'r-ttest-ind': {
    kind: 'result',
    title: 'Independent-samples t test',
    dialog: 'ttest-ind',
    dialogLabel: 'Independent-Samples T Test',
    why: 'You are comparing the average of a number between two separate groups.',
    check: [
      'The outcome is a number and the groups do not overlap (nobody is in both).',
      'Scores are roughly normal in each group, or each group has about 30 or more cases.',
      "Equal spread in both groups: Levene's test is in the output, and the table gives a row for each case."
    ],
    report: 'Report the group means and SDs, then t(df) = …, p = …, and the mean difference with its 95% confidence interval.',
    fallback: { label: 'Not normal and the groups are small', next: 'r-mannwhitney' }
  },
  'r-ttest-paired': {
    kind: 'result',
    title: 'Paired-samples t test',
    dialog: 'ttest-paired',
    dialogLabel: 'Paired-Samples T Test',
    why: 'The same people (or matched pairs) were measured twice, and you want to know whether the average changed.',
    check: ['Each person has both measurements.', 'The differences between the two measurements are roughly normal, or you have about 30 or more pairs.'],
    report: 't(df) = …, p = …, with the mean difference and its 95% confidence interval.',
    fallback: { label: 'Differences are not normal and pairs are few', next: 'r-wilcoxon' }
  },
  'r-anova': {
    kind: 'result',
    title: 'One-way ANOVA',
    dialog: 'oneway',
    dialogLabel: 'One-Way ANOVA',
    why: 'You are comparing the average of a number across three or more separate groups. Running several t tests would raise the chance of a false positive; ANOVA tests them together.',
    check: [
      'The outcome is a number and each person is in exactly one group.',
      'Scores are roughly normal in each group, or groups are fairly large.',
      "Similar spread in each group (Levene's test is available under Options).",
      'If the result is significant, add a post hoc test (Tukey) to see which groups differ.'
    ],
    report: 'F(df between, df within) = …, p = …, plus which groups differ from the post hoc test.',
    fallback: { label: 'Not normal or very unequal spread', next: 'r-kruskal' }
  },
  'r-rm': {
    kind: 'result',
    title: 'Repeated-measures ANOVA',
    dialog: 'glm-repeated',
    dialogLabel: 'Repeated Measures',
    why: 'The same people were measured three or more times (for example week 1, 2 and 3) and you want to know whether the average changes.',
    check: ['Everyone has every measurement.', 'Sphericity: use the corrected result (Greenhouse–Geisser) if it is violated.'],
    report: 'F(df, df error) = …, p = …, stating which correction was used.',
    fallback: { label: 'Ordinal data or not normal', next: 'r-friedman' }
  },
  'r-chisq': {
    kind: 'result',
    title: 'Chi-square test of independence',
    dialog: 'crosstabs',
    dialogLabel: 'Crosstabs',
    why: 'You want to know whether two categorical variables are related, for example whether passing depends on gender.',
    check: [
      'Both variables are categories and each person falls in one cell.',
      'Expected counts: at least 5 in most cells. The output footnote tells you; with small tables use Fisher’s exact test.',
      'In Crosstabs, tick Chi-square under Statistics and Column percentages under Cells.'
    ],
    report: 'χ²(df, N = …) = …, p = …, and the percentages that show the pattern.'
  },
  'r-chisq-gof': {
    kind: 'result',
    title: 'Chi-square goodness of fit',
    dialog: 'npar-chisquare',
    dialogLabel: 'Chi-square',
    why: 'One categorical variable, and you want to know whether the counts match expected proportions (equal, or ones you specify).',
    check: ['Each case is counted once.', 'Expected count of at least 5 in each category.'],
    report: 'χ²(df, N = …) = …, p = ….'
  },
  'r-mcnemar': {
    kind: 'result',
    title: 'McNemar test',
    dialog: 'npar-2related',
    dialogLabel: '2 Related Samples',
    why: 'The same people answered yes/no twice (for example before and after), and you want to know whether the share of “yes” changed.',
    check: ['Both variables are two-category and measured on the same people.', 'Choose McNemar in the test type list.'],
    report: 'The McNemar test p value, with the counts that changed in each direction.'
  },
  'r-mannwhitney': {
    kind: 'result',
    title: 'Mann–Whitney U test',
    dialog: 'npar-2indep',
    dialogLabel: '2 Independent Samples',
    why: 'Two separate groups, and the outcome is a rank or is not close to normal. It compares the overall ordering of scores rather than the means.',
    check: ['The groups are separate.', 'The outcome can be ordered.', 'Choose Mann–Whitney U in the test type list.'],
    report: 'U = …, z = …, p = …, with the median of each group.'
  },
  'r-wilcoxon': {
    kind: 'result',
    title: 'Wilcoxon signed-rank test',
    dialog: 'npar-2related',
    dialogLabel: '2 Related Samples',
    why: 'The same people measured twice, and the differences are ranks or not close to normal.',
    check: ['Each person has both measurements.', 'Choose Wilcoxon in the test type list.'],
    report: 'z = …, p = …, with the median of each measurement.'
  },
  'r-kruskal': {
    kind: 'result',
    title: 'Kruskal–Wallis test',
    dialog: 'npar-kindep',
    dialogLabel: 'K Independent Samples',
    why: 'Three or more separate groups, and the outcome is a rank or not close to normal. The rank-based counterpart of one-way ANOVA.',
    check: ['Groups are separate.', 'If significant, follow with pairwise comparisons.'],
    report: 'H(df) = …, p = ….'
  },
  'r-friedman': {
    kind: 'result',
    title: 'Friedman test',
    dialog: 'npar-krelated',
    dialogLabel: 'K Related Samples',
    why: 'The same people measured three or more times, and the outcome is a rank or not close to normal.',
    check: ['Everyone has every measurement.'],
    report: 'χ²(df) = …, p = ….'
  },
  'r-pearson': {
    kind: 'result',
    title: 'Pearson correlation',
    dialog: 'correlate',
    dialogLabel: 'Bivariate Correlations',
    why: 'Both variables are numbers and you want to know how strongly and in which direction they move together.',
    check: [
      'Draw a scatterplot first (Graphs): the pattern should be roughly a straight line.',
      'No extreme outliers; both variables roughly normal.',
      'Correlation is not causation.'
    ],
    report: 'r(df) = …, p = …; as a rough guide .1 small, .3 medium, .5 large.',
    fallback: { label: 'Outliers or a curved pattern', next: 'r-spearman' }
  },
  'r-spearman': {
    kind: 'result',
    title: 'Spearman rank correlation',
    dialog: 'correlate',
    dialogLabel: 'Bivariate Correlations',
    why: 'Ranks, or numbers with outliers or heavy skew. It measures whether the variables rise together, not whether the line is straight.',
    check: ['In the dialog, tick Spearman under Correlation Coefficients.', 'The relationship should be consistently increasing or decreasing.'],
    report: 'rₛ(df) = …, p = ….'
  },
  'r-linreg': {
    kind: 'result',
    title: 'Linear regression',
    dialog: 'regression',
    dialogLabel: 'Linear Regression',
    why: 'You want to predict a number from one or more other variables, and see how much each contributes.',
    check: [
      'The outcome is a number.',
      'Plot the residuals (Plots) to check the pattern is linear and the spread is even.',
      'Predictors should not be near-copies of each other (ask for collinearity statistics).',
      'Roughly 10 or more cases per predictor.'
    ],
    report: 'R², F(df, df) = …, p = …, and for each predictor B, β, t and p.'
  },
  'r-logit': {
    kind: 'result',
    title: 'Binary logistic regression',
    dialog: 'logistic',
    dialogLabel: 'Binary Logistic',
    why: 'The outcome is two categories (yes/no, passed/failed) and you want to know which variables predict it.',
    check: ['The outcome has exactly two categories.', 'Enough cases in the smaller category (about 10 per predictor).', 'Predictors not near-copies of each other.'],
    report: 'For each predictor: B, Wald, p and the odds ratio Exp(B) with its 95% interval.'
  },
  'r-multinom': {
    kind: 'result',
    title: 'Multinomial logistic regression',
    dialog: 'multinomial',
    dialogLabel: 'Multinomial Logistic',
    why: 'The outcome is a category with three or more options and you want to know which variables predict it.',
    check: ['Choose a reference category.', 'Enough cases in every category.'],
    report: 'For each predictor and category: B, p and the odds ratio.'
  },
  'r-ordinal': {
    kind: 'result',
    title: 'Ordinal regression',
    dialog: 'ordinal',
    dialogLabel: 'Ordinal Regression',
    why: 'The outcome is an ordered rating (low / medium / high) and you want to know which variables predict it.',
    check: ['The outcome has a clear order.', 'Check the test of parallel lines in the output.'],
    report: 'For each predictor: estimate, p and the odds ratio.'
  },
  'r-freq': {
    kind: 'result',
    title: 'Frequencies',
    dialog: 'frequencies',
    dialogLabel: 'Frequencies',
    why: 'A count and percentage for each category, with an optional bar or pie chart.',
    check: ['Look at the Missing row so you know how many answers are absent.'],
    report: 'n and % for each category.'
  },
  'r-desc': {
    kind: 'result',
    title: 'Descriptive statistics',
    dialog: 'descriptives',
    dialogLabel: 'Descriptives',
    why: 'The mean, standard deviation, minimum and maximum of a number.',
    check: ['If the data are skewed or have outliers, report the median and range instead (use Frequencies or Explore).'],
    report: 'M = …, SD = …, range …–….'
  },
  'r-explore': {
    kind: 'result',
    title: 'Explore',
    dialog: 'explore',
    dialogLabel: 'Explore',
    why: 'A fuller picture of a number: shape, outliers, and tests of normality, optionally split by group.',
    check: ['Under Plots, tick Normality plots with tests.', 'Shapiro–Wilk is more reliable than Kolmogorov–Smirnov for small samples.'],
    report: 'Mean or median with spread, and whether normality holds.'
  }
}
