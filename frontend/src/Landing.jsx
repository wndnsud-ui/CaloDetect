// 서비스 소개 페이지. 브랜드·기능·가입 안내를 표시하고 선택한 메뉴를 회원 앱 진입 콜백으로 전달한다.
import React, {useEffect, useState} from 'react';
import {PromoSlider} from './RewardMall';
import {Brand} from './Visuals';
import LandingAccount, {useLandingSession} from './LandingAccount';
import FeatureSection from './FeatureSection';
import './landing-compact.css';
import './landing-mobile.css';
const steps = [
  ['01','회원가입','기본 정보를 설정해요.','회원가입','phone'],
  ['02','사진 업로드','오늘 먹은 음식을 촬영해요.','음식 추가','camera'],
  ['03','자동 분석','음식을 인식하고 영양을 계산해요.','음식 추가','chart'],
  ['04','다음 식사 추천','기록에 맞는 다음 메뉴를 확인해요.','식사 추천','meal'],
];
// 서비스 소개 페이지. 브랜드·기능·가입 안내를 표시하고 선택한 메뉴를 회원 앱 진입 콜백으로 전달한다.
function StepIcon({type}) {
  return <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {type==='phone'&&<><rect x="9" y="3" width="14" height="26" rx="3"/><path d="M13 6h6M15 25h2"/></>}
    {type==='camera'&&<><path d="M4 10h6l2-4h8l2 4h6v17H4Z"/><circle cx="16" cy="18" r="5"/></>}
    {type==='chart'&&<><rect x="5" y="17" width="4" height="11" rx="1" fill="currentColor" stroke="none"/><rect x="14" y="5" width="4" height="23" rx="1" fill="currentColor" stroke="none"/><rect x="23" y="11" width="4" height="17" rx="1" fill="currentColor" stroke="none"/></>}
    {type==='meal'&&<><path d="M7 4v9M11 4v9M15 4v9M7 10v3a4 4 0 0 0 8 0v-3M11 17v11M25 4c-4 3-5 8-5 13h5M25 4v24"/></>}
  </svg>;
}
// 이용 방법 영역: 리워드몰 공개 슬라이드(콜라보·실존 브랜드 제외)가 있으면 그것을, 없으면(교환 기능 꺼짐·오류) 4단계 이용 흐름을 보여 준다.
function HowSection({onOpen}) {
  const [promos, setPromos] = useState([]);
  useEffect(() => {
    let alive = true;
    fetch('/api/rewards/promotions/public', {credentials: 'include'}).then(r => r.ok ? r.json() : {items: []})
      .then(data => { if (alive) setPromos(data.items || []); }).catch(() => {});
    return () => { alive = false; };
  }, []);
  if (promos.length) return <section className="landing-section landing-promos" id="how" aria-label="리워드몰 소개"><PromoSlider items={promos} onOpen={() => onOpen('리워드')}/></section>;
  return <section className="landing-section" id="how" aria-labelledby="how-title"><div className="service-flow">
  <div className="service-flow-intro"><p className="service-flow-label"><svg className="section-flow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="6" rx="1.5"/><rect x="14" y="15" width="7" height="6" rx="1.5"/><path d="M10 6h7a2 2 0 0 1 2 2v3M16 9l3 3 3-3M14 18H7a2 2 0 0 1-2-2v-3M2 15l3-3 3 3"/></svg>서비스 이용 흐름</p><h2 id="how-title">이렇게 시작해요.<br/>4단계로 간편하게.</h2></div>
  <ol className="service-flow-steps">{steps.map(([n,title,description,page,icon])=><li key={n}>
    <button onClick={()=>onOpen(page)}><span className={`service-step-icon service-step-${icon}`}><StepIcon type={icon}/></span><strong>{title}</strong><small>{description}</small></button>
  </li>)}</ol>
</div></section>;
}
// 서비스 소개 페이지. 브랜드·기능·가입 안내를 표시하고 선택한 메뉴를 회원 앱 진입 콜백으로 전달한다.
export default function Landing({onOpen}) {const session=useLandingSession();const member=!!session.user;return <div className="landing"><header className="landing-header"><Brand onClick={()=>window.scrollTo({top:0,behavior:'smooth'})}/><nav aria-label="홈페이지 메뉴"><a href="#service">서비스 소개</a><a href="#features">주요 기능</a><a href="#how">이용 방법</a><a href="#faq">FAQ</a></nav><LandingAccount onOpen={onOpen} session={session}/></header><main className="landing-main"><section className="landing-hero hero-with-background" id="service"><div className="hero-copy"><span className="pill">매일의 식사를 위한 파트너</span><h1>사진 한 장으로 기록하고,<br/>메뉴가 고민될 땐<br/>지방이에게 물어보세요<span>.</span></h1><p>사진 한 장으로 먹은 음식과 영양을 기록해 보세요.<br/>다음 끼니가 고민될 땐, 지방이가 내 기록과 목표에 맞는 메뉴를 추천해 드려요.</p><div className="hero-actions">{/* 비회원은 가입으로, 로그인 회원은 식단 기록으로 유도한다. 세션 확인 중에는 기존 문구를 둔다. */}{session.loading?<button className="primary" onClick={()=>onOpen('음식 추가')}>📷 사진으로 첫 끼 기록하기</button>:member?<button className="primary" onClick={()=>onOpen('음식 추가')}>📷 사진으로 첫 끼 기록하기</button>:<button className="primary" onClick={()=>onOpen('회원가입')}>📷 사진으로 첫 끼 기록하기</button>}<button className="outline" onClick={()=>onOpen(member?'홈':'회원가입')}>{member?'내 홈으로 가기':'회원가입하고 시작하기'}</button></div><small>인식이 어려운 음식은 검색하거나 직접 입력할 수 있어요.</small></div></section><FeatureSection onOpen={onOpen}/>
<HowSection onOpen={onOpen}/><section className="landing-section faq" id="faq"><h2>자주 묻는 질문</h2><details open><summary>서비스를 이용하려면 가입해야 하나요?</summary><p>네, 회원가입 후 로그인해 이용해 주세요. 식단 기록과 영양 분석, 맞춤 메뉴 추천을 내 계정에서 이어갈 수 있어요.</p></details><details><summary>한식도 잘 알아보나요? 못 알아보면요?</summary><p>음식 사진을 분석해 후보를 보여 드려요. 인식 결과가 다르면 음식을 검색해 수정하거나 이름·양과 알고 있는 영양값을 직접 입력할 수 있어요.</p></details><details><summary>제 음식 사진은 어디에 쓰이나요?</summary><p>음식 인식과 식단 기록에 사용하며, 모델 재학습에는 사용하지 않습니다. 커뮤니티 사진 공개는 게시물별로 직접 선택할 수 있어요.</p></details><details><summary>매일 기록 못 하면 소용없나요?</summary><p>하루 한 끼부터 시작해도 괜찮아요. 목표와 남긴 기록을 바탕으로 다음 식사를 추천해 드려요.</p></details></section><section className="landing-section landing-final-cta"><h2>오늘 저녁 한 끼부터 시작해요.</h2><button className="primary" onClick={()=>onOpen(member?'음식 추가':'회원가입')}>📷 첫 끼 기록하기</button></section></main><footer><Brand onClick={()=>onOpen('홈')}/><span>나를 위한 건강한 한 끼 · © 2026 CaloDetect</span></footer></div>;}
