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

export default function RewardHomeCard({api, me, onNavigate, onChanged}) {
  if (!me) return <section className="panel reward-home-card"><p className="muted" role="status">리워드를 불러오고 있어요…</p></section>;
  const goal = me.goal;
  return <section className="panel reward-home-card" aria-labelledby="reward-home-title">
    <div className="section-heading"><h2 id="reward-home-title">오늘의 건강 리워드</h2><button className="text-button" onClick={() => onNavigate('리워드', 'growth')}>성장 보기 →</button></div>
    <div className="reward-home-top">
      <button type="button" className="reward-home-room" onClick={() => onNavigate('리워드', 'room')} aria-label={`${CHARACTER_NAME} 방 꾸미기로 이동`}>
        <Jibang equipment={me.equipment} level={me.level} bubble={bubbleFor(me)} figureWidth={118} motion="breathe"
          badge={me.streak?.days ? <><span className="reward-flame"><Flame/></span>{me.streak.days}일 연속 기록 중</> : null}/>
      </button>
      <div className="reward-home-stats">
        <p className="reward-level-name">LV.{me.level} · {me.level_name} {CHARACTER_NAME}</p>
        <Progress value={me.level_progress} label="다음 레벨까지 XP 진행률"/>
        <p className="reward-small">{me.next_level_xp ? `${fmt(me.xp_total)} / ${fmt(me.next_level_xp)} XP · ${etaText(me.xp_eta_days).replace('지금 속도면 ', '')}` : `${fmt(me.xp_total)} XP · 최고 레벨`}</p>
        <div className="reward-balance"><p className="reward-points">{fmt(me.balance)}<span>P</span></p><p className="reward-today">오늘 +{fmt(me.today_points)}P</p></div>
        {me.deco_only > 0 && <p className="reward-small">그중 꾸미기 전용 {fmt(me.deco_only)}P</p>}
        {me.expiring_soon > 0 && <p className="reward-expire">30일 안에 사라지는 포인트 {fmt(me.expiring_soon)}P</p>}
      </div>
    </div>
    <StreakNotice api={api} streak={me.streak} onChanged={onChanged}/>
    {goal && <button type="button" className="reward-goal" onClick={() => onNavigate('리워드', 'mall')}>
      <span className="reward-goal-head"><span>{goal.chosen ? '목표 리워드' : '다음 목표'} · {goal.name}</span><b>{fmt(goal.price)}P</b></span>
      <Progress value={goal.progress} tone="gold" label={`${goal.name}까지 진행률`}/>
      <span className="reward-goal-foot"><span>{goal.remaining ? `${fmt(goal.remaining)}P 남았어요` : '모두 모았어요'}</span><span>{etaText(goal.eta_days)}</span></span>
    </button>}
    {me.actions?.length > 0 && <div className="reward-actions-list"><p>오늘 더 받을 수 있어요</p>
      <ul>{me.actions.map(action => <li key={action.id}><span className="dot" aria-hidden="true"/><span>{action.label}<small>{action.detail}{action.goal ? ` · ${action.progress}/${action.goal}` : ''}</small></span><b>+{action.points}P · +{action.xp} XP</b></li>)}</ul></div>}
    {me.today_items?.length > 0 && <details className="reward-today-list"><summary>오늘 받은 내역 {me.today_items.length}건</summary>
      <ul>{me.today_items.map(row => <li key={row.key}><span>{row.label}</span><b>{row.points ? `+${row.points}P` : ''}{row.points && row.xp ? ' · ' : ''}{row.xp ? `+${row.xp} XP` : ''}</b></li>)}</ul></details>}
  </section>;
}
