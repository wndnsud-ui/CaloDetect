// 식단 항목을 음식 한 개당 한 행으로 펼치는 기록 표.
// 음식명 검색·식사 유형 필터·날짜 정렬은 받은 기록 범위 안에서 수행하며 영양값은 저장된 서버 값을 표시한다.
import React, { useEffect, useRef, useState } from 'react';
import './meal-history.css';
import ChatConsumptionEdit from './ChatConsumptionEdit';

const meals = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
const columns = [['cal','열량','kcal'], ['carbs','탄수화물','g'], ['protein','단백질','g'], ['fat','지방','g'], ['sugar','당류','g'], ['sodium','나트륨','mg']];
// 모바일 표에서 쓰는 월/일 표기 (예: 2026-10-28 → 10/28)
const shortDate = iso => { const [, m, d] = String(iso).split('-'); return m && d ? `${Number(m)}/${Number(d)}` : iso; };
const format = value => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('ko-KR', {maximumFractionDigits:1});
const PAGE_SIZE = 15;

// 식단 항목을 음식 한 개당 한 행으로 펼치는 기록 표.
export default function MealHistory({history, api, onChanged, headerTabs}) {
  // 챗으로 수정 대상 {meal, item}. 서버가 CHAT_RECORD_ENABLED일 때만 항목에 version 키가 있어 진입 버튼이 보인다.
  const [editing, setEditing] = useState(null);
  const [query, setQuery] = useState('');
  const [type, setType] = useState('all');
  const [order, setOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const tableScroll = useRef(null);
  // 식단별 중첩 항목을 평탄화한 뒤 음식명/식사 조건을 적용한다. 원본 history 배열은 바꾸지 않는다.
  const rows = history.flatMap(meal => meal.items.map(item => ({meal, item})))
    .filter(({meal, item}) => (type === 'all' || meal.meal_type === type) && item.food_name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
    .sort((a, b) => order === 'desc' ? b.meal.meal_date.localeCompare(a.meal.meal_date) : a.meal.meal_date.localeCompare(b.meal.meal_date));
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const start = (currentPage - 1) * PAGE_SIZE;
  const visibleRows = rows.slice(start, start + PAGE_SIZE);
  const pageNumbers = [...new Set([1, currentPage - 1, currentPage, currentPage + 1, pageCount])]
    .filter(number => number >= 1 && number <= pageCount).sort((a, b) => a - b);
  useEffect(() => { setPage(previous => Math.min(previous, pageCount)); }, [pageCount]);
  useEffect(() => { if (tableScroll.current) tableScroll.current.scrollTop = 0; }, [currentPage, query, type, order]);

  return <div className="meal-history">
    {headerTabs}
    <section className="history-database" aria-label="식단 기록 데이터베이스">
      <div className="history-toolbar">
        <label className="history-search">음식 검색<input type="search" placeholder="음식 이름으로 검색" value={query} onChange={e => {setQuery(e.target.value); setPage(1);}}/></label>
        <label>식사 구분<select value={type} onChange={e => {setType(e.target.value); setPage(1);}}><option value="all">전체 식사</option>{Object.entries(meals).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>날짜 정렬<select value={order} onChange={e => {setOrder(e.target.value); setPage(1);}}><option value="desc">최신순</option><option value="asc">오래된순</option></select></label>
        <span className="history-count" role="status">음식 <strong>{rows.length.toLocaleString('ko-KR')}</strong>개<small>페이지당 {PAGE_SIZE}개</small></span>
      </div>
      <div ref={tableScroll} id="meal-history-table" className="history-table-scroll" tabIndex={0} role="region" aria-label="식단 기록 표 · 가로 스크롤 가능">
        <table><caption>조회된 식단 기록 · 음식별 섭취량과 영양 정보</caption><thead><tr><th scope="col" aria-sort={order === 'desc' ? 'descending' : 'ascending'}>날짜 {order === 'desc' ? '↓' : '↑'}</th><th scope="col">식사</th><th scope="col">음식</th><th scope="col"><span className="history-date-full">섭취량</span><span className="history-date-short">수정</span></th>{columns.map(([key, label, unit]) => <th scope="col" className="history-number" key={key}>{label}<small>{unit}</small></th>)}</tr></thead>
          <tbody>{visibleRows.map(({meal, item}) => <tr key={`${meal.id}-${item.id}`}><td className="history-date"><span className="history-date-full">{meal.meal_date}</span><span className="history-date-short">{shortDate(meal.meal_date)}</span></td><td><span className={`history-meal-tag history-meal-${meal.meal_type}`}>{meals[meal.meal_type] || meal.meal_type}</span></td><th scope="row">{item.food_name}</th><td className="history-serving"><span className="history-serving-text">기준량 × {format(item.effective_multiplier ?? item.serving_multiplier)}</span>{item.consumption_ratio != null && item.consumption_ratio !== 1 && <span className="history-ratio" title={`기록 기준량 × ${format(item.serving_multiplier)} 중 섭취 비율`}>섭취 {Math.round(item.consumption_ratio * 100)}%</span>}{api && item.version !== undefined && <button type="button" className="history-chat-edit" onClick={() => setEditing({meal, item})}>챗으로 수정</button>}</td>{columns.map(([key]) => <td key={key} className={`history-number ${key === 'cal' ? 'history-calories' : ''}`}>{format(item.nutrition?.[key])}</td>)}</tr>)}</tbody>
        </table>
        {!rows.length && <p className="history-empty">{history.length ? '검색 조건에 맞는 기록이 없습니다.' : '아직 기록된 식단이 없습니다. 첫 식단을 추가해 보세요.'}</p>}
      </div>
      <div className="history-pagination">
        <p className="history-page-summary" role="status" aria-live="polite">{rows.length ? <><strong>{start + 1}–{Math.min(start + PAGE_SIZE, rows.length)}</strong> / 전체 {rows.length.toLocaleString('ko-KR')}개</> : '표시할 기록이 없습니다.'}</p>
        <nav aria-label="히스토리 페이지 이동" aria-controls="meal-history-table">
          <button type="button" className="history-page-direction" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>‹ 이전</button>
          {pageNumbers.map((number, index) => <React.Fragment key={number}>
            {index > 0 && number - pageNumbers[index - 1] > 1 && <span className="history-page-gap" aria-hidden="true">…</span>}
            <button type="button" className={number === currentPage ? 'is-current' : ''} aria-label={`${number}페이지`} aria-current={number === currentPage ? 'page' : undefined} onClick={() => setPage(number)}>{number}</button>
          </React.Fragment>)}
          <button type="button" className="history-page-direction" disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)}>다음 ›</button>
        </nav>
      </div>
      <p className="history-table-note">음식 한 개당 한 행으로 표시합니다. 영양 정보는 기록한 섭취량 기준입니다.</p>
    </section>
    {editing && <ChatConsumptionEdit api={api} meal={editing.meal} item={editing.item} onClose={() => setEditing(null)} onSaved={onChanged}/>}
  </div>;
}
