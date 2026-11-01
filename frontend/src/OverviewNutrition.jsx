import React from 'react';

const macros = [['carbs', '탄수화물'], ['protein', '단백질'], ['fat', '지방']];
const number = value => Number.isFinite(value) ? value.toLocaleString('ko-KR', {maximumFractionDigits: 1}) : '—';

export default function OverviewNutrition({data, targets, currentDay, error}) {
  const meals = data?.meals || [];
  const latest = [...meals].sort((a, b) => Number(b.id) - Number(a.id))[0];
  const names = latest?.items?.map(item => item.food_name).filter(Boolean).join(' · ');
  const calories = latest?.items?.reduce((sum, item) => sum + (item.nutrition?.cal || 0), 0);
  return <div className="hd-overview-nutrition">
    <div className="hd-overview-heading"><h2>{currentDay ? '오늘의' : '선택한 날의'} 영양 균형</h2><span>섭취량 / 하루 목표</span></div>
    <div className="hd-overview-macros">{macros.map(([key, label]) => {
      const value = data?.totals?.[key];
      const goal = targets?.[key];
      const progress = goal > 0 && Number.isFinite(value) ? Math.max(0, Math.min(100, value / goal * 100)) : 0;
      return <div className={`hd-overview-macro hd-overview-${key}`} key={key}>
        <span>{label}</span><strong>{number(value)}<small>{goal > 0 ? ` / ${number(goal)} g` : ' g'}</small></strong>
        <div className="hd-overview-track" role="img" aria-label={`${label} ${number(value)} g${goal > 0 ? `, 목표 ${number(goal)} g` : ', 목표 미설정'}`}><i style={{width: `${progress}%`}}/></div>
        {!(goal > 0) && <small>목표 미설정</small>}
      </div>;
    })}</div>
    <div className="hd-overview-note"><span aria-hidden="true">🌱</span><p><strong>지방이의 한마디</strong>{error ? '기록을 불러오지 못했어요. 아래에서 다시 불러와 주세요.' : !data ? '식사 기록을 불러오고 있어요…' : meals.length ? '한 끼씩 쌓인 기록이 건강한 습관이 돼요. 다음 식사도 함께 기록해요!' : currentDay ? '첫 끼를 기록하면 오늘의 영양 균형을 알려드려요.' : '이날은 저장된 식사 기록이 없어요.'}</p></div>
    {latest && <div className="hd-overview-recent"><span>최근 기록</span><strong>{names || '식사 기록'}</strong><small>{number(calories)} kcal</small></div>}
  </div>;
}
