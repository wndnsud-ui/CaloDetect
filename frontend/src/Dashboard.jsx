// 기존 대시보드 표시 컴포넌트. 전달된 오늘의 영양 합계와 식단을 사용하며 화면 이동은 상위 콜백에 맡긴다.
import React from 'react';
import SavedMeals from './SavedMeals';
import {Ring} from './Visuals';
const nutrients=[['protein','단백질','g'],['carbs','탄수화물','g'],['fat','지방','g'],['sugar','당류','g'],['sodium','나트륨','mg']];

// 기존 대시보드 표시 컴포넌트. 전달된 오늘의 영양 합계와 식단을 사용하며 화면 이동은 상위 콜백에 맡긴다.
export default function Dashboard({user,today,onNavigate}) {
 const date=today?.date ? new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'long',day:'numeric',weekday:'short'}).format(new Date(`${today.date}T12:00:00+09:00`)) : new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'long',day:'numeric',weekday:'short'}).format(new Date());
 return <><div className="page-heading"><div><p className="eyebrow">MY DAILY BALANCE</p><h1>안녕하세요, {user?`${user.name}님`:'방문자님'}! <span className="wave">☀</span></h1><p>{date} · Asia/Seoul</p></div><button className="primary" onClick={()=>onNavigate('음식 추가')}>＋ 식단 기록하기</button></div><div className="dashboard-grid photo-dashboard"><section className="panel balance"><div className="section-heading"><h2>오늘의 영양 상태</h2><span className="pill">{today?`${today.meals.length}끼 기록`:'나의 하루'}</span></div><div className="balance-content"><Ring value={today?.totals.cal||0} target={today?.target_calories}/><div className="home-nutrient-cards">{nutrients.map(([k,l,u])=><div key={k} className={`home-nutrient home-nutrient-${k}`}><div className="home-nutrient-outline"><strong>{l}</strong><b>{today?.totals[k]?.toLocaleString()??'—'} <small>{u}</small></b><span>기록한 섭취량</span></div></div>)}</div></div><p className="muted">{!user?'로그인하면 실제 식단의 영양 구성을 확인할 수 있습니다.':today?.message||'식단 기록을 불러오고 있습니다.'} · 영양소별 목표는 팀 기준 확정 전입니다.</p></section></div><SavedMeals meals={today?.meals||[]} onNavigate={onNavigate}/><div className="next-banner"><div><p className="eyebrow">A GOAL THAT FITS YOU</p><h2>나에게 맞는 하루 목표를 찾아보세요.</h2><p>신체 정보와 활동 수준으로 목표 범위를 확인할 수 있어요.</p></div><button className="outline" onClick={()=>onNavigate('목표 설정')}>목표 설정 →</button></div></>;
}
