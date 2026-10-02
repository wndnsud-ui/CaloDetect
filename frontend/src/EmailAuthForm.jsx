import React from 'react';

export default function EmailAuthForm({signup, policy, busy, onSubmit}) {
  return <form key={signup ? 'signup' : 'login'} className="panel auth-panel" onSubmit={onSubmit}>
    <h3>{signup ? '이메일로 회원가입' : '이메일로 로그인'}</h3>
    {signup && policy?.local_test_mode && <p className="notice" role="status">로컬 테스트 가입이 활성화되었습니다. 테스트용 이름과 이메일로 가입해 주세요.</p>}
    <fieldset disabled={busy} className="auth-fields">
      {signup && <>
        <label>이름<input name="name" required maxLength="80" autoComplete="name"/></label>
        <label>만 나이<input name="age" type="number" required min={policy?.age_min || 18} step="1" max="120"/></label>
      </>}
      <label>이메일<input name="email" type="email" required autoComplete="email"/></label>
      <label>비밀번호<input name="password" type="password" required minLength="8" maxLength="128"
        autoComplete={signup ? 'new-password' : 'current-password'}/></label>
      {signup && <>
        <p className="notice">{policy?.service_consent_text || policy?.notice || '가입 정책을 확인하고 있습니다.'}</p>
        <label className="check"><input name="service_consent" type="checkbox" required/>서비스 이용·개인정보 처리 동의</label>
      </>}
      <button className="primary" disabled={busy || (signup && !policy?.signup_enabled)}>
        {signup ? '이메일로 가입하기' : '로그인'}
      </button>
    </fieldset>
    {signup && policy && !policy.signup_enabled && <p className="muted" role="status">
      가입 동의 내용이 아직 준비되지 않아 신규 회원가입을 진행할 수 없습니다. 기존 회원은 로그인 탭을 이용해 주세요.
    </p>}
  </form>;
}
