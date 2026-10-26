// 리워드 메뉴(지시서 v3 §11-5): 리워드 몰 / 지방이 방 / 성장 · 랭킹 탭. 쿠폰함은 Stage C 플래그가 켜질 때만(현재 비활성).
// 가격·잔액·진행률·예상 일수·미션 문구는 모두 서버 응답을 쓰고 화면에서 계산하지 않는다.
import React, {useCallback, useEffect, useRef, useState} from 'react';
import Jibang, {JibangFigure, CHARACTER_NAME} from './Jibang';
import JibangBackground, {BACKGROUND_LABELS} from './JibangBackgrounds';
import RewardDialog from './RewardDialog';
import NicknameDialog from './NicknameDialog';
import StreamlitChart from './StreamlitChart';
import {Progress, StreakNotice, Flame, etaText, fmt} from './RewardHomeCard';
import {Coupons} from './RewardExchange';
import RewardMall from './RewardMall.jsx';

const TABS = [['mall', '리워드 몰'], ['room', `${CHARACTER_NAME} 방`], ['growth', '성장 · 랭킹']];
const ROOM_LINES = {bg_lv1: '여기가 우리 방이야', bg_lv2: '새싹이 돋았어!', bg_lv3: '같이 걸을래?', bg_lv4: '채소가 자라고 있어', bg_lv5: '여기까지 왔다니!', starter_bg: '깔끔해서 좋아!'};

function ShieldIcon() {
  return <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#16805C" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/><path d="M9 12l2 2 4-4"/></svg>;
}

// 장착 상태에 아이템 하나를 입힌 모습. 운동복은 몸통 의상(outfit)과 함께 입지 않는다.
function wearing(equipment, item) {
  const preview = {...equipment, [item.slot]: item.id};
  if (item.id === 'outfit_workout') delete preview.outfit;
  return preview;
}

function ItemPreview({item, equipment, level}) {
  if (item.kind === 'protector') return <span className="mall-item-art"><ShieldIcon/></span>;
  if (item.slot === 'background') return <span className="mall-item-art bg"><JibangBackground id={item.id}/></span>;
  const preview = wearing(equipment, item);
  return <span className="mall-item-art"><JibangFigure equipment={preview} level={level} width={78} motion="none" label={`${item.name} 착용 미리보기`}/></span>;
}

