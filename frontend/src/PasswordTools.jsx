import React, {useState} from 'react';

export function ForgotPassword({api, enabled, disabled}) {
  const [open, setOpen] = useState(false), [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(''), [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    const email = new FormData(event.currentTarget).get('email');
    setBusy(true); setMessage(''); setError('');
    try {setMessage((await api('/auth/password/forgot', {email})).message);}
    catch (err) {setError(err.message);}
    finally {setBusy(false);}
  }
  return <section className="panel">
    <button type="button" className="text-button" disabled={disabled || busy} aria-expanded={open}
      onClick={()=>setOpen(value=>!value)}>비밀번호 찾기</button>
    {open && <form onSubmit={submit}>
      <h3>비밀번호 재설정 메일 받기</h3>
      <p className="muted">이메일로 가입한 주소를 입력하세요. 메일의 링크는 15분 동안 유효합니다.</p>
      <fieldset className="auth-fields" disabled={disabled || busy}>
        <label>가입 이메일<input name="email" type="email" required maxLength="254" autoComplete="email"/></label>
        <button className="primary" disabled={!enabled}>{busy ? '요청 중…' : '재설정 메일 보내기'}</button>
      </fieldset>
      {!enabled && <p className="notice">재설정 이메일 발송 설정이 준비되지 않았습니다. 운영자에게 문의해 주세요.</p>}
    </form>}
    {message && <p className="notice" role="status">{message}</p>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}

export function PasswordForm({api, token, onChanged, onCancel}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setError('');
    if (data.new_password !== data.confirm_password) {setError('새 비밀번호가 일치하지 않습니다.');return;}
    setBusy(true);
    try {
      const body = token ? {token, new_password:data.new_password}
        : {current_password:data.current_password, new_password:data.new_password};
      const result = await api(token ? '/auth/password/reset' : '/users/me/password', body);
      form.reset(); onChanged(result.message);
    } catch (err) {setError(err.message);}
    finally {setBusy(false);}
  }
  return <section className="panel auth-panel">
    <h2>{token ? '비밀번호 재설정' : '비밀번호 변경'}</h2>
    <p className="muted">8~128자로 입력하세요. 변경 후 모든 기기에서 로그아웃됩니다.</p>
    <form onSubmit={submit}>
      <fieldset className="auth-fields" disabled={busy}>
        {!token && <label>현재 비밀번호<input name="current_password" type="password" required
          minLength="8" maxLength="128" autoComplete="current-password"/></label>}
        <label>새 비밀번호<input name="new_password" type="password" required minLength="8"
          maxLength="128" autoComplete="new-password"/></label>
        <label>새 비밀번호 확인<input name="confirm_password" type="password" required minLength="8"
          maxLength="128" autoComplete="new-password"/></label>
        <button className="primary">{busy ? '변경 중…' : '비밀번호 변경하기'}</button>
      </fieldset>
    </form>
    {error && <p className="error" role="alert">{error}</p>}
    {token && <button type="button" className="text-button" disabled={busy} onClick={onCancel}>로그인 / 새 재설정 메일 요청</button>}
  </section>;
}

export function takeResetToken() {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const token = params.get('password_reset');
  if (token) window.history.replaceState({}, '', window.location.pathname + window.location.search);
  return token;
}
