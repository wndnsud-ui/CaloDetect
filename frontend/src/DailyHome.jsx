import React, {useEffect, useState} from 'react';
import SavedMeals from './SavedMeals';
import {Ring, Bowl, MenuIcon} from './Visuals';
import './dashboard.css';

export default function DailyHome({user,today:liveToday,onNavigate,onAddMeal,api}) {
 const [showTip,setShowTip]=useState(true);
 const parts=new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
 const part=key=>parts.find(p=>p.type===key).value;
 const todayDate=liveToday?.date||`${part('year')}-${part('month')}-${part('day')}`;
 const [selectedDate,setSelectedDate]=useState(todayDate);
 const [pastDay,setPastDay]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 useEffect(()=>{
  let active=true;setPastDay(null);setError('');
  if(!user||selectedDate===todayDate)return;
  const [year,month]=selectedDate.split('-');
  api(`/analytics/month?year=${year}&month=${Number(month)}`).then(result=>{
   if(!active)return;
   const day=result.days.find(day=>day.date===selectedDate);
   setPastDay({date:selectedDate,meals:day?.meals||[],totals:day?.totals||{cal:0,carbs:0,protein:0,fat:0,sugar:0,sodium:0},message:'선택한 날짜에 기록한 섭취량입니다.'});
  }).catch(err=>{if(active)setError(err.message)});
  return()=>{active=false};
 },[api,user?.id,selectedDate,todayDate,retry]);
 const today=selectedDate===todayDate?liveToday:pastDay;
 const current=new Date(`${selectedDate}T12:00:00+09:00`);
 const monday=new Date(current); monday.setUTCDate(current.getUTCDate()-((current.getUTCDay()+6)%7));
 const week=Array.from({length:7},(_,i)=>{const d=new Date(monday);d.setUTCDate(monday.getUTCDate()+i);return d;});
 const value=k=>today?.totals[k]?.toLocaleString()??'—';
 return <div className="daily-home">
  <header className="daily-header"><div className="daily-header-top"><div><p>나의 하루, 건강한 한 끼</p><h1>{current.getUTCMonth()+1}.{current.getUTCDate()} {['일','월','화','수','목','금','토'][current.getUTCDay()]}<span className="daily-today">{selectedDate===todayDate?'오늘':'선택한 날'}</span></h1></div><button className="daily-account" aria-label="내 계정" onClick={()=>onNavigate('마이페이지')}><MenuIcon page="마이페이지"/></button></div>
   <div className="daily-week" aria-label="이번 주 달력">{week.map((d,i)=>{const date=d.toISOString().slice(0,10);return <button type="button" key={date} className={date===selectedDate?'is-today':''} aria-label={`${date} 식단과 사진 보기`} aria-pressed={date===selectedDate} onClick={()=>setSelectedDate(date)}><span>{['월','화','수','목','금','토','일'][i]}</span><strong>{d.getUTCDate()}</strong></button>})}</div>
  </header>
  <div className="daily-body">
   <div className="daily-date-controls"><label>식단 날짜 <input type="date" value={selectedDate} onChange={e=>{if(e.target.value)setSelectedDate(e.target.value)}}/></label>{selectedDate!==todayDate&&<button className="text-button" onClick={()=>setSelectedDate(todayDate)}>오늘로 돌아가기 →</button>}</div>
   {error?<div role="alert"><p className="error">{error}</p><button className="text-button" onClick={()=>setRetry(n=>n+1)}>다시 불러오기</button></div>:!today&&user?<p role="status">{selectedDate} 식단과 사진을 불러오고 있습니다…</p>:today&&today.meals.length===0?<p className="muted">{selectedDate}에 기록된 식단이 없습니다.</p>:null}
   {showTip&&<section className="daily-record-card"><button className="daily-dismiss" aria-label="식단 기록 안내 닫기" onClick={()=>setShowTip(false)}>×</button><div className="daily-record-copy"><p className="daily-kicker">매일 조금씩, 더 건강하게</p><h2>{user?`${user.name}님,`:'오늘도,'}<br/>오늘의 한 끼를 기록해 보세요</h2><span className="daily-soft-pill">사진 한 장으로 간편하게 기록해요</span></div><div className="daily-bowl" aria-hidden="true"><Bowl/></div><button className="primary" onClick={()=>onNavigate('음식 추가')}>지금 기록할게요 <span>＋</span></button></section>}
   <section className="panel daily-food-card"><div className="section-heading"><h2>{selectedDate===todayDate?'오늘의 식단':`${selectedDate} 식단`}</h2><button className="text-button" onClick={()=>onNavigate('히스토리')}>기록 보기 →</button></div><div className="daily-calories"><strong>{value('cal')}</strong><span>kcal</span><small>{today?`${today.meals.length}끼 기록`:user?'불러오는 중':'로그인 후 기록'}</small></div><div className="daily-macros">{[['carbs','탄수화물'],['protein','단백질'],['fat','지방']].map(([k,label])=><span key={k}><i className={`macro-dot ${k}`}/>{label} <b>{value(k)} g</b></span>)}</div><SavedMeals meals={today?.meals||[]} onNavigate={selectedDate===todayDate?onNavigate:undefined} onAddMeal={onAddMeal}/></section>
   <div className="daily-detail-grid"><section className="panel daily-energy"><div className="section-heading"><h2>하루 칼로리</h2><button className="text-button" onClick={()=>onNavigate('목표 설정')}>목표 설정 →</button></div><Ring value={today?.totals.cal||0} target={today?.target_calories}/><p className="muted">{!user?'로그인하면 실제 식단 기록을 확인할 수 있어요.':today?.message||'식단 기록을 불러오고 있습니다.'}</p></section><section className="panel daily-more"><h2>함께 확인해요</h2><div className="daily-extra">{[['sugar','당류','g'],['sodium','나트륨','mg']].map(([k,label,unit])=><div key={k}><span>{label}</span><strong>{value(k)} <small>{unit}</small></strong></div>)}</div><p className="muted">기록한 섭취량 · 영양소별 목표는 미설정</p><button className="daily-recommend" onClick={()=>onNavigate('식사 추천')}>다음 한 끼, 무엇을 먹을까요? <span>→</span></button><button className="text-button" onClick={()=>onNavigate('식단 분석')}>내 식단 분석 보기 →</button></section></div>
  </div>
 </div>;
}
