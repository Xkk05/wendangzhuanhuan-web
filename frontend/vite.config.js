import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'electron' ? './' : '/',
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['antd', 'framer-motion'],
          utils: ['jszip', 'file-saver', 'react-hot-toast'],
        },
      },
    },
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    cssCodeSplit: true,
    chunkSizeWarningLimit: 1000,
  },
  server: {
    port: 5176,
    strictPort: true,
    host: '0.0.0.0',
    hmr: {
      overlay: false,
    },
    proxy: {
      '/kq-auth': {
        target: 'https://api-web.kunqiongai.com',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/kq-auth/, ''),
      },
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'antd', 'framer-motion'],
  },
}))
