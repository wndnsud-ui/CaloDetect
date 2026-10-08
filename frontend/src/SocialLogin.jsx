// Google 인증 SDK/Authorization Code 로그인과 신규 가입 보완 폼.
// 서버의 제공자 설정으로 사용 가능 여부를 판단하고 인증 검증·계정 생성은 Backend에 맡긴다.
import React, { useEffect, useRef, useState } from 'react';

// SDK 주소별 진행 Promise를 공유해 컴포넌트 재진입 시 중복 script 추가를 막는다.
const scripts = new Map();
// 동일 SDK 주소의 Promise를 공유해 중복 로딩을 막고 실패한 항목은 제거해 재시도를 허용한다.
function loadScript(src) {
  if (!scripts.has(src)) scripts.set(src, new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src; script.async = true;
    script.onload = resolve;
    script.onerror = () => {scripts.delete(src); script.remove(); reject(new Error('로그인 서비스를 불러오지 못했습니다. 네트워크 연결을 확인해 주세요.'));};
    document.head.appendChild(script);
  }));
  return scripts.get(src);
}

const googleErrors = {
  account_conflict: '이 이메일은 다른 로그인 방식으로 이미 가입되어 있습니다. 기존 방식으로 로그인해 주세요.',
  signup_unavailable: 'Google 가입은 승인된 서비스 이용·개인정보 동의 문구 설정 후 사용할 수 있습니다.',
  google_unavailable: 'Google 로그인을 사용할 수 없습니다. 설정을 확인한 뒤 다시 시도해 주세요.',
};

