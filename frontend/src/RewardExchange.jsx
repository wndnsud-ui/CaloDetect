// 리워드 Stage C 화면: 쿠폰함·포인트 내역(리워드몰 v1.3 §7-5, 시안 W3)·쿠폰 상세. 건강상품 목록·상세·교환은 RewardMall.jsx.
// 서버가 REWARD_EXCHANGE_ENABLED일 때만 /rewards/me에 exchange가 들어오고, 그때만 이 화면을 쓴다.
// §11-10: 알림 약속 문구, 스캔 자동 사용 안내, 바코드 이미지 저장 버튼, 밝기 조절 버튼은 만들지 않는다(밝기는 안내 문구만).
import React, {useCallback, useEffect, useState} from 'react';
import RewardDialog from './RewardDialog';
import CouponBarcode from './CouponBarcode';
import {MOOD_IMAGES, CHARACTER_NAME} from './Jibang';
import {fmt} from './RewardHomeCard';
import {COUPON_TABS, couponsFor, couponChip, targetSuffix, nextMonthLabel} from './rewardMallUtils';
import './reward-mall.css';

const day = value => value ? new Date(value).toLocaleDateString('ko-KR', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\. ?/g, '.').replace(/\.$/, '') : '—';
const short = value => value ? new Date(value).toLocaleDateString('ko-KR', {timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric'}) : '—';
const STATE_LABEL = {requested: '발급 대기', held: '확인 중', issued: '사용 가능', used: '사용 완료', canceled: '취소됨', failed: '발급 안 됨'};

// 쿠폰 상세: PC는 창, 모바일은 진녹 전체 화면(CSS). 바코드·번호·복사·유효기간·사용 방법·이미 사용했어요.
function CouponDialog({api, coupon, onClose, onChanged}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [copied, setCopied] = useState(false);
  async function used() {
    setBusy(true); setError('');
    try { await api(`/rewards/coupons/${coupon.id}/used`, {}); onChanged(); onClose(); } catch (e) { setError(e.message); setBusy(false); }
  }
  async function copy() {
    try { await navigator.clipboard.writeText(coupon.coupon_code); setCopied(true); } catch { setError('복사하지 못했어요. 번호를 직접 입력해 주세요.'); }
  }
  const usable = coupon.state === 'active';
  return <RewardDialog labelledBy="coupon-title" onClose={onClose} className="coupon-dialog">
    <div className="coupon-dialog-body">
      <div className="coupon-main">
        <div className="coupon-head"><div><small>{coupon.partner_label} 모바일 쿠폰</small><h2 id="coupon-title">{couponName(coupon)}</h2></div>
          <span>{STATE_LABEL[coupon.status]}{usable && coupon.days_left != null ? ` · D-${coupon.days_left}` : ''}</span></div>
        <div className="coupon-code-box">
          {coupon.coupon_code ? <><CouponBarcode code={coupon.coupon_code} height={96}/>
            <p className="coupon-number">{coupon.coupon_code}</p>
            <button type="button" className="text-button" onClick={copy}>{copied ? '복사했어요' : '번호 복사'}</button></>
            : <p className="muted">{coupon.state === 'pending' ? (coupon.status === 'held' ? '첫 교환이라 운영자가 확인하고 있어요. 발급되면 여기에 바코드가 생겨요.' : '쿠폰을 발급하고 있어요. 발급되면 여기에 바코드가 생겨요.') : '쿠폰 번호가 없어요.'}</p>}
          <dl className="coupon-meta"><div><dt>교환일</dt><dd>{short(coupon.requested_at)} · {fmt(coupon.points)}P</dd></div>
            <div><dt>발급일</dt><dd>{short(coupon.issued_at)}</dd></div>
            <div className="gold"><dt>유효기간</dt><dd>{coupon.coupon_expires_at ? `${day(coupon.coupon_expires_at)}까지` : '—'}</dd></div>
            <div><dt>사용처</dt><dd>{coupon.partner_label}</dd></div></dl>
        </div>
      </div>
      <div className="coupon-side">
        <p className="reward-section-title">이렇게 사용해요</p>
        <ol className="coupon-howto"><li>{coupon.partner_label} 계산대에서 바코드를 보여주세요.</li><li>사용한 뒤에는 아래 <b>이미 사용했어요</b>를 눌러 주세요. 자동으로 바뀌지 않아요.</li></ol>
        <p className="reward-small">매장에서는 휴대폰이 편해요. 휴대폰에서 CaloDetect에 로그인해 <b>리워드 › 쿠폰함</b>을 열면 같은 쿠폰이 보여요. 스캔이 잘 안 되면 화면 밝기를 최대로 올려 주세요.</p>
        <p className="jb-bubble static">맛있게 먹고 또 기록해 줘!</p>
        {error && <p className="error" role="alert">{error}</p>}
        {usable && <button type="button" className="primary" onClick={used} disabled={busy}>이미 사용했어요</button>}
        <p className="reward-small">발급된 쿠폰은 취소할 수 없어요 · 사용 조건은 제휴사 정책을 따라요</p>
      </div>
    </div>
  </RewardDialog>;
}

const EMPTY = {all: '아직 교환한 쿠폰이 없어요.', active: '사용할 수 있는 쿠폰이 아직 없어요.', pending: '발급을 기다리는 쿠폰이 없어요.', closed: '지난 쿠폰이 없어요.'};
const when = value => new Date(value).toLocaleString('ko-KR', {timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false});

// 쿠폰 이름 + 수량(수량 상품만 "× N").
export function couponName(coupon) {
  return `${coupon.product_name}${coupon.quantity > 1 ? ` × ${coupon.quantity}` : ' 1개'}`;
}

function CouponCard({coupon, onOpen, onCancel, busy}) {
  const option = coupon.option_label ? ` · 옵션 ${coupon.option_label}` : '';
  const meta = coupon.state === 'pending' ? `${short(coupon.requested_at)} 교환 신청${option} · 발급 전까지 취소할 수 있어요.`
    : coupon.state === 'active' ? `${short(coupon.requested_at)} 교환${option} · 유효기간 ${day(coupon.coupon_expires_at)}까지${coupon.days_left != null ? ` (D-${coupon.days_left})` : ''}`
    : `${short(coupon.requested_at)} 교환${option} · ${couponChip(coupon)}${coupon.used_marked_at ? ` ${short(coupon.used_marked_at)}` : ''}`;
  return <article className={`my-coupon is-${coupon.state}`}>
    <div className="my-coupon-head"><div><small>{coupon.partner_label} 모바일 쿠폰</small><b>{couponName(coupon)}</b></div><em>{couponChip(coupon)}</em></div>
    <div className="my-coupon-body">
      {coupon.state === 'active' && coupon.coupon_code && <><CouponBarcode code={coupon.coupon_code} height={56}/><p className="mall-small center">{coupon.coupon_code}</p></>}
      {coupon.state === 'pending' && <ol className="mall-steps">
        <li className="done"><span>1</span><div><b>교환 신청 · {fmt(coupon.points)}P 차감</b></div></li>
        <li className="now"><span>2</span><div><b>{coupon.status === 'held' ? '운영자 확인 · 쿠폰 발급 중' : '쿠폰 발급 중 · 보통 [N시간]'}</b>{coupon.status === 'held' && <small>첫 교환은 운영자가 확인한 뒤 발급돼요</small>}</div></li>
        <li><span>3</span><div><b>쿠폰함 도착</b></div></li></ol>}
      <p className="mall-small">{meta}</p>
      {coupon.state === 'active' ? <button type="button" className="primary" onClick={() => onOpen(coupon)}>쿠폰 크게 보기</button>
        : coupon.cancelable ? <button type="button" className="outline" onClick={() => onCancel(coupon)} disabled={busy}>{busy ? '취소하는 중…' : '교환 취소'}</button>
        : <button type="button" className="outline" onClick={() => onOpen(coupon)}>자세히</button>}
    </div>
  </article>;
}

function Ledger({api}) {
  const [kind, setKind] = useState(''), [data, setData] = useState(null), [error, setError] = useState('');
  async function fetchPage(more) {
    try {
      const cursor = more && data?.next_cursor ? `cursor=${encodeURIComponent(data.next_cursor)}` : '';
      const query = [kind ? `kind=${kind}` : '', cursor].filter(Boolean).join('&');
      const page = await api(`/rewards/ledger${query ? `?${query}` : ''}`);
      setData(current => more && current ? {...page, items: [...current.items, ...page.items]} : page);
    } catch (e) { setError(e.message); }
  }
  useEffect(() => { setData(null); fetchPage(false); }, [api, kind]);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!data) return <p className="muted" role="status">포인트 내역을 불러오고 있어요…</p>;
  const s = data.summary;
  const kindLabel = row => row.kind === 'earn' ? '적립' : row.kind === 'revoke' ? (row.source === 'expire' ? '소멸' : '회수') : '사용';
  const amount = row => `${row.amount > 0 ? '+' : '−'}${fmt(Math.abs(row.amount))}P`;
  return <div className="my-rewards">
    <div className="my-ledger-sum">
      <div><small>보유</small><b>{fmt(s.balance)}P</b></div>
      <div><small>{s.month}월 적립</small><b className="plus">+{fmt(s.month_earned)}P</b></div>
      <div><small>{s.month}월 사용</small><b className="minus">−{fmt(s.month_spent)}P</b></div>
      <div><small>소멸 예정 (30일 안)</small><b>{fmt(s.expiring_soon)}P</b></div>
    </div>
    <div className="mall-chips" role="tablist" aria-label="내역 종류">{[['', '전체'], ['earn', '적립'], ['spend', '사용·회수']].map(([key, label]) =>
      <button key={key || 'all'} type="button" role="tab" aria-selected={kind === key} className={kind === key ? 'on' : ''} onClick={() => setKind(key)}>{label}</button>)}</div>
    {data.items.length ? <>
      <div className="my-table-box"><table className="my-table"><thead><tr><th scope="col">일시</th><th scope="col">내용</th><th scope="col">구분</th><th scope="col">포인트</th></tr></thead>
        <tbody>{data.items.map(row => <tr key={row.type + row.id}><td className="when">{when(row.at)}</td><td>{row.label}{targetSuffix(row.target_date)}</td><td className="kind">{kindLabel(row)}</td>
          <td className={`amt ${row.amount < 0 ? 'minus' : 'plus'}`}>{amount(row)}</td></tr>)}</tbody></table></div>
      <ul className="my-ledger-list">{data.items.map(row => <li key={row.type + row.id}><span>{row.label}{targetSuffix(row.target_date)}<small>{when(row.at)} · {kindLabel(row)}</small></span>
        <b className={row.amount < 0 ? 'minus' : 'plus'}>{amount(row)}</b></li>)}</ul>
    </> : <p className="mall-panel muted">아직 내역이 없어요.</p>}
    {data.next_cursor && <button type="button" className="text-button" onClick={() => fetchPage(true)}>더 보기</button>}
    <p className="mall-small">포인트 유효기간은 적립일부터 12개월이에요. 먼저 받은(만료가 빠른) 포인트부터 쓰여요.</p>
  </div>;
}

// 쿠폰함 · 포인트 내역(시안 W3): 상단 요약 카드 → [쿠폰함 | 포인트 내역] → 상태 탭·쿠폰 카드 / 요약·필터·표.
export function Coupons({api, me, onChanged, onTab, initialView = 'coupons'}) {
  const [view, setView] = useState(initialView), [data, setData] = useState(null), [state, setState] = useState('all'), [open, setOpen] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState('');
  const load = useCallback(() => api('/rewards/coupons').then(setData).catch(e => setError(e.message)), [api]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { setView(initialView); }, [initialView]);
  async function cancel(coupon) {
    setBusy(coupon.id); setError('');
    try { await api(`/rewards/exchanges/${coupon.id}/cancel`, {}); await load(); onChanged(); } catch (e) { setError(e.message); } finally { setBusy(''); }
  }
  const s = data?.summary;
  const used = s && s.monthly_used >= s.monthly_limit;
  const items = data ? couponsFor(data.items, state) : [];
  return <div className="mall-page my-rewards">
    <section className="my-summary"><img src={MOOD_IMAGES.cheer} alt={`응원하는 ${CHARACTER_NAME}`}/>
      <div><p className="mall-eyebrow">CALO REWARD</p><p className="balance">{fmt(me?.balance)}<span>P</span></p>
        {s && <p className="sub">이번 달 실물 교환 {s.monthly_used} / {s.monthly_limit}회{used ? ` · 다음 교환은 ${nextMonthLabel(new Date().getMonth() + 1)}부터` : ''}</p>}</div>
      <p className="mall-hand">맛있게 먹고 또 기록해 줘!</p></section>
    <div className="my-seg" role="tablist" aria-label="보기">{[['coupons', '쿠폰함'], ['ledger', '포인트 내역']].map(([key, label]) =>
      <button key={key} type="button" role="tab" aria-selected={view === key} className={view === key ? 'on' : ''} onClick={() => setView(key)}>{label}</button>)}</div>
    {view === 'ledger' ? <Ledger api={api}/> : !data ? (error ? <p className="error" role="alert">{error}</p> : <p className="muted" role="status">쿠폰함을 불러오고 있어요…</p>) : <>
      <div className="mall-chips" role="tablist" aria-label="쿠폰 상태">{COUPON_TABS.map(([key, label]) =>
        <button key={key} type="button" role="tab" aria-selected={state === key} className={state === key ? 'on' : ''} onClick={() => setState(key)}>{label}</button>)}</div>
      {error && <p className="error" role="alert">{error}</p>}
      {items.length ? <div className="my-coupons">{items.map(coupon => <CouponCard key={coupon.id} coupon={coupon} onOpen={setOpen} onCancel={cancel} busy={busy === coupon.id}/>)}</div>
        : <div className="mall-panel coupon-empty"><img src={MOOD_IMAGES.smile} alt=""/><p>{EMPTY[state]}</p><button type="button" className="text-button" onClick={() => onTab('mall', 'goods')}>리워드몰 둘러보기 →</button></div>}
      <p className="mall-small">발급된 쿠폰은 취소할 수 없어요. 쿠폰 사용 조건은 제휴사 정책을 따라요. 꾸미기 아이템은 지방이 방에서 확인할 수 있어요.</p>
    </>}
    {open && <CouponDialog api={api} coupon={open} onClose={() => setOpen(null)} onChanged={() => { load(); onChanged(); }}/>}
  </div>;
}
