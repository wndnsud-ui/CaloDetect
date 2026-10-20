// 기존 회원 안내 카드(지시서 v3 §11-11 ③). nickname_prompt="card"일 때 홈과 마이페이지 상단에 1개.
// 한 곳에서 닫으면 서버에 기록돼 두 곳 모두 사라진다.
import React, {useState} from 'react';

export default function NicknamePromptCard({api, nickname, onChoose, onDismissed}) {
  const [busy, setBusy] = useState(false);
  async function dismiss() {
    setBusy(true);
    try { await api('/rewards/nickname/prompt/dismiss', {}); onDismissed?.(); } finally { setBusy(false); }
  }
  return <section className="nickname-prompt" aria-label="닉네임 안내">
    <p><strong>랭킹에 보일 닉네임을 정해 보세요</strong><span>지금은 ‘{nickname}’</span></p>
    <button type="button" className="primary" onClick={onChoose}>정하기</button>
    <button type="button" className="nickname-prompt-close" aria-label="닉네임 안내 닫기" onClick={dismiss} disabled={busy}>×</button>
  </section>;
}
