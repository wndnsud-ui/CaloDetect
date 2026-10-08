// 서버 영양값을 총 열량·탄단지 구성비·당류/나트륨으로 표시한다.
// 4/4/9 kcal/g은 표시용 환산이며 CSV 총 열량을 재계산하거나 정책상 목표 비율로 해석하지 않는다.
import React from 'react';

// 탄수화물/단백질 4, 지방 9 kcal/g 환산 상수. 정책상 권장 섭취 비율과는 별개다.
const macros = [
  {key:'carbs', label:'탄수화물', factor:4},
  {key:'protein', label:'단백질', factor:4},
  {key:'fat', label:'지방', factor:9},
];
const format = value => Number(value).toLocaleString('ko-KR', {maximumFractionDigits:1});

// 서버 영양값을 총 열량·탄단지 구성비·당류/나트륨으로 표시한다.
export default function NutritionSummary({data}) {
  if (!data) return null;
  // 누락·비숫자·음수는 구성비 계산에 넣지 않고 정보 없음으로 표시한다.
  const available = macros.every(({key}) => data[key] != null && Number.isFinite(Number(data[key])) && Number(data[key]) >= 0);
  // 환산 열량 합계로 구성비를 계산한다. 실제 총 열량 표시는 전달된 data.cal을 그대로 사용한다.
  const energy = available ? macros.map(({key,factor}) => Number(data[key]) * factor) : [];
  const total = energy.reduce((sum,value) => sum + value, 0);
  // Largest remainders keep displayed integer percentages at exactly 100%.
  const raw = energy.map(value => total > 0 ? value / total * 100 : 0);
  // 정수 퍼센트를 먼저 내림하고 나머지가 큰 항목부터 1씩 배분해 표시 합계가 100%가 되게 한다.
  const percentages = raw.map(Math.floor);
  if (total > 0) {
    const order = raw.map((value,index) => ({index,remainder:value-percentages[index]})).sort((a,b) => b.remainder-a.remainder);
    const remaining = 100-percentages.reduce((sum,value) => sum+value,0);
    for (let i=0; i<remaining; i++) percentages[order[i].index]++;
  }
  return <section className="meal-nutrition" aria-label="식단 영양 요약">
    <div className="meal-nutrition-heading"><h3>총 열량</h3><strong>{data.cal == null ? '—' : format(data.cal)} <small>kcal</small></strong></div>
    <div className="meal-macro-legend">{macros.map(({key,label},index) => <div key={key}><i className={`meal-macro-${key}`} aria-hidden="true"/><span>{label} <b>{data[key] == null ? '—' : format(data[key])}g</b></span>{total > 0 && <small>{percentages[index]}%</small>}</div>)}</div>
    {total > 0 ? <div className="meal-macro-bar" role="img" aria-label={macros.map(({label},index) => `${label} ${percentages[index]}%`).join(', ')}>{macros.map(({key},index) => raw[index] > 0 && <div key={key} className={`meal-macro-${key}`} style={{width:`${raw[index]}%`}}>{raw[index] >= 10 && <span>{percentages[index]}%</span>}</div>)}</div> : <div className="meal-macro-empty">{available ? '탄단지 섭취량이 0g입니다.' : '탄단지 정보를 확인할 수 없습니다.'}</div>}
    <p className="meal-macro-caption">탄단지 비율은 열량 환산 기준입니다. 탄수화물·단백질 4 kcal/g, 지방 9 kcal/g을 적용하며 총 열량과 차이가 있을 수 있습니다.</p>
    <div className="meal-nutrition-details"><div><span>당류</span><strong>{data.sugar == null ? '—' : format(data.sugar)} <small>g</small></strong></div><div><span>나트륨</span><strong>{data.sodium == null ? '—' : format(data.sodium)} <small>mg</small></strong></div></div>
  </section>;
}
