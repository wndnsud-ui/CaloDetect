// 로그인/회원가입 이메일 폼. 서버 가입 정책에 맞춰 이름·만 나이·필수 동의 항목을 표시한다.
// 요청 처리는 상위 onSubmit에 맡기고 비밀번호 찾기 화면을 함께 제공한다.
import React from 'react';
import {ForgotPassword} from './PasswordTools';

// 로그인/회원가입 이메일 폼. 서버 가입 정책에 맞춰 이름·만 나이·필수 동의 항목을 표시한다.
export default function EmailAuthForm({signup, policy, busy, onSubmit, api}) {
  return <><form key={signup ? 'signup' : 'login'} className="panel auth-panel" onSubmit={onSubmit}>
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
        <p className="notice">{policy?.local_test_mode
          ? '로컬 개발 테스트용 가입 동의: 이 환경은 CaloDetect 기능 확인용입니다. 만 18세 이상만 테스트 계정을 만들 수 있습니다. 실제 개인정보 대신 테스트용 이름·이메일을 입력해 주세요. 이름, 이메일, 만 나이, 비밀번호 해시와 동의 내용이 개발 DB에 저장됩니다. 로그인과 식단 기능 테스트에 사용하며 운영용 동의 문구가 아닙니다. 테스트 가입에 동의하지 않으면 계정을 만들 수 없고 비회원 계산 기능은 사용할 수 있습니다. 사진의 모델 개선 활용은 이 동의에 포함하지 않습니다.'
          : policy?.service_consent_text || policy?.notice || '가입 정책을 확인하고 있습니다.'}</p>
        <label className="check"><input name="service_consent" type="checkbox" required/>서비스 이용·개인정보 처리 동의</label>
      </>}
      <button className="primary" disabled={busy || (signup && !policy?.signup_enabled)}>
        {signup ? '이메일로 가입하기' : '로그인'}
      </button>
    </fieldset>
    {signup && policy && !policy.signup_enabled && <p className="muted" role="status">
      가입 동의 내용이 아직 준비되지 않아 신규 회원가입을 진행할 수 없습니다. 기존 회원은 로그인 탭을 이용해 주세요.
    </p>}
  </form>{!signup && <ForgotPassword api={api} enabled={policy?.password_reset_enabled} disabled={busy}/>}</>;
}
