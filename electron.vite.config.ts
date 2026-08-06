import { resolve } from 'path'
import { defineConfig } from 'electron-vite'
import react from '@vitejs/plugin-react'

// Three renderer windows (Data Editor, Output Viewer, Syntax Editor) as
// separate HTML entries. Main + preload build to out/{main,preload}.
export default defineConfig({
  main: {
    build: {
      outDir: 'out/main',
      rollupOptions: { input: resolve(__dirname, 'src/main/index.ts') }
    }
  },
  preload: {
    build: {
      outDir: 'out/preload',
      rollupOptions: { input: resolve(__dirname, 'src/preload/index.ts') }
    }
  },
  renderer: {
    root: resolve(__dirname, 'src/renderer'),
    plugins: [react()],
    build: {
      outDir: 'out/renderer',
      rollupOptions: {
        input: {
          dataeditor: resolve(__dirname, 'src/renderer/dataeditor/index.html'),
          viewer: resolve(__dirname, 'src/renderer/viewer/index.html'),
          syntax: resolve(__dirname, 'src/renderer/syntax/index.html')
        }
      }
    }
  }
})
