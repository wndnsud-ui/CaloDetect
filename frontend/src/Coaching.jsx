// 리워드몰 v1.3 M4: 전문 코칭 이용권(외부 채널 연결형, 지시서 §7-7). REWARD_COACHING_ENABLED가 꺼져 API가 404면
// 몰의 전문 코칭 탭은 기존 코칭 시안 화면(preview)을 그대로 보여 준다. 연락처는 구매자 본인 응답에만 온다.
import React, {useCallback, useEffect, useState} from 'react';
import RewardDialog from './RewardDialog';
import {MOOD_IMAGES, CHARACTER_NAME} from './Jibang';
import {Progress, etaText, fmt} from './RewardHomeCard';
import {imageUrl} from './rewardMallUtils';

const SPECS = [['', '전체'], ['nutrition', '영양'], ['diet', '다이어트'], ['exercise', '운동'], ['lifestyle', '생활습관']];
const NOTICE = '코치 정보는 시연용이에요. 코칭은 영양·생활습관 조언이며 질병 진단이나 처방은 제공하지 않아요.';
const day = value => value ? new Date(value).toLocaleDateString('ko-KR', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\. ?/g, '.').replace(/\.$/, '') : '—';
const newKey = () => (globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`);

function Avatar({coach, size = 'md', photo}) {
  if (photo && coach.profile_image) return <img className={`coach-avatar ${size} photo`} src={imageUrl(coach.profile_image)} alt={`${coach.name} 프로필 사진`}/>;
  return <span className={`coach-avatar ${size} tone-${coach.tone || 'nutrition'}`} aria-hidden="true">{coach.name?.slice(0, 1) || coach.coach_name?.slice(0, 1)}</span>;
}

function OfferCard({offer}) {
  if (!offer) return null;
  const left = offer.shortfall;
  return <div className="coach-offer">
    <div className="mall-goal-head"><b>7회 코칭 이용권</b><b>{fmt(offer.price)}P</b></div>
    <Progress value={offer.price ? offer.exchangeable / offer.price : 0} tone={left ? 'gold' : 'xp'} label="코칭 이용권까지 진행률"/>
    <div className="mall-goal-foot"><span>보유 {fmt(offer.exchangeable)}P{left ? ` · ${fmt(left)}P 남음` : ' · 지금 구매 가능'}</span><span>{left ? etaText(offer.eta_days) : ''}</span></div>
  </div>;
}

function MyPasses({api}) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [phone, setPhone] = useState('');
  useEffect(() => { api('/rewards/coach-passes').then(setData).catch(e => setError(e.message)); }, [api]);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!data) return <p className="muted" role="status">이용권을 불러오고 있어요…</p>;
  return <div className="coach-my">
    <div><p className="mall-eyebrow">MY COACHING</p><h2>내 코칭 이용권</h2></div>
    {!data.items.length && <p className="mall-panel muted">아직 구매한 이용권이 없어요.</p>}
    {data.items.map(row => <section key={row.id} className="coach-pass">
      <div className="coach-pass-head"><Avatar coach={{name: row.coach_name, tone: row.tone}}/><div><small>{row.headline}</small><b>{row.coach_name}</b></div>
        <span>{row.status === 'in_use' ? '● 사용 중' : row.status === 'refunded' ? '환불됨' : '종료'}</span></div>
      <div className="coach-pass-body">
        <div className="coach-pass-facts"><div><small>이용권</small><b>{row.sessions}회 코칭권</b></div><div><small>구매일</small><b>{day(row.purchased_at)}</b></div>
          <div><small>사용 포인트</small><b className="gold">{fmt(row.points)}P</b></div></div>
        {row.kakao_link && <div className="mall-actions"><a className="kakao-button" href={row.kakao_link} target="_blank" rel="noreferrer">카카오톡 상담하기</a>
          <button type="button" className="outline" aria-expanded={phone === row.id} onClick={() => setPhone(current => current === row.id ? '' : row.id)}>{phone === row.id ? `${row.phone} (시연용)` : '연락처 보기'}</button></div>}
        <p className="mall-note">상담 횟수는 코치와 카카오톡에서 확인해요. 남은 횟수 표시(예: 5 / 7회)는 다음 단계에서 지원할 예정이에요.</p>
      </div>
    </section>)}
    <p className="mall-small">{data.notice}</p>
  </div>;
}

// 전문 코칭 탭: 코치 찾기(분야 필터·코치 카드) + Coach Feed + 내 이용권.
export default function CoachingTab({api, preview, onOpenCoach}) {
  const [state, setState] = useState('loading'), [spec, setSpec] = useState(''), [data, setData] = useState(null), [feed, setFeed] = useState([]), [sub, setSub] = useState('find');
  const load = useCallback(() => api(`/rewards/coaches${spec ? `?specialty=${spec}` : ''}`).then(row => { setData(row); setState('on'); })
    .catch(e => setState(e.status === 404 ? 'off' : 'error')), [api, spec]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (state === 'on') api('/rewards/coaches/feed').then(r => setFeed(r.items)).catch(() => setFeed([])); }, [api, state]);
  if (state === 'off') return preview;
  if (state === 'loading' && !data) return <p className="muted" role="status">코치를 불러오고 있어요…</p>;
  if (state === 'error') return <p className="error" role="alert">코치 정보를 불러오지 못했어요.</p>;
  return <div className="coach-tab">
    <div className="mall-chips" role="tablist" aria-label="코칭 메뉴">{[['find', '코치 찾기'], ['feed', 'Coach Feed'], ['my', '내 이용권']].map(([key, label]) =>
      <button key={key} type="button" role="tab" aria-selected={sub === key} className={sub === key ? 'on' : ''} onClick={() => setSub(key)}>{label}</button>)}</div>
    {sub === 'my' ? <MyPasses api={api}/> : <>
      <section className="coach-hero"><div><p className="mall-eyebrow light">COACHING</p><h2>나에게 맞는 코치와<br/>7회 코칭을 시작해요</h2>
        <p>이용권을 사면 코치의 카카오톡이 열려요. 상담과 식단 피드백은 카카오톡에서 진행해요.</p></div><OfferCard offer={data.offer}/></section>
      <ol className="coach-steps">{[['코치 고르기', '프로필과 활동 콘텐츠 확인'], ['700P로 이용권 구매', '총 7회 피드백·상담'], ['카카오톡으로 상담', '구매 후 연락처가 열려요']].map(([t, d], i) =>
        <li key={t}><span>{i + 1}</span><p><b>{t}</b><small>{d}</small></p></li>)}</ol>
      {sub === 'find' && <>
        <div className="mall-tabs" role="tablist" aria-label="코칭 분야">{SPECS.map(([key, label]) =>
          <button key={key || 'all'} type="button" role="tab" aria-selected={spec === key} className={spec === key ? 'on' : ''} onClick={() => setSpec(key)}>{label}</button>)}</div>
        {data.items.length ? <div className="coach-grid">{data.items.map(coach => <article key={coach.id} className="coach-card">
          <div className="coach-card-head"><Avatar coach={coach}/><div><b>{coach.name}</b><small className={`ink-${coach.tone}`}>{coach.headline}</small></div></div>
          <p className="mall-small"><span aria-hidden="true" className="star">★</span> <b>{coach.rating_text}</b> · 누적 코칭 {fmt(coach.coaching_count)}회 · 시연용</p>
          <p className="coach-quote">“{coach.quote}”</p>
          {coach.pass_status === 'in_use' && <span className="coach-inuse">● 이용권 사용 중</span>}
          <button type="button" className="primary" onClick={() => onOpenCoach(coach.id)}>코칭 보기</button>
        </article>)}</div> : <p className="mall-panel muted center">이 분야 코치는 준비 중이에요.</p>}
      </>}
      {sub === 'feed' || sub === 'find' ? <section className="coach-feed" aria-labelledby="coach-feed-title"><h2 id="coach-feed-title">Coach Feed</h2>
        {feed.map(item => <button type="button" key={item.id} className="coach-feed-item" onClick={() => onOpenCoach(item.coach_id)}>
          <span className="coach-feed-head"><Avatar coach={{name: item.coach_name, tone: item.tone}} size="sm"/><b>{item.coach_name}</b><em>{item.label}</em></span>
          <b>{item.title}</b><small>{item.body}</small></button>)}</section> : null}
    </>}
    <p className="mall-small">{NOTICE}</p>
  </div>;
}

function BuyFlow({api, coach, offer, onClose, onDone}) {
  const [key] = useState(newKey), [busy, setBusy] = useState(false), [error, setError] = useState(''), [result, setResult] = useState(null);
  async function buy() {
    if (busy) return;
    setBusy(true); setError('');
    try { const row = await api(`/rewards/coaches/${coach.id}/passes`, {idem_key: key}); setResult(row); onDone(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <RewardDialog labelledBy="coach-buy-title" onClose={onClose} className={`mall-flow${result ? ' is-done' : ''}`}>
    <div className="mall-flow-art">{result ? <><img src={MOOD_IMAGES.cheer} alt={`신난 ${CHARACTER_NAME}`}/><p className="mall-hand">코치님한테 인사해 봐!</p></> : <Avatar coach={coach} size="lg"/>}</div>
    <div className="mall-flow-body">
      {!result ? <>
        <div><p className="mall-kicker orange">전문 코칭 · 7회 이용권</p><h2 id="coach-buy-title">{coach.name}</h2></div>
        <dl className="mall-sum"><div><dt>쓸 수 있는 포인트</dt><dd>{fmt(offer.exchangeable)}P</dd></div><div><dt>사용할 포인트</dt><dd className="gold">−{fmt(offer.price)}P</dd></div>
          <div className="total"><dt>구매 후 잔액</dt><dd>{fmt(Math.max(0, offer.exchangeable - offer.price))}P</dd></div></dl>
        <p className="mall-warn">구매하면 코치 연락처가 바로 공개되어 취소할 수 없어요.</p>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="mall-actions"><button type="button" className="outline" onClick={onClose}>취소</button>
          <button type="button" className="primary" onClick={buy} disabled={busy}>{busy ? '구매 중…' : `${fmt(offer.price)}P로 구매하기`}</button></div>
      </> : <>
        <div><h2 id="coach-buy-title">코칭 이용권 구매 완료</h2><p className="mall-small">{coach.name} · {result.sessions}회 코칭 이용 가능</p></div>
        <a className="kakao-button" href={result.kakao_link} target="_blank" rel="noreferrer">카카오톡으로 상담하기</a>
        <dl className="mall-sum"><div><dt>연락처</dt><dd>{result.phone} (시연용)</dd></div><div><dt>이용권 상태</dt><dd className="ok">● 사용 중</dd></div>
          <div><dt>사용 포인트</dt><dd>{fmt(result.points)}P</dd></div><div className="total"><dt>남은 포인트</dt><dd>{fmt(result.balance)}P</dd></div></dl>
        <p className="mall-small">CaloDetect는 대화 내용을 보지 않아요.</p>
        <div className="mall-actions"><button type="button" className="primary" onClick={onClose}>닫기</button></div>
      </>}
    </div>
  </RewardDialog>;
}

// 코치 상세(시안 CW2): 프로필·이렇게 관리해요·코치 활동·후기(시연용 예시)·오른쪽 이용권 카드·연락 채널·지방이 응원.
export function CoachDetail({api, id, onBack, onChanged, onCategory}) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [buying, setBuying] = useState(false), [busy, setBusy] = useState(false);
  const load = useCallback(() => api(`/rewards/coaches/${id}`).then(setData).catch(e => setError(e.message)), [api, id]);
  useEffect(() => { load(); window.scrollTo?.({top: 0}); }, [load]);
  if (error) return <div className="mall-page"><button type="button" className="text-button" onClick={onBack}>← 리워드몰</button><p className="error" role="alert">{error}</p></div>;
  if (!data) return <p className="muted" role="status">코치 정보를 불러오고 있어요…</p>;
  const offer = data.offer, mine = data.pass;
  async function goal() {
    setBusy(true);
    try { await api('/rewards/goal', {ref: `product:${offer.product_id}`}, 'PUT'); onChanged(); await load(); } finally { setBusy(false); }
  }
  return <div className="mall-page">
    <nav className="mall-crumbs" aria-label="현재 위치"><button type="button" className="mall-back" onClick={onBack} aria-label="뒤로 가기">←</button><button type="button" onClick={onBack}>리워드몰</button>
      <span aria-hidden="true">›</span><button type="button" onClick={() => onCategory('pro')}>전문 코칭</button>
      <span aria-hidden="true">›</span><button type="button" onClick={() => onCategory('pro')}>{data.crumb}</button><span aria-hidden="true">›</span><b>{data.name}</b></nav>
    <div className="coach-detail">
      <div className="coach-detail-main">
        <section className="mall-panel coach-profile" aria-label="코치 프로필">
          <div className="coach-profile-top"><Avatar coach={data} size="xl" photo/>
            <div><span className="coach-headline">{data.headline}</span><h1>{data.name}</h1>
              <p className="mall-small"><span aria-hidden="true" className="star">★</span> <b>{data.rating_text}</b> · 누적 코칭 {fmt(data.coaching_count)}회 · 시연용</p>
              <blockquote className="coach-philosophy">{data.philosophy}</blockquote>
              {data.sticky && <p className="mall-hand sticky">{data.sticky}</p>}</div></div>
          <div className="coach-profile-facts">
            <div><h2>전문 분야</h2>{data.areas.map(([, t]) => <span key={t}>✓ {t}</span>)}</div>
            <div><h2>경력</h2>{data.career.map(t => <span key={t}>{t}</span>)}<small>[자격·경력 증빙은 실제 코치 등록 시 확인]</small></div>
          </div>
          <div className="coach-intro-row"><p>{data.introduction}</p>
            {data.side_image && <div className="coach-side-photo">{data.side_note && <p className="mall-hand">{data.side_note}</p>}<img src={imageUrl(data.side_image)} alt={`${data.name} 상담 사진`}/></div>}</div>
        </section>
        <section className="mall-panel" aria-labelledby="coach-how"><div className="mall-section-head"><h2 id="coach-how" className="bar">이렇게 관리해요</h2><span className="mall-small">{data.how}</span></div>
          <ol className="coach-how">{data.steps.map(([, title, desc], i) => <li key={title}><span>{i + 1}</span><b>{title}</b><small>{desc}</small></li>)}</ol></section>
        <section aria-labelledby="coach-activity"><h2 id="coach-activity" className="mall-h2">코치 활동</h2>
          <div className="coach-activity">{data.contents.map(c => <article key={c.id} className={`mall-panel${c.image ? ' has-image' : ''}`}><div><em>{c.label}</em><b>{c.title}</b><small>{c.body}</small></div>
            {c.image && <img src={imageUrl(c.image)} alt=""/>}</article>)}</div></section>
        <section className="mall-panel" aria-labelledby="coach-reviews"><h2 id="coach-reviews">후기</h2>
          <p className="mall-small"><span aria-hidden="true" className="star">★</span> <b>{data.rating_text}</b> · 이용권 구매자만 작성 · 시연용 예시</p>
          {data.reviews.length > 0 && <div className="coach-reviews">{data.reviews.map(([text, who]) => <article key={text}><span aria-hidden="true" className="star">★★★★★</span><p>{text}</p><small>{who}</small></article>)}</div>}
          <p className="mall-note">실제 이용자 후기 영역 · 위 후기는 시연용 예시이며, 구매자 후기가 쌓이면 대체돼요.</p></section>
      </div>
      <div className="coach-detail-side" role="complementary" aria-label="코칭 이용권과 연락 채널">
        <section className="coach-pass-card" aria-labelledby="coach-pass-title"><p className="mall-kicker orange">전문 코칭 · 외부 채널</p><h2 id="coach-pass-title">7회 코칭 이용권</h2>
          <p className="mall-small">{data.name} · 총 7회 피드백·상담</p>
          <div className="coach-pass-art"><div><p className="mall-price-big">{fmt(offer.price)}<span>P</span></p>
            <ul>{data.includes.map(t => <li key={t}>{t}</li>)}</ul></div>
            <img src={imageUrl('coaches/pass_jibang.png')} alt=""/><p className="mall-hand note">건강한 식사가<br/>좋은 하루를 만듭니다.</p></div>
          {mine ? <p className="coach-inuse big">● 이용권 사용 중</p>
            : offer.shortfall ? <div className="mall-short"><div className="mall-row"><span>쓸 수 있는 포인트</span><b>{fmt(offer.exchangeable)} / {fmt(offer.price)}P</b></div>
                <Progress value={offer.exchangeable / offer.price} tone="gold" label="코칭 이용권까지 진행률"/>
                <p className="mall-small">{fmt(offer.shortfall)}P 더 모으면 돼요 · {etaText(offer.eta_days)}</p>
                {offer.is_goal ? <p className="mall-goal-now"><b>나의 목표</b> · {fmt(offer.shortfall)}P 남음</p>
                  : <button type="button" className="primary" disabled={busy} onClick={goal}>목표 리워드로 설정하기</button>}</div>
            : <button type="button" className="primary mall-cta" onClick={() => setBuying(true)}>{fmt(offer.price)}P로 이용권 구매하기 →</button>}
        </section>
        <section className="mall-panel" aria-labelledby="coach-contact"><h2 id="coach-contact">코치 연락 채널</h2>
          {mine ? <><a className="kakao-button" href={mine.kakao_link} target="_blank" rel="noreferrer">카카오톡으로 상담하기</a><div className="mall-row"><span>연락처</span><b>{mine.phone} (시연용)</b></div></>
            : <><p className="coach-locked" aria-disabled="true">🔒 카카오톡 상담 · 이용권 <b>구매 후 이용 가능</b></p><div className="mall-row"><span>연락처</span><b>010-****-****</b></div></>}
          <p className="mall-small">상담과 식단 피드백은 카카오톡에서 진행해요.<br/>CaloDetect는 대화 내용을 보지 않아요.</p></section>
        <section className="mall-panel coach-cheer"><div className="mall-cheer"><img src={MOOD_IMAGES.cheer} alt={`응원하는 ${CHARACTER_NAME}`}/><p>지속하는 포인트로<br/>코치를 만나보세요!</p></div>
          <p className="mall-small">이용권을 구매하면 코치 연락 채널이 열려요. 구매 즉시 연락처가 공개되어 취소할 수 없어요. 코칭은 영양·생활습관 조언이며 질병 진단이나 처방은 제공하지 않아요.</p></section>
        <img className="coach-side-banner" src={imageUrl('coaches/side_banner.png')} alt="좋은 식습관이 좋은 일상을 만들어요. CaloDetect와 함께 건강한 변화를 시작하세요."/>
      </div>
    </div>
    <p className="mall-small">{data.notice}</p>
    {buying && <BuyFlow api={api} coach={data} offer={offer} onClose={() => { setBuying(false); load(); }} onDone={onChanged}/>}
  </div>;
}
