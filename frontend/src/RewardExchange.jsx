// 리워드 Stage C 화면(지시서 v3 §11-5·§11-7, 시안 15-1·17·17-1·17-2): 건강상품 목록·교환 신청·쿠폰함·쿠폰 상세.
// 서버가 REWARD_EXCHANGE_ENABLED일 때만 /rewards/me에 exchange가 들어오고, 그때만 이 화면을 쓴다.
// §11-10: 알림 약속 문구, 스캔 자동 사용 안내, 바코드 이미지 저장 버튼, 밝기 조절 버튼은 만들지 않는다(밝기는 안내 문구만).
import React, {useCallback, useEffect, useState} from 'react';
import RewardDialog from './RewardDialog';
import CouponBarcode from './CouponBarcode';
import {MOOD_IMAGES, CHARACTER_NAME} from './Jibang';
import {Progress, etaText, fmt} from './RewardHomeCard';

const day = value => value ? new Date(value).toLocaleDateString('ko-KR', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\. ?/g, '.').replace(/\.$/, '') : '—';
const short = value => value ? new Date(value).toLocaleDateString('ko-KR', {timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric'}) : '—';
const STATE_LABEL = {requested: '발급 대기', held: '확인 중', issued: '사용 가능', used: '사용 완료', canceled: '취소됨', failed: '발급 안 됨'};

// 상품 이미지: image_key가 생기면 /products/<image_key>를 쓰고, 없으면 이름 첫 글자 타일(사용자가 이미지 교체 예정).
export function ProductArt({product, size = 'md'}) {
  if (product.image_key) return <span className={`product-art ${size}`}><img src={`/products/${product.image_key}`} alt=""/></span>;
  return <span className={`product-art ${size} ${product.category}`} aria-hidden="true">{product.name.slice(0, 1)}</span>;
}

// 교환 조건 패널: 가입 14일 D-n, 이번 달 n/1회, 실물 교환에 쓸 수 있는 포인트, 꾸미기 전용.
function ConditionPanel({conditions}) {
  const days = conditions.account_days_left;
  return <section className="panel exchange-conditions" aria-label="실물 교환 조건">
    <div className={days ? 'wait' : 'ok'}><span>가입 14일 이후</span><b>{days ? `D-${days}` : '충족'}</b></div>
    <div className={conditions.monthly_used >= conditions.monthly_limit ? 'wait' : 'ok'}><span>이번 달 실물 교환</span><b>{conditions.monthly_used} / {conditions.monthly_limit}회</b></div>
    <div><span>실물 교환에 쓸 수 있는 포인트</span><b className="gold">{fmt(conditions.exchangeable)}P</b></div>
    {conditions.deco_only > 0 && <p className="reward-small">가입 보너스·커뮤니티 포인트 {fmt(conditions.deco_only)}P는 꾸미기 전용이에요.</p>}
  </section>;
}

function ExchangeDialog({api, product, conditions, onClose, onDone, onTab}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [result, setResult] = useState(null);
  async function submit() {
    if (busy) return;
    setBusy(true); setError('');
    try { setResult(await api('/rewards/exchanges', {product_id: product.id})); onDone(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function cancel() {
    setBusy(true); setError('');
    try { await api(`/rewards/exchanges/${result.id}/cancel`, {}); onDone(); onClose(); }
    catch (e) { setError(e.message); setBusy(false); }
  }
  const after = conditions.exchangeable - product.price;
  if (result) return <RewardDialog labelledBy="exchange-done" onClose={onClose} className="exchange-dialog">
    <p className="reward-eyebrow">교환 신청 완료</p>
    <div className="exchange-done-head"><img src={MOOD_IMAGES.proud} alt={`뿌듯한 ${CHARACTER_NAME}`}/><div><h2 id="exchange-done">교환 신청을 받았어요</h2><p className="jb-bubble static">기록한 보람이야!</p></div></div>
    <ol className="exchange-steps">
      <li className="done"><span>1</span><div><b>교환 신청 · {fmt(product.price)}P 사용</b><small>{new Date(result.requested_at).toLocaleString('ko-KR', {timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'})}</small></div></li>
      <li className="now"><span>2</span><div><b>{result.first_exchange ? '운영자 확인 · 쿠폰 발급 중' : '쿠폰 발급 중'}</b><small>{result.first_exchange ? '첫 교환은 운영자가 확인한 뒤 발급돼요.' : '발급되면 쿠폰함에서 확인할 수 있어요.'}</small></div></li>
      <li><span>3</span><div><b>쿠폰함 도착</b><small>리워드 › 쿠폰함</small></div></li>
    </ol>
    <p className="reward-soft-note">발급 전에 취소하면 {fmt(product.price)}P를 그대로 돌려받아요. 사정으로 발급되지 않으면 자동으로 돌려드려요.</p>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="reward-actions"><button type="button" className="outline" onClick={cancel} disabled={busy}>교환 취소</button>
      <button type="button" className="primary" onClick={() => { onClose(); onTab('coupons'); }}>쿠폰함 보기</button></div>
  </RewardDialog>;
  return <RewardDialog labelledBy="exchange-title" onClose={onClose} className="exchange-dialog">
    <p className="reward-eyebrow">교환 확인</p>
    <div className="exchange-product"><ProductArt product={product}/><div><small>건강상품 · 모바일 쿠폰</small><h2 id="exchange-title">{product.name}</h2><p className="reward-small">{product.partner_label} · {product.description}</p></div></div>
    <ul className="exchange-checks">
      <li className={conditions.account_days_left ? 'no' : 'yes'}>가입 14일 이후{conditions.account_days_left ? ` · ${conditions.account_days_left}일 남음` : ''}</li>
      <li className={conditions.monthly_used >= conditions.monthly_limit ? 'no' : 'yes'}>이번 달 실물 교환 {conditions.monthly_used} / {conditions.monthly_limit}회</li>
    </ul>
    <dl className="exchange-sum">
      <div><dt>실물 교환에 쓸 수 있는 포인트</dt><dd>{fmt(conditions.exchangeable)}P</dd></div>
      <div><dt>사용할 포인트</dt><dd className="gold">−{fmt(product.price)}P</dd></div>
      <div className="total"><dt>교환 후 잔액</dt><dd>{fmt(Math.max(0, after))}P</dd></div>
    </dl>
    {conditions.deco_only > 0 && <p className="reward-small">가입 보너스·커뮤니티 포인트 {fmt(conditions.deco_only)}P는 꾸미기 전용이라 그대로 남아요.</p>}
    <p className="reward-small">받는 곳: CaloDetect 쿠폰함 (따로 입력할 정보 없음)<br/>쿠폰이 발급되기 전까지는 취소할 수 있어요.{conditions.first_hold ? ' 첫 교환은 운영자가 확인한 뒤 발급돼요.' : ''}</p>
    {!product.can_exchange && <p className="error" role="alert">{product.message}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <div className="reward-actions"><button type="button" className="outline" onClick={onClose}>취소</button>
      <button type="button" className="primary" onClick={submit} disabled={busy || !product.can_exchange}>{busy ? '신청 중…' : `${fmt(product.price)}P로 교환 신청`}</button></div>
  </RewardDialog>;
}

// 리워드 몰의 건강상품·AI 서비스·전문 코칭 탭.
export function ProductSection({api, category, onChanged, onTab, onGoal}) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [picked, setPicked] = useState(null);
  const load = useCallback(() => api('/rewards/products').then(setData).catch(e => setError(e.message)), [api]);
  useEffect(() => { load(); }, [load]);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!data) return <p className="muted" role="status">상품을 불러오고 있어요…</p>;
  const items = data.items.filter(item => item.category === category);
  return <>
    {category === 'goods' && <ConditionPanel conditions={data.conditions}/>}
    <div className="mall-grid">{items.map(item => <article key={item.id} className={`mall-item product-item${item.available ? '' : ' is-soon'}`}>
      <ProductArt product={item}/>
      <h3>{item.name}</h3><p className="reward-small">{item.description}</p><p className="mall-price">{fmt(item.price)}P</p>
      {!item.available ? <p className="reward-small">준비 중이에요</p>
        : item.shortfall > 0 ? <><Progress value={(item.price - item.shortfall) / item.price} tone="gold" label={`${item.name}까지 진행률`}/><p className="reward-small">{fmt(item.shortfall)}P 남음 · {etaText(item.eta_days).replace('지금 속도면 ', '')}</p></>
        : !item.can_exchange ? <p className="reward-small">{item.message}</p> : <p className="reward-small ok">지금 교환할 수 있어요</p>}
      {item.available && (item.can_exchange
        ? <button type="button" className="primary" onClick={() => setPicked(item)}>교환하기</button>
        : <button type="button" className="outline" onClick={() => item.shortfall ? onGoal(item) : setPicked(item)}>{item.shortfall ? '목표로 정하기' : '조건 보기'}</button>)}
    </article>)}</div>
    {category !== 'goods' && <p className="reward-small">AI 서비스·전문 코칭은 준비 중이에요. 열리면 리워드 몰에서 알려 드릴게요.</p>}
    {picked && <ExchangeDialog api={api} product={picked} conditions={data.conditions} onClose={() => setPicked(null)} onDone={() => { load(); onChanged(); }} onTab={onTab}/>}
  </>;
}

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
        <div className="coupon-head"><div><small>{coupon.partner_label} 모바일 쿠폰</small><h2 id="coupon-title">{coupon.product_name} 1개</h2></div>
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

const TABS = [['active', '사용 가능'], ['pending', '발급 대기'], ['closed', '지난 쿠폰']];
const EMPTY = {active: '사용할 수 있는 쿠폰이 아직 없어요.', pending: '발급을 기다리는 쿠폰이 없어요.', closed: '지난 쿠폰이 없어요.'};

export function Coupons({api, onChanged, onTab}) {
  const [data, setData] = useState(null), [state, setState] = useState('active'), [open, setOpen] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState('');
  const load = useCallback(() => api('/rewards/coupons').then(setData).catch(e => setError(e.message)), [api]);
  useEffect(() => { load(); }, [load]);
  async function cancel(coupon) {
    setBusy(coupon.id); setError('');
    try { await api(`/rewards/exchanges/${coupon.id}/cancel`, {}); await load(); onChanged(); } catch (e) { setError(e.message); } finally { setBusy(''); }
  }
  if (!data) return error ? <p className="error" role="alert">{error}</p> : <p className="muted" role="status">쿠폰함을 불러오고 있어요…</p>;
  const items = data.items.filter(item => item.state === state);
  const s = data.summary;
  return <div className="coupons">
    <div><p className="reward-eyebrow">MY COUPONS</p><h1 className="coupons-title">쿠폰함</h1><p className="reward-small">교환한 건강상품 쿠폰을 모아 봐요. 매장에서는 바코드를 보여주면 돼요.</p></div>
    <section className="coupon-summary">
      <div><span>사용 가능</span><b>{s.active}<small>장</small></b></div>
      <div><span>발급 대기</span><b>{s.pending}<small>장</small></b></div>
      <div><span>이번 달 실물 교환</span><b>{s.monthly_used}<small> / {s.monthly_limit}회</small></b></div>
      <div className={s.expiring_soon ? 'warn' : ''}><span>곧 만료되는 쿠폰</span><b>{s.expiring_soon ? `${s.expiring_soon}장` : '없음'}</b></div>
    </section>
    <div className="reward-chips" role="tablist" aria-label="쿠폰 상태">{TABS.map(([key, label]) => <button key={key} role="tab" aria-selected={state === key} className={state === key ? 'active' : ''} onClick={() => setState(key)}>{label}</button>)}</div>
    {error && <p className="error" role="alert">{error}</p>}
    {items.length ? <div className="coupon-grid">{items.map(coupon => <article key={coupon.id} className={`coupon-card s-${coupon.status}`}>
      <button type="button" className="coupon-card-open" onClick={() => setOpen(coupon)} aria-label={`${coupon.product_name} 쿠폰 열기, ${STATE_LABEL[coupon.status]}`}>
        <span className="coupon-card-head"><span><small>{coupon.partner_label} 모바일 쿠폰</small><b>{coupon.product_name} 1개</b></span><em>{STATE_LABEL[coupon.status]}</em></span>
        <span className="coupon-card-foot">
          <span><small>{coupon.state === 'active' ? '유효기간' : coupon.state === 'pending' ? '신청일' : '처리일'}</small><b>{coupon.state === 'active' ? `${day(coupon.coupon_expires_at)} · D-${coupon.days_left}` : short(coupon.state === 'pending' ? coupon.requested_at : coupon.used_marked_at || coupon.issued_at || coupon.requested_at)}</b></span>
          <span><small>사용 포인트</small><b>{fmt(coupon.points)}P</b></span>
          <span className="cta">{coupon.state === 'active' ? '바코드 열기' : '자세히'} →</span>
        </span>
      </button>
      {coupon.cancelable && <button type="button" className="text-button" onClick={() => cancel(coupon)} disabled={busy === coupon.id}>{busy === coupon.id ? '취소하는 중…' : `교환 취소 · ${fmt(coupon.points)}P 돌려받기`}</button>}
    </article>)}</div>
      : <div className="panel coupon-empty"><img src={MOOD_IMAGES.smile} alt=""/><p>{EMPTY[state]}</p><button type="button" className="text-button" onClick={() => onTab('mall', 'goods')}>리워드 몰 둘러보기 →</button></div>}
    <p className="reward-small">발급 전 쿠폰은 취소하면 포인트를 그대로 돌려받아요. 발급된 쿠폰은 취소할 수 없고, 사용 조건과 유효기간은 제휴사 정책을 따라요.</p>
    {open && <CouponDialog api={api} coupon={open} onClose={() => setOpen(null)} onChanged={() => { load(); onChanged(); }}/>}
  </div>;
}
