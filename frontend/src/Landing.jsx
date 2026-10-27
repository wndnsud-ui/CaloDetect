// 서비스 소개 페이지. 브랜드·기능·가입 안내를 표시하고 선택한 메뉴를 회원 앱 진입 콜백으로 전달한다.
import React, {useEffect, useState} from 'react';
import {PromoSlider} from './RewardMall';
import {Brand} from './Visuals';
import LandingAccount, {useLandingSession} from './LandingAccount';
import FeatureSection from './FeatureSection';
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
export default function Landing({onOpen}) {const session=useLandingSession();const member=!!session.user;return <div className="landing"><header className="landing-header"><Brand onClick={()=>window.scrollTo({top:0,behavior:'smooth'})}/><nav aria-label="홈페이지 메뉴"><a href="#service">서비스 소개</a><a href="#features">주요 기능</a><a href="#how">이용 방법</a><a href="#faq">FAQ</a></nav><LandingAccount onOpen={onOpen} session={session}/></header><main className="landing-main"><section className="landing-hero hero-with-background" id="service"><div className="hero-copy"><span className="pill">매일의 식사를 위한 파트너</span><h1>오늘 뭐 먹지?<br/>데이터로 해결하다<span>.</span></h1><p>사진 한 장으로 시작하는 식단 기록,<br/>나의 영양 상태에 맞는 다음 한 끼.<br/>건강한 식사 습관을 CaloDetect와 함께하세요.</p><div className="hero-actions">{/* 비회원은 가입으로, 로그인 회원은 식단 기록으로 유도한다. 세션 확인 중에는 기존 문구를 둔다. */}{session.loading?<button className="primary" onClick={()=>onOpen('음식 추가')}>내 식단 기록 시작하기 →</button>:member?<button className="primary" onClick={()=>onOpen('음식 추가')}>내 식단 기록하기 →</button>:<button className="primary" onClick={()=>onOpen('회원가입')}>회원가입하고 시작하기 →</button>}<button className="outline" onClick={()=>onOpen('홈')}>웹앱 둘러보기</button></div><small>{member?'오늘의 식사를 사진 한 장으로 기록해 보세요.':'음식 조회와 목표 계산부터 경험해보세요.'}</small></div></section><FeatureSection onOpen={onOpen}/>
<HowSection onOpen={onOpen}/><section className="landing-section faq" id="faq"><h2>자주 묻는 질문</h2><details><summary>가입 전에 사용할 수 있는 기능이 있나요?</summary><p>음식 영양 조회와 목표 칼로리 계산을 경험할 수 있습니다. 개인 식단 저장과 회원정보 관리는 로그인이 필요합니다.</p></details></section></main><footer><Brand onClick={()=>onOpen('홈')}/><span>나를 위한 건강한 한 끼 · © 2026 CaloDetect</span></footer></div>;}
