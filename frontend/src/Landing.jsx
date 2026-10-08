// 서비스 소개 페이지. 브랜드·기능·가입 안내를 표시하고 선택한 메뉴를 회원 앱 진입 콜백으로 전달한다.
import React from 'react';
import {Brand} from './Visuals';
import LandingAccount from './LandingAccount';
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
// 서비스 소개 페이지. 브랜드·기능·가입 안내를 표시하고 선택한 메뉴를 회원 앱 진입 콜백으로 전달한다.
export default function Landing({onOpen}) {return <div className="landing"><header className="landing-header"><Brand onClick={()=>window.scrollTo({top:0,behavior:'smooth'})}/><nav aria-label="홈페이지 메뉴"><a href="#service">서비스 소개</a><a href="#features">주요 기능</a><a href="#how">이용 방법</a><a href="#faq">FAQ</a></nav><LandingAccount onOpen={onOpen}/></header><main className="landing-main"><section className="landing-hero hero-with-background" id="service"><div className="hero-copy"><span className="pill">매일의 식사를 위한 파트너</span><h1>오늘 뭐 먹지?<br/>데이터로 해결하다<span>.</span></h1><p>사진 한 장으로 시작하는 식단 기록,<br/>나의 영양 상태에 맞는 다음 한 끼.<br/>건강한 식사 습관을 CaloDetect와 함께하세요.</p><div className="hero-actions"><button className="primary" onClick={()=>onOpen('음식 추가')}>내 식단 기록 시작하기 →</button><button className="outline" onClick={()=>onOpen('홈')}>웹앱 둘러보기</button></div><small>음식 조회와 목표 계산부터 경험해보세요.</small></div></section><FeatureSection onOpen={onOpen}/>
<section className="landing-section" id="how" aria-labelledby="how-title"><div className="service-flow">
  <div className="service-flow-intro"><p className="service-flow-label"><svg className="section-flow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="6" rx="1.5"/><rect x="14" y="15" width="7" height="6" rx="1.5"/><path d="M10 6h7a2 2 0 0 1 2 2v3M16 9l3 3 3-3M14 18H7a2 2 0 0 1-2-2v-3M2 15l3-3 3 3"/></svg>서비스 이용 흐름</p><h2 id="how-title">이렇게 시작해요.<br/>4단계로 간편하게.</h2></div>
  <ol className="service-flow-steps">{steps.map(([n,title,description,page,icon])=><li key={n}>
    <button onClick={()=>onOpen(page)}><span className={`service-step-icon service-step-${icon}`}><StepIcon type={icon}/></span><strong>{title}</strong><small>{description}</small></button>
  </li>)}</ol>
</div></section><button className="landing-cta landing-cta-link" onClick={()=>onOpen('목표 설정')}>
  <span className="cta-copy"><span className="cta-caption">맛있는 식사가<br/>건강한 하루를 만듭니다.</span>
    <span className="cta-title">지금, CaloDetect와 함께<br/>시작해 보세요.</span>
    <span className="cta-action">무료로 시작하기 <span aria-hidden="true">→</span></span>
  </span><img className="cta-poke" src="/images/cta-poke.webp.png" alt="" loading="lazy" decoding="async"/>
</button><section className="landing-section faq" id="faq"><h2>자주 묻는 질문</h2><details><summary>가입 전에 사용할 수 있는 기능이 있나요?</summary><p>음식 영양 조회와 목표 칼로리 계산을 경험할 수 있습니다. 개인 식단 저장과 회원정보 관리는 로그인이 필요합니다.</p></details><details><summary>사진은 모델 학습에 자동 사용되나요?</summary><p>모델 개선 활용은 별도 동의와 관리자 QA가 필요합니다. 동의 문구 및 이미지 정책은 팀에서 확정 후 적용합니다.</p></details></section></main><footer><Brand onClick={()=>onOpen('홈')}/><span>나를 위한 건강한 한 끼 · © 2026 CaloDetect</span></footer></div>;}
