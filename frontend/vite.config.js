import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/upload': 'http://localhost:8001',
      '/results': 'http://localhost:8001',
      '/detect_frame': 'http://localhost:8001',
      '/uploads': 'http://localhost:8001',
      '/auth': 'http://localhost:8001',
      '/login/google': 'http://localhost:8001',
      '/login/github': 'http://localhost:8001',
      '/users': 'http://localhost:8001'
    }
  }
})
