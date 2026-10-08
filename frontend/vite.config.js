// Vite 개발 서버와 Backend 프록시 설정. 브라우저의 /api 요청을 서버로 전달하고 API별 경로 처리 규칙을 유지한다.
import { defineConfig } from 'vite';

// 환경변수로 Backend 주소를 바꿀 수 있으며 기본값은 로컬 IPv6 loopback이다.
const target = process.env.CALODETECT_API_TARGET || 'http://[::1]:8000';
export default defineConfig({server: {port: 5173, strictPort: true, proxy: {'/api': {
  target,
  changeOrigin: true,
  // 브라우저 /api 접두사를 제거해 Backend의 실제 라우트와 연결한다.
  rewrite: path => path.replace(/^\/api/, ''),
  // Backend에 연결할 수 없을 때 HTML 대신 공통 JSON 오류를 반환해 응답 파서가 안내를 표시하게 한다.
  configure(proxy) {
    proxy.on('error', (error, request, response) => {
      // 이미 완료됐거나 HTTP 응답 인터페이스가 아닌 연결에는 중복 오류 응답을 쓰지 않는다.
      if (!response.writeHead || response.headersSent || response.writableEnded) return;
      response.writeHead(502, {'Content-Type': 'application/json; charset=utf-8'});
      response.end(JSON.stringify({error: {
        code: 'API_PROXY_UNAVAILABLE',
        message: `Backend 연결 실패 (${target}, ${error.code || 'PROXY_ERROR'}). Backend 포트와 CALODETECT_API_TARGET을 확인해 주세요.`,
      }}));
    });
  },
}}}});
