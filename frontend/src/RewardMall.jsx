// 리워드몰 v1.3 화면(지시서 §7, 시안 v5): 상단 포인트·목표 카드, 프로모션 슬라이더, 건강상품 그리드·오른쪽 열,
// 상품 상세(공통 템플릿)·교환 확인(웹 모달/모바일 바텀시트)·신청 완료, 콜라보 기획전. 전문 코칭은 Coaching.jsx.
// 가격·잔액·사유·예상 일수·적립 규칙은 서버 값을 쓴다. 이미지는 키만 받고, 파일이 없으면 자리표시 그림을 쓴다(§5-3).
import React, {useCallback, useEffect, useRef, useState} from 'react';
import RewardDialog from './RewardDialog';
import {MOOD_IMAGES, CHARACTER_NAME} from './Jibang';
import {Progress, etaText, fmt} from './RewardHomeCard';
import {clampQty, shouldAutoplay, nextSlide, imageUrl, nextMonthLabel, productGallery, HD_PRODUCTS} from './rewardMallUtils';
import CoachingTab, {CoachDetail} from './Coaching';
import './reward-mall.css';

const TAG_TONE = {green: 'tone-green', gold: 'tone-gold', dark: 'tone-dark', soft: 'tone-soft'};
const NOTICES = {
  deco: '디지털 아이템은 바로 쓸 수 있어요. 카드 그림을 누르면 내 지방이에게 미리 입혀 볼 수 있어요.',
  goods: '실물 교환은 가입 14일 이후 월 1회 가능해요. 모바일 쿠폰으로 쿠폰함에 발급돼요.',
  pro: '코치별 7회 코칭 이용권이에요. 구매하면 코치의 카카오톡·연락처가 열리고, 상담은 카카오톡에서 진행해요. 질병 진단이나 처방은 제공하지 않아요.',
};
const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// 상품 그림: 이미지 파일이 있으면 쓰고, 없거나 실패하면 하위분류 색 + 상품명 자리표시(aria-hidden).
export function ProductArt({product, className = '', label, image}) {
  const src = imageUrl(image || product.hero);
  const [failed, setFailed] = useState(!src);
  const tone = product.collab_brand ? 'art-collab' : product.subcategory === '음료' ? 'art-drink' : product.coach_id ? 'art-coach' : 'art-meal';
  if (!failed) return <img className={`mall-art ${className}`} src={src} alt={label || ''} onError={() => setFailed(true)}/>;
  return <span className={`mall-art mall-art-ph ${tone} ${className}`} aria-hidden="true">
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      {product.collab_brand ? <><rect x="13" y="10" width="22" height="30" rx="3"/><path d="M18 18h12M18 24h12M24 10V6"/></>
        : product.subcategory === '음료' ? <><path d="M16 8h16l-2 34H18z"/><path d="M17 18h14"/></>
        : <><path d="M8 26h32a16 16 0 0 1-32 0Z"/><path d="M16 26a8 8 0 0 1 16 0M24 12v4"/></>}
    </svg>
    <b>{product.name}</b>
  </span>;
}

function Tags({tags}) {
  return <div className="mall-tags">{(tags || []).map(tag => <span key={tag.t} className={TAG_TONE[tag.tone] || 'tone-soft'}>{tag.t}</span>)}</div>;
}

// 상단: 포인트 카드(보유·실물 교환에 쓸 수 있는 포인트·내 지방이·쿠폰함/포인트 내역 바로 가기) + 나의 목표 카드.
function MallHeader({me, figure, figureLabel, onTab, onOpenGoal}) {
  const goal = me.goal;
  return <section className="mall-hero-card" aria-label="보유 포인트와 나의 목표">
    <div className="mall-hero-me">
      <span className="mall-hero-figure">{figure}</span>
      <p className="mall-hero-label">{figureLabel}</p>
    </div>
    <div className="mall-hero-points">
      <p className="mall-eyebrow">CALO REWARD</p>
      <p className="mall-hero-balance">{fmt(me.balance)}<span>P</span></p>
      {me.exchange ? <p className="mall-hero-sub">실물 교환에 쓸 수 있는 포인트 {fmt(me.exchange.exchangeable)}P</p>
        : me.deco_only > 0 && <p className="mall-hero-sub">꾸미기 전용 {fmt(me.deco_only)}P 포함</p>}
      {me.expiring_soon > 0 && <p className="mall-hero-sub">30일 안에 사라지는 포인트 {fmt(me.expiring_soon)}P</p>}
      {me.exchange && <div className="mall-hero-links"><button type="button" onClick={() => onTab('coupons')}>쿠폰함</button><button type="button" onClick={() => onTab('ledger')}>포인트 내역</button></div>}
    </div>
    {goal && <button type="button" className="mall-goal-card" onClick={() => onOpenGoal(goal)}>
      <span className="mall-goal-head"><b>{goal.chosen ? '나의 목표' : '다음 목표'} · {goal.name}</b><b>{fmt(goal.price)}P</b></span>
      <Progress value={goal.progress} tone={goal.remaining ? 'gold' : 'xp'} label={`${goal.name}까지 진행률`}/>
      <span className="mall-goal-foot"><span>{goal.remaining ? `${fmt(goal.remaining)}P 남음` : '지금 교환할 수 있어요'}</span>
        <span>{goal.remaining ? etaText(goal.eta_days) : me.exchange ? `이번 달 교환 ${me.exchange.monthly_used} / ${me.exchange.monthly_limit}회` : ''}</span></span>
    </button>}
  </section>;
}

