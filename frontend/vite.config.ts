import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // File events do not cross a bind mount on macOS or Windows: docker-compose.override.yaml turns polling on there.
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
  },
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      // lcov is what ci/crap.py reads to compute the CRAP score.
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,vue}'],
      exclude: ['src/**/*.test.ts', 'src/main.ts', 'src/vite-env.d.ts'],
    },
  },
})
