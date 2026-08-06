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
      { label: 'Reports', enabled: false, submenu: [proc('Codebook'), proc('OLAP Cubes'), proc('Case Summaries'), proc('Report Summaries in Rows'), proc('Report Summaries in Columns')] },
      {
        label: 'Descriptive Statistics',
        submenu: [
          dialogItem('Frequencies…', 'frequencies', open),
          dialogItem('Descriptives…', 'descriptives', open),
          proc('Explore…'),
          dialogItem('Crosstabs…', 'crosstabs', open),
          proc('TURF Analysis'),
          proc('Ratio…'),
          proc('P-P Plots…'),
          proc('Q-Q Plots…')
        ]
      },
      { label: 'Bayesian Statistics', enabled: false, submenu: [proc('One Sample Normal…'), proc('One Sample Binomial…'), proc('One Sample Poisson…'), proc('Related Sample Normal…'), proc('Independent Sample Normal…')] },
      { label: 'Tables', enabled: false, submenu: [proc('Custom Tables…'), proc('Multiple Response Sets…')] },
      {
        label: 'Compare Means',
        submenu: [
          proc('Means…'),
          dialogItem('One-Sample T Test…', 'ttest-one', open),
          dialogItem('Independent-Samples T Test…', 'ttest-ind', open),
          proc('Summary Independent-Samples T Test…'),
          dialogItem('Paired-Samples T Test…', 'ttest-paired', open),
          proc('One-Way ANOVA…')
        ]
      },
      {
        label: 'General Linear Model',
        submenu: [
          proc('Univariate…'),
          proc('Multivariate…'),
          proc('Repeated Measures…'),
          proc('Variance Components…')
        ]
      },
      { label: 'Generalized Linear Models', enabled: false, submenu: [proc('Generalized Linear Models…'), proc('Generalized Estimating Equations…')] },
      { label: 'Mixed Models', enabled: false, submenu: [proc('Linear…'), proc('Generalized Linear…')] },
      {
        label: 'Correlate',
        submenu: [dialogItem('Bivariate…', 'correlate', open), proc('Partial…'), proc('Distances…'), proc('Canonical Correlation')]
      },
      {
        label: 'Regression',
        submenu: [
          proc('Automatic Linear Modeling…'),
          proc('Linear…'),
          proc('Curve Estimation…'),
          proc('Partial Least Squares…'),
          proc('Binary Logistic…'),
          proc('Multinomial Logistic…'),
          proc('Ordinal…'),
          proc('Probit…'),
          proc('Nonlinear…'),
          proc('Weight Estimation…'),
          proc('2-Stage Least Squares…'),
          proc('Optimal Scaling (CATREG)…')
        ]
      },
      { label: 'Loglinear', enabled: false, submenu: [proc('General…'), proc('Logit…'), proc('Model Selection…')] },
      { label: 'Neural Networks', enabled: false, submenu: [proc('Multilayer Perceptron…'), proc('Radial Basis Function…')] },
      { label: 'Classify', enabled: false, submenu: [proc('TwoStep Cluster…'), proc('K-Means Cluster…'), proc('Hierarchical Cluster…'), proc('Cluster Silhouettes…'), proc('Discriminant…'), proc('Nearest Neighbor…'), proc('ROC Curve…'), proc('ROC Analysis…')] },
      {
        label: 'Dimension Reduction',
        submenu: [proc('Factor…'), proc('Correspondence Analysis…'), proc('Optimal Scaling…')]
      },
      {
        label: 'Scale',
        submenu: [proc('Reliability Analysis…'), proc('Weighted Kappa…'), proc('Multidimensional Unfolding (PREFSCAL)…'), proc('Multidimensional Scaling (PROXSCAL)…'), proc('Multidimensional Scaling (ALSCAL)…')]
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
              proc('Chi-square…'),
              proc('Binomial…'),
              proc('Runs…'),
              proc('1-Sample K-S…'),
              proc('2 Independent Samples…'),
              proc('K Independent Samples…'),
              proc('2 Related Samples…'),
              proc('K Related Samples…')
            ]
          }
        ]
      },
      { label: 'Forecasting', enabled: false, submenu: [proc('Create Traditional Models…'), proc('Create Temporal Causal Models…'), proc('Apply Traditional Models…'), proc('Seasonal Decomposition…'), proc('Spectral Analysis…')] },
      { label: 'Survival', enabled: false, submenu: [proc('Life Tables…'), proc('Kaplan-Meier…'), proc('Cox Regression…'), proc('Cox w/ Time-Dep Cov…')] },
      { label: 'Multiple Response', enabled: false, submenu: [proc('Define Variable Sets…'), proc('Frequencies…'), proc('Crosstabs…')] },
      proc('Simulation…'),
      { label: 'Quality Control', enabled: false, submenu: [proc('Control Charts…'), proc('Pareto Charts…')] },
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
        { role: 'services' },
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
          proc('Syntax'),
          proc('Output'),
          proc('Script…')
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
      proc('Open Database'),
      proc('Import Data'),
      { type: 'separator' },
      proc('Close'),
      { label: 'Save', accelerator: 'CmdOrCtrl+S', click: actions.fileSave },
      { label: 'Save As…', accelerator: 'CmdOrCtrl+Shift+S', click: actions.fileSaveAs },
      proc('Export'),
      { type: 'separator' },
      proc('Print…'),
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
      proc('Find…'),
      proc('Options…')
    ]
  })

  template.push({
    label: 'View',
    submenu: [
      proc('Status Bar'),
      proc('Toolbars'),
      proc('Fonts…'),
      proc('Grid Lines'),
      proc('Value Labels'),
      { type: 'separator' },
      { role: 'reload' },
      { role: 'toggleDevTools' }
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
      proc('Sort Cases…'),
      proc('Sort Variables…'),
      proc('Transpose…'),
      proc('Merge Files'),
      proc('Restructure…'),
      proc('Aggregate…'),
      { type: 'separator' },
      proc('Split File…'),
      proc('Select Cases…'),
      proc('Weight Cases…')
    ]
  })

  template.push({
    label: 'Transform',
    submenu: [
      proc('Compute Variable…'),
      proc('Count Values within Cases…'),
      proc('Shift Values…'),
      proc('Recode into Same Variables…'),
      proc('Recode into Different Variables…'),
      proc('Automatic Recode…'),
      proc('Visual Binning…'),
      proc('Rank Cases…'),
      { type: 'separator' },
      proc('Date and Time Wizard…'),
      proc('Replace Missing Values…'),
      proc('Random Number Generators…'),
      { type: 'separator' },
      proc('Run Pending Transforms')
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
        submenu: [proc('Bar…'), proc('3-D Bar…'), proc('Line…'), proc('Area…'), proc('Pie…'), proc('High-Low…'), proc('Boxplot…'), proc('Error Bar…'), proc('Population Pyramid…'), proc('Scatter/Dot…'), proc('Histogram…')]
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
    submenu: [proc('Topics'), proc('SPSS Statistics Help'), proc('About…')]
  })

  return Menu.buildFromTemplate(template)
}

export function focusOrShow(win: BrowserWindow | null): void {
  if (!win) return
  if (win.isMinimized()) win.restore()
  win.show()
  win.focus()
}
