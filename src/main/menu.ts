import { Menu, MenuItemConstructorOptions, app, BrowserWindow } from 'electron'

/**
 * Full SPSS menu bar (PHASE-0 section 2). Top-level order and labels match
 * SPSS exactly. The Analyze submenu is fully populated with leaf items, all
 * disabled — later phases enable items rather than restructuring the tree.
 *
 * Everything not wired yet is a stub that logs.
 */

export interface MenuActions {
  showWindow: (name: 'dataeditor' | 'viewer' | 'syntax') => void
  fileNew: () => void
  fileOpen: () => void
  fileSave: () => void
  fileSaveAs: () => void
  filePrint: () => void
  fileImport: () => void
  checkUpdates: () => void
  newScript: () => void
  viewToggle: (kind: string) => void
  execSyntax: (text: string) => void
  showAbout: () => void
  openDialog: (id: string) => void
}

function stub(label: string): () => void {
  return () => console.log(`[menu] stub: ${label}`)
}

// A leaf procedure item: present but disabled until its phase lands.
function proc(label: string): MenuItemConstructorOptions {
  return { label, enabled: false, click: stub(label) }
}

function dialogItem(label: string, id: string, open: (id: string) => void): MenuItemConstructorOptions {
  return { label, click: () => open(id) }
}

