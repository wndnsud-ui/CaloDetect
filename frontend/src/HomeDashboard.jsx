// 실제 식단·보상 데이터와 기존 지방이 이미지를 사용하는 회원 홈.
import React, {useEffect, useState} from 'react';
import SavedMeals from './SavedMeals';
import Jibang, {JibangFigure} from './Jibang';
import {Progress, StreakNotice, fmt} from './RewardHomeCard';
import MobileHome from './MobileHome';
import useIsMobile from './useIsMobile';
import './dashboard.css';
import './home-dashboard.css';

const MEALS = [['breakfast','아침'],['lunch','점심'],['dinner','저녁'],['snack','간식']];
const percent = (value,target) => target > 0 ? Math.min(100,Math.max(0,Math.round(value/target*100))) : null;
const display = value => Number.isFinite(value) ? value.toLocaleString('ko-KR',{maximumFractionDigits:2}) : '—';

export default function HomeDashboard({user,today:liveToday,onNavigate,onAddMeal,api,homeCard,me,onRewardsChanged,displayName}) {
  const isMobile = useIsMobile();
  const parts = new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const part = key => parts.find(p=>p.type===key).value;
  const todayDate = liveToday?.date || `${part('year')}-${part('month')}-${part('day')}`;
  const [selectedDate,setSelectedDate] = useState(todayDate);
  const [pastDay,setPastDay] = useState(null),[error,setError] = useState(''),[retry,setRetry] = useState(0);
  useEffect(()=>{
    let active=true;setPastDay(null);setError('');
    if (!user || selectedDate===todayDate) return;
    const [year,month]=selectedDate.split('-');
    api(`/analytics/month?year=${year}&month=${Number(month)}`).then(result=>{
      if (!active) return;
      const day=result.days.find(row=>row.date===selectedDate);
      setPastDay({meals:day?.meals||[],totals:day?.totals||{cal:0,carbs:0,protein:0,fat:0,sugar:0,sodium:0}});
    }).catch(e=>{if(active)setError(e.message)});
    return ()=>{active=false};
  },[api,user?.id,selectedDate,todayDate,retry]);
  const currentDay=selectedDate===todayDate, data=currentDay?liveToday:pastDay;
  const totals=data?.totals, meals=data?.meals||[], target=liveToday?.target_calories;
  const remaining=MEALS.filter(([key])=>!meals.some(meal=>meal.meal_type===key));
  const date=new Date(`${selectedDate}T12:00:00+09:00`);
  const addMeal=type=>user?onAddMeal(type||remaining[0]?.[0]||'breakfast'):onNavigate('로그인');
  function previousDay(){const d=new Date(date);d.setUTCDate(d.getUTCDate()-1);setSelectedDate(d.toISOString().slice(0,10));}
  const nutrients=[['carbs','탄수화물','g','🌿'],['protein','단백질','g','🥚'],['fat','지방','g','💧'],['sodium','나트륨','mg','♧'],['sugar','당류','g','◇']];
  const caloriePercent=percent(totals?.cal||0,target);
  const nutritionPanel = (
    <section className="hd-panel" aria-labelledby="hd-nutrition-title">
      <div className="hd-section-head"><div><h2 id="hd-nutrition-title">{currentDay?'오늘':'선택한 날'} 영양 상태</h2><p>기록한 식단의 영양 정보를 확인해 보세요.</p></div><button type="button" className="text-button" onClick={()=>onNavigate('식단 분석')}>자세히 보기 →</button></div>
      <div className="hd-nutrition"><div className="hd-energy"><div className="hd-ring" style={{'--hd-progress':`${caloriePercent||0}%`}} role="img" aria-label={`섭취 ${display(totals?.cal)} kcal, 목표 ${display(target)} kcal`}><div><span aria-hidden="true">🔥</span><strong>{display(totals?.cal)}</strong><small>/ {display(target)} kcal</small><b>{caloriePercent===null?'목표 미설정':`${caloriePercent}%`}</b></div></div><div className="hd-macro-legend">{nutrients.slice(0,3).map(([key,label])=><span key={key}>{label} <b>{display(totals?.[key])}g</b></span>)}</div></div>
        <div className="hd-nutrients">{nutrients.map(([key,label,unit,icon])=>{const goal=['sugar','sodium'].includes(key)?liveToday?.sugar_sodium_limits?.[key]:liveToday?.macro_targets?.[key];const progress=percent(totals?.[key]||0,goal);return <div key={key} className={`hd-nutrient hd-${key}`}><span className="hd-nutrient-icon" aria-hidden="true">{icon}</span><div><span>{label}</span><strong>{display(totals?.[key])}{goal?` / ${display(goal)}`:''} {unit}</strong></div><div className="hd-nutrient-track"><span style={{width:`${progress||0}%`}}/></div><small>{progress===null?'목표 기준 미설정':`${progress}%`}</small></div>})}</div>
      </div>
      <div className="hd-tip"><span aria-hidden="true">💡</span><div><strong>다음 한 끼도 건강하게 골라보세요.</strong><p>기록한 식단과 목표를 바탕으로 식사 후보를 확인해 보세요.</p></div><button type="button" className="outline" onClick={()=>onNavigate('식사 추천')}>메뉴 추천받기 →</button></div>
    </section>
  );
  // 760px 이하에서는 모바일 전용 홈(시안 3안)을 그린다. 데이터와 날짜 상태는 위에서 만든 값을 그대로 넘긴다.
  if (isMobile) {
    const status = error ? <div role="alert"><p className="error">{error}</p><button type="button" className="m-link" onClick={()=>setRetry(n=>n+1)}>다시 불러오기</button></div>
      : user&&!data ? <p role="status" className="muted">기록을 불러오고 있어요…</p> : null;
    return <MobileHome user={user} me={me} displayName={displayName} liveToday={liveToday} totals={totals} meals={meals} target={target}
      todayDate={todayDate} selectedDate={selectedDate} onSelectDate={setSelectedDate} currentDay={currentDay} remaining={remaining}
      onAddMeal={addMeal} onNavigate={onNavigate} homeCard={homeCard} status={status}
      streak={me&&<StreakNotice api={api} streak={me.streak} onChanged={onRewardsChanged}/>}/>;
  }
  return <div className="home-dashboard">
    {homeCard}
    <section className="hd-hero hd-hero--overview hd-overview-summary" aria-label="선택한 날의 기록 요약">
      <div className="hd-hero-content">
      <div className="hd-room"><Jibang equipment={me?.equipment} level={me?.level||1} background="bg_lv1" bubble="오늘도 잘 하고 있어요!" figureWidth={230} className="hd-hero-scene"/></div>
        <div className="hd-date"><strong>{date.getUTCMonth()+1}.{date.getUTCDate()} {['일','월','화','수','목','금','토'][date.getUTCDay()]}</strong><button type="button" aria-label="이전 날짜 기록 보기" onClick={previousDay}>‹</button><button type="button" className="hd-today" onClick={()=>setSelectedDate(todayDate)}>{currentDay?'오늘':'오늘로'}</button></div>
        <div className="hd-stats"><div><i aria-hidden="true">🔥</i><span>섭취 칼로리<strong>{display(totals?.cal)} <small>/ {display(target)} kcal</small></strong></span></div><div><i className="hd-check" aria-hidden="true">✓</i><span>기록 현황<strong>{4-remaining.length}끼 기록 완료</strong></span></div><div><i aria-hidden="true">🍴</i><span>남은 기록<strong>{remaining.map(([,label])=>label).join(' · ')||'모두 완료!'}</strong></span></div></div>
        <button type="button" className="hd-record" onClick={()=>addMeal()}>＋ 식사 기록하기 <span aria-hidden="true">→</span></button>
      </div>
    </section>
    {nutritionPanel}
    <section className="hd-panel hd-records" aria-labelledby="hd-record-title">
      <div className="hd-section-head"><div><h2 id="hd-record-title">{currentDay?'오늘의':'선택한 날의'} 기록 요약</h2><p>어떤 식사를 하셨나요?</p></div><label className="hd-date-picker"><span className="sr-only">식단 조회 날짜</span><input type="date" max={todayDate} value={selectedDate} onChange={e=>{if(e.target.value)setSelectedDate(e.target.value)}}/></label></div>
      {error?<div role="alert"><p className="error">{error}</p><button type="button" className="text-button" onClick={()=>setRetry(n=>n+1)}>다시 불러오기</button></div>:user&&!data?<p role="status">기록을 불러오고 있어요…</p>:null}
      <SavedMeals meals={meals} onNavigate={onNavigate} onAddMeal={addMeal}/>
    </section>
    <section className="hd-panel" aria-labelledby="hd-reward-title">
      <div className="hd-section-head"><div><h2 id="hd-reward-title">성장 / 리워드</h2><p>꾸준히 기록하고, 포인트와 레벨을 올려보세요!</p></div><button type="button" className="text-button" onClick={()=>onNavigate('리워드','mall')}>전체 리워드 보기 →</button></div>
      {me?<><div className="hd-rewards"><div className="hd-growth-profile"><button type="button" className="hd-reward-mascot" onClick={()=>onNavigate('리워드','room')} aria-label="지방이 방 보기"><Jibang equipment={me.equipment} level={me.level} bubble={me.streak?.today_recorded?'오늘도 기록했어요!':'한 끼씩 함께 기록해요!'} figureWidth={120}/></button><button type="button" className="hd-level" onClick={()=>onNavigate('리워드','growth')}><span className="hd-level-badge">LV</span><div><strong>LV.{me.level} · {me.level_name} 지방이</strong><Progress value={me.level_progress} label="다음 레벨까지 XP"/><small>{fmt(me.xp_total)}{me.next_level_xp?` / ${fmt(me.next_level_xp)}`:''} XP</small><p className="hd-points">{fmt(me.balance)}<small>P</small> <span>오늘 +{fmt(me.today_points)}P</span></p><small>그중 꾸미기 전용 {fmt(me.deco_only)}P</small></div></button></div>
        <div className="hd-missions"><h3>오늘의 미션</h3><p>오늘도 건강한 습관을 이어가요!</p>{me.actions?.length?me.actions.map(action=><button key={action.id} type="button" onClick={()=>addMeal(MEALS.some(([key])=>key===action.id)?action.id:undefined)}><span className="hd-mission-icon" aria-hidden="true">{action.id==='mission'?'▣':'♧'}</span><span><strong>{action.label}</strong><small>{action.detail} {action.goal?`· ${action.progress}/${action.goal}`:''}</small></span><b>+{action.points}P</b></button>):<p className="hd-complete">오늘의 기록을 모두 마쳤어요! ✓</p>}</div>

      </div><StreakNotice api={api} streak={me.streak} onChanged={onRewardsChanged}/>{me.today_items?.length>0&&<details className="hd-earned"><summary>오늘 받은 포인트·XP 내역</summary><ul>{me.today_items.map(row=><li key={row.key}><span>{row.label}</span><b>{row.points?`+${fmt(row.points)}P`:''} {row.xp?`+${fmt(row.xp)} XP`:''}</b></li>)}</ul></details>}</>:<div className="hd-guest"><JibangFigure width={100}/><p>{user?'리워드를 불러오고 있어요…':'로그인하고 지방이와 함께 기록을 시작해 보세요.'}</p>{!user&&<button type="button" className="primary" onClick={()=>onNavigate('로그인')}>로그인 / 회원가입</button>}</div>}
    </section>
  </div>;
}
