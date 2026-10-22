// 기록 직후 보상(지시서 v3 §11-2, 시안 3·13). 식단 저장 성공 뒤 그 저장의 보상 묶음만 보여 준다.
// PC는 오른쪽 패널, 모바일은 전체 화면(CSS). 보상이 없으면 패널 대신 이유 1줄.
import React, {useEffect, useRef, useState} from 'react';
import {MOOD_IMAGES, CHARACTER_NAME} from './Jibang';
import {Progress, fmt} from './RewardHomeCard';

const MEALS = ['breakfast', 'lunch', 'dinner', 'snack'];

export default function RewardGrantPanel({api, mealId, onClose, onNavigate, onLoaded, onShare}) {
  const [data, setData] = useState(null), [error, setError] = useState('');
  const closeButton = useRef(null);
  useEffect(() => {
    let active = true;
    api(`/rewards/grants?meal_id=${encodeURIComponent(mealId)}`).then(result => { if (active) { setData(result); onLoaded?.(result); } }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [api, mealId]);
  useEffect(() => {
    if (!data?.items?.length) return undefined;
    closeButton.current?.focus();
    const key = event => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', key);
    return () => document.removeEventListener('keydown', key);
  }, [data, onClose]);
  if (error) return null;
  if (!data) return null;
  if (!data.items.length) return <div className="reward-skip" role="status">
    <span>이 기록은 포인트 지급 대상이 아니에요 · {data.skip_message || '오늘·어제 기록만 받을 수 있어요.'}</span>
    <button type="button" className="text-button" onClick={onClose} aria-label="안내 닫기">×</button>
  </div>;
  const status = data.today_meals;
  // 보유 포인트·총 XP는 이번 보상이 더해진 값이다. 기록 전 값 + 이번 보상 = 현재 값으로 풀어서 보여 준다.
  const before = data.balance - data.total_points, xpBefore = data.xp_total - data.total_xp;
  const threeLeft = ['breakfast', 'lunch', 'dinner'].filter(type => !status[type].done);
  return <aside className="reward-grant" role="dialog" aria-modal="false" aria-labelledby="reward-grant-title">
    <div className="reward-grant-head"><p className="reward-eyebrow" id="reward-grant-title">REWARD</p>
      <button ref={closeButton} type="button" className="reward-dialog-close" aria-label="보상 닫기" onClick={onClose}>×</button></div>
    <div className="reward-grant-badges">
      {data.total_points > 0 && <span className="badge-points">+{fmt(data.total_points)}P</span>}
      {data.total_xp > 0 && <span className="badge-xp">+{fmt(data.total_xp)} XP</span>}
    </div>
    <img className="reward-grant-mood jb-hop" src={MOOD_IMAGES.cheer} alt={`신난 ${CHARACTER_NAME}`}/>
    <p className="jb-bubble static center">맛있게 먹었구나! 기록 고마워</p>
    <ul className="reward-grant-items">{data.items.map(row => <li key={row.key}><span>{row.label}</span><b>{row.points ? `+${row.points}P` : ''}{row.points && row.xp ? ' · ' : ''}{row.xp ? `+${row.xp} XP` : ''}</b></li>)}</ul>
    {data.skip_message && <p className="reward-soft-note" role="status">{data.skip_message} 이 식단의 끼니 포인트·XP는 지급되지 않았어요.</p>}
    <p className="reward-small">포인트와 성장 XP는 별개예요. 이번 기록으로 받은 XP는 {fmt(data.total_xp)} XP예요.</p>
    <div className="reward-meal-cells">{MEALS.map(type => {
      const cell = status[type], now = type === data.meal_type;
      return <div key={type} className={now ? 'is-now' : cell.done ? 'is-done' : 'is-open'}><b>{cell.label}</b>
        <small>{now ? '방금' : cell.done ? '완료' : `+${type === 'snack' ? 1 : data.photo_points}P`}</small></div>;
    })}</div>
    <div className="reward-grant-level">
      <p><b>LV.{data.level} · 다음 레벨까지</b><span>{data.next_level_xp ? <>{xpBefore >= 0 && data.total_xp > 0 ? <>{fmt(xpBefore)} <b className="reward-plus">+{fmt(data.total_xp)}</b> = </> : null}{fmt(data.xp_total)} / {fmt(data.next_level_xp)} XP</> : '최고 레벨'}</span></p>
      <Progress value={data.level_progress} label="다음 레벨까지 XP 진행률"/>
      <p className="reward-small">{threeLeft.length && threeLeft.length < 3 ? `${threeLeft.map(type => status[type].label).join('·')}까지 기록하면 3끼 완료 +3P` : threeLeft.length === 0 ? '오늘 세 끼를 모두 기록했어요' : '세 끼를 모두 기록하면 +3P'} · 보유 {before >= 0 && data.total_points > 0 ? <>{fmt(before)}P <b className="reward-plus">+{fmt(data.total_points)}P</b> = <b>{fmt(data.balance)}P</b></> : `${fmt(data.balance)}P`}</p>
    </div>
    <p className="reward-small">사진으로 기록하면 +{data.photo_points}P, 사진 없이 기록하면 +{data.text_points}P예요.</p>
    {onShare && <button type="button" className="primary" onClick={() => onShare(mealId)}>커뮤니티에 남기기</button>}
    <button type="button" className="outline" onClick={() => { onClose(); onNavigate('홈'); }}>홈에서 오늘 기록 보기</button>
  </aside>;
}