function analyzeSubmenu(open: (id: string) => void): MenuItemConstructorOptions {
  return {
    label: 'Analyze',
    submenu: [
      { label: 'Reports', submenu: [dialogItem('Codebook', 'codebook', open), dialogItem('OLAP Cubes', 'olap', open), dialogItem('Case Summaries', 'summarize', open), proc('Report Summaries in Rows'), proc('Report Summaries in Columns')] },
      {
        label: 'Descriptive Statistics',
        submenu: [
          dialogItem('Frequencies…', 'frequencies', open),
          dialogItem('Descriptives…', 'descriptives', open),
          dialogItem('Explore…', 'explore', open),
          dialogItem('Crosstabs…', 'crosstabs', open),
          proc('TURF Analysis'),
          dialogItem('Ratio…', 'ratio', open),
          dialogItem('P-P Plots…', 'ppplot', open),
          dialogItem('Q-Q Plots…', 'qqplot', open)
        ]
      },
      { label: 'Bayesian Statistics', submenu: [dialogItem('One Sample Normal…', 'bayes-normal', open), dialogItem('One Sample Binomial…', 'bayes-binomial', open), dialogItem('One Sample Poisson…', 'bayes-poisson', open), proc('Related Sample Normal…'), proc('Independent Sample Normal…')] },
      { label: 'Tables', submenu: [dialogItem('Custom Tables…', 'ctables', open), proc('Multiple Response Sets…')] },
      {
        label: 'Compare Means',
        submenu: [
          dialogItem('Means…', 'means', open),
          dialogItem('One-Sample T Test…', 'ttest-one', open),
          dialogItem('Independent-Samples T Test…', 'ttest-ind', open),
          proc('Summary Independent-Samples T Test…'),
          dialogItem('Paired-Samples T Test…', 'ttest-paired', open),
          dialogItem('One-Way ANOVA…', 'oneway', open)
        ]
      },
      {
        label: 'General Linear Model',
        submenu: [
          dialogItem('Univariate…', 'univariate', open),
          dialogItem('Multivariate…', 'multivariate-glm', open),
          dialogItem('Repeated Measures…', 'glm-repeated', open),
          dialogItem('Variance Components…', 'varcomp', open)
        ]
      },
      { label: 'Generalized Linear Models', submenu: [dialogItem('Generalized Linear Models…', 'genlin', open), dialogItem('Generalized Estimating Equations…', 'gee', open)] },
      { label: 'Mixed Models', submenu: [dialogItem('Linear…', 'mixed', open), dialogItem('Generalized Linear…', 'gee', open)] },
      {
        label: 'Correlate',
        submenu: [dialogItem('Bivariate…', 'correlate', open), dialogItem('Partial…', 'partial', open), dialogItem('Distances…', 'distances', open), dialogItem('Canonical Correlation', 'cancorr', open)]
      },
      {
        label: 'Regression',
        submenu: [
          proc('Automatic Linear Modeling…'),
          dialogItem('Linear…', 'regression', open),
          dialogItem('Curve Estimation…', 'curvefit', open),
          dialogItem('Partial Least Squares…', 'pls', open),
          dialogItem('Binary Logistic…', 'logistic', open),
          dialogItem('Multinomial Logistic…', 'multinomial', open),
          dialogItem('Ordinal…', 'ordinal', open),
          dialogItem('Probit…', 'probit', open),
          proc('Nonlinear…'),
          proc('Weight Estimation…'),
          dialogItem('2-Stage Least Squares…', 'tsls', open),
          proc('Optimal Scaling (CATREG)…')
        ]
      },
      { label: 'Loglinear', submenu: [dialogItem('General…', 'genlog', open), dialogItem('Logit…', 'genlog', open), proc('Model Selection…')] },
      { label: 'Neural Networks', submenu: [dialogItem('Multilayer Perceptron…', 'mlp', open), dialogItem('Radial Basis Function…', 'rbf', open)] },
      {
        label: 'Classify',
        submenu: [
          dialogItem('TwoStep Cluster…', 'twostep', open),
          dialogItem('K-Means Cluster…', 'kmeans', open),
          dialogItem('Hierarchical Cluster…', 'hierarchical', open),
          proc('Cluster Silhouettes…'),
          dialogItem('Discriminant…', 'discriminant', open),
          dialogItem('Nearest Neighbor…', 'knn', open),
          dialogItem('ROC Curve…', 'roc', open),
          proc('ROC Analysis…')
        ]
      },
      {
        label: 'Dimension Reduction',
        submenu: [dialogItem('Factor…', 'factor', open), dialogItem('Correspondence Analysis…', 'correspondence', open), proc('Optimal Scaling…')]
      },
      {
        label: 'Scale',
        submenu: [dialogItem('Reliability Analysis…', 'reliability', open), dialogItem('Weighted Kappa…', 'kappa', open), dialogItem('Multidimensional Unfolding (PREFSCAL)…', 'prefscal', open), dialogItem('Multidimensional Scaling (PROXSCAL)…', 'proxscal', open), dialogItem('Multidimensional Scaling (ALSCAL)…', 'alscal', open)]
      },
      {
        label: 'Nonparametric Tests',
        submenu: [
          proc('One Sample…'),
          proc('Independent Samples…'),
          proc('Related Samples…'),
          {
            label: 'Legacy Dialogs',
            submenu: [
              dialogItem('Chi-square…', 'npar-chisquare', open),
              dialogItem('Binomial…', 'npar-binomial', open),
              dialogItem('Runs…', 'npar-runs', open),
              dialogItem('1-Sample K-S…', 'npar-ks', open),
              dialogItem('2 Independent Samples…', 'npar-2indep', open),
              dialogItem('K Independent Samples…', 'npar-kindep', open),
              dialogItem('2 Related Samples…', 'npar-2related', open),
              dialogItem('K Related Samples…', 'npar-krelated', open)
            ]
          }
        ]
      },
      { label: 'Forecasting', submenu: [dialogItem('Create Traditional Models…', 'arima', open), proc('Create Temporal Causal Models…'), proc('Apply Traditional Models…'), dialogItem('Seasonal Decomposition…', 'season', open), dialogItem('Spectral Analysis…', 'spectra', open)] },
      { label: 'Survival', submenu: [dialogItem('Life Tables…', 'lifetable', open), dialogItem('Kaplan-Meier…', 'km', open), dialogItem('Cox Regression…', 'coxreg', open), proc('Cox w/ Time-Dep Cov…')] },
      { label: 'Multiple Response', submenu: [proc('Define Variable Sets…'), dialogItem('Frequencies…', 'multiresponse', open), proc('Crosstabs…')] },
      { label: 'Complex Samples', submenu: [dialogItem('Descriptives…', 'csdescr', open), dialogItem('Crosstabs…', 'cstab', open)] },
      proc('Simulation…'),
      { label: 'Quality Control', submenu: [dialogItem('Control Charts…', 'spchart', open), dialogItem('Pareto Charts…', 'pareto', open)] },
      proc('Spatial and Temporal Modeling…')
    ]
  }
}

