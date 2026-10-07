// Helpers shared by the chart viewer and the Chart Editor.

// Okabe–Ito: a palette designed to stay distinguishable with the common kinds of colour blindness.
export const COLOURBLIND_SAFE = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#CC79A7', '#56B4E9', '#F0E442', '#000000']
export const STANDARD_SWATCHES = ['#4e79c4', '#5aa552', '#d9a441', '#d9433f', '#8c66b5', '#41b2c2', '#6d6e71', '#1192e8']

// A darker shade of a #rrggbb colour, for bar outlines.
export function darken(hex: string, factor = 0.72): string {
  const n = parseInt(hex.slice(1), 16)
  const ch = (shift: number): string =>
    Math.round(((n >> shift) & 255) * factor)
      .toString(16)
      .padStart(2, '0')
  return `#${ch(16)}${ch(8)}${ch(0)}`
}

// Rasterize an SVG string to a base64 PNG (so an edited chart still exports to .spv).
export async function svgToPng(svg: string, scale = 2): Promise<string | null> {
  try {
    const img = new Image()
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
    await img.decode()
    const canvas = document.createElement('canvas')
    canvas.width = img.naturalWidth * scale
    canvas.height = img.naturalHeight * scale
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/png').split(',')[1]
  } catch {
    return null
  }
}

export function base64ToBlob(b64: string, type: string): Blob {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return new Blob([bytes], { type })
}

export async function copyChartImage(svg: string): Promise<boolean> {
  const png = await svgToPng(svg, 3)
  if (!png) return false
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': base64ToBlob(png, 'image/png') })])
  return true
}
