import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // host: true is required for the dev server to be reachable from outside
    // the container when running under docker compose.
    host: true,
    port: 5173,
    strictPort: true,
    watch: {
      // Bind-mounted volumes on Linux/macOS Docker do not reliably emit inotify
      // events; polling keeps hot reload working inside the container.
      usePolling: true,
    },
  },
  preview: {
    host: true,
    port: 5173,
  },
})
