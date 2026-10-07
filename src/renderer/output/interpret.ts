import type { PivotTableJson } from './PivotTable'
import { pivotToText } from './apa'

// Plain-English reading of a test table. Rule-based on purpose: every number in the sentence is
// copied from the table, so it cannot disagree with it. Returns null for tables it does not know.
// Wording follows APA 7 (italic symbols are plain here; no leading zero on p and r).

const ALPHA = 0.05

const num = (s: string | undefined): number => {
  const v = parseFloat((s ?? '').replace(/[*,]/g, '').trim())
  return Number.isFinite(v) ? v : NaN
}
// Round half away from zero (as SPSS does); toFixed rounds the binary value, so 0.155 would give 0.15.
const fix = (x: number, d = 2): string => {
  if (!Number.isFinite(x)) return '?'
  const k = 10 ** d
  return ((x < 0 ? -1 : 1) * (Math.round(Math.abs(x) * k + 1e-9) / k)).toFixed(d)
}
const noZero = (s: string): string => s.replace(/^(-?)0\./, '$1.')
const dfText = (x: number): string => (Number.isInteger(x) ? String(x) : fix(x, 2))

export const pText = (p: number): string => (!Number.isFinite(p) ? 'p = ?' : p < 0.001 ? 'p < .001' : `p = ${noZero(fix(p, 3))}`)
const rText = (r: number): string => noZero(fix(r, 2))
const alpha = `α = ${noZero(String(ALPHA))}`

function colIndex(row: string[], label: string): number {
  return row.findIndex((c) => c.trim() === label)
}

export function interpret(t: PivotTableJson): string | null {
  let text
  try {
    text = pivotToText(t)
  } catch {
    return null
  }
  const { head, body } = text
  if (body.length === 0 || head.length === 0) return null
  const leaf = head[head.length - 1]
  const flatHead = head.flat().join(' ')
  return (
    tTest(leaf, body, flatHead) ??
    anova(leaf, body) ??
    chiSquare(leaf, body) ??
    correlations(head, body) ??
    null
  )
}

// ---- t tests (independent, one-sample, paired) ----
function tTest(leaf: string[], body: string[][], flatHead: string): string | null {
  const iT = colIndex(leaf, 't')
  const iDf = colIndex(leaf, 'df')
  const iSig = leaf.findIndex((c) => c.trim() === 'Sig. (2-tailed)')
  if (iT < 0 || iDf < 0 || iSig < 0) return null
  const iDiff = Math.max(colIndex(leaf, 'Mean Difference'), colIndex(leaf, 'Mean'))
  const iLo = colIndex(leaf, 'Lower')
  const iHi = colIndex(leaf, 'Upper')
  const independent = /Levene/.test(flatHead)

  const dep = body.map((r) => r[0]).find((c) => c.trim()) ?? 'the outcome'
  let row = body[0]
  let note = ''
  if (independent) {
    const iLev = leaf.findIndex((c) => c.trim() === 'Sig.')
    const assumed = body.find((r) => /assumed/i.test(r[1]) && !/not/i.test(r[1])) ?? body[0]
    const notAssumed = body.find((r) => /not assumed/i.test(r[1])) ?? assumed
    const levene = num(assumed[iLev])
    const equal = !(levene < ALPHA)
    row = equal ? assumed : notAssumed
    note = Number.isFinite(levene)
      ? ` Levene's test was ${equal ? 'not significant' : 'significant'} (${pText(levene)}), so equal variances ${equal ? 'were' : 'were not'} assumed.`
      : ''
  }
  const tv = num(row[iT])
  const df = num(row[iDf])
  const p = num(row[iSig])
  const diff = iDiff >= 0 ? num(row[iDiff]) : NaN
  const ci = iLo >= 0 && iHi >= 0 ? ` 95% CI [${fix(num(row[iLo]), 2)}, ${fix(num(row[iHi]), 2)}]` : ''
  const kind = independent ? 'An independent-samples t-test' : flatHead.includes('Paired') || /Pair/.test(body[0]?.[0] ?? '') ? 'A paired-samples t-test' : 'A one-sample t-test'
  const diffText = Number.isFinite(diff) ? `; mean difference = ${fix(diff, 2)},${ci}` : ''
  return (
    `${kind} on ${dep} found ${p < ALPHA ? 'a statistically significant' : 'no statistically significant'} difference (${alpha}): ` +
    `t(${dfText(df)}) = ${fix(tv, 2)}, ${pText(p)}${diffText}.${note}`
  )
}

