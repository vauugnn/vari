import type { SpssApi } from '../shared/types'

declare global {
  interface Window {
    spss: SpssApi
  }
}

export {}
