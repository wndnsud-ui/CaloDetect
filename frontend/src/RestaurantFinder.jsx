import React, { useEffect, useRef, useState } from 'react';
import './restaurant-finder.css';

const distanceText = meters => meters >= 1000 ? `${(meters / 1000).toFixed(1)}km` : `${meters}m`;
// 카카오맵 JavaScript 키(공개용, 카카오 콘솔에 등록한 도메인에서만 동작). 없으면 지도 없이 목록만 보여 준다.
const KAKAO_JS_KEY = import.meta.env.VITE_KAKAO_JS_KEY;
let kakaoMaps = null;

// 카카오맵 SDK를 처음 쓸 때 한 번만 불러온다. 실패하면 다음 검색에서 다시 시도한다.
function loadKakaoMaps() {
  if (!KAKAO_JS_KEY) return Promise.reject(new Error('missing key'));
  if (window.kakao?.maps?.LatLng) return Promise.resolve(window.kakao.maps);
  kakaoMaps ||= new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(KAKAO_JS_KEY)}&autoload=false`;
    script.onload = () => window.kakao?.maps ? window.kakao.maps.load(() => resolve(window.kakao.maps)) : reject(new Error('sdk'));
    script.onerror = () => reject(new Error('sdk'));
    document.head.appendChild(script);
  }).catch(error => { kakaoMaps = null; throw error; });
  return kakaoMaps;
}

// 검색 결과 음식점을 번호 핀으로 표시한다. active가 바뀌면 그 가게로 이동하고, 핀을 누르면 onSelect.
function PlaceMap({places, active, onSelect}) {
  const box = useRef(null);
  const map = useRef(null);
  const pins = useRef([]);
  const [failed, setFailed] = useState(false);
  const points = places.filter(place => place.lat != null && place.lng != null);

  useEffect(() => {
    let cancelled = false;
    if (!points.length) return undefined;
    loadKakaoMaps().then(maps => {
      if (cancelled || !box.current) return;
      const bounds = new maps.LatLngBounds();
      map.current = new maps.Map(box.current, {center: new maps.LatLng(points[0].lat, points[0].lng), level: 4});
      map.current.addControl(new maps.ZoomControl(), maps.ControlPosition.RIGHT);
      pins.current = places.map((place, index) => {
        if (place.lat == null || place.lng == null) return null;
        const position = new maps.LatLng(place.lat, place.lng);
        bounds.extend(position);
        const pin = document.createElement('button');
        pin.type = 'button';
        pin.className = 'finder-pin';
        pin.textContent = String(index + 1);
        pin.setAttribute('aria-label', `${index + 1}번 ${place.name}`);
        pin.addEventListener('click', () => onSelect(index));
        new maps.CustomOverlay({map: map.current, position, content: pin, yAnchor: 1});
        return {pin, position};
      });
      if (points.length > 1) map.current.setBounds(bounds, 40, 40, 40, 40);
    }).catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; map.current = null; pins.current = []; if (box.current) box.current.innerHTML = ''; };
  }, [places]);

  useEffect(() => {
    pins.current.forEach((item, index) => item?.pin.classList.toggle('is-active', index === active));
    const target = pins.current[active];
    if (map.current && target) map.current.panTo(target.position);
  }, [active, places]);

  if (failed || !points.length) return null;
  return <div ref={box} className="finder-map" role="region" aria-label="음식점 위치 지도"/>;
}

// 추천 카드의 [근처 맛집 찾기]. 지역명 또는 현재 위치로 그 메뉴를 파는 음식점을 카카오맵 결과로 보여 준다.
// 지역·좌표는 이번 검색 요청에만 쓰고 저장하지 않는다.
export default function RestaurantFinder({api, food, onClose}) {
  const [area, setArea] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [active, setActive] = useState(null);
  const items = useRef([]);

  useEffect(() => {
    const close = event => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [onClose]);

  async function search(body, label) {
    setBusy(label); setError('');
    try { setResult({...(await api('/recommendations/places', {query: food, ...body})), label: body.area ? `${body.area} 근처` : '내 위치 근처'}); setActive(null); }
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
  // 지도 핀을 누르면 목록의 같은 가게를 강조하고 보이게 스크롤한다.
  function selectFromMap(index) {
    setActive(index);
    items.current[index]?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
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
          {result.places.length > 0 && <PlaceMap places={result.places} active={active} onSelect={selectFromMap}/>}
          {result.places.length ? <ol>{result.places.map((place, index) => <li key={`${place.url}-${index}`} ref={node => { items.current[index] = node; }} className={index === active ? 'is-active' : undefined}>
            <span className="finder-rank" aria-hidden="true">{index + 1}</span>
            <button type="button" className="finder-place" onClick={() => setActive(index)} aria-pressed={index === active}>
              <p><b>{place.name}</b>{place.distance != null && <span>{distanceText(place.distance)}</span>}</p>
              <small>{[place.category, place.address].filter(Boolean).join(' · ')}</small>
            </button>
            {place.url && <a href={place.url} target="_blank" rel="noreferrer" aria-label={`${place.name} 카카오맵에서 보기`}>카카오맵</a>}
          </li>)}</ol> : <p className="finder-empty">이 근처에서 찾지 못했어요. 다른 지역 이름으로 찾아보세요.</p>}
        </div>}
        <p className="finder-note">카카오맵 검색 결과입니다. 입력한 지역과 위치는 저장하지 않아요. 식당 메뉴의 1인분 양은 추천 기준 제공량과 다를 수 있어요.</p>
      </div>
    </section>
  </div>;
}
