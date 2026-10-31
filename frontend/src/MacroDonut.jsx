import React from 'react';
import StreamlitChart from './StreamlitChart';

const macros = [
  {key: 'carbs', label: '탄수화물', factor: 4, color: '#79af81'},
  {key: 'protein', label: '단백질', factor: 4, color: '#e5b76f'},
  {key: 'fat', label: '지방', factor: 9, color: '#63b6ae'},
];

// Only convert server values for visual proportions; keep reported total kcal unchanged.
export default function MacroDonut({data}) {
  const available = macros.every(({key}) => data?.[key] != null && Number.isFinite(Number(data[key])) && Number(data[key]) >= 0);
  const energy = macros.map(({key, factor}) => available ? Number(data[key]) * factor : 0);
  const total = energy.reduce((sum, value) => sum + value, 0);
  return <section className="analysis-macro-card" aria-label="탄단지 열량 구성비">
    <h3>탄단지 구성비</h3>
    <div className="analysis-macro-body">
      <div className="analysis-macro-donut"><StreamlitChart kind="macro_donut" data={{carbs: available ? data.carbs : 0, protein: available ? data.protein : 0, fat: available ? data.fat : 0}} height={240} title="탄수화물 단백질 지방 열량 구성비 도넛차트"/></div>
      <ul className="analysis-macro-legend">{macros.map((macro, index) => <li key={macro.key}>
        <i style={{background: macro.color}} aria-hidden="true"/>
        <span>{macro.label}<small>{available ? `${Number(data[macro.key]).toLocaleString()}g` : '—'}</small></span>
        <b>{total > 0 ? `${(energy[index] / total * 100).toFixed(1)}%` : '—'}</b>
      </li>)}</ul>
    </div>
    <p>탄수화물·단백질 4 kcal/g, 지방 9 kcal/g 환산 기준입니다. 표시된 총 칼로리와 차이가 있을 수 있습니다.</p>
  </section>;
}
