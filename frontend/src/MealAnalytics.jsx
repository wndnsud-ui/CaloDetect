// 기존 월별 분석 API로 일간 식사별·월간 날짜별 영양 차트를 표시한다.
// 미기록(null)과 0 섭취량을 구분하며 월 차트의 날짜를 선택하면 해당 일간 기록으로 이동한다.
import React, {useEffect, useState} from 'react';
import SavedMeals from './SavedMeals';
import StreamlitChart from './StreamlitChart';

const nutrients = {cal:['칼로리','kcal'], carbs:['탄수화물','g'], protein:['단백질','g'], fat:['지방','g'], sugar:['당류','g'], sodium:['나트륨','mg']};
const types = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
const kstDate = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Seoul'}).format(new Date());

// 칼로리는 목표를 포함한 공통 축, 다른 영양소는 최대값 기준으로 표시한다.
function Bars({items,unit,onSelect,target,monthly}) {
  return <StreamlitChart kind="bars" data={{items,unit,target,monthly}} onSelect={onSelect} height={270} title="식단 칼로리 및 영양 막대그래프"/>;
}
// 기존 월별 분석 API로 일간 식사별·월간 날짜별 영양 차트를 표시한다.
export default function MealAnalytics({api, targetCalories}) {
  const [date,setDate] = useState(kstDate), [mode,setMode] = useState('daily');
  const [metric,setMetric] = useState('cal'), [data,setData] = useState(null);
  const [error,setError] = useState(''), [retry,setRetry] = useState(0);
  // 월이 같으면 조회 결과를 재사용한다. 날짜 선택만 바뀌면 같은 월 자료에서 해당 일자를 찾는다.
  const month = date.slice(0,7);
  // 의존값 변경/마운트에 맞춰 외부 데이터 또는 브라우저 자원을 동기화한다. 반환하는 정리 함수는 이전 작업/자원을 해제한다.
  useEffect(()=>{
    let active=true; setData(null); setError('');
    const [year,number]=month.split('-');
    api(`/analytics/month?year=${year}&month=${Number(number)}`).then(result=>{if(active)setData(result)}).catch(err=>{if(active)setError(err.message)});
    return()=>{active=false};
  },[api,month,retry]);
  const day=data?.days.find(item=>item.date===date);
  // 일간은 날짜 합계, 월간은 서버의 기록일 평균을 표시한다.
  const totals=mode==='daily'?day?.totals:data?.averages;
  const [label,unit]=nutrients[metric];
  // 일간은 저장 음식의 식사 유형별 합계, 월간은 서버 날짜별 합계를 사용하며 미기록은 null을 유지한다.
  const bars=mode==='daily'?Object.entries(types).map(([key,label])=>{
    const meals=day?.meals.filter(meal=>meal.meal_type===key) || [];
    return {label,value:meals.length ? Math.round(meals.flatMap(meal=>meal.items).reduce((sum,item)=>sum+item.nutrition[metric],0)*100)/100 : null};
  }):Array.from({length:new Date(Number(month.slice(0,4)),Number(month.slice(5)),0).getDate()},(_,index)=>{
    const date=`${month}-${String(index+1).padStart(2,'0')}`;
    const day=data?.days.find(day=>day.date===date);
    return {label:String(index+1),date,value:day?.totals?.[metric]??null};
  });
  return <><p className="eyebrow">MEAL ANALYTICS</p><h1>기록으로 보는 나의 식단.</h1>
    <section className="panel"><div className="analysis-controls"><div className="segmented" role="group" aria-label="분석 기간">{[['daily','일간 분석'],['monthly','월별 분석']].map(([key,label])=><button key={key} className={mode===key?'selected':''} aria-pressed={mode===key} onClick={()=>setMode(key)}>{label}</button>)}</div>
    <label>{mode==='daily'?'날짜':'월'}<input type={mode==='daily'?'date':'month'} value={mode==='daily'?date:month} onChange={e=>{if(e.target.value)setDate(mode==='daily'?e.target.value:`${e.target.value}-01`)}}/></label>
    <label>영양 항목<select value={metric} onChange={e=>setMetric(e.target.value)}>{Object.entries(nutrients).map(([key,[label]])=><option key={key} value={key}>{label}</option>)}</select></label></div>
    {error?<div role="alert"><p className="error">{error}</p><button className="text-button" onClick={()=>setRetry(value=>value+1)}>다시 불러오기</button></div>:!data?<p role="status">분석 기록을 불러오고 있습니다…</p>:<>
    <h2>{mode==='daily'?`${date} 식사별 ${label}`:`${month}월 일별 ${label}${metric==='cal'?`(목표 칼로리: ${targetCalories>0?`${targetCalories}kcal`:'미설정'})`:''}`}</h2>
    {mode==='daily'&&metric==='cal'&&<p className="analysis-target">목표 칼로리: {targetCalories>0?`${targetCalories}kcal`:'미설정'}</p>}
    <p className="muted">단위: {unit} · 한국 시간 기준 · —는 미기록입니다.{mode==='monthly'&&' 막대를 누르면 해당 날짜의 일간 분석을 볼 수 있습니다.'}</p>
    {mode==='daily'&&!day?.totals?<p className="empty">이 기간에 기록된 식단이 없습니다.</p>:<Bars items={bars} unit={unit} monthly={mode==='monthly'} target={metric==='cal'?targetCalories:undefined} onSelect={mode==='monthly'?item=>{setDate(item.date);setMode('daily')}:undefined}/>}
    {mode==='daily'&&<SavedMeals meals={day?.meals||[]} title={`${date} 먹은 식단 · 저장한 사진`}/>}
    <h2>{mode==='daily'?'하루 기록 합계':'기록한 날의 하루 평균'}</h2><div className="nutrition-grid">{Object.entries(nutrients).map(([key,[label,unit]])=><div key={key}><span>{label}</span><strong>{totals?.[key]?.toLocaleString()??'—'}<small> {unit}</small></strong></div>)}</div>
    {mode==='monthly'&&<p className="muted">{data.recorded_days}일 기록 · 미기록일은 평균에서 제외합니다. 일부 식사만 기록한 날도 포함됩니다.</p>}
    </>}</section></>;
}