// ---- one-way ANOVA and regression ANOVA ----
function anova(leaf: string[], body: string[][]): string | null {
  const iF = colIndex(leaf, 'F')
  const iSig = colIndex(leaf, 'Sig.')
  const iDf = colIndex(leaf, 'df')
  if (iF < 0 || iSig < 0 || iDf < 0 || colIndex(leaf, 'Sum of Squares') < 0) return null
  const effect = body.find((r) => /Between Groups|Regression/i.test(r[0]) || /Between Groups|Regression/i.test(r[1] ?? ''))
  const error = body.find((r) => /Within Groups|Residual/i.test(r[0]) || /Within Groups|Residual/i.test(r[1] ?? ''))
  if (!effect || !error) return null
  const f = num(effect[iF])
  const p = num(effect[iSig])
  const reg = /Regression/i.test(effect.join(' '))
  const lead = reg ? 'The regression model' : 'A one-way ANOVA'
  const claim = reg
    ? `${p < ALPHA ? 'predicts' : 'does not significantly predict'} the outcome`
    : `found ${p < ALPHA ? 'a significant' : 'no significant'} difference among the group means`
  return `${lead} ${claim}: F(${dfText(num(effect[iDf]))}, ${dfText(num(error[iDf]))}) = ${fix(f, 2)}, ${pText(p)}.`
}

// ---- chi-square test of association ----
function chiSquare(leaf: string[], body: string[][]): string | null {
  const iVal = colIndex(leaf, 'Value')
  const iDf = colIndex(leaf, 'df')
  const iSig = leaf.findIndex((c) => /Asymptotic Significance|Asymp\. Sig/i.test(c))
  const row = body.find((r) => /Pearson Chi-Square/i.test(r.join(' ')))
  if (iVal < 0 || iDf < 0 || iSig < 0 || !row) return null
  const n = num(body.find((r) => /N of Valid Cases/i.test(r.join(' ')))?.[iVal])
  const p = num(row[iSig])
  const nText = Number.isFinite(n) ? `, N = ${n}` : ''
  return (
    `A chi-square test of independence found ${p < ALPHA ? 'a significant' : 'no significant'} association between the variables: ` +
    `χ²(${dfText(num(row[iDf]))}${nText}) = ${fix(num(row[iVal]), 2)}, ${pText(p)}.`
  )
}

// ---- Pearson correlations ----
function correlations(head: string[][], body: string[][]): string | null {
  const names = head[head.length - 1].slice(2)
  const firstRowLabel = body.find((r) => /Pearson Correlation/i.test(r[1]))
  if (!firstRowLabel || names.length < 2) return null
  const lines: string[] = []
  const rowOf = (i: number, label: RegExp): string[] | undefined => {
    const start = body.findIndex((r) => /Pearson Correlation/i.test(r[1]))
    const blocks = body.slice(start).reduce<string[][][]>((acc, r) => {
      if (/Pearson Correlation/i.test(r[1])) acc.push([])
      acc[acc.length - 1].push(r)
      return acc
    }, [])
    return blocks[i]?.find((r) => label.test(r[1]))
  }
  for (let i = 0; i < names.length; i++) {
    for (let j = i + 1; j < names.length; j++) {
      const r = num(rowOf(i, /Pearson Correlation/i)?.[2 + j])
      const p = num(rowOf(i, /Sig\./i)?.[2 + j])
      const n = num(rowOf(i, /^N$/)?.[2 + j])
      if (!Number.isFinite(r)) continue
      const size = Math.abs(r) < 0.1 ? 'negligible' : Math.abs(r) < 0.3 ? 'small' : Math.abs(r) < 0.5 ? 'medium' : 'large'
      const dir = r > 0 ? 'positively' : r < 0 ? 'negatively' : 'not'
      const df = Number.isFinite(n) ? `(${n - 2})` : ''
      lines.push(
        p < ALPHA
          ? `${names[i]} and ${names[j]} were ${dir} correlated, r${df} = ${rText(r)}, ${pText(p)} (a ${size} effect).`
          : `${names[i]} and ${names[j]} were not significantly correlated, r${df} = ${rText(r)}, ${pText(p)}.`
      )
    }
  }
  return lines.length ? lines.join(' ') : null
}
