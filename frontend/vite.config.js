import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/upload': 'http://localhost:8000',
      '/results': 'http://localhost:8000',
      '/detect_frame': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/login/google': 'http://localhost:8000',
      '/login/github': 'http://localhost:8000',
      '/users': 'http://localhost:8000'
    }
  }
})
