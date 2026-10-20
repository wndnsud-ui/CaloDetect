// 회원 이름·이메일과 저장한 프로필을 표시하는 계정 화면. 이름 수정과 목표 이동은 상위 콜백으로 처리한다.
// 리워드 지시서 v3 §11-11 ②: 이름 아래에 닉네임 행을 추가한다(기존 이름 폼·PUT /users/me는 그대로).
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

export default function AccountInfo({user,profile,busy,onUpdate,onGoals,api,rewards,onRewardsChanged,startNicknameOpen=false}) {
  const [nicknameOpen,setNicknameOpen]=useState(startNicknameOpen);
  return <>{rewards?.nickname_prompt==='card'&&!nicknameOpen&&<NicknamePromptCard api={api} nickname={rewards.nickname.nickname} onChoose={()=>setNicknameOpen(true)} onDismissed={onRewardsChanged}/>}
  <div className="two-col account-details"><section className="panel"><div className="profile-identity"><span>{user.name.slice(0,1)}</span><div><h2>{user.name}</h2><p>{user.email || '카카오 계정으로 로그인'}</p></div></div><form onSubmit={e=>{e.preventDefault();onUpdate(new FormData(e.currentTarget).get('name'));}}><label>이름<input name="name" required maxLength={80} defaultValue={user.name}/></label><small className="account-help">커뮤니티 피드에 표시돼요</small>{api&&<NicknameRow api={api} rewards={rewards} open={nicknameOpen} onOpen={setNicknameOpen} onChanged={onRewardsChanged}/>}<label>이메일<input readOnly value={user.email || ''} placeholder="이메일 제공 안 함"/></label><button className="primary" disabled={busy}>회원정보 저장</button></form></section><section className="panel"><h2>나의 목표</h2>{profile?<dl>{[['height','키','cm'],['weight','체중','kg'],['age','나이','세'],['target_calories','목표 칼로리','kcal']].map(([k,l,u])=><div key={k}><dt>{l}</dt><dd>{profile[k]??'미설정'} {profile[k]!=null?u:''}</dd></div>)}</dl>:<p className="muted">아직 저장된 목표가 없습니다.</p>}<button className="outline full spaced" onClick={onGoals}>목표 수정하기 →</button></section></div></>;
}
