// 회원 이름·이메일과 저장한 프로필을 표시하는 계정 화면. 목표 이동은 상위 콜백으로 처리한다.
// 계정 이름·이메일은 읽기 전용이다(2026-10-27 사용자 결정). 화면에 보이는 이름은 이름 아래 닉네임 행에서 바꾼다.
// 나의 목표의 만 나이는 목표 설정 화면과 같이 회원가입 때 입력한 나이(user.age)를 우선 표시한다.
import React, {useEffect, useState} from 'react';
import NicknameField from './NicknameField';
import NicknamePromptCard from './NicknamePromptCard';

// 닉네임 행: 지금 값·자동 생성 배지·바꾸기(같은 자리에서 펼침). 이름 폼 안에 있어도 Enter가 이름 저장을 보내지 않게 막는다.
function NicknameRow({api, rewards, open, onOpen, onChanged}) {
  const [info, setInfo] = useState(null), [value, setValue] = useState(''), [valid, setValid] = useState(false);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [status, setStatus] = useState('');
  const load = () => api('/rewards/nickname').then(setInfo).catch(e => setError(e.message));
  useEffect(() => { load(); }, [api, rewards?.nickname?.nickname]);
  useEffect(() => { if (open && info) setValue(info.nickname || ''); }, [open, info]);
  async function save() {
    if (!valid || busy) return;
    setBusy(true); setError('');
    try { await api('/rewards/nickname', {nickname: value.trim(), via: 'account'}, 'PUT'); onOpen(false); setStatus('닉네임을 바꿨어요'); await load(); onChanged?.(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  if (!info) return null;

  return <div className="account-nickname" onKeyDown={event => { if (event.key === 'Enter' && event.target.tagName === 'INPUT') { event.preventDefault(); save(); } }}>
    <p className="account-nickname-label">닉네임</p>
    {open ? <>
      <NicknameField api={api} label="새 닉네임" value={value} onChange={next => { setValue(next); setError(''); }} onValidity={setValid} serverError={error} autoFocus/>
      <div className="reward-actions"><button type="button" className="outline" onClick={() => onOpen(false)}>취소</button><button type="button" className="primary" onClick={save} disabled={!valid || busy}>저장</button></div>
    </> : <div className="account-nickname-value">
      <strong>{info.nickname || '아직 없어요'}</strong>{info.generated && <span className="nickname-badge">자동으로 만든 닉네임</span>}
      <button type="button" className="text-button" onClick={() => onOpen(true)}>닉네임 바꾸기</button>
    </div>}
    <small className="account-help">주간 랭킹에 표시돼요 · 언제든 바꿀 수 있어요</small>
    {status && <p className="notice" role="status">{status}</p>}
  </div>;
}

export default function AccountInfo({user,profile,onGoals,api,rewards,onRewardsChanged,startNicknameOpen=false}) {
  const [nicknameOpen,setNicknameOpen]=useState(startNicknameOpen);
  return <>{rewards?.nickname_prompt==='card'&&!nicknameOpen&&<NicknamePromptCard api={api} nickname={rewards.nickname.nickname} onChoose={()=>setNicknameOpen(true)} onDismissed={onRewardsChanged}/>}
  <div className="two-col account-details"><section className="panel"><div className="profile-identity"><span>{(rewards?.nickname?.nickname||user.name).slice(0,1)}</span><div><h2>{rewards?.nickname?.nickname||user.name}</h2><p>{user.email || '카카오 계정으로 로그인'}</p></div></div><div className="account-fields"><label>이름<input className="account-readonly" readOnly value={user.name || ''}/></label><small className="account-help">계정 이름은 바꿀 수 없어요 · 화면에는 닉네임이 표시돼요</small>{api&&<NicknameRow api={api} rewards={rewards} open={nicknameOpen} onOpen={setNicknameOpen} onChanged={onRewardsChanged}/>}<label>이메일<input className="account-readonly" readOnly value={user.email || ''} placeholder="이메일 제공 안 함"/></label><small className="account-help">이메일은 바꿀 수 없어요</small></div></section><section className="panel"><h2>나의 목표</h2>{profile?<dl>{[['height','키','cm'],['weight','체중','kg'],['age','만 나이','세'],['target_calories','목표 칼로리','kcal']].map(([k,l,u])=>{const v=k==='age'?(user.age??profile.age):profile[k];return <div key={k}><dt>{l}</dt><dd>{v??'미설정'} {v!=null?u:''}</dd></div>})}</dl>:<p className="muted">아직 저장된 목표가 없습니다.</p>}<button className="outline full spaced" onClick={onGoals}>목표 수정하기 →</button></section></div></>;
}