// 프로모션 슬라이더(M3, 현재 공개 홈페이지 Landing에서만 사용): 5초 자동 넘김, 마우스 올림·키보드 포커스 시 멈춤, 일시정지·이전·다음·점, 터치·마우스 끌어 넘기기.
// 움직임 줄이기면 자동 넘김 끔. 마우스 클릭으로 생긴 포커스는 자동 넘김을 멈추지 않는다(눌러 본 뒤 계속 멈춰 있지 않게).
export function PromoSlider({items, onOpen}) {
  const [index, setIndex] = useState(0), [paused, setPaused] = useState(false), [hovering, setHovering] = useState(false), [focused, setFocused] = useState(false);
  const drag = useRef(null), dragged = useRef(false);
  const count = items.length;
  const auto = shouldAutoplay({reducedMotion: reducedMotion(), paused, hovering, focused, count});
  useEffect(() => {
    if (!auto) return undefined;
    const timer = setInterval(() => setIndex(i => nextSlide(i, 1, count)), 5000);
    return () => clearInterval(timer);
  }, [auto, count]);
  if (!count) return null;
  const go = step => setIndex(i => nextSlide(i, step, count));
  return <section className="mall-slider" aria-roledescription="carousel" aria-label="리워드 프로모션">
    <div className="mall-slider-frame" onMouseEnter={() => setHovering(true)} onMouseLeave={() => setHovering(false)}
      onFocus={event => setFocused(event.target.matches?.(':focus-visible') ?? true)} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false); }}>
      <div className="mall-slider-track" style={{transform: `translateX(-${index * 100}%)`, touchAction: 'pan-y'}}
        onPointerDown={event => { if (event.button === 0) drag.current = {x: event.clientX, moved: false}; }}
        onPointerMove={event => { if (drag.current && Math.abs(event.clientX - drag.current.x) > 8) drag.current.moved = true; }}
        onPointerUp={event => { const start = drag.current; drag.current = null; if (!start) return;
          dragged.current = start.moved; const dx = event.clientX - start.x; if (dx < -40) go(1); else if (dx > 40) go(-1); }}
        onPointerCancel={() => { drag.current = null; }}
        onDragStart={event => event.preventDefault()}
        onClickCapture={event => { if (dragged.current) { dragged.current = false; event.preventDefault(); event.stopPropagation(); } }}>
        {items.map((slide, i) => <div key={slide.id} data-promotion={slide.id} className={`mall-slide theme-${slide.theme}`} role="group" aria-roledescription="slide"
          aria-label={`${i + 1} / ${count}`} aria-hidden={i !== index}>
          <div className="mall-slide-copy">
            <span className="mall-eyebrow">{slide.eyebrow}</span>
            <h2>{slide.title}</h2>
            <p>{slide.desc}</p>
            <span className="mall-slide-chip">{slide.chip}</span>
            <button type="button" className="mall-slide-cta" tabIndex={i === index ? 0 : -1} onClick={() => onOpen(slide)}>{slide.cta}</button>
          </div>
          <div className="mall-slide-art"><ProductArt product={{name: slide.title.split('\n').pop(), hero: slide.image, collab_brand: slide.target === 'collab' || slide.id === 'premium30' ? 'collab' : null,
            subcategory: slide.id === 'drink' ? '음료' : '간편식'}}/></div>
        </div>)}
      </div>
      <div className="mall-slider-controls">
        <button type="button" aria-label={paused ? '자동 넘김 재생' : '자동 넘김 일시정지'} onClick={() => setPaused(p => !p)}>
          {paused ? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4l13 8-13 8z"/></svg>
            : <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>}</button>
        <button type="button" aria-label="이전 슬라이드" onClick={() => go(-1)}><svg viewBox="0 0 24 24" aria-hidden="true" className="line"><path d="M15 18l-6-6 6-6"/></svg></button>
        <span aria-live="polite">{index + 1} / {count}</span>
        <button type="button" aria-label="다음 슬라이드" onClick={() => go(1)}><svg viewBox="0 0 24 24" aria-hidden="true" className="line"><path d="M9 6l6 6-6 6"/></svg></button>
      </div>
    </div>
    <div className="mall-slider-dots" role="group" aria-label="슬라이드 선택">{items.map((slide, i) =>
      <button key={slide.id} type="button" aria-label={`${i + 1}번 슬라이드 보기`} aria-current={i === index} onClick={() => setIndex(i)}><span/></button>)}</div>
  </section>;
}

