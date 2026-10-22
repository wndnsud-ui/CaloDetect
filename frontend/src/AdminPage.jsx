// 관리자 화면(사용자 결정 2026-10-20: 웹앱 안에서 처리). role=admin 계정에만 메뉴가 보이고 서버도 get_admin으로 다시 검사한다.
// 탭: 교환 신청 처리(보류·쿠폰 발급·실패) / 닉네임 관리(부적절 닉네임 초기화). 쿠폰 번호는 관리자 응답에도 내려오지 않는다.
import React, {useCallback, useEffect, useState} from 'react';
import RewardDialog from './RewardDialog';

const STATUS = {requested: '대기', held: '보류', issued: '발급', used: '사용', canceled: '취소', failed: '실패'};
const FILTERS = [['', '전체'], ['requested', '대기'], ['held', '보류'], ['issued', '발급'], ['used', '사용'], ['canceled', '취소'], ['failed', '실패']];
const when = value => value ? new Date(value).toLocaleString('ko-KR', {timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'}) : '—';
const kstDate = days => new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Seoul'}).format(new Date(Date.now() + days * 86400000));

function IssueDialog({api, row, onClose, onDone}) {
  const [code, setCode] = useState(''), [expires, setExpires] = useState(kstDate(30)), [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      await api(`/admin/rewards/exchanges/${row.id}/issue`, {coupon_code: code.trim(), coupon_expires_at: `${expires}T23:59:59+09:00`});
      onDone('쿠폰을 발급했어요. 회원 쿠폰함에서 확인할 수 있어요.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <RewardDialog labelledBy="issue-title" onClose={onClose}>
    <form className="admin-form" onSubmit={submit}>
      <h2 id="issue-title">쿠폰 발급 · {row.product_name}</h2>
      <p className="muted">{row.nickname || `회원 ${row.user_id}`} · {row.points.toLocaleString()}P{row.first_exchange ? ' · 첫 교환' : ''}</p>
      <label>쿠폰 번호<input value={code} onChange={e => setCode(e.target.value)} required minLength={4} maxLength={64} pattern="[0-9A-Za-z\-]{4,64}" autoComplete="off" placeholder="예: CALO-ENERGY-0001"/></label>
      <small className="muted">영문·숫자·-로 4~64자. 저장할 때 암호화되고 관리자 화면에는 다시 보이지 않아요.</small>
      <label>유효기간(이날까지)<input type="date" value={expires} min={kstDate(1)} onChange={e => setExpires(e.target.value)} required/></label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="reward-actions"><button type="button" className="outline" onClick={onClose}>취소</button><button className="primary" disabled={busy || code.trim().length < 4}>{busy ? '발급 중…' : '발급하기'}</button></div>
    </form>
  </RewardDialog>;
}

function ConfirmDialog({title, body, action, onClose, onConfirm}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function confirm() {
    setBusy(true); setError('');
    try { await onConfirm(); } catch (e) { setError(e.message); setBusy(false); }
  }
  return <RewardDialog labelledBy="confirm-title" onClose={onClose}>
    <h2 id="confirm-title">{title}</h2><p>{body}</p>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="reward-actions"><button type="button" className="outline" onClick={onClose}>닫기</button><button type="button" className="primary" onClick={confirm} disabled={busy}>{action}</button></div>
  </RewardDialog>;
}

function Exchanges({api}) {
  const [filter, setFilter] = useState(''), [rows, setRows] = useState(null), [all, setAll] = useState([]), [error, setError] = useState(''), [disabled, setDisabled] = useState(false);
  const [issuing, setIssuing] = useState(null), [confirming, setConfirming] = useState(null), [notice, setNotice] = useState('');
  const load = useCallback(async () => {
    try {
      const [list, every] = await Promise.all([api(`/admin/rewards/exchanges${filter ? `?status=${filter}` : ''}`), api('/admin/rewards/exchanges')]);
      setRows(list.items); setAll(every.items); setDisabled(false); setError('');
    } catch (e) { if (e.status === 404) setDisabled(true); else setError(e.message); }
  }, [api, filter]);
  useEffect(() => { load(); }, [load]);
  const done = text => { setIssuing(null); setConfirming(null); setNotice(text); load(); };
  if (disabled) return <section className="panel admin-empty"><h2>교환 기능이 꺼져 있어요</h2>
    <p className="muted">Backend `.env`에 <code>REWARD_EXCHANGE_ENABLED=true</code>와 <code>REWARD_EXCHANGE_GLOBAL_MONTHLY_CAP</code>(예: 100)을 넣고 Backend를 다시 시작하면 열려요.</p></section>;
  const count = status => all.filter(row => row.status === status).length;
  return <>
    <div className="admin-stats">{[['requested', '발급 대기'], ['held', '보류(확인 필요)'], ['issued', '발급됨'], ['used', '사용 완료']].map(([key, label]) =>
      <button type="button" key={key} className={filter === key ? 'active' : ''} onClick={() => setFilter(filter === key ? '' : key)}><span>{label}</span><b>{count(key)}</b></button>)}</div>
    <div className="reward-chips" role="tablist" aria-label="상태">{FILTERS.map(([key, label]) => <button key={key || 'all'} role="tab" aria-selected={filter === key} className={filter === key ? 'active' : ''} onClick={() => setFilter(key)}>{label}</button>)}</div>
    {notice && <p className="notice" role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!rows ? <p className="muted" role="status">불러오는 중…</p> : !rows.length ? <section className="panel admin-empty"><p className="muted">해당하는 교환 신청이 없어요.</p></section> :
      <div className="admin-list">{rows.map(row => <article key={row.id} className={`panel admin-row status-${row.status}`}>
        <div className="admin-row-main">
          <p className="admin-row-title"><b>{row.product_name}{row.quantity > 1 ? ` × ${row.quantity}` : ''}</b>{row.option_label && <span>옵션 {row.option_label}</span>}<span>{row.points.toLocaleString()}P</span>{row.first_exchange && <em className="admin-badge first">첫 교환</em>}<em className={`admin-badge s-${row.status}`}>{STATUS[row.status]}</em></p>
          <p className="muted">{row.nickname || '닉네임 없음'} · 회원 {row.user_id} · 가입 {row.signup_days}일 · 신청 {when(row.requested_at)}{row.issued_at ? ` · 발급 ${when(row.issued_at)}` : ''}{row.coupon_expires_at ? ` · ${row.coupon_expires_at.slice(0, 10)}까지` : ''}</p>
          <p className="admin-signal">최근 30일 기록 <b>{row.recorded_days_30}일</b> · 식단 {row.meals_30}건 · 사진 비율 <b>{Math.round(row.photo_ratio_30 * 100)}%</b></p>
        </div>
        {['requested', 'held'].includes(row.status) && <div className="admin-row-actions">
          <button type="button" className="primary" onClick={() => setIssuing(row)}>쿠폰 발급</button>
          {row.status === 'requested' && <button type="button" className="outline" onClick={() => setConfirming({row, kind: 'hold'})}>보류</button>}
          <button type="button" className="text-button danger" onClick={() => setConfirming({row, kind: 'fail'})}>실패 처리</button>
        </div>}
      </article>)}</div>}
    {issuing && <IssueDialog api={api} row={issuing} onClose={() => setIssuing(null)} onDone={done}/>}
    {confirming && <ConfirmDialog title={confirming.kind === 'hold' ? '이 신청을 보류할까요?' : '실패 처리할까요?'}
      body={confirming.kind === 'hold' ? '보류한 신청은 회원이 직접 취소할 수 있고, 확인 뒤 발급하거나 실패 처리할 수 있어요.' : `${confirming.row.points.toLocaleString()}P를 회원에게 모두 돌려주고 이번 달 교환 횟수도 되돌려요.`}
      action={confirming.kind === 'hold' ? '보류하기' : '실패 처리하기'} onClose={() => setConfirming(null)}
      onConfirm={async () => { await api(`/admin/rewards/exchanges/${confirming.row.id}/${confirming.kind}`, {}); done(confirming.kind === 'hold' ? '보류했어요.' : '실패 처리하고 포인트를 돌려줬어요.'); }}/>}
  </>;
}

function Nicknames({api}) {
  const [query, setQuery] = useState(''), [rows, setRows] = useState(null), [error, setError] = useState(''), [target, setTarget] = useState(null), [notice, setNotice] = useState('');
  const search = useCallback(async (text = '') => {
    try { setRows((await api(`/admin/rewards/nicknames${text ? `?q=${encodeURIComponent(text)}` : ''}`)).items); setError(''); } catch (e) { setError(e.message); }
  }, [api]);
  useEffect(() => { search(); }, [search]);
  return <>
    <form className="admin-search" onSubmit={e => { e.preventDefault(); search(query.trim()); }}>
      <label className="sr-only" htmlFor="admin-nickname-q">닉네임 검색</label>
      <input id="admin-nickname-q" value={query} onChange={e => setQuery(e.target.value)} placeholder="닉네임 일부로 검색" maxLength={40}/>
      <button className="primary">검색</button>
    </form>
    <p className="muted">부적절한 닉네임을 자동 생성 닉네임으로 되돌려요. 회원은 바로 한 번 다시 바꿀 수 있어요.</p>
    {notice && <p className="notice" role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {rows && <div className="admin-list">{rows.map(row => <article key={row.user_id} className="panel admin-row">
      <div className="admin-row-main"><p className="admin-row-title"><b>{row.nickname}</b>{row.generated && <em className="admin-badge">자동 생성</em>}</p>
        <p className="muted">회원 {row.user_id} · {row.set_via === 'signup' ? '가입 때 정함' : row.set_via === 'admin_reset' ? '관리자 초기화' : row.set_via === 'generated' ? '자동 생성' : '직접 변경'} · 최근 변경 {when(row.updated_at)}</p></div>
      <div className="admin-row-actions"><button type="button" className="outline" onClick={() => setTarget(row)}>초기화</button></div>
    </article>)}{!rows.length && <p className="muted">찾는 닉네임이 없어요.</p>}</div>}
    {target && <ConfirmDialog title={`'${target.nickname}'을(를) 초기화할까요?`} body="자동 생성 닉네임으로 바뀌고, 회원은 변경 주기 제한 없이 한 번 다시 정할 수 있어요." action="초기화하기"
      onClose={() => setTarget(null)} onConfirm={async () => { await api(`/admin/rewards/nicknames/${target.user_id}/reset`, {}); setTarget(null); setNotice('닉네임을 초기화했어요.'); search(query.trim()); }}/>}
  </>;
}

// 리워드몰 v1.3 M4: 코칭 이용권 목록·수동 환불(코치 연락 불가 같은 예외). 코칭 플래그가 꺼져 404면 안내만.
function CoachPasses({api}) {
  const [rows, setRows] = useState(null), [off, setOff] = useState(false), [error, setError] = useState(''), [target, setTarget] = useState(null), [notice, setNotice] = useState('');
  const load = () => api('/admin/rewards/coach-passes').then(data => setRows(data.items)).catch(e => e.status === 404 ? setOff(true) : setError(e.message));
  useEffect(() => { load(); }, []);
  if (off) return <section className="panel admin-empty"><p className="muted">전문 코칭 이용권 기능이 꺼져 있어요(REWARD_COACHING_ENABLED=false).</p></section>;
  return <>
    {notice && <p className="notice" role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!rows ? <p className="muted" role="status">불러오는 중…</p> : !rows.length ? <section className="panel admin-empty"><p className="muted">구매된 이용권이 없어요.</p></section> :
      <div className="admin-list">{rows.map(row => <article key={row.id} className="panel admin-row">
        <div className="admin-row-main"><p className="admin-row-title"><b>{row.coach_id} 코치 · 7회</b><span>{row.points.toLocaleString()}P</span><em className="admin-badge">{{in_use: '사용 중', refunded: '환불됨', completed: '종료'}[row.status]}</em></p>
          <p className="muted">{row.nickname || '닉네임 없음'} · 회원 {row.user_id} · 구매 {when(row.purchased_at)}{row.closed_at ? ` · 종료 ${when(row.closed_at)}` : ''}</p></div>
        {row.status === 'in_use' && <div className="admin-row-actions"><button type="button" className="outline" onClick={() => setTarget(row)}>수동 환불</button></div>}
      </article>)}</div>}
    {target && <ConfirmDialog title="이용권을 환불할까요?" body={`${target.points.toLocaleString()}P를 회원에게 돌려주고 이용권을 '환불됨'으로 바꿔요. 코치 연락 불가 같은 예외에만 쓰세요.`} action="환불하기"
      onClose={() => setTarget(null)} onConfirm={async () => { await api(`/admin/rewards/coach-passes/${target.id}/refund`, {}); setTarget(null); setNotice('환불했어요.'); load(); }}/>}
  </>;
}

export default function AdminPage({api}) {
  const [tab, setTab] = useState('exchanges');
  return <div className="admin-page">
    <div><p className="eyebrow">ADMIN</p><h1>관리자</h1><p className="muted">건강상품 교환 신청을 처리하고 닉네임을 관리해요. 실제 쿠폰 번호는 제휴처에서 받은 값을 입력하세요.</p></div>
    <div className="reward-tabs" role="tablist" aria-label="관리자 메뉴">{[['exchanges', '교환 신청 처리'], ['passes', '코칭 이용권'], ['nicknames', '닉네임 관리']].map(([key, label]) =>
      <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</div>
    {tab === 'exchanges' ? <Exchanges api={api}/> : tab === 'passes' ? <CoachPasses api={api}/> : <Nicknames api={api}/>}
  </div>;
}
