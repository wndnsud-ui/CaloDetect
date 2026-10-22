// 홈 리워드 카드(지시서 v3 §11-1, 시안 1·9). 기존 홈은 그대로 두고 카드 1개만 추가한다.
// 진행률·예상 일수는 서버가 §6-12 한 함수로 계산한 값만 쓴다. 연속 기록이 끊겨도 부정 문구를 쓰지 않는다.
import React, {useState} from 'react';
import Jibang, {CHARACTER_NAME} from './Jibang';

export const fmt = value => Number(value || 0).toLocaleString('ko-KR');
export const Flame = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="#CF7150" aria-hidden="true"><path d="M12 2c1.5 5 6.5 6.5 6.5 12a6.5 6.5 0 0 1-13 0c0-3.5 2.5-5 2.5-8.5 2 1.3 3 2.6 4-3.5z"/></svg>;

export function Progress({value, label, tone = 'xp'}) {
  const percent = Math.round(Math.min(1, Math.max(0, value || 0)) * 100);
  return <div className={`reward-bar ${tone}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label={label}><span style={{width: `${percent}%`}}/></div>;
}

export function etaText(days) {
  if (days === 0) return '지금 바로 받을 수 있어요';
  return days == null ? '기록을 이어가면 계산돼요' : `지금 속도면 약 ${fmt(days)}일`;
}

export function bubbleFor(me) {
  const next = me?.actions?.find(action => ['breakfast', 'lunch', 'dinner'].includes(action.id));
  if (!me) return '';
  if (me.streak?.missed_yesterday && !me.streak?.today_recorded && me.streak?.days === 0) return '다시 시작해 볼까?';
  return next ? `${next.label.replace(' 기록', '')}도 같이 먹자!` : '오늘도 기록 고마워!';
}

// 보호권 안내. 보호권이 있을 때만 "이어갈 수 있어요"를, 없으면 회복 문구만 보여 준다(§6-3).
export function StreakNotice({api, streak, onChanged}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  if (!streak?.missed_yesterday || streak.today_recorded && streak.days > 1) return null;
  if (!streak.protect_available) return streak.days <= 1 ? <p className="reward-soft-note">어제는 쉬어 갔어요. 오늘부터 다시 시작해요.</p> : null;
  async function protect() {
    setBusy(true); setError('');
    try { await api('/rewards/streak/protect', {}); onChanged?.(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <div className="reward-protect">
    <p>어제를 놓쳤어요 · 보호권으로 <b>{streak.streak_if_protected}일 연속</b>을 이어갈 수 있어요 <small>(보유 {streak.protectors}장)</small></p>
    <button type="button" className="outline" onClick={protect} disabled={busy}>보호권 쓰기</button>
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}

const MEALS = ['breakfast', 'lunch', 'dinner', 'snack'];
const ActionIcon = ({id}) => <svg viewBox="0 0 24 24" aria-hidden="true">{id === 'snack'
  ? <><path d="M12 7c-3-2-7 0-7 5 0 5 3 9 5 9 1 0 1.3-.5 2-.5s1 .5 2 .5c2 0 5-4 5-9 0-5-4-7-7-5Z"/><path d="M12 7c0-2 1-3 3-4"/></>
  : MEALS.includes(id) ? <><path d="M3 12h18a9 9 0 0 1-18 0Z"/><path d="M7 12a5 5 0 0 1 10 0M12 4v2"/></>
  : <><rect x="4" y="4" width="16" height="16" rx="4"/><path d="m8.5 12 2.5 2.5 5-5"/></>}</svg>;
const Camera = () => <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4Z"/><circle cx="12" cy="13" r="3.5"/></svg>;

// 홈 지방이 카드. 식사 기록 안내와 리워드(레벨·포인트·목표·오늘 받을 수 있는 보상)를 한 카드로 묶는다.
// me가 없으면(비로그인·불러오는 중) 기록 안내와 기본 지방이만 보여 준다. name은 닉네임(호칭 통일).
export default function RewardHomeCard({api, name, me, onNavigate, onChanged, onRecord, loading = false}) {
  const [todayOpen, setTodayOpen] = useState(false);
  const goal = me?.goal;
  const record = type => onRecord ? onRecord(type) : onNavigate('음식 추가');
  return <section className="panel reward-home-card home-jibang-card" aria-labelledby="home-jibang-title">
    <div className="home-hero">
      <div className="home-hero-copy">
        <p className="home-hero-kicker">{name && <strong className="home-hero-name">{name}님, </strong>}매일 조금씩, 더 건강하게</p>
        <h2 id="home-jibang-title">오늘의 한 끼를<br/>기록해 보세요</h2>
        <p className="home-hero-sub">사진 한 장으로 간편하게 기록하고<br/>건강한 습관을 만들어가요!</p>
        <span className="home-hero-pill"><Camera/>사진 한 장으로 간편하게 기록해요</span>
        <button type="button" className="primary home-hero-cta" onClick={() => record()}>지금 기록할게요 <span aria-hidden="true">→</span></button>
      </div>
      <button type="button" className="home-hero-room" onClick={() => onNavigate(me ? '리워드' : '음식 추가', me ? 'room' : undefined)}
        aria-label={me ? `${CHARACTER_NAME} 방 꾸미기로 이동` : '식사 기록하러 가기'}>
        <Jibang equipment={me?.equipment} level={me?.level || 1} bubble={bubbleFor(me)} figureWidth={150} motion="breathe"
          badge={me?.streak?.days ? <><span className="reward-flame"><Flame/></span>{me.streak.days}일 연속 기록 중</> : null}/>
      </button>
    </div>
    {loading && !me && <p className="muted home-reward-loading" role="status">리워드를 불러오고 있어요…</p>}
    {me && <>
      <div className="home-reward-row">
        <button type="button" className="home-level" onClick={() => onNavigate('리워드', 'growth')} aria-label="지방이 성장 보기">
          <span className="home-level-badge" aria-hidden="true">LV</span>
          <span className="home-level-body">
            <span className="reward-level-name">LV.{me.level} · {me.level_name} {CHARACTER_NAME}</span>
            <Progress value={me.level_progress} label="다음 레벨까지 XP 진행률"/>
            <span className="reward-small">{me.next_level_xp ? `${fmt(me.xp_total)} / ${fmt(me.next_level_xp)} XP · ${etaText(me.xp_eta_days).replace('지금 속도면 ', '')}` : `${fmt(me.xp_total)} XP · 최고 레벨`}</span>
            <span className="reward-balance"><span className="reward-points">{fmt(me.balance)}<span>P</span></span><span className="reward-today">오늘 +{fmt(me.today_points)}P</span></span>
            {me.deco_only > 0 && <span className="reward-small">그중 꾸미기 전용 {fmt(me.deco_only)}P</span>}
            {me.expiring_soon > 0 && <span className="reward-expire">30일 안에 사라지는 포인트 {fmt(me.expiring_soon)}P</span>}
          </span>
        </button>
        {goal && <button type="button" className="reward-goal" onClick={() => onNavigate('리워드', 'mall')}>
          <span className="reward-goal-head"><span><span aria-hidden="true">🎁 </span>{goal.chosen ? '목표 리워드' : '다음 목표'} · {goal.name}</span><b>{fmt(goal.price)}P</b></span>
          <Progress value={goal.progress} tone="gold" label={`${goal.name}까지 진행률`}/>
          <span className="reward-goal-foot"><span>{goal.remaining ? `${fmt(goal.remaining)}P 남았어요` : '모두 모았어요'}</span><span>{etaText(goal.eta_days)}</span></span>
        </button>}
      </div>
      <StreakNotice api={api} streak={me.streak} onChanged={onChanged}/>
      {(me.actions?.length > 0 || me.today_items?.length > 0) && <div className="home-actions">
        <div className="home-actions-head"><h3>{me.actions?.length ? '오늘 더 받을 수 있어요' : '오늘 받은 보상'}</h3>
          {me.today_items?.length > 0 && <button type="button" className="text-button" aria-expanded={todayOpen} onClick={() => setTodayOpen(open => !open)}>오늘 받은 내역 {me.today_items.length}건 <span aria-hidden="true">{todayOpen ? '˄' : '›'}</span></button>}</div>
        {todayOpen && <ul className="home-today-list">{me.today_items.map(row => <li key={row.key}><span>{row.label}</span><b>{row.points ? `+${row.points}P` : ''}{row.points && row.xp ? ' · ' : ''}{row.xp ? `+${row.xp} XP` : ''}</b></li>)}</ul>}
        {me.actions?.length > 0 && <ul className="home-action-list">{me.actions.map(action => <li key={action.id}>
          <button type="button" onClick={() => record(MEALS.includes(action.id) ? action.id : undefined)}>
            <span className={`home-action-icon is-${MEALS.includes(action.id) ? (action.id === 'snack' ? 'snack' : 'meal') : 'done'}`}><ActionIcon id={action.id}/></span>
            <span className="home-action-text"><strong>{action.label}</strong><small>{action.detail}{action.goal ? ` · ${action.progress}/${action.goal}` : ''}</small></span>
            <b>+{action.points}P · +{action.xp} XP</b><span className="home-action-arrow" aria-hidden="true">›</span>
          </button></li>)}</ul>}
      </div>}
    </>}
  </section>;
}
