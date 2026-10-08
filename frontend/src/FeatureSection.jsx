// 소개 페이지의 기능 안내와 비회원 미리보기를 연결하는 섹션. 사용자 선택을 해당 기능 화면으로 전달한다.
import React from 'react';

const features=[
  {id:'meal',icon:'camera',title:<>사진으로 간편하게<br/>식단 기록</>,description:'사진 한 장으로 음식을 인식하고, 영양 정보를 자동으로 분석합니다.',page:'음식 추가'},
  {id:'nutrition',icon:'chart',title:<>오늘의 영양 상태<br/>정확하게 분석</>,description:'섭취한 칼로리와 영양소를 확인하고, 한눈에 파악할 수 있습니다.',page:'홈'},
  {id:'recommendation',icon:'meal',title:<>지금 먹을 수 있는<br/>맞춤 메뉴 추천</>,description:'당신의 목표와 현재 상태에 맞는 다음 식사 메뉴를 추천합니다.',page:'식사 추천'},
  {id:'nearby',icon:'pin',title:<>주변 맛집 · 제품까지<br/>한 번에</>,description:'지금 위치에서 갈 수 있는 건강한 식당과 제품을 추천합니다.',pending:true},
];
// 소개 페이지의 기능 안내와 비회원 미리보기를 연결하는 섹션. 사용자 선택을 해당 기능 화면으로 전달한다.
function FeatureIcon({type}){
  return <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {type==='camera'&&<><path d="M5 10h6l2-4h6l2 4h6v16H5Z"/><circle cx="16" cy="18" r="5"/></>}
    {type==='chart'&&<><path d="M8 26V18M16 26V10M24 26V5" strokeWidth="4"/></>}
    {type==='meal'&&<><path d="M6 5v8M10 5v8M14 5v8M6 11v3a4 4 0 0 0 8 0v-3M10 18v9M25 5c-4 3-5 8-5 13h5M25 5v22"/></>}
    {type==='pin'&&<><path d="M16 28S6 17 6 12a10 10 0 0 1 20 0c0 5-10 16-10 16Z"/><circle cx="16" cy="12" r="3"/></>}
  </svg>;
}
// 소개 페이지의 기능 안내와 비회원 미리보기를 연결하는 섹션. 사용자 선택을 해당 기능 화면으로 전달한다.
export default function FeatureSection({onOpen}){
  return <section className="landing-section feature-showcase" id="features" aria-labelledby="features-title">
    <div className="section-heading"><div><p className="feature-section-label"><svg className="feature-section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>주요 기능 소개</p><h2 id="features-title">기록에서 다음 선택까지,<br/><strong>CaloDetect가 함께합니다.</strong></h2></div><button className="text-button" onClick={()=>onOpen('홈')}>모든 기능 보기 →</button></div>
    <div className="feature-grid">{features.map(feature=>{
      const content=<><span className={`feature-showcase-icon icon-${feature.icon}`}><FeatureIcon type={feature.icon}/></span><h3>{feature.title}</h3><img className="feature-photo" src={`/images/feature-${feature.id}.webp.png`} alt="" loading="lazy" width="1586" height="992"/><p>{feature.description}</p></>;
      return <article className={`feature-showcase-card card-${feature.id}`} key={feature.id}>{feature.pending?<div className="feature-card-content">{content}<span className="feature-pending">준비 중</span></div>:<button className="feature-card-content" onClick={()=>onOpen(feature.page)}>{content}</button>}</article>;
    })}</div>
  </section>;
}
