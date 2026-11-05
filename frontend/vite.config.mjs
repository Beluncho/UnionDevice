import { defineConfig } from 'vitest/config'
import ts from 'typescript'

function typescriptInProcess() {
  return {
    name: 'typescript-in-process',
    enforce: 'pre',
    transform(code, id) {
      if (!/\.[cm]?tsx?$/.test(id) || id.includes('/node_modules/')) return null
      const result = ts.transpileModule(code, {
        fileName: id,
        compilerOptions: {
          target: ts.ScriptTarget.ES2022,
          module: ts.ModuleKind.ESNext,
          moduleResolution: ts.ModuleResolutionKind.Bundler,
          jsx: ts.JsxEmit.ReactJSX,
          sourceMap: true,
        },
      })
      return { code: result.outputText, map: result.sourceMapText ?? null }
    },
  }
}

export default defineConfig({
  esbuild: false,
  plugins: [typescriptInProcess()],
  optimizeDeps: {
    noDiscovery: true,
    include: [],
  },
  build: {
    minify: false,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    globals: true,
    pool: 'threads',
    poolOptions: {
      threads: { singleThread: true },
    },
    deps: {
      optimizer: {
        web: { enabled: false },
        ssr: { enabled: false },
      },
    },
  },
})
