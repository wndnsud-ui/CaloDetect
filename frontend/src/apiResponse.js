// fetch 응답을 한 번 읽어 JSON 또는 사용자용 오류로 변환한다.
// HTTP 오류뿐 아니라 비어 있거나 JSON이 아닌 응답도 실패로 처리해 화면에서 서버 연결 문제를 설명할 수 있게 한다.
// 응답 text를 한 번 읽어 JSON으로 해석하고 HTTP 실패/잘못된 본문을 Error로 변환한다.
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
