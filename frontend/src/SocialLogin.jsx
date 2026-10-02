import React, { useEffect, useRef, useState } from 'react';

const scripts = new Map();
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

export default function SocialLogin({api, policy, onAuthenticated, disabled, signup = false}) {
  const googleButton = useRef(null), apple = useRef(null), active = useRef(false);
  const [providers, setProviders] = useState(null), [appleReady, setAppleReady] = useState(false), [googleReady, setGoogleReady] = useState(false);
  const [working, setWorking] = useState(false), [error, setError] = useState('');
  const [pending, setPending] = useState(null), [generation, setGeneration] = useState(0);
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
  useEffect(() => {
    active.current = true;
    let cancelled = false;
    setAppleReady(false); setGoogleReady(false); apple.current = null; setPending(null); setError('');
    googleButton.current?.replaceChildren();
    async function setup() {
      try {
        const config = await api('/auth/social/policy');
        if (cancelled) return;
        setProviders(config);
        await Promise.allSettled(['google', 'apple'].map(async provider => {
          if (!config[provider].enabled) return;
          try {
            await loadScript(provider === 'google' ? 'https://accounts.google.com/gsi/client'
              : 'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js');
            if (cancelled) return;
            const challenge = await api(`/auth/social/${provider}/challenge`, {});
            if (cancelled) return;
            if (provider === 'google') {
              window.google.accounts.id.initialize({client_id: config.google.client_id, nonce: challenge.nonce,
                auto_select: false, callback: result => {
                  if (!cancelled) finish('google', {id_token: result.credential});
                }});
              googleButton.current.replaceChildren();
              window.google.accounts.id.renderButton(googleButton.current, {type: 'standard', theme: 'outline',
                size: 'large', text: signup ? 'signup_with' : 'signin_with', locale: 'ko'});
              setGoogleReady(true);
            } else {
              apple.current = {config: config.apple, challenge}; setAppleReady(true);
            }
          } catch (err) {if (!cancelled) setError(err.message);}
        }));
      } catch (err) {if (!cancelled) setError(err.message);}
    }
    setup();
    return () => {cancelled = true; active.current = false;};
  }, [generation, signup]);
  function unavailable(provider) {
    setError(`${provider} 계정 연결 설정이 아직 완료되지 않았습니다. 서비스 운영자가 연결을 완료하면 회원가입과 로그인을 사용할 수 있습니다.`);
  }
  function appleLogin() {
    const context = apple.current;
    if (!context) return;
    setError(''); setWorking(true);
    window.AppleID.auth.init({clientId: context.config.client_id, scope: 'name email',
      redirectURI: context.config.redirect_uri, nonce: context.challenge.nonce,
      state: context.challenge.state, usePopup: true});
    // Open during the click gesture so the browser permits the popup.
    window.AppleID.auth.signIn().then(result => {
      if (!active.current) return;
      const name = [result.user?.name?.firstName, result.user?.name?.lastName].filter(Boolean).join(' ');
      return finish('apple', {id_token: result.authorization.id_token, state: result.authorization.state}, name);
    }).catch(() => {
      if (active.current) {setWorking(false); setError('Apple 로그인이 취소되었거나 실패했습니다. 다시 시도해 주세요.');}
    });
  }
  function register(event) {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget));
    finish(pending.provider, {...pending.data, name: form.name, age: Number(form.age),
      service_consent: form.consent === 'on', consent_text: policy?.service_consent_text});
  }
  const locked = disabled || working;
  return <section className="social-login" aria-label={signup ? '소셜 회원가입' : '소셜 로그인'}>
    <p className="social-divider">{signup ? '소셜 계정으로 회원가입' : '소셜 계정으로 로그인'}</p>
    <p className="muted">{signup ? 'Google 또는 Apple 계정 선택 → 이름·만 나이·동의 확인 → 가입 완료' : '처음 이용하는 소셜 계정은 인증 후 회원가입으로 이어집니다.'}</p>
    <div hidden={!!pending}>
      <div ref={googleButton} className="google-login-button" hidden={!googleReady} inert={locked ? true : undefined}/>
      {!googleReady && <button type="button" className="social-button" disabled={locked || !providers || providers.google.enabled}
        onClick={()=>unavailable('Google')}>Google로 {signup ? '회원가입' : '로그인'}{(!providers || providers.google.enabled) ? ' · 준비 중' : ''}</button>}
      <button type="button" className="social-button apple-login-button" disabled={locked || !providers || (providers.apple.enabled && !appleReady)}
        onClick={()=>providers.apple.enabled ? appleLogin() : unavailable('Apple')}>
        Apple로 {signup ? '회원가입' : '로그인'}{(!providers || (providers.apple.enabled && !appleReady)) ? ' · 준비 중' : ''}
      </button>
      {providers && (!providers.google.enabled || !providers.apple.enabled) && <p className="muted" role="status">
        {[!providers.google.enabled && 'Google', !providers.apple.enabled && 'Apple'].filter(Boolean).join('·')} 계정 연결이 준비 중입니다. 연결 완료 후 사용할 수 있습니다.
      </p>}
    </div>
    {pending && <form onSubmit={register}>
      <h3>{pending.provider === 'google' ? 'Google' : 'Apple'} 회원가입 마무리</h3><p className="muted">{pending.email}</p>
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