// 구매 창(§11-6): 미리보기·보유/사용/남는 포인트·제한 포인트 우선 사용·환불 불가 → 완료. 부족하면 필요 P·예상 일수·목표 설정.
function PurchaseDialog({api, item, me, onClose, onDone, onGoal, onNavigate}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [result, setResult] = useState(null);
  const short = Math.max(0, item.price - me.balance);
  async function buy() {
    if (busy) return;
    setBusy(true); setError('');
    try { setResult(await api(`/rewards/items/${item.id}/purchase`, {})); onDone(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function equip() {
    if (item.kind !== 'protector') await api('/rewards/equipment', {slot: item.slot, item_id: item.id}, 'PUT');
    onDone(); onClose(); onNavigate(item.kind === 'protector' ? 'growth' : 'room');
  }
  return <RewardDialog labelledBy="purchase-title" onClose={onClose} className="purchase">
    <h2 id="purchase-title">{result ? '구매했어요' : item.name}</h2>
    <ItemPreview item={item} equipment={me.equipment} level={me.level}/>
    {result ? <>
      <p className="center">{item.name}을(를) 받았어요. 남은 포인트 {fmt(result.balance)}P</p>
      {result.notice && <p className="reward-small center">{result.notice}</p>}
      <button type="button" className="primary" onClick={equip}>{item.kind === 'protector' ? '성장 화면에서 확인' : `${CHARACTER_NAME} 방에서 착용하기`}</button>
    </> : short > 0 ? <>
      <p className="center">포인트가 부족해요. <b>{fmt(short)}P</b> 더 모으면 돼요.</p>
      <p className="reward-small center">{etaText(item.eta_days)}</p>
      <button type="button" className="primary" onClick={() => onGoal(item)}>목표 리워드로 설정하기</button>
    </> : <>
      <dl className="purchase-sum"><div><dt>보유</dt><dd>{fmt(me.balance)}P</dd></div><div><dt>사용</dt><dd>-{fmt(item.price)}P</dd></div><div><dt>구매 후</dt><dd>{fmt(me.balance - item.price)}P</dd></div></dl>
      {me.deco_only > 0 && <p className="reward-small center">가입 보너스·커뮤니티 포인트 {fmt(Math.min(item.price, me.deco_only))}P가 먼저 사용돼요.</p>}
      <p className="reward-small center">디지털 아이템은 구매 후 환불되지 않아요.</p>
      <button type="button" className="primary" onClick={buy} disabled={busy}>{busy ? '처리 중…' : `${fmt(item.price)}P로 구매하기`}</button>
    </>}
    {error && <p className="error" role="alert">{error}</p>}
  </RewardDialog>;
}

// 전문 코칭 탭의 기존 시안 화면. REWARD_COACHING_ENABLED가 꺼져 코칭 API가 404면 이 화면을 그대로 보여 준다(§6-4).
function CoachingPreview() {
  return <section className="coaching-preview" aria-labelledby="coaching-title">
    <div className="panel coaching-intro"><span className="coaching-label">COACHING · 서비스 시안</span><h3 id="coaching-title">작은 습관부터, 나에게 맞는 코칭</h3><p>꾸준히 모은 포인트로 만나 보는 건강한 일상.</p><small>아래 서비스와 포인트는 예시예요. 실제 신청·포인트 차감은 제공하지 않아요.</small></div>
    <div className="coaching-grid">{[
      {icon:'01',tag:'식단 돌아보기',name:'일주일 식단 피드백',description:'최근 식단 기록을 함께 돌아보고, 다음 주에 실천할 식사 습관을 제안해요.',details:'7일 기록 리뷰 · 피드백 리포트 1회',price:1500},
      {icon:'02',tag:'나만의 루틴',name:'1:1 식습관 코칭',description:'나의 생활 패턴과 고민을 나누고, 무리 없이 이어갈 식사 루틴을 함께 정해요.',details:'온라인 상담 30분 · 실천 가이드',price:3000},
      {icon:'03',tag:'꾸준함을 함께',name:'4주 건강 습관 프로그램',description:'작은 목표를 세우고 매주 기록을 점검하며, 나에게 맞는 건강 습관을 만들어 가요.',details:'4주 프로그램 · 주 1회 체크인',price:8000}
    ].map(service=><article className="mall-item coaching-card" key={service.icon}>
      <div className="coaching-art" aria-hidden="true"><span>{service.icon}</span><svg viewBox="0 0 80 80" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><rect x="19" y="16" width="42" height="51" rx="8"/><path d="M30 16v-4h20v4M29 33l4 4 7-8M45 34h7M29 49l4 4 7-8M45 50h7"/></svg></div>
      <span className="coaching-label">{service.tag}</span><h3>{service.name}</h3><p className="coaching-description">{service.description}</p><p className="reward-small">{service.details}</p><p className="mall-price">{fmt(service.price)}P <small>예시</small></p><button type="button" className="outline" disabled>서비스 준비 중</button>
    </article>)}</div>
  </section>;
}

// 리워드몰(몰 전용, 2026-10-22 메뉴 결정): 본문은 RewardMall(v1.3). 꾸미기 그리드·미리 입어보기·구매 창은 여기서 넘긴다.
function Mall({api, me, catalog, onChanged, onTab, initialCategory}) {
  const [buying, setBuying] = useState(null), [ledger, setLedger] = useState(null);
  // 방 배경은 레벨(XP) 보상이라 몰에서 팔지 않는다. 적용은 지방이 성장 > 내 방 꾸미기에서 한다.
  const items = catalog.items.filter(item => !['starter_sticker', 'starter_hat'].includes(item.id) && item.slot !== 'background' &&
    (item.sellable || item.default_provided || item.slot === 'outfit'))
    .sort((a, b) => (a.default_provided ? 0 : a.price ?? Infinity) -
      (b.default_provided ? 0 : b.price ?? Infinity));
  const [equipping, setEquipping] = useState(false), [equipError, setEquipError] = useState('');
  // 미리 입어보기: 카드 그림을 누르면 위쪽 '내 지방이'에만 잠깐 입혀 본다. 저장하지 않는다.
  const [trying, setTrying] = useState(null);
  const tryable = item => item.kind !== 'protector';
  const shown = trying ? wearing(me.equipment, trying) : me.equipment;
  async function toggleItem(item) {
    setTrying(null);
    setEquipping(true); setEquipError('');
    try {
      await api('/rewards/equipment', {slot: item.slot, item_id: item.equipped ? null : item.id}, 'PUT');
      onChanged();
    } catch (error) { setEquipError(error.message); } finally { setEquipping(false); }
  }
  async function setGoal(item) {
    await api('/rewards/goal', {ref: `item:${item.id}`}, 'PUT');
    setBuying(null); onChanged();
  }
  async function more() {
    const page = await api(`/rewards/ledger${ledger?.next_cursor ? `?cursor=${encodeURIComponent(ledger.next_cursor)}` : ''}`);
    setLedger(current => ({items: [...(current?.items || []), ...page.items], next_cursor: page.next_cursor}));
  }
  const figure = <JibangFigure equipment={shown} level={me.level} width={80} motion="breathe"/>;
  const figureLabel = trying ? <><b>{trying.name} 미리보기</b><button type="button" className="text-button" onClick={() => setTrying(null)}>되돌리기</button></>
    : <><b>내 {CHARACTER_NAME}</b><small>바로 적용하면 여기 보여요</small></>;
  const deco = <>
    <div className="mall-grid mall-deco-grid">{items.map(item => <article key={item.id} className={`mall-item${item.equipped ? ' is-equipped' : ''}`}>
      {tryable(item) ? <button type="button" className={`mall-try${trying?.id === item.id ? ' is-trying' : ''}`} aria-pressed={trying?.id === item.id}
        aria-label={`${item.name} 내 ${CHARACTER_NAME}에게 미리 입어보기`} onClick={() => setTrying(current => current?.id === item.id ? null : item)}>
        <ItemPreview item={item} equipment={{}} level={me.level}/></button>
        : <ItemPreview item={item} equipment={{}} level={me.level}/>}
      <h3>{item.name}</h3><p className="mall-price">{item.default_provided ? '기본 제공' : item.sellable ? `${fmt(item.price)}P` : `LV.${item.level_required} 레벨 보상`}</p>
      {item.owned && item.kind !== 'protector' ? <p className="reward-small">{item.equipped ? '착용 중' : '보유'}</p>
        : item.lock_reason ? <p className="reward-small">{item.lock_reason}</p>
        : item.shortfall > 0 ? <><Progress value={me.balance / item.price} tone="gold" label={`${item.name}까지 진행률`}/><p className="reward-small">{fmt(item.shortfall)}P 남음 · {etaText(item.eta_days).replace('지금 속도면 ', '')}</p></>
        : item.kind === 'protector' && item.quantity ? <p className="reward-small">보유 {item.quantity}장</p> : null}
      {!(item.owned && item.kind !== 'protector') && !item.lock_reason && <button type="button" className={item.shortfall ? 'outline' : 'primary'} onClick={() => setBuying(item)}>{item.shortfall ? '살펴보기' : '구매하기'}</button>}
      {item.owned && item.kind !== 'protector' && <button type="button" className="outline" disabled={equipping} onClick={() => toggleItem(item)}>{item.equipped ? '빼기' : '바로 적용하기'}</button>}
    </article>)}</div>
    {equipError && <p className="error" role="alert">{equipError}</p>}
  </>;
  // 교환 기능이 꺼져 쿠폰함이 없을 때만 몰 아래에 적립·사용 내역을 둔다(켜지면 쿠폰함 > 포인트 내역).
  const ledgerBox = <details className="panel reward-ledger" onToggle={event => { if (event.currentTarget.open && !ledger) more(); }}>
    <summary>적립·사용 내역</summary>
    {ledger && <ul>{ledger.items.map(row => <li key={row.type + row.id}><span>{row.label}<small>{new Date(row.at).toLocaleString('ko-KR', {timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'})}{row.expires_at ? ` · ${new Date(row.expires_at).toLocaleDateString('ko-KR', {timeZone: 'Asia/Seoul'})}까지` : ''}</small></span><b className={row.amount < 0 ? 'minus' : ''}>{row.amount > 0 ? '+' : ''}{fmt(row.amount)}P</b></li>)}</ul>}
    {ledger?.next_cursor && <button type="button" className="text-button" onClick={more}>더 보기</button>}
    {ledger && !ledger.items.length && <p className="muted">아직 내역이 없어요.</p>}
    <p className="reward-small">포인트 유효기간은 적립일부터 12개월이에요. 먼저 받은(만료가 빠른) 포인트부터 쓰여요.</p>
  </details>;
  return <>
    <RewardMall api={api} me={me} onChanged={onChanged} onTab={onTab} initialCategory={initialCategory} figure={figure} figureLabel={figureLabel}
      deco={deco} proPreview={<CoachingPreview/>} ledger={ledgerBox}/>
    {buying && <PurchaseDialog api={api} item={buying} me={me} onClose={() => setBuying(null)} onDone={onChanged} onGoal={setGoal} onNavigate={onTab}/>}
  </>;
}

function Room({api, me, catalog, onChanged}) {
  const backgrounds = catalog.items.filter(item => item.slot === 'background');
  const decos = catalog.items.filter(item => item.owned && item.slot !== 'background' && item.kind !== 'protector');
  const applied = me.equipment.background || 'bg_lv1';
  const [selected, setSelected] = useState(applied), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const item = backgrounds.find(row => row.id === selected) || backgrounds[0];
  const locked = item && !item.owned;
  async function equip(slot, itemId) {
    setBusy(true); setError('');
    try { await api('/rewards/equipment', {slot, item_id: itemId}, 'PUT'); onChanged(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  const nextBackground = backgrounds.find(row => !row.owned && row.level_required);
  return <div className="room-layout">
    <section className="panel room-stage">
      <Jibang equipment={{...me.equipment, background: selected}} level={me.level} figureWidth={170} className="room-scene"
        bubble={locked ? null : ROOM_LINES[selected]} badge={locked ? `미리보기 · ${item.lock_reason || '아직 잠겨 있어요'}` : null}/>
      <div className="room-apply"><div><p className="room-name">{item?.level_required ? `LV.${item.level_required} · ` : ''}{BACKGROUND_LABELS[selected] || item?.name}</p>
        <p className="reward-small">{item?.default_provided ? '기본 제공 · 포인트 없이 사용할 수 있어요' : item?.sellable ? '리워드 몰 판매 배경' : '레벨 보상 · 판매하지 않아요'}</p></div>
        <button type="button" className="primary" disabled={locked || selected === applied || busy} onClick={() => equip('background', selected)}>{locked ? (item.lock_reason || '잠겨 있어요') : selected === applied ? '적용 중' : '이 배경 적용하기'}</button></div>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
    <section className="room-side">
      <div className="panel"><div className="section-heading"><h2>배경</h2><span className="reward-small">{backgrounds.filter(row => row.owned).length} / {backgrounds.length} 보유</span></div>
        <div className="room-thumbs">{backgrounds.map(row => <button type="button" key={row.id} aria-pressed={selected === row.id} className={selected === row.id ? 'selected' : ''} onClick={() => setSelected(row.id)}
          aria-label={`${BACKGROUND_LABELS[row.id]}${row.owned ? '' : ', 잠김'}`}>
          <span className={`room-thumb${row.owned ? '' : ' locked'}`}><JibangBackground id={row.id}/></span>
          <b>{row.level_required ? `LV.${row.level_required} ` : ''}{BACKGROUND_LABELS[row.id]}</b>
          <small>{applied === row.id ? '적용 중' : row.owned ? '보유' : row.lock_reason || `${fmt(row.price)}P`}</small></button>)}</div></div>
      <div className="panel"><h2>꾸미기</h2>{decos.length ? <div className="room-decos">{decos.map(row => {
        const on = me.equipment[row.slot] === row.id;
        return <button type="button" key={row.id} aria-pressed={on} className={on ? 'selected' : ''} disabled={busy} onClick={() => equip(row.slot, on ? null : row.id)}>{row.name}<small>{on ? '착용 중 · 벗기' : '착용하기'}</small></button>;
      })}</div> : <p className="muted">리워드 몰에서 꾸미기 아이템을 받을 수 있어요.</p>}</div>
      {nextBackground && <p className="reward-soft-note">다음 배경까지 {fmt(Math.max(0, me.next_level_xp ? me.next_level_xp - me.xp_total : 0))} XP · {etaText(me.xp_eta_days)}</p>}
    </section>
  </div>;
}

function Growth({api, me, onChanged}) {
  const [data, setData] = useState(null), [rank, setRank] = useState(null), [nickname, setNickname] = useState(null), [editing, setEditing] = useState(false), [error, setError] = useState('');
  const load = useCallback(async () => {
    try { const [growth, ranking, nick] = await Promise.all([api('/rewards/growth'), api('/rewards/ranking'), api('/rewards/nickname')]); setData(growth); setRank(ranking); setNickname(nick); }
    catch (e) { setError(e.message); }
  }, [api]);
  useEffect(() => { load(); }, [load, me]);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!data) return <p className="muted" role="status">성장 기록을 불러오고 있어요…</p>;
  const today = new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Seoul'}).format(new Date());
  const nextBonus = data.streak.next_bonus_in_days;
  return <>
    <section className="panel growth-head">
      <div><p className="reward-eyebrow">GROWTH</p><h1>LV.{data.level} {data.level_name} {CHARACTER_NAME}</h1><p className="reward-small">포인트를 써도 XP는 줄지 않아요 · 레벨은 내려가지 않아요</p></div>
      <div className="growth-meter"><p><b>{data.next_level_xp ? `${fmt(data.xp_total)} / ${fmt(data.next_level_xp)} XP` : `${fmt(data.xp_total)} XP`}</b><span>{data.next_level_xp ? `다음 레벨까지 ${fmt(data.xp_to_next)} XP · ${etaText(data.xp_eta_days).replace('지금 속도면 ', '')}` : '최고 레벨'}</span></p>
        <Progress value={data.level_progress} label="다음 레벨까지 XP 진행률"/></div>
      <ol className="growth-roadmap">{data.roadmap.map(step => <li key={step.level} className={step.level === data.level ? 'is-now' : step.reached ? 'is-done' : ''}>
        <span className="growth-thumb"><Jibang equipment={{}} background={`bg_lv${step.level}`} level={step.level} figureWidth={58} motion={step.level === data.level ? 'breathe' : 'none'}/></span>
        <b>LV.{step.level} {step.name}</b><small>{step.items.join(' · ') || '기본 캐릭터'}{step.points ? ` · +${fmt(step.points)}P` : ''}</small>
        <em>{step.level === data.level ? '지금' : step.reached ? '달성' : `${fmt(step.xp)} XP`}</em></li>)}</ol>
    </section>
    <div className="growth-grid">
      <section className="panel">
        <div className="section-heading"><h2>이번 주 연속 기록</h2><span className="reward-small">보호권 {data.streak.protectors}장</span></div>
        <p className="growth-streak"><Flame/> <b>{data.streak.days}일째</b></p>
        <div className="growth-week">{data.week.map(day => <div key={day.date}><small>{day.weekday}</small>
          <span className={`day ${day.state}${day.date === today ? ' is-today' : ''}`} aria-label={`${day.weekday}요일 ${{recorded: '기록함', protected: '보호됨', joined: '가입한 날', before_join: '가입 전', missed: '쉬어 감', today: '오늘', future: '예정'}[day.state]}${day.bonus_points ? ` · 보너스 +${day.bonus_points}P` : ''}`}>{day.bonus_points ? `+${day.bonus_points}P` : ''}</span></div>)}</div>
        <p className="reward-soft-note">{nextBonus ? `${nextBonus}일 더 기록하면 연속 보너스 +${data.streak.next_bonus_points}P` : ''}{data.streak.protectors ? ' · 하루 놓쳐도 보호권으로 이어갈 수 있어요.' : ' · 하루 놓쳐도 보호권(리워드 몰)으로 이어갈 수 있어요.'}</p>
        <StreakNotice api={api} streak={data.streak} onChanged={() => { onChanged(); load(); }}/>
        <p className="jb-bubble static">끊겨도 괜찮아, 다시 시작하면 돼!</p>
        <h3 className="reward-section-title">미션</h3>
        <ul className="growth-missions">{data.missions.map(mission => <li key={mission.id} className={mission.done ? 'done' : ''}><span><b>{mission.title}</b>{mission.text}</span>
          <span>{mission.done ? '완료' : `${mission.progress}/${mission.goal}`} · +{mission.points}P{mission.xp ? ` · +${mission.xp} XP` : ''}</span></li>)}</ul>
      </section>
      <section className="panel">
        <div className="section-heading"><h2>이번 주 받은 XP</h2><span className="reward-small">합계 {fmt(data.week.reduce((sum, day) => sum + day.xp, 0))} XP</span></div>
        <StreamlitChart kind="xp_week" height={178} title="요일별 받은 XP" data={{items: data.week.map(day => ({label: day.weekday, value: Math.max(0, day.xp), today: day.date === today}))}}/>
        <h3 className="reward-section-title">오늘 받은 XP · {fmt(data.today_xp.reduce((sum, row) => sum + row.xp, 0))}</h3>
        <ul className="growth-xp">{data.today_xp.map(row => <li key={row.key} className={row.counts_for_ranking ? '' : 'muted'}><span>{row.label}{row.counts_for_ranking ? '' : ' (레벨에만 반영)'}</span><b>{row.xp > 0 ? '+' : ''}{row.xp}</b></li>)}</ul>
        {!data.today_xp.length && <p className="muted">오늘 첫 기록을 남기면 XP가 쌓여요.</p>}
      </section>
      <section className="panel">
        <h2>주간 랭킹</h2><p className="reward-small">{rank?.notice}</p>
        <ol className="growth-rank">{rank?.items.map((row, index) => <li key={`${row.rank}-${index}`} className={row.is_me ? 'is-me' : ''}><span className={`medal m${row.rank}`}>{row.rank}</span><span className="name">{row.nickname}{row.is_me ? ' · 나' : ''}</span><b>{fmt(row.xp)} XP</b></li>)}</ol>
        {rank && !rank.items.length && <p className="muted">이번 주 첫 기록으로 랭킹을 시작해 보세요.</p>}
        {rank && <div className="growth-me"><span>내 순위 {rank.me.rank ? `${rank.me.rank}위` : '집계 전'} · {rank.me.nickname} · {fmt(rank.me.xp)} XP</span>
          <button type="button" className="outline" onClick={() => setEditing(true)}>닉네임 바꾸기</button></div>}
      </section>
    </div>
    {editing && <NicknameDialog api={api} current={nickname?.nickname} nextChangeDate={nickname?.next_change_date} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); load(); }}/>}
  </>;
}

// 지방이 성장 한 페이지: 성장·랭킹을 먼저, 내 방 꾸미기를 뒤에 둔다. 'room'으로 들어오면 꾸미기 위치로 스크롤한다.
function JibangPage({api, me, catalog, onChanged, focusRoom}) {
  const roomRef = useRef(null);
  useEffect(() => { if (focusRoom) roomRef.current?.scrollIntoView({behavior: 'smooth', block: 'start'}); }, [focusRoom]);
  return <>
    <Growth api={api} me={me} onChanged={onChanged}/>
    <section className="jibang-room-section" ref={roomRef} aria-labelledby="jibang-room-title">
      <h2 id="jibang-room-title" className="jibang-section-title">내 방 꾸미기</h2>
      <Room key={me.equipment.background} api={api} me={me} catalog={catalog} onChanged={onChanged}/>
    </section>
  </>;
}

export default function Rewards({api, me, tab = 'mall', onTab, onChanged, showTabs = true}) {
  const [catalog, setCatalog] = useState(null), [error, setError] = useState(''), [mallCategory, setMallCategory] = useState(null);
  // 쿠폰함 탭은 교환 기능(Stage C 플래그)이 켜져 /rewards/me에 exchange가 있을 때만 보인다.
  const tabs = me?.exchange ? [...TABS, ['coupons', '쿠폰함']] : TABS;
  const goTab = (next, category) => { if (category) setMallCategory(category); onTab(next); };
  const loadCatalog = useCallback(() => api('/rewards/items').then(setCatalog).catch(e => setError(e.message)), [api]);
  useEffect(() => { loadCatalog(); }, [loadCatalog, me]);
  const changed = () => { onChanged(); };
  return <div className="rewards-page">
    {showTabs && <div role="tablist" aria-label="리워드 메뉴" className="reward-tabs">{tabs.map(([key, label]) => <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? 'active' : ''} onClick={() => goTab(key)}>{label}</button>)}</div>}
    {error && <p className="error" role="alert">{error}</p>}
    {!me || !catalog ? <p className="muted" role="status">리워드를 불러오고 있어요…</p>
      : tab === 'room' || tab === 'growth' ? <JibangPage api={api} me={me} catalog={catalog} onChanged={changed} focusRoom={tab === 'room'}/>
      : (tab === 'coupons' || tab === 'ledger') && me.exchange ? <Coupons api={api} me={me} onChanged={changed} onTab={goTab} initialView={tab === 'ledger' ? 'ledger' : 'coupons'}/>
      : <Mall key={mallCategory || 'default'} api={api} me={me} catalog={catalog} onChanged={changed} onTab={goTab} initialCategory={mallCategory}/>}
  </div>;
}
