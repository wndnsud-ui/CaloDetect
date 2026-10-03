import React, {useId} from 'react';
export function MenuIcon({page}) {
  const shapes = {
    '홈': <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/></>,
    '음식 추가': <><rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 8h8M8 12h5M12 15v4M10 17h4"/></>,
    '목표 설정': <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></>,
    '식사 추천': <><path d="M7 14a5 5 0 0 1-1-10 6 6 0 0 1 12 0 5 5 0 0 1-1 10v7H7ZM7 17h10"/></>,
    '식단 분석': <><path d="M4 3v18h17M8 16v-5M13 16V7M18 16V4"/></>,
    '히스토리': <><path d="M3 10a9 9 0 1 1 2 8M3 4v6h6M12 7v5l3 2"/></>,
    '마이페이지': <><circle cx="12" cy="7" r="4"/><path d="M4 21v-3a8 8 0 0 1 16 0v3ZM9 15l3 3 3-3"/></>,
  };
  return <svg className="sidebar-menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{shapes[page]}</svg>;
}
export function Brand({onClick}) {
  const id=useId();
  return <button type="button" className="brand" onClick={onClick} aria-label="CaloDetect 홈">
    <svg viewBox="0 0 48 44" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-left`} x1="3" y1="12" x2="25" y2="40" gradientUnits="userSpaceOnUse"><stop stopColor="#16aa7d"/><stop offset="1" stopColor="#086447"/></linearGradient>
        <linearGradient id={`${id}-right`} x1="44" y1="3" x2="24" y2="40" gradientUnits="userSpaceOnUse"><stop stopColor="#149b72"/><stop offset="1" stopColor="#07563e"/></linearGradient>
      </defs>
      <path d="M24 40C10 39 3 30 3 14c12-1 23 8 21 26Z" fill={`url(#${id}-left)`}/>
      <path d="M25 40C20 31 20 20 28 12 33 7 39 4 45 3c2 17-5 32-20 37Z" fill={`url(#${id}-right)`}/>
      <path d="M23.5 40C23 29 28 19 38 12 30 21 26 30 25.5 40Z" fill="#f0fff8"/>
      <path d="M23.5 40C21 31 16 24 9 19 17 24 23 30 25 40Z" fill="#f0fff8"/>
    </svg><span className="brand-wordmark">CaloDetect</span>
  </button>;
}
export function Bowl({small=false}) {return <div className={`food-bowl ${small?'small':''}`} role="img" aria-label="채소와 달걀을 담은 식사 일러스트"><div className="greens"/><div className="rice"/><div className="chicken"/><div className="egg"/><div className="avocado"/><div className="tomato one"/><div className="tomato two"/><div className="tomato three"/></div>;}
export function Ring({value=0,target,example=false}) {const percent=target?Math.min(100,Math.round(value/target*100)):0;return <div className="ring-wrap"><div className="ring" style={{'--progress':`${percent}%`}}><div><strong>{value.toLocaleString()}</strong><span>{target?`/ ${target.toLocaleString()} kcal`:'목표 설정 전'}</span></div></div><b>{target?`${percent}%`:'—'}</b>{example&&<small>화면 예시</small>}</div>;}
