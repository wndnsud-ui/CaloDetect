// 이 브라우저의 이메일만 보관한다. 저장소가 차단되어도 로그인은 계속한다.
const KEY = 'calodetect.rememberedEmail';

export function readRememberedEmail() {
  try { return window.localStorage.getItem(KEY) || ''; }
  catch { return ''; }
}

export function saveRememberedEmail(email, remember) {
  try {
    if (remember) window.localStorage.setItem(KEY, email.trim().toLowerCase());
    else window.localStorage.removeItem(KEY);
  } catch { /* 브라우저 저장 실패를 인증 실패로 처리하지 않는다. */ }
}