export function buildMenu(actions: MenuActions): Menu {
  const { showWindow } = actions
  const isMac = process.platform === 'darwin'

  const template: MenuItemConstructorOptions[] = []

  if (isMac) {
    template.push({
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    })
  }

  template.push({
    label: 'File',
    submenu: [
      {
        label: 'New',
        submenu: [
          { label: 'Data', accelerator: 'CmdOrCtrl+N', click: actions.fileNew },
          { label: 'Syntax', click: () => actions.showWindow('syntax') },
          { label: 'Output', click: () => actions.showWindow('viewer') },
          { label: 'Script…', click: actions.newScript }
        ]
      },
      {
        label: 'Open',
        submenu: [
          { label: 'Data…', accelerator: 'CmdOrCtrl+O', click: actions.fileOpen },
          proc('Syntax…'),
          proc('Output…'),
          proc('Script…')
        ]
      },
      { label: 'Open Database', submenu: [{ label: 'New Query…', click: () => actions.openDialog('opendb') }] },
      {
        label: 'Import Data',
        submenu: [
          { label: 'CSV Data…', click: actions.fileImport },
          { label: 'Text Data…', click: actions.fileImport }
        ]
      },
      { type: 'separator' },
      { label: 'Close', role: 'close' },
      { label: 'Save', accelerator: 'CmdOrCtrl+S', click: actions.fileSave },
      { label: 'Save As…', accelerator: 'CmdOrCtrl+Shift+S', click: actions.fileSaveAs },
      proc('Export'),
      { type: 'separator' },
      { label: 'Print…', accelerator: 'CmdOrCtrl+P', click: actions.filePrint },
      { type: 'separator' },
      isMac ? { role: 'close' } : { role: 'quit', label: 'Exit' }
    ]
  })

  template.push({
    label: 'Edit',
    submenu: [
      { role: 'undo' },
      { role: 'redo' },
      { type: 'separator' },
      { role: 'cut' },
      { role: 'copy' },
      { role: 'paste' },
      { role: 'selectAll' },
      { type: 'separator' },
      dialogItem('Find…', 'find', actions.openDialog),
      dialogItem('Go to Case…', 'gotocase', actions.openDialog),
      dialogItem('Go to Variable…', 'gotovar', actions.openDialog),
      { type: 'separator' },
      proc('Options…')
    ]
  })

  template.push({
    label: 'View',
    submenu: [
      { label: 'Status Bar', click: () => actions.viewToggle('statusbar') },
      {
        label: 'Toolbars',
        submenu: [{ label: 'Customize…', click: () => actions.openDialog('customize-toolbar') }]
      },
      proc('Fonts…'),
      { label: 'Grid Lines', click: () => actions.viewToggle('gridlines') },
      { label: 'Value Labels', click: () => actions.viewToggle('valuelabels') },
      // Dev-only affordances: never expose Reload / DevTools in a packaged build.
      ...(app.isPackaged
        ? []
        : [
            { type: 'separator' } as MenuItemConstructorOptions,
            { role: 'reload' } as MenuItemConstructorOptions,
            { role: 'toggleDevTools' } as MenuItemConstructorOptions
          ])
    ]
  })

  template.push({
    label: 'Data',
    submenu: [
      proc('Define Variable Properties…'),
      proc('Copy Data Properties…'),
      proc('Define Dates…'),
      proc('Define Multiple Response Sets…'),
      { type: 'separator' },
      dialogItem('Sort Cases…', 'sort', actions.openDialog),
      proc('Sort Variables…'),
      dialogItem('Transpose…', 'transpose', actions.openDialog),
      {
        label: 'Merge Files',
        submenu: [
          dialogItem('Add Cases…', 'add-cases', actions.openDialog),
          dialogItem('Add Variables…', 'add-variables', actions.openDialog)
        ]
      },
      {
        label: 'Restructure',
        submenu: [
          dialogItem('Variables to Cases…', 'varstocases', actions.openDialog),
          dialogItem('Cases to Variables…', 'casestovars', actions.openDialog)
        ]
      },
      dialogItem('Aggregate…', 'aggregate', actions.openDialog),
      { type: 'separator' },
      dialogItem('Split File…', 'splitfile', actions.openDialog),
      dialogItem('Select Cases…', 'selectcases', actions.openDialog),
      dialogItem('Weight Cases…', 'weight', actions.openDialog)
    ]
  })

  template.push({
    label: 'Transform',
    submenu: [
      dialogItem('Compute Variable…', 'compute', actions.openDialog),
      dialogItem('Count Values within Cases…', 'count', actions.openDialog),
      dialogItem('Shift Values…', 'shift-values', actions.openDialog),
      dialogItem('Recode into Same Variables…', 'recode-same', actions.openDialog),
      dialogItem('Recode into Different Variables…', 'recode-different', actions.openDialog),
      dialogItem('Automatic Recode…', 'autorecode', actions.openDialog),
      dialogItem('Visual Binning…', 'visualbin', actions.openDialog),
      dialogItem('Rank Cases…', 'rank', actions.openDialog),
      { type: 'separator' },
      proc('Date and Time Wizard…'),
      dialogItem('Replace Missing Values…', 'rmv', actions.openDialog),
      dialogItem('Random Number Generators…', 'random-seed', actions.openDialog),
      { type: 'separator' },
      { label: 'Run Pending Transforms', accelerator: 'CmdOrCtrl+G', click: () => actions.execSyntax('EXECUTE.') }
    ]
  })

  template.push(analyzeSubmenu(actions.openDialog))

  template.push({
    label: 'Graphs',
    submenu: [
      proc('Chart Builder…'),
      proc('Graphboard Template Chooser…'),
      proc('Weibull Plot…'),
      proc('Compare Subgroups'),
      proc('Regression Variable Plots'),
      {
        label: 'Legacy Dialogs',
        submenu: [
          dialogItem('Bar…', 'graph-bar', actions.openDialog),
          dialogItem('3-D Bar…', 'graph-bar3d', actions.openDialog),
          dialogItem('Line…', 'graph-line', actions.openDialog),
          dialogItem('Area…', 'graph-area', actions.openDialog),
          dialogItem('Pie…', 'graph-pie', actions.openDialog),
          dialogItem('High-Low…', 'graph-highlow', actions.openDialog),
          dialogItem('Boxplot…', 'graph-boxplot', actions.openDialog),
          dialogItem('Error Bar…', 'graph-errorbar', actions.openDialog),
          dialogItem('Population Pyramid…', 'graph-pyramid', actions.openDialog),
          dialogItem('Scatter/Dot…', 'graph-scatter', actions.openDialog),
          dialogItem('Histogram…', 'graph-histogram', actions.openDialog)
        ]
      }
    ]
  })

  template.push({
    label: 'Utilities',
    submenu: [
      proc('Variables…'),
      proc('OMS Control Panel…'),
      proc('OMS Identifiers…'),
      proc('Scoring Wizard…'),
      proc('Merge Model XML…'),
      proc('Data File Comments…'),
      proc('Define Variable Sets…'),
      proc('Use Variable Sets…'),
      proc('Show All Variables'),
      { type: 'separator' },
      { label: 'Run Script…', click: actions.newScript },
      proc('Custom Dialog Builder…')
    ]
  })

  template.push({
    label: 'Extensions',
    submenu: [proc('Extension Hub…'), proc('Install Local Extension Bundle…'), proc('Create Extension Bundle…'), proc('Utilities')]
  })

  template.push({
    label: 'Window',
    submenu: [
      { label: 'Data Editor', click: () => showWindow('dataeditor') },
      { label: 'Output Viewer', click: () => showWindow('viewer') },
      { label: 'Syntax Editor', click: () => showWindow('syntax') },
      { type: 'separator' },
      { role: 'minimize' },
      ...(isMac ? [{ role: 'zoom' } as MenuItemConstructorOptions, { type: 'separator' } as MenuItemConstructorOptions, { role: 'front' } as MenuItemConstructorOptions] : [])
    ]
  })

  template.push({
    label: 'Help',
    submenu: [
      proc('Topics'),
      proc('SPSS Statistics Help'),
      { type: 'separator' },
      { label: 'Check for Updates…', click: actions.checkUpdates },
      { label: 'About…', click: actions.showAbout }
    ]
  })

  return Menu.buildFromTemplate(template)
}

export function focusOrShow(win: BrowserWindow | null): void {
  if (!win) return
  if (win.isMinimized()) win.restore()
  win.show()
  win.focus()
}
