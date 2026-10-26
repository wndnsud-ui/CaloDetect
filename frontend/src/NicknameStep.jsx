// 회원가입 마지막 단계 "닉네임 정하기"(지시서 v3 §11-11 ①). 이메일·구글·카카오 가입 직후, 홈·첫날 꾸미기보다 먼저 띄운다.
// 건너뛰기 버튼은 없다. 다시 로그인했을 때 재표시(allowClose)에서만 닫기를 허용하고, 닫으면 자동 생성 닉네임을 유지한다.
import React, {useEffect, useState} from 'react';
import NicknameField from './NicknameField';
import {JibangFigure, CHARACTER_NAME} from './Jibang';

export default function NicknameStep({api, onDone, allowClose = false}) {
  const [value, setValue] = useState(''), [valid, setValid] = useState(false), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  useEffect(() => { api('/rewards/nickname/suggestion').then(result => setValue(result.nickname)).catch(e => setError(e.message)); }, [api]);
  async function save(event) {
    event.preventDefault();
    if (!valid || busy) return;
    setBusy(true); setError('');
    try { await api('/rewards/nickname', {nickname: value.trim(), via: 'signup'}, 'PUT'); onDone(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function close() {
    setBusy(true);
    try { await api('/rewards/nickname/prompt/dismiss', {}); } catch { /* 닫기 실패는 다음 로그인에서 다시 묻는다 */ }
    onDone();
  }
  return <div className="reward-overlay" role="dialog" aria-modal="true" aria-labelledby="nickname-step-title">
    <form className="nickname-step" onSubmit={save}>
      <h2 id="nickname-step-title">랭킹에서 불릴 닉네임을 정해 주세요</h2>
      <p className="muted">나중에 마이페이지에서 바꿀 수 있어요</p>
      <div className="nickname-hello"><JibangFigure width={96} label={CHARACTER_NAME}/><p className="jb-bubble static">반가워, {value.trim() || '…'}!</p></div>
      <NicknameField api={api} value={value} onChange={next => { setValue(next); setError(''); }} onValidity={setValid} serverError={error} autoFocus/>
      <button className="primary" disabled={!valid || busy}>{busy ? '저장하고 있어요…' : '이 닉네임으로 시작하기'}</button>
      {allowClose && <button type="button" className="text-button" onClick={close} disabled={busy}>지금은 닫기 · 자동 닉네임 쓰기</button>}
    </form>
  </div>;
}