// Google 인증 SDK/Authorization Code 로그인과 신규 가입 보완 폼.
export default function SocialLogin({api, policy, onAuthenticated, disabled, signup = false}) {
  const googleButton = useRef(null), active = useRef(false);
  const [providers, setProviders] = useState(null), [googleReady, setGoogleReady] = useState(false);
  const [working, setWorking] = useState(false), [error, setError] = useState('');
  const [pending, setPending] = useState(null), [generation, setGeneration] = useState(0);

  // 제공자 인증 결과를 Backend에서 검증하고 기존 회원 로그인 또는 신규 가입 보완 입력으로 연결한다.
  async function finish(provider, data, suggestedName = '') {
    setWorking(true); setError('');
    try {
      const result = await api(`/auth/social/${provider}/complete`, data);
      if (!active.current) return;
      if (result.registration_required) {
        setPending({provider, data, email: result.email, name: suggestedName || result.name});
      } else {
        await onAuthenticated(result);
      }
    } catch (err) {if (active.current) setError(err.message);}
    finally {if (active.current) setWorking(false);}
  }

  // 의존값 변경/마운트에 맞춰 외부 데이터 또는 브라우저 자원을 동기화한다. 반환하는 정리 함수는 이전 작업/자원을 해제한다.
  useEffect(() => {
    active.current = true;
    // effect 정리 뒤 완료되는 SDK/정책 조회가 현재 화면을 갱신하지 않게 한다.
    let cancelled = false;
    setGoogleReady(false); setPending(null); setError('');
    googleButton.current?.replaceChildren();

    // 제공자 설정과 반환 URL을 읽어 Google SDK 또는 Authorization Code 인증 화면을 준비한다.
    async function setup() {
      try {
        const config = await api('/auth/social/policy');
        if (cancelled) return;
        setProviders(config);

        const params = new URLSearchParams(window.location.search);
        const signupReturn = params.get('social_signup') === 'google';
        const errorCode = params.get('social_error');
        if (signupReturn || errorCode || params.has('social_success')) {
          // 소셜 반환 안내를 읽은 뒤 URL을 정리해 새로고침에서 같은 반환 처리를 반복하지 않게 한다.
          window.history.replaceState({}, '', `${window.location.pathname}${window.location.hash}`);
        }
        if (signupReturn) {
          try {
            const result = await api('/auth/social/google/pending', undefined, 'GET');
            if (!cancelled && result.registration_required) {
              setPending({...result, authorization_code: true});
            }
          } catch (err) {if (!cancelled) setError(err.message);}
        } else if (errorCode) {
          setError(googleErrors[errorCode] || 'Google 인증에 실패했습니다. 다시 시도해 주세요.');
        }

        if (config.google.enabled && !config.google.authorization_code_enabled) {
          try {
            await loadScript('https://accounts.google.com/gsi/client');
            if (cancelled) return;
            const challenge = await api('/auth/social/google/challenge', {});
            if (cancelled) return;
            window.google.accounts.id.initialize({
              client_id: config.google.client_id,
              nonce: challenge.nonce,
              auto_select: false,
              callback: result => {
                if (!cancelled) finish('google', {id_token: result.credential});
              },
            });
            googleButton.current?.replaceChildren();
            window.google.accounts.id.renderButton(googleButton.current, {
              type: 'standard', theme: 'outline', size: 'large',
              text: signup ? 'signup_with' : 'signin_with', locale: 'ko',
            });
            setGoogleReady(true);
          } catch (err) {if (!cancelled) setError(err.message);}
        }

      } catch (err) {if (!cancelled) setError(err.message);}
    }
    setup();
    return () => {cancelled = true; active.current = false;};
  }, [generation, signup]);

  // 신규 소셜 회원의 이름·만 나이·현재 동의 문구를 전송한다. Authorization Code 반환은 가입 쿠키, GIS는 인증 토큰 검증 경로를 사용한다.
  async function register(event) {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget));
    const data = {name: form.name, age: Number(form.age),
      service_consent: form.consent === 'on', consent_text: policy?.service_consent_text};
    if (!pending.authorization_code) {
      finish(pending.provider, {...pending.data, ...data});
      return;
    }
    setWorking(true); setError('');
    try {
      const result = await api('/auth/social/google/register', data);
      if (active.current) await onAuthenticated(result);
    } catch (err) {if (active.current) setError(err.message);}
    finally {if (active.current) setWorking(false);}
  }

  const locked = disabled || working;
  return <section className="social-login" aria-label={signup ? '소셜 회원가입' : '소셜 로그인'}>
    <p className="social-divider">{signup ? '소셜 계정으로 회원가입' : '소셜 계정으로 로그인'}</p>
    <p className="muted">{signup ? 'Google 계정 선택 → 이름·만 나이·동의 확인 → 가입 완료' : '처음 이용하는 소셜 계정은 인증 후 회원가입으로 이어집니다.'}</p>
    <div hidden={!!pending}>
      {providers?.google.authorization_code_enabled
        ? <button type="button" className="social-button google-login-button" disabled={locked}
            onClick={()=>window.location.assign('/api/auth/google/login')}>
            Google로 {signup ? '회원가입' : '로그인'}
          </button>
        : <div ref={googleButton} className="google-login-button" hidden={!googleReady}
            inert={locked ? true : undefined}/>}
      {providers && !providers.google.enabled && <button type="button" className="social-button google-login-button" disabled>
        Google로 {signup ? '회원가입' : '로그인'} · 준비 중
      </button>}
      {providers && !providers.google.enabled && <p className="muted" role="status">
        Google 계정 연결이 준비 중입니다. 연결 완료 후 사용할 수 있습니다.
      </p>}
    </div>
    {pending && <form onSubmit={register}>
      <h3>Google 회원가입 마무리</h3><p className="muted">{pending.email}</p>
      <label>이름<input name="name" required maxLength="80" defaultValue={pending.name}/></label>
      <label>만 나이<input name="age" type="number" min={policy?.age_min || 18} max="120" step="1" required/></label>
      <p className="notice">{policy?.service_consent_text || policy?.notice || '가입 동의 문구 확인 중'}</p>
      <label className="check"><input type="checkbox" name="consent" required/>서비스 이용·개인정보 처리 동의</label>
      <button className="primary" disabled={locked || !policy?.signup_enabled}>동의하고 가입하기</button>
      {policy && !policy.signup_enabled && <p className="muted" role="status">가입 동의 내용이 준비된 후 가입을 완료할 수 있습니다.</p>}
    </form>}
    {working && <p className="muted" role="status">소셜 로그인을 확인하고 있습니다.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {(error || pending) && <button type="button" className="text-button" disabled={locked} onClick={()=>{
      setPending(null); setError(''); setGeneration(value => value + 1);
    }}>소셜 로그인 다시 시작</button>}
  </section>;
}
