/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// SECURITY T-10: CSP for the built SPA (served by `vite preview` in `make demo`).
// style-src needs 'unsafe-inline' for React style attributes (charts, QR); no inline scripts.
function csp(apiBase: string | undefined): string {
  const api = apiBase ? new URL(apiBase).origin : ''
  return [
    "default-src 'self'",
    `connect-src 'self' ${api}`.trim(),
    "img-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ')
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true },
  preview: {
    port: 5173,
    strictPort: true,
    headers: {
      'Content-Security-Policy': csp(process.env.VITE_API_BASE_URL),
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
