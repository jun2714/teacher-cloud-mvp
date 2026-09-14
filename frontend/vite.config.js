import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const apiTarget = process.env.VITE_API_PROXY || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 6060,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0,
      },
      '/admin': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/media': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
