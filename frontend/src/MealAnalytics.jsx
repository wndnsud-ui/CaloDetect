import React, {useEffect, useState} from 'react';
import SavedMeals from './SavedMeals';

const nutrients = {cal:['칼로리','kcal'], carbs:['탄수화물','g'], protein:['단백질','g'], fat:['지방','g'], sugar:['당류','g'], sodium:['나트륨','mg']};
const types = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
const kstDate = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Seoul'}).format(new Date());

function Bars({items, unit, onSelect}) {
  const max = Math.max(1, ...items.map(item=>item.value ?? 0));
  return <div className="analysis-bars">{items.map(item=><button type="button" key={item.label} className="analysis-bar" onClick={()=>onSelect?.(item)} aria-label={`${item.label}: ${item.value == null ? '미기록' : `${item.value} ${unit}`}`}>
    <span className="analysis-bar-value">{item.value == null ? '—' : item.value.toLocaleString()}</span>
    <span className="analysis-bar-track"><span style={{height:`${(item.value ?? 0)/max*100}%`}}/></span>
    <span>{item.label}</span>
  </button>)}</div>;
}

export default function MealAnalytics({api}) {
  const [date,setDate] = useState(kstDate), [mode,setMode] = useState('daily');
  const [metric,setMetric] = useState('cal'), [data,setData] = useState(null);
  const [error,setError] = useState(''), [retry,setRetry] = useState(0);
  const month = date.slice(0,7);
  useEffect(()=>{
    let active=true; setData(null); setError('');
    const [year,number]=month.split('-');
    api(`/analytics/month?year=${year}&month=${Number(number)}`).then(result=>{if(active)setData(result)}).catch(err=>{if(active)setError(err.message)});
    return()=>{active=false};
  },[api,month,retry]);
  const day=data?.days.find(item=>item.date===date);
  const totals=mode==='daily'?day?.totals:data?.averages;
  const [label,unit]=nutrients[metric];
  const bars=mode==='daily'?Object.entries(types).map(([key,label])=>{
    const meals=day?.meals.filter(meal=>meal.meal_type===key) || [];
    return {label,value:meals.length ? Math.round(meals.flatMap(meal=>meal.items).reduce((sum,item)=>sum+item.nutrition[metric],0)*100)/100 : null};
  }):(data?.days || []).map(day=>({label:day.date.slice(8),date:day.date,value:day.totals?.[metric]??null}));
  return <><p className="eyebrow">MEAL ANALYTICS</p><h1>기록으로 보는 나의 식단.</h1>
    <section className="panel"><div className="analysis-controls"><div className="segmented" role="group" aria-label="분석 기간">{[['daily','일간 분석'],['monthly','월별 분석']].map(([key,label])=><button key={key} className={mode===key?'selected':''} aria-pressed={mode===key} onClick={()=>setMode(key)}>{label}</button>)}</div>
    <label>{mode==='daily'?'날짜':'월'}<input type={mode==='daily'?'date':'month'} value={mode==='daily'?date:month} onChange={e=>{if(e.target.value)setDate(mode==='daily'?e.target.value:`${e.target.value}-01`)}}/></label>
    <label>영양 항목<select value={metric} onChange={e=>setMetric(e.target.value)}>{Object.entries(nutrients).map(([key,[label]])=><option key={key} value={key}>{label}</option>)}</select></label></div>
    {error?<div role="alert"><p className="error">{error}</p><button className="text-button" onClick={()=>setRetry(value=>value+1)}>다시 불러오기</button></div>:!data?<p role="status">분석 기록을 불러오고 있습니다…</p>:<>
    <h2>{mode==='daily'?`${date} 식사별 ${label}`:`${month} 일별 ${label}`}</h2>
    <p className="muted">단위: {unit} · 한국 시간 기준 · —는 미기록입니다.{mode==='monthly'&&' 막대를 누르면 해당 날짜의 일간 분석을 볼 수 있습니다.'}</p>
    {(mode==='daily'?!day?.totals:!data.recorded_days)?<p className="empty">이 기간에 기록된 식단이 없습니다.</p>:<Bars items={bars} unit={unit} onSelect={mode==='monthly'?item=>{setDate(item.date);setMode('daily')}:undefined}/>}
    {mode==='daily'&&<SavedMeals meals={day?.meals||[]} title={`${date} 먹은 식단 · 저장한 사진`}/>}
    <h2>{mode==='daily'?'하루 기록 합계':'기록한 날의 하루 평균'}</h2><div className="nutrition-grid">{Object.entries(nutrients).map(([key,[label,unit]])=><div key={key}><span>{label}</span><strong>{totals?.[key]?.toLocaleString()??'—'}<small> {unit}</small></strong></div>)}</div>
    {mode==='monthly'&&<p className="muted">{data.recorded_days}일 기록 · 미기록일은 평균에서 제외합니다. 일부 식사만 기록한 날도 포함됩니다.</p>}
    </>}</section></>;
}
