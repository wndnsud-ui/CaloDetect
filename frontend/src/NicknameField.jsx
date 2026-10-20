// 닉네임 공통 입력(지시서 v3 §11-11): 가입 단계·마이페이지·랭킹 창에서 같이 쓴다.
// 입력을 멈추고 400ms 뒤 서버 검사(/rewards/nickname/check) 결과를 입력란 아래 1줄로 알린다. 저장 오류는 검사 결과보다 우선한다.
import React, {useEffect, useId, useRef, useState} from 'react';

export const NICKNAME_MIN = 2, NICKNAME_MAX = 12;

export default function NicknameField({api, value, onChange, onValidity, serverError, label = '닉네임', autoFocus = false}) {
  const id = useId(), [check, setCheck] = useState(null), [suggesting, setSuggesting] = useState(false);
  const request = useRef(0);
  useEffect(() => {
    const current = ++request.current;
    setCheck(null); onValidity?.(false);
    const text = value.trim();
    if (!text) return undefined;
    const timer = setTimeout(() => {
      api(`/rewards/nickname/check?nickname=${encodeURIComponent(text)}`)
        .then(result => { if (current === request.current) { setCheck(result); onValidity?.(result.ok); } })
        .catch(error => { if (current === request.current) setCheck({ok: false, message: error.message}); });
    }, 400);
    return () => clearTimeout(timer);
  }, [value, api]);
  async function suggest() {
    setSuggesting(true);
    try { onChange((await api('/rewards/nickname/suggestion')).nickname); }
    catch (error) { setCheck({ok: false, message: error.message}); }
    finally { setSuggesting(false); }
  }
  const message = serverError || check?.message || '';
  const ok = !serverError && check?.ok;
  return <div className="nickname-field">
    <label htmlFor={`${id}-input`}>{label}</label>
    <div className="nickname-input-row">
      <input id={`${id}-input`} value={value} maxLength={NICKNAME_MAX} autoFocus={autoFocus} autoComplete="off"
        aria-describedby={`${id}-rule ${id}-status`} aria-invalid={message && !ok ? 'true' : undefined}
        onChange={event => onChange(event.target.value)}/>
      <span className="nickname-count" aria-hidden="true">{[...value].length}/{NICKNAME_MAX}</span>
    </div>
    <p id={`${id}-rule`} className="nickname-rule">한글·영문·숫자, {NICKNAME_MIN}~{NICKNAME_MAX}자 · 랭킹에 표시돼요</p>
    <p id={`${id}-status`} className={`nickname-status ${ok ? 'is-ok' : message ? 'is-error' : ''}`} aria-live="polite">{message}</p>
    <button type="button" className="text-button nickname-suggest" onClick={suggest} disabled={suggesting}>{suggesting ? '추천을 받고 있어요…' : '다른 추천 받기'}</button>
  </div>;
}
