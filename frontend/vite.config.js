import { defineConfig } from 'vite';

const target = process.env.CALODETECT_API_TARGET || 'http://[::1]:8000';
export default defineConfig({server: {port: 5173, strictPort: true, proxy: {'/api': {
  target,
  changeOrigin: true,
  rewrite: path => path.replace(/^\/api/, ''),
  configure(proxy) {
    proxy.on('error', (error, request, response) => {
      if (!response.writeHead || response.headersSent || response.writableEnded) return;
      response.writeHead(502, {'Content-Type': 'application/json; charset=utf-8'});
      response.end(JSON.stringify({error: {
        code: 'API_PROXY_UNAVAILABLE',
        message: `Backend 연결 실패 (${target}, ${error.code || 'PROXY_ERROR'}). Backend 포트와 CALODETECT_API_TARGET을 확인해 주세요.`,
      }}));
    });
  },
}}}});
