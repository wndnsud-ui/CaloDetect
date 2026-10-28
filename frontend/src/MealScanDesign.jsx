import React from 'react';
import {JibangFigure} from './Jibang';
import './meal-scan.css';
import MenuPageHero from './MenuPageHero';

export function MealScanHero({children}) {
  return <MenuPageHero kind="record" className="meal-scan-hero">{children}</MenuPageHero>;
}

export function MealScanStep({kind, title, children}) {
  return <div className="meal-scan-step">
    <span className="meal-scan-step-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {kind === 'camera' ? <><path d="M3 7h4l2-3h6l2 3h4v14H3z"/><circle cx="12" cy="13" r="4"/></>
        : <><path d="M4 3v6a2 2 0 0 0 4 0V3M6 3v18M16 3c-3 2-3 7 0 8h3V3h-3ZM18 11v10"/></>}
    </svg></span>
    <div><h2>{title}</h2><p>{children}</p></div>
  </div>;
}

export function MealScanFood() {
  return <div className="meal-scan-food" aria-hidden="true">
    <p>이렇게<br/>찍어보세요!</p>
    <svg className="meal-scan-food-marks" viewBox="0 0 150 85" fill="none">
      <path d="M8 72 Q38 65 77 67" stroke="#087966" strokeWidth="2" strokeLinecap="round"/>
      <path d="M91 44 85 30M109 40 110 19M125 47 136 34" stroke="#F7C927" strokeWidth="3.5" strokeLinecap="round"/>
    </svg>
    <img src="/images/meal-scan/korean-meal-collage.png" alt=""/>
  </div>;
}

export function MealScanJibang({level, equipment}) {
  return <div className="meal-scan-jibang" aria-hidden="true">
    <p>지방이와 기록하는 한 끼,<br/>건강한 습관의 시작이에요!</p>
    <div className="meal-scan-jibang-stage">
      <svg className="meal-scan-rug" viewBox="0 0 280 60" aria-hidden="true">
        <ellipse cx="140" cy="30" rx="140" ry="30" fill="#EAF5EE"/>
        <ellipse cx="140" cy="30" rx="112" ry="22" fill="none" stroke="#BFDDCB" strokeWidth="4"/>
      </svg>
      <JibangFigure level={level || 1} equipment={equipment || {}} width={155}/>
    </div>
  </div>;
}
