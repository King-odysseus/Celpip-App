import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
  server: {
    port: 5173,
    // In development the SPA talks to the Django backend through this proxy,
    // so the app can use relative /api URLs and avoid CORS during dev.
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    // Playwright's own specs (frontend/e2e/**) use @playwright/test's test()/
    // expect(), not Vitest's — collecting them here fails outright. They run
    // via `npx playwright test`, configured separately in playwright.config.ts.
    exclude: ['**/node_modules/**', '**/e2e/**'],
  },
})
