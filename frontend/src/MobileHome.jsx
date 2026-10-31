// 모바일 홈(시안 3안: A안 카드형 + B안 지방이 영역). HomeDashboard가 760px 이하에서 이 컴포넌트를 대신 그린다.
// 데이터 조회·날짜 선택 상태는 HomeDashboard가 갖고, 여기서는 받은 값만 표시한다.
import React from 'react';
import {JibangFigure} from './Jibang';
import {fmt} from './RewardHomeCard';
import './mobile-home.css';

const MEALS = [['breakfast', '아침'], ['lunch', '점심'], ['dinner', '저녁'], ['snack', '간식']];
const DAYS = ['일', '월', '화', '수', '목', '금', '토'];
const MACROS = [['carbs', '탄수화물', 'is-carbs'], ['protein', '단백질', 'is-protein'], ['fat', '지방', 'is-fat']];
const pct = (value, target) => target > 0 ? Math.min(100, Math.max(0, Math.round(value / target * 100))) : 0;
const num = value => Number.isFinite(value) ? Math.round(value).toLocaleString('ko-KR') : '—';
const shift = (iso, days) => { const d = new Date(`${iso}T12:00:00+09:00`); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); };
const mealCalories = meal => (meal.items || []).reduce((sum, item) => sum + (item.nutrition?.cal || 0), 0);

function headline({currentDay, date, remaining, recordedCount}) {
  if (!currentDay) return `${date.getUTCMonth() + 1}월 ${date.getUTCDate()}일 기록`;
  const mains = remaining.filter(([key]) => key !== 'snack').map(([, label]) => label);
  if (recordedCount === 0) return '오늘 첫 끼를\n기록해 볼까요?';
  if (!mains.length) return '오늘 식사 기록\n모두 마쳤어요!';
  return `${mains.join('·')}만 남았어요`;
}

export default function MobileHome({user, me, displayName, liveToday, totals, meals, target, todayDate, selectedDate, onSelectDate,
  currentDay, remaining, onAddMeal, onNavigate, homeCard, status, streak}) {
  const date = new Date(`${selectedDate}T12:00:00+09:00`);
  const week = Array.from({length: 7}, (_, i) => shift(todayDate, i - 6));
  const eaten = totals?.cal || 0;
  const left = target > 0 ? Math.max(0, Math.round(target - eaten)) : null;
  const action = me?.actions?.[0];
  const bubble = !user ? '로그인하고 함께 기록해요!' : action ? `${action.label} +${fmt(action.points)}P` : '오늘도 잘 하고 있어요!';
  const title = headline({currentDay, date, remaining, recordedCount: 4 - remaining.length});
  const ring = pct(eaten, target);

  return <div className="m-home">
    {homeCard}
    <section className="m-home-hero" aria-label="오늘의 지방이">
      <div className="m-home-hello">
        <p>{date.getUTCMonth() + 1}월 {date.getUTCDate()}일 {DAYS[date.getUTCDay()]}요일</p>
        <h1>{user && displayName ? <>{displayName}님,<br/></> : null}<span>{title}</span></h1>
        {me && <button type="button" className="m-home-level" onClick={() => onNavigate('리워드', 'growth')}
          aria-label={`LV.${me.level} ${me.level_name} 지방이, 다음 레벨까지 ${Math.round((me.level_progress || 0) * 100)}%`}>
          <b>LV.{me.level}</b><span className="m-home-xp"><span style={{width: `${Math.round((me.level_progress || 0) * 100)}%`}}/></span>
          <small>{Math.round((me.level_progress || 0) * 100)}%</small>
        </button>}
      </div>
      <button type="button" className="m-home-jibang" onClick={() => onNavigate(user ? '리워드' : '로그인', 'room')} aria-label="지방이 방 보기">
        <span className="m-home-bubble">{bubble}</span>
        <JibangFigure equipment={me?.equipment} level={me?.level || 1} width={112}/>
      </button>
    </section>

    <div className="m-home-week" role="group" aria-label="최근 7일 중 날짜 선택">
      {week.map(iso => {
        const d = new Date(`${iso}T12:00:00+09:00`), active = iso === selectedDate;
        return <button key={iso} type="button" className={active ? 'is-active' : ''} aria-pressed={active}
          aria-label={`${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 ${DAYS[d.getUTCDay()]}요일`} onClick={() => onSelectDate(iso)}>
          {DAYS[d.getUTCDay()]}<b>{d.getUTCDate()}</b>
        </button>;
      })}
    </div>

    {status}

    <section className="m-home-energy" aria-label="칼로리와 탄단지">
      <div className="m-home-ring" style={{'--m-ring': `${ring}%`}} role="img"
        aria-label={target ? `섭취 ${num(eaten)} kcal, 목표 ${num(target)} kcal` : `섭취 ${num(eaten)} kcal, 목표 미설정`}>
        <div><strong>{num(eaten)}</strong><small>{target ? `/ ${num(target)} kcal` : 'kcal'}</small></div>
      </div>
      <div className="m-home-macros">
        {MACROS.map(([key, label, tone]) => {
          const goal = liveToday?.macro_targets?.[key];
          return <div key={key} className={tone}>
            <div><span>{label}</span><b>{num(totals?.[key])}{goal ? ` / ${num(goal)}` : ''}g</b></div>
            <span className="m-home-bar"><span style={{width: `${pct(totals?.[key] || 0, goal)}%`}}/></span>
          </div>;
        })}
        {!target && user && <button type="button" className="m-home-goal" onClick={() => onNavigate('목표 설정')}>목표 칼로리 설정하기 →</button>}
      </div>
    </section>

    <section className="m-home-meals" aria-labelledby="m-home-meals-title">
      <div className="m-home-head"><h2 id="m-home-meals-title">{currentDay ? '오늘의 식사' : '이날의 식사'}</h2>
        <button type="button" className="m-link" onClick={() => onNavigate('히스토리')}>전체 보기</button></div>
      <div className="m-home-meal-grid">
        {MEALS.map(([key, label]) => {
          const records = meals.filter(meal => meal.meal_type === key);
          if (records.length) {
            const kcal = records.reduce((sum, meal) => sum + mealCalories(meal), 0);
            return <button key={key} type="button" className="m-meal is-done" onClick={() => onNavigate('히스토리')}
              aria-label={`${label} ${num(kcal)} kcal 기록됨, 기록 보기`}>
              <span>{label}</span><b>{num(kcal)}</b><small>✓ 기록</small>
            </button>;
          }
          return <button key={key} type="button" className="m-meal is-empty" onClick={() => onAddMeal(key)} aria-label={`${label} 기록하기`}>
            <span>{label}</span><b aria-hidden="true">＋</b><small>기록하기</small>
          </button>;
        })}
      </div>
    </section>

    <button type="button" className="m-home-recommend" onClick={() => onNavigate('식사 추천')}>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="5.5"/><path d="M2 3v5a2 2 0 0 0 4 0V3M4 3v18M22 21V3c-2 1-3 4-3 7v2h3"/></svg>
      <span>다음 메뉴 추천받기{left !== null && <small> · {num(left)}kcal 남음</small>}</span>
      <span aria-hidden="true">→</span>
    </button>
    {streak}
  </div>;
}
