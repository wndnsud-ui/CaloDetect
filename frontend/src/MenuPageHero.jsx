import React from 'react';
import './menu-backgrounds.css';

const copy = {
  account: ['MY LITTLE SPACE', '내 정보 & 설정', '나의 정보와 건강 목표를 살펴보고, 지방이와 함께 성장해요.'],
  home: ['MY DAILY BALANCE', '오늘도 건강한 한 끼를 기록해요!', '식단을 기록하고, 건강한 습관과 더 나은 나를 만들어가요.'],
  recommend: ['YOUR NEXT MEAL', '지금의 기록에 맞는 다음 식사', '나의 목표와 식사 기록을 바탕으로 다음 한 끼를 골라보세요.'],
  management: ['MY MEAL JOURNAL', '한 끼씩 쌓이는 나의 기록', '날짜별 기록과 영양 분석으로 나의 식습관을 돌아보세요.'],
  community: ['TOGETHER, A BETTER MEAL', '함께 나누는 건강한 일상', '오늘의 한 끼를 나누고, 함께 건강해져요.'],
  rewards: ['SMALL STEPS, LITTLE REWARDS', '꾸준한 기록이 나를 위한 선물로', '차곡차곡 모은 포인트로 지방이를 꾸미고 리워드를 만나보세요.'],
  record: ['MEAL SCAN', '사진에서 식단 기록까지', '오늘의 한 끼가 더 건강한 내일이 됩니다.'],
};

export default function MenuPageHero({kind, className = '', children}) {
  const [eyebrow, title, description] = copy[kind];
  return <section className={`menu-page-hero ${className}`} aria-label={title}>
    <p className="menu-hero-eyebrow">{eyebrow}</p>
    <h1 className="menu-hero-title">{title}</h1>
    <p className="menu-hero-description">{description}</p>
    {children && <div className="menu-hero-actions">{children}</div>}
  </section>;
}
