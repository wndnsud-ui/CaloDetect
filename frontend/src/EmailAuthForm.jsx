// 로그인/회원가입 이메일 폼. 서버 가입 정책에 맞춰 이름·만 나이·필수 동의 항목을 표시한다.
// 요청 처리는 상위 onSubmit에 맡기고 비밀번호 찾기 화면을 함께 제공한다.
import React, {useEffect, useRef, useState} from 'react';
import {ForgotPassword} from './PasswordTools';
import {readRememberedEmail, saveRememberedEmail} from './rememberedEmail';

// 로그인/회원가입 이메일 폼. 서버 가입 정책에 맞춰 이름·만 나이·필수 동의 항목을 표시한다.
export default function EmailAuthForm({signup, policy, busy, error, onSubmit, api, signedUpEmail = ''}) {
  // 방금 가입한 이메일이 있으면 로그인 칸에 우선 채운다(브라우저에 영구 저장하지는 않는다).
  const [loginEmail, setLoginEmail] = useState(() => signedUpEmail || readRememberedEmail());
  const [signupEmail, setSignupEmail] = useState('');
  // 가입 탭에서 입력한 이메일은 로그인 탭으로 바꿀 때 그대로 넘긴다.
  useEffect(() => { if (!signup && signupEmail.trim()) setLoginEmail(signupEmail.trim()); }, [signup]);
  const [rememberEmail, setRememberEmail] = useState(() => !!readRememberedEmail());
  // 가입 때만 비밀번호 확인 칸을 두고, 다르면 브라우저 검증으로 제출을 막는다. 확인 값은 서버로 보내지 않는다.
  const [password, setPassword] = useState(''), [passwordConfirm, setPasswordConfirm] = useState('');
  const confirmRef = useRef(null);
  // 로그인↔가입 탭을 바꾸면 이전처럼 비밀번호 입력을 비운다.
  useEffect(() => { setPassword(''); setPasswordConfirm(''); }, [signup]);
  const mismatch = signup && passwordConfirm !== '' && password !== passwordConfirm;
  useEffect(() => { confirmRef.current?.setCustomValidity(mismatch ? '비밀번호가 일치하지 않아요.' : ''); }, [mismatch, signup]);
  return <><form key={signup ? 'signup' : 'login'} className="panel auth-panel" onSubmit={onSubmit}>
    <h3>{signup ? '이메일로 회원가입' : '이메일로 로그인'}</h3>
    {signup && policy?.local_test_mode && <p className="notice" role="status">로컬 테스트 가입이 활성화되었습니다. 테스트용 이름과 이메일로 가입해 주세요.</p>}
    <fieldset disabled={busy} className="auth-fields">
      {signup && <>
        <label>이름<input name="name" required maxLength="80" autoComplete="name"/></label>
        <label>만 나이<input name="age" type="number" required min={policy?.age_min || 18} step="1" max="120" defaultValue={Math.max(18, policy?.age_min || 0)}/></label>
      </>}
      <label>이메일<input name="email" type="email" required autoComplete="email"
        value={signup ? signupEmail : loginEmail}
        onChange={e => signup ? setSignupEmail(e.target.value) : setLoginEmail(e.target.value)}/></label>
      <label>비밀번호<input name="password" type="password" required minLength="8" maxLength="128"
        autoComplete={signup ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)}/></label>
      {signup && <><label>비밀번호 확인<input ref={confirmRef} name="password_confirm" type="password" required minLength="8" maxLength="128"
        autoComplete="new-password" aria-invalid={mismatch} aria-describedby="password-confirm-status"
        value={passwordConfirm} onChange={e => setPasswordConfirm(e.target.value)}/></label>
        <p id="password-confirm-status" className={mismatch ? 'error' : 'muted'} role="status">
          {mismatch ? '비밀번호가 일치하지 않아요.' : passwordConfirm && password === passwordConfirm ? '비밀번호가 일치해요.' : ''}</p></>}
      {!signup && <label className="check"><input name="remember_email" type="checkbox"
        checked={rememberEmail} onChange={e => {
          setRememberEmail(e.target.checked);
          if (!e.target.checked) saveRememberedEmail('', false);
        }}/>이메일 기억하기</label>}
      {signup && <>
        <p className="notice">{policy?.local_test_mode
          ? '로컬 개발 테스트용 가입 동의: 이 환경은 CaloDetect 기능 확인용입니다. 만 18세 이상만 테스트 계정을 만들 수 있습니다. 실제 개인정보 대신 테스트용 이름·이메일을 입력해 주세요. 이름, 이메일, 만 나이, 비밀번호 해시와 동의 내용이 개발 DB에 저장됩니다. 로그인과 식단 기능 테스트에 사용하며 운영용 동의 문구가 아닙니다. 테스트 가입에 동의하지 않으면 계정을 만들 수 없고 비회원 계산 기능은 사용할 수 있습니다.'
          : policy?.service_consent_text || policy?.notice || '가입 정책을 확인하고 있습니다.'}</p>
        <label className="check"><input name="service_consent" type="checkbox" required/>서비스 이용·개인정보 처리 동의</label>
      </>}
      <button className="primary" disabled={busy || (signup && !policy?.signup_enabled)}>
        {signup ? '이메일로 가입하기' : '로그인'}
      </button>
    </fieldset>
    {error && <p className="error" role="alert">{error}</p>}
    {signup && policy && !policy.signup_enabled && <p className="muted" role="status">
      가입 동의 내용이 아직 준비되지 않아 신규 회원가입을 진행할 수 없습니다. 기존 회원은 로그인 탭을 이용해 주세요.
    </p>}
  </form>{!signup && <ForgotPassword api={api} enabled={policy?.password_reset_enabled} disabled={busy}/>}</>;
}
