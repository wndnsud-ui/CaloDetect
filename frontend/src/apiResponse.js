export async function readApiResponse(response) {
  const body = await response.text();
  let data;
  try { data = body.trim() ? JSON.parse(body) : null; } catch { data = null; }
  if (!response.ok || data === null) {
    const message = data?.error?.message || (response.status >= 500
      ? 'API 서버 연결에 문제가 있습니다. Backend 실행 상태와 프런트엔드 API 주소를 확인해 주세요.'
      : '서버에서 올바른 응답을 받지 못했습니다. 다시 시도해 주세요.');
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}
