import React from 'react';
import './menu-backgrounds.css';

const copy = {
  account: ['MY LITTLE SPACE', '내 정보 & 설정', '나의 정보와 건강 목표를 살펴보고, 지방이와 함께 성장해요.'],
  home: ['MY DAILY BALANCE', '오늘도 건강한 한 끼를 기록해요!', '식단을 기록하고, 건강한 습관과 더 나은 나를 만들어가요.'],
  recommend: ['YOUR NEXT MEAL', '지금의 기록에 맞는 다음 식사', '오늘 먹은 양을 보고 다음 한 끼를 골랐어요.'],
  management: ['MY MEAL JOURNAL', '한 끼씩 쌓이는 나의 기록', '날짜별로 먹은 걸 모아 봤어요.'],
  community: ['TOGETHER, A BETTER MEAL', '함께 나누는 건강한 일상', '오늘 다른 사람들은 뭘 먹었을까요?'],
  rewards: ['SMALL STEPS, LITTLE REWARDS', '꾸준한 기록이 나를 위한 선물로', '차곡차곡 모은 포인트로 지방이를 꾸미고 리워드를 만나보세요.'],
  record: ['MEAL SCAN', '사진 한 장이면 기록 끝', '오늘의 한 끼가 더 건강한 내일이 됩니다.'],
};

export default function MenuPageHero({kind, className = '', children, titleOverride}) {
  const [eyebrow, defaultTitle, description] = copy[kind];
  const title=titleOverride||defaultTitle;
  return <section className={`menu-page-hero ${className}`} aria-label={title}>
    <p className="menu-hero-eyebrow">{eyebrow}</p>
    <h1 className="menu-hero-title">{title}</h1>
    <p className="menu-hero-description">{description}</p>
    {children && <div className="menu-hero-actions">{children}</div>}
  </section>;
}
