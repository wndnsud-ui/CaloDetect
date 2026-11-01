import React, { useEffect, useState } from 'react';
import './restaurant-finder.css';

const distanceText = meters => meters >= 1000 ? `${(meters / 1000).toFixed(1)}km` : `${meters}m`;

// 추천 카드의 [근처 맛집 찾기]. 지역명 또는 현재 위치로 그 메뉴를 파는 음식점을 카카오맵 결과로 보여 준다.
// 지역·좌표는 이번 검색 요청에만 쓰고 저장하지 않는다.
export default function RestaurantFinder({api, food, onClose}) {
  const [area, setArea] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    const close = event => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [onClose]);

  async function search(body, label) {
    setBusy(label); setError('');
    try { setResult({...(await api('/recommendations/places', {query: food, ...body})), label: body.area ? `${body.area} 근처` : '내 위치 근처'}); }
    catch (e) { setError(e.message); }
    finally { setBusy(''); }
  }
  function searchArea(event) {
    event.preventDefault();
    if (!area.trim() || busy) return;
    search({area: area.trim()}, 'area');
  }
  function searchHere() {
    if (busy) return;
    if (!navigator.geolocation || !window.isSecureContext) { setError('위치 확인은 HTTPS 또는 localhost에서만 돼요. 지역 이름을 입력해 주세요.'); return; }
    setBusy('locate'); setError('');
    navigator.geolocation.getCurrentPosition(
      position => search({lat: position.coords.latitude, lng: position.coords.longitude}, 'locate'),
      () => { setBusy(''); setError('위치 권한이 없어서 찾지 못했어요. 지역 이름을 입력해 주세요.'); },
      {timeout: 10000, maximumAge: 300000});
  }

  return <div className="finder-backdrop" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="finder" role="dialog" aria-modal="true" aria-labelledby="finder-title">
      <header>
        <div><p className="eyebrow">근처 맛집 찾기</p><h2 id="finder-title">{food} 맛집</h2></div>
        <button type="button" className="finder-close" onClick={onClose} aria-label="닫기">×</button>
      </header>
      <div className="finder-body">
        <form className="finder-search" onSubmit={searchArea}>
          <input value={area} onChange={event => setArea(event.target.value)} maxLength={30} placeholder="지역 이름 (예: 강남역, 판교)" aria-label="지역 이름" autoFocus/>
          <button type="submit" className="primary" disabled={!area.trim() || !!busy}>{busy === 'area' ? '찾는 중…' : '찾기'}</button>
        </form>
        <button type="button" className="outline finder-here" onClick={searchHere} disabled={!!busy}>{busy === 'locate' ? '위치 확인 중…' : '📍 내 위치로 찾기'}</button>
        {error && <p className="error" role="alert">{error}</p>}
        {result && <div className="finder-results" role="status">
          <p className="finder-caption">{result.label} · {food}</p>
          {result.places.length ? <ol>{result.places.map((place, index) => <li key={`${place.url}-${index}`}>
            <span className="finder-rank" aria-hidden="true">{index + 1}</span>
            <div>
              <p><b>{place.name}</b>{place.distance != null && <span>{distanceText(place.distance)}</span>}</p>
              <small>{[place.category, place.address].filter(Boolean).join(' · ')}</small>
            </div>
            {place.url && <a href={place.url} target="_blank" rel="noreferrer" aria-label={`${place.name} 카카오맵에서 보기`}>지도</a>}
          </li>)}</ol> : <p className="finder-empty">이 근처에서 찾지 못했어요. 다른 지역 이름으로 찾아보세요.</p>}
        </div>}
        <p className="finder-note">카카오맵 검색 결과입니다. 입력한 지역과 위치는 저장하지 않아요. 식당 메뉴의 1인분 양은 추천 기준 제공량과 다를 수 있어요.</p>
      </div>
    </section>
  </div>;
}
