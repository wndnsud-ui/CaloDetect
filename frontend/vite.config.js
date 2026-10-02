import { defineConfig } from 'vite';
export default defineConfig({server: {port: 5173, strictPort: true, proxy: {'/api': {target: process.env.CALODETECT_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '')}}}});
