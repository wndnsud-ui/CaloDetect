// 식단 항목을 음식 한 개당 한 행으로 펼치는 기록 표.
// 음식명 검색·식사 유형 필터·날짜 정렬은 받은 기록 범위 안에서 수행하며 영양값은 저장된 서버 값을 표시한다.
import React, { useState } from 'react';
import './meal-history.css';

const meals = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
const columns = [['cal','열량','kcal'], ['carbs','탄수화물','g'], ['protein','단백질','g'], ['fat','지방','g'], ['sugar','당류','g'], ['sodium','나트륨','mg']];
const format = value => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('ko-KR', {maximumFractionDigits:1});

// 식단 항목을 음식 한 개당 한 행으로 펼치는 기록 표.
export default function MealHistory({history, onAdd}) {
  const [query, setQuery] = useState('');
  const [type, setType] = useState('all');
  const [order, setOrder] = useState('desc');
  // 식단별 중첩 항목을 평탄화한 뒤 음식명/식사 조건을 적용한다. 원본 history 배열은 바꾸지 않는다.
  const rows = history.flatMap(meal => meal.items.map(item => ({meal, item})))
    .filter(({meal, item}) => (type === 'all' || meal.meal_type === type) && item.food_name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
    .sort((a, b) => order === 'desc' ? b.meal.meal_date.localeCompare(a.meal.meal_date) : a.meal.meal_date.localeCompare(b.meal.meal_date));

  return <div className="meal-history">
    <p className="eyebrow">MEAL HISTORY</p>
    <div className="history-heading"><div><h1>한 끼씩 쌓이는 나의 기록.</h1><p className="muted">날짜별 음식과 영양 정보를 한눈에 확인하세요.</p></div><button className="primary" onClick={onAdd}>+ 식단 추가하기</button></div>
    <section className="history-database" aria-label="식단 기록 데이터베이스">
      <div className="history-toolbar">
        <label className="history-search">음식 검색<input type="search" placeholder="음식 이름으로 검색" value={query} onChange={e => setQuery(e.target.value)}/></label>
        <label>식사 구분<select value={type} onChange={e => setType(e.target.value)}><option value="all">전체 식사</option>{Object.entries(meals).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>날짜 정렬<select value={order} onChange={e => setOrder(e.target.value)}><option value="desc">최신순</option><option value="asc">오래된순</option></select></label>
        <span className="history-count" role="status">음식 {rows.length}개</span>
      </div>
      <div className="history-table-scroll" tabIndex={0} role="region" aria-label="식단 기록 표 · 가로 스크롤 가능">
        <table><caption>조회된 식단 기록 · 음식별 섭취량과 영양 정보</caption><thead><tr><th scope="col" aria-sort={order === 'desc' ? 'descending' : 'ascending'}>날짜 {order === 'desc' ? '↓' : '↑'}</th><th scope="col">식사</th><th scope="col">음식</th><th scope="col">섭취량</th>{columns.map(([key, label, unit]) => <th scope="col" className="history-number" key={key}>{label}<small>{unit}</small></th>)}</tr></thead>
          <tbody>{rows.map(({meal, item}) => <tr key={`${meal.id}-${item.id}`}><td className="history-date">{meal.meal_date}</td><td><span className={`history-meal-tag history-meal-${meal.meal_type}`}>{meals[meal.meal_type] || meal.meal_type}</span></td><th scope="row">{item.food_name}</th><td className="history-serving">기준량 × {format(item.serving_multiplier)}</td>{columns.map(([key]) => <td key={key} className={`history-number ${key === 'cal' ? 'history-calories' : ''}`}>{format(item.nutrition?.[key])}</td>)}</tr>)}</tbody>
        </table>
        {!rows.length && <p className="history-empty">{history.length ? '검색 조건에 맞는 기록이 없습니다.' : '아직 기록된 식단이 없습니다. 첫 식단을 추가해 보세요.'}</p>}
      </div>
      <p className="history-table-note">음식 한 개당 한 행으로 표시합니다. 영양 정보는 기록한 섭취량 기준입니다.</p>
    </section>
  </div>;
}