function statusLine(item) {
  if (item.can_exchange) return {text: '지금 교환 가능', ok: true};
  if (item.reason === 'insufficient') return {text: `${fmt(item.shortfall)}P 남음 · ${etaText(item.eta_days).replace('지금 속도면 ', '')}`, ok: false};
  return {text: item.message, ok: false};
}

function ProductCard({item, exchangeable, onOpen}) {
  const status = statusLine(item);
  const ratio = item.price ? Math.min(1, exchangeable / item.price) : 0;
  return <article className={`mall-card${item.is_goal ? ' is-goal' : ''}`}>
    <button type="button" className="mall-card-open" onClick={() => onOpen(item)} aria-label={`${item.name} ${fmt(item.price)}포인트, ${status.text}`}>
      <ProductArt product={item} className="mall-card-art"/>
      <span className="mall-card-title"><span>{item.name}</span><b>{fmt(item.price)}P</b></span>
    </button>
    <span className={`mall-bar ${status.ok ? 'ok' : 'short'}`} aria-hidden="true"><span style={{width: `${Math.round(ratio * 100)}%`}}/></span>
    <span id={`product-status-${item.id}`} className={`mall-card-status${status.ok ? ' ok' : ''}`}>{status.text}</span>
    <button type="button" className="primary mall-exchange-button" disabled={!item.can_exchange}
      aria-describedby={`product-status-${item.id}`} onClick={() => onOpen(item)}>{item.can_exchange ? '교환하기' : '교환 불가'}</button>
  </article>;
}

function MallSide({me, conditions, showCollab, onCollab}) {
  const rules = me.earn_rules || [];
  return <div className="mall-side" role="complementary" aria-label="교환 조건과 포인트 안내">
    {showCollab && <button type="button" className="mall-collab-banner" onClick={onCollab}>
      <span className="mall-eyebrow gold">SPECIAL COLLABORATION</span><b>CaloPoint × 태극사계<br/>프리미엄 홍삼 기획전</b><span>180P부터 교환 ›</span></button>}
    {conditions && <section className="mall-panel">
      <h2>실물 교환 조건</h2>
      <div className="mall-row"><span>가입 14일 이후</span><b className={conditions.account_days_left ? 'wait' : 'ok'}>{conditions.account_days_left ? `D-${conditions.account_days_left}` : '충족'}</b></div>
      <div className="mall-row"><span>이번 달 실물 교환</span><b className={conditions.monthly_used >= conditions.monthly_limit ? 'wait' : 'ok'}>{conditions.monthly_used} / {conditions.monthly_limit}회</b></div>
      <div className="mall-row"><span>실물 교환에 쓸 수 있는 포인트</span><b>{fmt(conditions.exchangeable)}P</b></div>
      {conditions.deco_only > 0 && <p className="mall-small">가입 보너스·커뮤니티 포인트 {fmt(conditions.deco_only)}P는 꾸미기에만 쓸 수 있어요.</p>}
    </section>}
    {rules.length > 0 && <details className="mall-panel mall-earn-toggle">
      <summary>포인트 모으는 법</summary>
      <div className="mall-earn-content">
      {rules.map(rule => <div className="mall-row" key={rule.id}><span>{rule.label}<small>{rule.condition}</small></span><b className="gold">+{rule.points}P</b></div>)}
      <div className="mall-cheer"><img src={MOOD_IMAGES.proud} alt={`뿌듯한 ${CHARACTER_NAME}`}/><p>오늘 기록하면 목표가 가까워져!</p></div>
      </div>
    </details>}
    <p className="mall-small">포인트는 적립일로부터 12개월간 유효하고, 먼저 받은 포인트부터 사용돼요. 건강상품은 모바일 쿠폰으로 쿠폰함에 발급돼요. 시연용 가상 상품·리뷰예요.</p>
  </div>;
}

