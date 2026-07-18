import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/askMe':    'http://localhost:8000',
      '/sapAgent': 'http://localhost:8000',
    },
  },
})
