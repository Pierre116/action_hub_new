import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../static/dist",
    emptyOutDir: true,
    commonjsOptions: {
      include: [/node_modules/],
    },
    rollupOptions: {
      external: ['react-i18next'],
    },
  },
  optimizeDeps: {
    include: ['i18next', 'react-i18next'],
    exclude: [],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
