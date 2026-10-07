import React, {lazy,Suspense,useState} from 'react';
import {progress,streak} from './engagement';
const Jibangi3D=lazy(()=>import('./Jibangi3D'));

export function Jibangi({outfit='basic',className='',interactive=false,pose='standing'}) {return <div className={'jibangi '+className}><Suspense fallback={<span role="status">지방이가 오고 있어요…</span>}><Jibangi3D outfit={outfit} interactive={interactive} pose={pose}/></Suspense></div>;}

export default function CharacterStudio({user,history=[],joined=[]}) {
 const growth=progress(history,joined);
 const stages=['basic','ribbon','sport','crown'];
 const evolved=stages[growth.level-1];
 const key=`calodetect-character-${user?.id||'guest'}`;
 const [outfit,setOutfit]=useState(()=>{try{return ['basic','ribbon','sport'].includes(localStorage.getItem(key))?localStorage.getItem(key):'basic';}catch{return 'basic';}});
 const [note,setNote]=useState('');
 function wear(value){setOutfit(value);try{localStorage.setItem(key,value);setNote('이 브라우저에 꾸미기를 저장했어요.');}catch{setNote('꾸미기를 변경했어요. 브라우저 저장은 사용할 수 없습니다.');}}
 return <div className="character-page"><p className="eyebrow">MY LITTLE COMPANION</p><h1>나의 지방이</h1><p className="muted">한 끼씩 쌓이는 습관, 함께하는 작은 친구.</p><section className="character-stage"><span className="studio-badge">꾸미기 체험</span><Jibangi outfit={outfit==='basic'||stages.indexOf(outfit)>=growth.level?evolved:outfit} interactive/><h2>오늘도 함께해요 ♡</h2><p>좋아하는 스타일로 지방이를 꾸며보세요.</p></section><section className="panel growth-summary"><h2>{`Lv. ${growth.level} · ${growth.points} P`}</h2><p>{growth.next?`${growth.next-growth.points} P 더 모으면 다음 모습을 만나요.`:"모든 성장 단계를 만났어요!"}</p><p className="streak-pill">{streak(history)} {"\uC77C \uC5F0\uC18D \uAE30\uB85D"}</p><progress value={growth.points} max={growth.next||growth.points||1}/><p className="muted">{"내부 실험 · 식단 기록 +20 P · 챌린지 완료 보상 · 현재 불러온 기록 기준"}</p></section><section className="panel"><h2>오늘의 스타일</h2><div className="outfit-options">{[['basic','새싹 기본형'],['ribbon','분홍 리본'],['sport','산뜻한 운동복']].map(([value,label])=><button key={value} className={outfit===value?'selected':''} aria-pressed={outfit===value} disabled={growth.level<stages.indexOf(value)+1} onClick={()=>wear(value)}><Jibangi outfit={value}/><strong>{label}</strong></button>)}</div><p role="status">{note}</p><p className="muted">꾸미기는 이 브라우저에서 체험할 수 있어요. 포인트가 쌓이면 새 스타일이 열려요. 잠긴 스타일은 선택할 수 없어요.</p></section><section className="panel"><h2>{"포인트 기록"}</h2>{growth.ledger.length?growth.ledger.map(event=><div className="point-event" key={event.id}><span>{event.title}<small>{event.date}</small></span><strong>+{event.points} P</strong></div>):<p>{"식단을 기록하면 지방이가 함께 성장해요."}</p>}</section></div>;
}
