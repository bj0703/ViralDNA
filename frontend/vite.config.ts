import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // 强制锁定5173端口，找不到直接报错，绝不漂移到其他端口
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 300000, // SSE长连接超时5分钟
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('[Vite Proxy] 代理错误:', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            proxyReq.path = req.url || proxyReq.path;
            console.log('[Vite Proxy] 转发请求:', req.method, req.url);
          });
        },
      },
    },
  },
})
