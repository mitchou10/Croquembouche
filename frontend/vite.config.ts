import { readFileSync } from 'node:fs'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// The version of the frontend is the one of the release, which bumps package.json: it is known when the page is built.
const { version } = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')) as { version: string }

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  define: { __APP_VERSION__: JSON.stringify(version) },
  server: {
    // File events do not cross a bind mount on macOS or Windows: docker-compose.override.yaml turns polling on there.
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
    // The page talks to the backend on its own origin (the session cookie is its own then, with no CORS): `/api` goes
    // through. In the compose stack the backend is the `backend` service.
    proxy: { '/api': { target: process.env.BACKEND_URL ?? 'http://localhost:8000' } },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      // lcov is what ci/crap.py reads to compute the CRAP score.
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,vue}'],
      exclude: ['src/**/*.test.ts', 'src/test/**', 'src/main.ts', 'src/vite-env.d.ts'],
    },
  },
})
