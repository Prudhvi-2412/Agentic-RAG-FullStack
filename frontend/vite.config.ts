import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: true
    },
    build: {
      outDir: 'dist',
      sourcemap: false,          // Disable in production to reduce bundle size
      chunkSizeWarningLimit: 1000
    },
    define: {
      // Inject backend URL — falls back to localhost for local dev
      __BACKEND_URL__: JSON.stringify(
        env.VITE_BACKEND_URL || 'http://localhost:8000'
      )
    }
  }
})