// 교환 확인 → 신청 완료(웹 모달, 모바일 ≤640px 바텀시트·완료는 전체 화면).
function ExchangeFlow({api, product, option, quantity, conditions, onClose, onChanged, onTab, onNextGoal}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [result, setResult] = useState(null);
  const total = product.price * quantity;
  const choice = option ? `옵션 · ${option}` : product.max_qty > 1 ? `수량 · ${quantity}개` : '';
  async function submit() {
    if (busy) return;
    setBusy(true); setError('');
    try { setResult(await api('/rewards/exchanges', {product_id: product.id, option, quantity})); onChanged(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function cancel() {
    setBusy(true); setError('');
    try { await api(`/rewards/exchanges/${result.id}/cancel`, {}); onChanged(); onClose(); } catch (e) { setError(e.message); setBusy(false); }
  }
  return <RewardDialog labelledBy="mall-flow-title" onClose={onClose} className={`mall-flow${result ? ' is-done' : ''}`}>
    <div className="mall-flow-art">
      {result ? <><img src={MOOD_IMAGES.proud} alt={`뿌듯한 ${CHARACTER_NAME}`}/><p className="mall-hand">기록한 보람이야!</p></>
        : <ProductArt product={product}/>}
    </div>
    <div className="mall-flow-body">
      {!result ? <>
        <p className="mall-step">① 교환 확인</p>
        <div><p className="mall-kicker">건강상품 · 모바일 쿠폰</p><h2 id="mall-flow-title">{product.name}</h2>{choice && <p className="mall-small">{choice}</p>}</div>
        <ul className="mall-checks">
          <li className={conditions.account_days_left ? 'no' : 'yes'}>가입 14일 이후{conditions.account_days_left ? ` · ${conditions.account_days_left}일 남음` : ''}</li>
          <li className={conditions.monthly_used >= conditions.monthly_limit ? 'no' : 'yes'}>이번 달 실물 교환 {conditions.monthly_used} / {conditions.monthly_limit}회</li>
        </ul>
        <dl className="mall-sum">
          <div><dt>실물 교환에 쓸 수 있는 포인트</dt><dd>{fmt(conditions.exchangeable)}P</dd></div>
          <div><dt>사용할 포인트</dt><dd className="gold">−{fmt(total)}P</dd></div>
          <div className="total"><dt>교환 후 잔액</dt><dd>{fmt(Math.max(0, conditions.exchangeable - total))}P</dd></div>
        </dl>
        <p className="mall-small">받는 곳: CaloDetect 쿠폰함 (따로 입력할 정보 없음)<br/>쿠폰이 발급되기 전까지는 취소할 수 있어요.</p>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="mall-actions"><button type="button" className="outline" onClick={onClose}>취소</button>
          <button type="button" className="primary" onClick={submit} disabled={busy}>{busy ? '신청 중…' : `${fmt(total)}P로 교환 신청`}</button></div>
      </> : <>
        <p className="mall-step">② 신청 완료</p>
        <div><h2 id="mall-flow-title">교환 신청을 받았어요</h2><p className="mall-small">{product.name}{choice ? ` · ${choice}` : ''}</p></div>
        <ol className="mall-steps">
          <li className="done"><span>1</span><div><b>교환 신청 · {fmt(result.points)}P 차감</b><small>남은 포인트 {fmt(Math.max(0, conditions.exchangeable - result.points))}P</small></div></li>
          <li className="now"><span>2</span><div><b>쿠폰 발급 중</b><small>{result.first_exchange ? '첫 교환은 운영자가 확인한 뒤 발급돼요' : '보통 [N시간] 안에 발급돼요'}</small></div></li>
          <li><span>3</span><div><b>쿠폰함 도착</b><small>내 정보 & 설정 › 쿠폰함</small></div></li>
        </ol>
        <p className="mall-note">발급 전에 취소하면 {fmt(result.points)}P를 그대로 돌려받아요.</p>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="mall-actions three"><button type="button" className="outline" onClick={cancel} disabled={busy}>교환 취소</button>
          <button type="button" className="outline" onClick={() => { onClose(); onNextGoal(); }}>다음 목표 정하기</button>
          <button type="button" className="primary" onClick={() => { onClose(); onTab('coupons'); }}>쿠폰함 보기</button></div>
      </>}
    </div>
  </RewardDialog>;
}

// 상품 상세(공통 템플릿 1개, §7-3).
function ProductDetail({api, id, onBack, onChanged, onTab, onOpen, onCollab, onCategory}) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [option, setOption] = useState(null), [qty, setQty] = useState(1);
  const [confirming, setConfirming] = useState(false), [busy, setBusy] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const load = useCallback(() => api(`/rewards/products/${id}`).then(row => { setData(row); setOption(current => current ?? row.options[0] ?? null); }).catch(e => setError(e.message)), [api, id]);
  useEffect(() => { setData(null); setQty(1); setOption(null); setSelectedImage(null); load(); window.scrollTo?.({top: 0}); }, [load]);
  if (error) return <div className="mall-page"><button type="button" className="text-button" onClick={onBack}>← 리워드몰</button><p className="error" role="alert">{error}</p></div>;
  if (!data) return <p className="muted" role="status">상품을 불러오고 있어요…</p>;
  const content = data.content || {};
  const gallery = productGallery(data);
  const activeImage = selectedImage || gallery[0];
  const c = data.conditions;
  const quantity = clampQty(qty, data.max_qty);
  const total = data.price * quantity;
  const short = Math.max(0, total - c.exchangeable);
  const blockReason = data.reason && !['insufficient'].includes(data.reason) ? data.message : null;
  async function goal() {
    setBusy(true);
    try { await api('/rewards/goal', {ref: `product:${data.id}`}, 'PUT'); onChanged(); await load(); } finally { setBusy(false); }
  }
  return <div className="mall-page">
    <nav className="mall-crumbs" aria-label="현재 위치"><button type="button" className="mall-back" onClick={onBack} aria-label="뒤로 가기">←</button><button type="button" onClick={onBack}>리워드몰</button>
      <span aria-hidden="true">›</span><button type="button" onClick={() => onCategory('goods')}>건강상품</button>
      {data.subcategory && <><span aria-hidden="true">›</span><span>{data.subcategory}</span></>}<span aria-hidden="true">›</span><b>{data.name}</b></nav>
    <div className="mall-detail">
      <section className="mall-detail-media" aria-label="상품 이미지">
        <ProductArt key={activeImage} product={data} image={activeImage} className="mall-detail-hero" label={`${data.name} 이미지 ${Math.max(0, gallery.indexOf(activeImage)) + 1}`}/>
        {gallery.length > 1 && <div className="mall-thumbs" role="group" aria-label="상품 이미지 선택">{gallery.map((key, i) =>
          <button type="button" key={key} aria-label={`${data.name} 이미지 ${i + 1} 보기`} aria-pressed={activeImage === key}
            className={activeImage === key ? 'on' : ''} onClick={() => setSelectedImage(key)}>
            <img src={imageUrl(key)} alt=""/>
          </button>)}</div>}
      </section>
      <section className="mall-detail-info" aria-label="상품 정보">
        <Tags tags={data.tags}/>
        <div><p className="mall-kicker">건강상품 · 모바일 쿠폰</p><h1>{data.name}</h1></div>
        {content.summary && <p className="mall-summary-text">{content.summary}</p>}
        {content.rating && <p className="mall-rating"><span aria-hidden="true">★★★★★</span><b>{content.rating}</b><span>리뷰 {content.review_count}개</span><em>시연용</em></p>}
        <div className="mall-buy">
          <div className="mall-price-row"><div><p className="mall-small">필요 포인트</p><p className="mall-price-big">{fmt(total)}<span>P</span></p></div>
            <div className="mall-price-side">{data.list_price_won && <s>{fmt(data.list_price_won * quantity)}원</s>}<span className="tone-gold">100% 포인트 교환</span></div></div>
          {data.options.length > 0 && <div role="radiogroup" aria-label="맛 선택" className="mall-options">{data.options.map(name =>
            <button key={name} type="button" role="radio" aria-checked={option === name} className={option === name ? 'on' : ''} onClick={() => setOption(name)}>{name}</button>)}</div>}
          {data.max_qty > 1 && <div className="mall-qty"><span>수량</span><div>
            <button type="button" aria-label="수량 줄이기" disabled={quantity <= 1} onClick={() => setQty(clampQty(quantity - 1, data.max_qty))}>−</button>
            <span aria-live="polite" aria-label={`수량 ${quantity}개`}>{quantity}</span>
            <button type="button" aria-label="수량 늘리기" disabled={quantity >= data.max_qty} onClick={() => setQty(clampQty(quantity + 1, data.max_qty))}>+</button></div></div>}
          <ul className="mall-checks">
            <li className={c.account_days_left ? 'no' : 'yes'}>가입 14일 이후{c.account_days_left ? ` · ${c.account_days_left}일 남음` : ''}</li>
            <li className={c.monthly_used >= c.monthly_limit ? 'no' : 'yes'}>이번 달 실물 교환 {c.monthly_used} / {c.monthly_limit}회</li>
          </ul>
          {data.is_goal && short > 0 ? <div className="mall-short"><p className="mall-goal-now"><b>나의 목표</b> · {fmt(short)}P 남음</p>
              <Progress value={c.exchangeable / total} tone="gold" label={`${data.name}까지 진행률`}/>
              <p className="mall-small">{quantity === 1 ? etaText(data.eta_days) : '기록을 이어가면 가까워져요'}</p>
              <button type="button" className="outline" onClick={onBack}>목표 바꾸기</button></div>
            : blockReason ? <p className="mall-block" role="status">{blockReason}</p>
            : short > 0 ? <div className="mall-short">
              <Progress value={c.exchangeable / total} tone="gold" label={`${data.name}까지 진행률`}/>
              <p className="mall-small">{fmt(short)}P 더 모으면 돼요{quantity === 1 && data.eta_days ? ` · ${etaText(data.eta_days)}` : ''}</p>
              <button type="button" className="primary" disabled={busy} onClick={goal}>목표 리워드로 설정하기</button></div>
            : <button type="button" className="primary mall-cta" onClick={() => setConfirming(true)} disabled={data.options.length > 0 && !option}>{fmt(total)}P로 교환 신청</button>}
        </div>
        {content.features?.length > 0 && <div className="mall-features">{content.features.map(([icon, title, desc]) => <div key={title}>
          <FeatureIcon name={icon}/><b>{title}</b><small>{desc}</small></div>)}</div>}
        <dl className="mall-info">
          <dt>받는 곳</dt><dd>CaloDetect 쿠폰함 (따로 입력할 정보 없음)</dd>
          <dt>발급</dt><dd>교환 신청 후 [N시간] 안에 모바일 쿠폰 발급</dd>
          <dt>취소</dt><dd>쿠폰 발급 전까지 가능 · 포인트 그대로 환불</dd>
          {content.storage && <><dt>보관방법</dt><dd>{content.storage}</dd></>}
        </dl>
      </section>
    </div>
    {content.rating && <section className="mall-panel mall-satisfaction" aria-label="리뷰 요약">
      <div><h2>교환한 사람들의 만족도</h2><p className="mall-small">★ {content.rating} · 리뷰 {content.review_count}개 · 시연용 수치예요.</p></div>
      {content.satisfaction?.length > 0 && <div className="mall-sat-bars">{content.satisfaction.map(([label, value]) => <div key={label}>
        <span>{label}</span><span className="mall-bar ok" role="img" aria-label={`${label} ${value}%`}><span style={{width: `${value}%`}}/></span><b>{value}%</b></div>)}</div>}
    </section>}
    {HD_PRODUCTS.has(data.id) ? <section className="mall-product-story" aria-label="상품 소개">
      <ProductArt product={data} image={gallery[gallery.length - 1]} label={`${data.name} 상품 사진`}/>
      <div><p className="mall-eyebrow">CALOPOINT SELECTION</p><h2>{data.name}</h2>
        <p>{content.summary || data.description}</p>
        {content.storage && <p className="mall-small">보관방법 · {content.storage}</p>}
      </div>
    </section> : content.detail && <section className="mall-detail-ad" aria-label="상품 상세 이미지" style={{background: content.detail_bg || '#F7EEE3'}}><img src={imageUrl(content.detail)} alt={`${data.name} 상세 이미지`}/></section>}
    {data.collab_brand && data.related.length > 0 && <section aria-labelledby="related-title" className="mall-related">
      <div className="mall-section-head"><h2 id="related-title">함께 만나보세요</h2><button type="button" className="text-button" onClick={onCollab}>기획전 전체 보기 ›</button></div>
      <div className="mall-related-grid">{data.related.map(item => <button type="button" key={item.id} className="mall-related-card" onClick={() => onOpen(item)}>
        <ProductArt product={item}/><span><b>{item.name}</b><small>{item.line || item.description}</small><strong>{fmt(item.price)}P {item.list_price_won && <s>{fmt(item.list_price_won)}원</s>}</strong></span></button>)}</div>
    </section>}
    {confirming && <ExchangeFlow api={api} product={data} option={data.options.length ? option : null} quantity={quantity} conditions={c}
      onClose={() => { setConfirming(false); load(); }} onChanged={onChanged} onTab={onTab} onNextGoal={onBack}/>}
  </div>;
}

function FeatureIcon({name}) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {name === 'dumbbell' && <path d="M6 7v10M9 5v14M15 5v14M18 7v10M9 12h6M3 10v4M21 10v4"/>}
    {name === 'leaf' && <><path d="M5 19C5 10 11 5 20 4c0 9-5 15-14 15z"/><path d="M5 19l8-8"/></>}
    {name === 'bolt' && <path d="M13 2L4 14h7l-1 8 9-12h-7z"/>}
    {name === 'clock' && <><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/></>}
    {name === 'gift' && <><rect x="3" y="8" width="18" height="13" rx="1"/><path d="M3 12h18M12 8v13M12 8c-2-4-7-4-7-1s5 1 7 1c2 0 7 2 7-1s-5-3-7 1z"/></>}
    {name === 'shield' && <><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></>}
  </svg>;
}

// 콜라보 기획전(M3, 플래그 on일 때만): 배너 → 혜택 → 추천 3종 → 브랜드 스토리 → 전체 라인업 → 이벤트 배너. 사진 대신 텍스트 배너.
function CollabPage({api, onBack, onOpen}) {
  const lineup = useRef(null);
  const browse = () => { lineup.current?.scrollIntoView({behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start'}); lineup.current?.focus({preventScroll: true}); };
  const [data, setData] = useState(null), [error, setError] = useState('');
  useEffect(() => { api('/rewards/collab').then(setData).catch(e => setError(e.message)); window.scrollTo?.({top: 0}); }, [api]);
  if (error) return <div className="mall-page"><button type="button" className="text-button" onClick={onBack}>← 리워드몰</button><p className="error" role="alert">{error}</p></div>;
  if (!data) return <p className="muted" role="status">기획전을 불러오고 있어요…</p>;
  const ex = data.conditions.exchangeable;
  return <div className="mall-page">
    <nav className="mall-crumbs" aria-label="현재 위치"><button type="button" className="mall-back" onClick={onBack} aria-label="뒤로 가기">←</button><button type="button" onClick={onBack}>리워드몰</button><span aria-hidden="true">›</span><b>CaloPoint × {data.brand} 기획전</b></nav>
    {data.images?.banner ? <button type="button" className="collab-image collab-browse" aria-label="콜라보 제품 둘러보기" onClick={browse} style={{background: '#F3EBDF'}}>
        <img src={imageUrl(data.images.banner)} alt={`CaloPoint × ${data.brand}, 프리미엄 홍삼을 포인트로 만나는 특별한 기회`}/></button>
      : <section className="collab-banner" aria-label="기획전 소개"><span className="mall-eyebrow gold">SPECIAL COLLABORATION</span>
        <h1>CaloPoint × {data.brand}</h1><p>프리미엄 홍삼을 포인트로 만나는 특별한 기회</p><small>{data.notice}</small></section>}
    <section className="mall-panel collab-perks">{[['기간 한정 이벤트', '지금만 만날 수 있는 시연용 혜택'], ['포인트 교환', 'CaloPoint로 만나는 프리미엄 홍삼'], ['선물 추천', '가족, 지인에게 마음을 전하세요']].map(([t, d]) =>
      <div key={t}><span aria-hidden="true"><FeatureIcon name="gift"/></span><p><b>{t}</b><small>{d}</small></p></div>)}</section>
    <section aria-labelledby="collab-picks" className="collab-picks"><p className="mall-eyebrow">SPECIAL ITEM</p><h2 id="collab-picks">CaloPoint × {data.brand} 추천 상품</h2>
      <div className="collab-grid">{data.picks.map(item => { const ok = item.price <= ex; return <article key={item.id} className="mall-card">
        <ProductArt product={item} image={item.pick_image} className="mall-card-art"/><span className="mall-card-title"><span>{item.name}</span><b>{fmt(item.price)}P</b></span>
        <span className="mall-small">{item.pick_desc}</span>
        <span className={`mall-bar ${ok ? 'ok' : 'short'}`} aria-hidden="true"><span style={{width: `${Math.round(Math.min(1, ex / item.price) * 100)}%`}}/></span>
        <span className={`mall-card-status${ok ? ' ok' : ''}`}>{ok ? '지금 교환 가능' : `${fmt(item.price - ex)}P 남음`}</span>
        <button type="button" className="primary" onClick={() => onOpen(item)}>상품 보기</button></article>; })}</div></section>
    {data.images?.story ? <section className="collab-image" aria-label="브랜드 스토리" style={{background: '#4A3528'}}>
        <img src={imageUrl(data.images.story)} alt={`계절이 빚어낸 한국적인 건강, ${data.brand} 브랜드 스토리`}/></section>
      : <section className="collab-story" aria-label="브랜드 스토리"><span className="mall-eyebrow gold">BRAND STORY</span><h2>계절이 빚어낸 한국적인 건강, {data.brand}</h2>
        <p>홍삼 브랜드와 함께하는 시연용 기획전이에요. 실제 제휴·판매와 관계없어요.</p></section>}
    <section ref={lineup} tabIndex={-1} className="mall-panel collab-lineup" aria-labelledby="collab-lineup"><h2 id="collab-lineup">{data.brand} 전체 상품</h2>
      <div className="collab-lineup-grid">{data.lineup.map(item => <button key={item.id} type="button" onClick={() => onOpen(item)}><ProductArt product={item} image={item.lineup_image}/><span>{item.name}</span><small>{fmt(item.price)}P</small></button>)}</div></section>
    {data.images?.event ? <section className="collab-image" aria-label="콜라보 이벤트" style={{background: '#3F2D24'}}>
        <img src={imageUrl(data.images.event)} alt="CaloPoint와 함께하는 더 건강한 오늘, 콜라보 이벤트"/></section>
      : <section className="collab-event" aria-label="콜라보 이벤트"><h2>CaloPoint와 함께하는 더 건강한 오늘</h2><p>기록으로 모은 포인트로 기획전 상품을 교환해 보세요.</p></section>}
    <p className="mall-small">{data.notice} 건강상품은 모바일 쿠폰으로 쿠폰함에 발급되고, 실물 교환은 가입 14일 이후 월 1회 가능해요.</p>
  </div>;
}

// 리워드몰 본문: 목록 ↔ 상품 상세 ↔ 기획전 ↔ 코치 상세. 뒤로 가기는 같은 탭·스크롤 위치로 돌아간다(§7-0).
export default function RewardMall({api, me, onChanged, onTab, initialCategory, figure, figureLabel, deco, proPreview, ledger}) {
  const [category, setCategory] = useState(initialCategory || (me.exchange ? 'goods' : 'deco'));
  const [view, setView] = useState({kind: 'list'});
  const [data, setData] = useState(null), [promos, setPromos] = useState([]), [error, setError] = useState('');
  const scroll = useRef(0);
  const load = useCallback(() => {
    if (!me.exchange) return;
    api('/rewards/products').then(setData).catch(e => setError(e.message));
    api('/rewards/promotions').then(r => setPromos(r.items)).catch(() => setPromos([]));
  }, [api, !!me.exchange]);
  useEffect(() => { load(); }, [load, me.balance, me.goal?.ref]);
  // 하위 화면(상세·기획전·코치)은 브라우저 기록에 남긴다. 브라우저 뒤로 가기·화면의 뒤로 가기 모두 같은 탭·스크롤 위치의 목록으로 돌아온다.
  const toList = () => { setView({kind: 'list'}); load(); requestAnimationFrame(() => window.scrollTo?.({top: scroll.current})); };
  useEffect(() => {
    const pop = event => { const next = event.state?.rewardMall; if (next && next.kind !== 'list') setView(next); else toList(); };
    window.addEventListener('popstate', pop);
    return () => window.removeEventListener('popstate', pop);
  }, [load]);
  const open = next => {
    if (view.kind === 'list') scroll.current = window.scrollY || 0;
    try { window.history.pushState({...(window.history.state || {}), rewardMall: next}, ''); } catch {}
    setView(next);
  };
  const back = () => { if (window.history.state?.rewardMall) window.history.back(); else toList(); };
  const showCategory = key => { setCategory(key); scroll.current = 0; back(); };
  const changed = () => { onChanged(); load(); };
  const openProduct = item => open(item.coach_id ? {kind: 'coach', id: item.coach_id} : {kind: 'product', id: item.id});
  const showCollab = promos.some(p => p.target === 'collab');
  function openGoal(goal) {
    if (goal.product_id) openProduct({id: goal.product_id, coach_id: goal.coach_id});
    else setCategory('deco');
  }
  if (view.kind === 'product') return <ProductDetail api={api} id={view.id} onBack={back} onChanged={changed} onTab={onTab} onOpen={openProduct} onCollab={() => open({kind: 'collab'})} onCategory={showCategory}/>;
  if (view.kind === 'collab') return <CollabPage api={api} onBack={back} onOpen={openProduct}/>;
  if (view.kind === 'coach') return <CoachDetail api={api} id={view.id} onBack={back} onChanged={changed} onCategory={showCategory}/>;
  const items = (data?.items || []).filter(item => item.category === category);
  const tabs = [['deco', '꾸미기'], ['goods', '건강상품'], ['pro', '전문 코칭']];
  return <div className="mall-page">
    {/* 프로모션 슬라이더는 사용자 결정(2026-10-26)으로 리워드몰에서 빼고 공개 홈페이지에서만 쓴다. promos는 기획전 배너 표시 여부에 계속 쓴다. */}
    <MallHeader me={me} figure={figure} figureLabel={figureLabel} onTab={onTab} onOpenGoal={openGoal}/>
    <div className="mall-layout">
      <section className="mall-main" aria-label="리워드 상품">
        <div className="mall-tabs" role="tablist" aria-label="리워드 종류">{tabs.map(([key, label]) =>
          <button key={key} type="button" role="tab" aria-selected={category === key} className={category === key ? 'on' : ''} onClick={() => setCategory(key)}>{label}</button>)}</div>
        <p className="mall-notice">{NOTICES[category]}</p>
        {error && <p className="error" role="alert">{error}</p>}
        {category === 'deco' ? deco
          : category === 'pro' ? <CoachingTab api={api} me={me} preview={proPreview} onOpenCoach={id => open({kind: 'coach', id})}/>
          : !me.exchange ? <section className="mall-panel mall-soon"><h3>건강상품</h3><p>준비 중이에요. 제휴와 운영 기준이 확정되면 열려요.</p>
              <p className="mall-small">실물 교환은 가입 14일 이후, 한 달에 한 번 신청할 수 있게 준비하고 있어요. 가입 보너스·커뮤니티 포인트는 꾸미기에만 쓸 수 있어요.</p></section>
          : !data ? <p className="muted" role="status">상품을 불러오고 있어요…</p>
          : <div className="mall-grid-v5">{items.map(item => <ProductCard key={item.id} item={item} exchangeable={data.conditions.exchangeable}
              onOpen={openProduct}/>)}</div>}
      </section>
      <MallSide me={me} conditions={category === 'goods' ? data?.conditions : null} showCollab={category === 'goods' && showCollab} onCollab={() => open({kind: 'collab'})}/>
    </div>
    {!me.exchange && ledger}
    {me.exchange && data?.conditions?.monthly_used >= data?.conditions?.monthly_limit && category === 'goods' &&
      <p className="mall-small center">이번 달 실물 교환을 신청했어요. 다음 교환은 {nextMonthLabel(new Date().getMonth() + 1)}부터 할 수 있어요.</p>}
  </div>;
}
