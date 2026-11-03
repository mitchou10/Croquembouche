import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
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
