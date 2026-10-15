// 채팅으로 식사 기록하기(A1). 사진 촬영·선택 → 서버 분석 → 대화로 섭취량을 말하면 서버가 자동으로 기록한다.
// 비율 버튼·조정 패널·저장 버튼은 없다(R14). 답장 칩은 정해진 문장을 일반 메시지로 보낼 뿐이다.
// 영양값·합계·확정은 모두 서버 응답을 표시하며, 대화·사진·초안은 서버에 저장돼 재접속해도 복원된다.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { newRequestId } from './ChatConsumptionEdit';
import StreamlitChart from './StreamlitChart';
import './chat-record.css';

const mealNames = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
const fmt = value => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('ko-KR', {maximumFractionDigits:1});
const percent = ratio => `${Math.round(Number(ratio) * 100)}%`;
const MAX_SIDE = 2048;

// 업로드 전 긴 변 2048px 이하 JPEG로 변환한다(10MB·2500만 화소 초과와 HEIC 방지). 디코딩 실패면 원본을 보내지 않는다.
async function toJpeg(file) {
  const url = URL.createObjectURL(file);
  try {
    const image = await new Promise((resolve, reject) => { const img = new Image(); img.onload = () => resolve(img); img.onerror = reject; img.src = url; });
    const scale = Math.min(1, MAX_SIDE / Math.max(image.naturalWidth, image.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(image.naturalWidth * scale); canvas.height = Math.round(image.naturalHeight * scale);
    canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
    if (!blob) throw new Error('encode');
    return blob;
  } finally { URL.revokeObjectURL(url); }
}

// 탐지 bbox로 원본 사진에서 음식 부분만 잘라 보여 준다. bbox가 없으면(이름으로 추가한 음식) 이름 첫 글자.
function FoodThumb({src, bbox, name}) {
  const canvas = useRef(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!src || !bbox) return;
    const img = new Image();
    img.onload = () => {
      const [x1, y1, x2, y2] = bbox; const ctx = canvas.current?.getContext('2d');
      if (!ctx) return;
      const w = Math.max(1, x2 - x1), h = Math.max(1, y2 - y1), side = Math.max(w, h);
      ctx.clearRect(0, 0, 96, 96);
      ctx.drawImage(img, x1 + w / 2 - side / 2, y1 + h / 2 - side / 2, side, side, 0, 0, 96, 96);
    };
    img.onerror = () => setFailed(true);
    img.src = src;
  }, [src, bbox]);
  if (!src || !bbox || failed) return <span className="food-thumb food-thumb-empty" aria-hidden="true">{name?.[0] || '?'}</span>;
  return <canvas ref={canvas} className="food-thumb" width={96} height={96} aria-hidden="true"/>;
}

// 읽기 전용 음식 카드. 비율 배지는 표시만 하며 누를 수 없다.
function FoodCards({draft}) {
  if (!draft?.items?.length) return null;
  return <div className="food-cards">
    {draft.items.map(item => <div key={item.id} className="food-card">
      <FoodThumb src={draft.image_url} bbox={item.bbox} name={item.food_name}/>
      <div><b>{item.food_name}</b><small>{item.unit} · 섭취 {percent(item.consumption_ratio)}</small></div>
      <span className="food-card-kcal">{fmt(item.nutrition.cal)}<small>kcal</small></span>
      <span className={`ratio-badge${item.consumption_ratio !== 1 ? ' changed' : ''}`}>{percent(item.consumption_ratio)}</span>
    </div>)}
    <p className="food-cards-total">합계 <b>{fmt(draft.totals.cal)} kcal</b> · 탄 {fmt(draft.totals.carbs)}g · 단 {fmt(draft.totals.protein)}g · 지 {fmt(draft.totals.fat)}g · {draft.meal_label}</p>
  </div>;
}

function SavedCard({meal}) {
  return <div className="saved-card">
    <p className="saved-check" aria-hidden="true">✓</p>
    <p className="saved-title">식사 기록이 저장되었어요!</p>
    {meal.image_url && <img src={meal.image_url} alt="기록한 식사 사진"/>}
    <p className="saved-meta">{meal.meal_label} · {meal.meal_date}</p>
    <ul>{meal.items.map((item, index) => <li key={index}><span>{item.food_name} <small>{percent(item.consumption_ratio)}</small></span><b>{fmt(item.cal)} kcal</b></li>)}</ul>
    <p className="saved-total">합계 <b>{fmt(meal.totals.cal)} kcal</b></p>
  </div>;
}

function CompareCards({cards}) {
  return <div className="compare-cards">{cards.map((card, index) => <p key={index}><b>{card.food_name}</b> {percent(card.before.consumption_ratio)} ({fmt(card.before.nutrition.cal)} kcal) → <b>{percent(card.after.consumption_ratio)}</b> ({fmt(card.after.nutrition.cal)} kcal)</p>)}</div>;
}

// 서버 기본값과 같은 시각 규칙(05~10 아침, 11~15 점심, 16~21 저녁, 그 외 간식, Asia/Seoul).
function currentMealType() {
  const hour = Number(new Intl.DateTimeFormat('en-US', {timeZone:'Asia/Seoul', hour:'numeric', hourCycle:'h23'}).format(new Date()));
  return hour >= 5 && hour < 11 ? 'breakfast' : hour >= 11 && hour < 16 ? 'lunch' : hour >= 16 && hour < 22 ? 'dinner' : 'snack';
}

const mealRows = [['breakfast', '아침', '🌅'], ['lunch', '점심', '☀️'], ['dinner', '저녁', '🌙'], ['snack', '간식', '🍪']];

// 우측 "오늘" 카드: 목표 대비 % 도넛, 총 섭취·목표 kcal, 아침·점심·저녁·간식별 kcal(서버 저장값 합계).
// 강조 행은 지금 기록 중인 식사 종류(없으면 현재 시각 기준). 행을 누르면 그 식사의 음식이 펼쳐진다.
function TodayMiniSummary({today, activeType, onRefresh, onCalendar}) {
  const [open, setOpen] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const eaten = Number(today?.totals?.cal || 0), target = Number(today?.target_calories || 0);
  const ratio = target > 0 ? eaten / target : 0;

  const day = today?.date ? new Date(`${today.date}T12:00:00+09:00`) : new Date();
  const dateText = new Intl.DateTimeFormat('ko-KR', {timeZone:'Asia/Seoul', year:'numeric', month:'long', day:'numeric'}).format(day);
  const weekday = new Intl.DateTimeFormat('ko-KR', {timeZone:'Asia/Seoul', weekday:'short'}).format(day);
  const byType = Object.fromEntries(mealRows.map(([type]) => {
    const meals = (today?.meals || []).filter(meal => meal.meal_type === type);
    const items = meals.flatMap(meal => meal.items);
    return [type, {items, cal: items.reduce((sum, item) => sum + Number(item.nutrition?.cal || 0), 0)}];
  }));
  async function refresh() {
    if (refreshing) return;
    setRefreshing(true);
    try { await onRefresh?.(); } finally { setRefreshing(false); }
  }
  return <section className="chat-side-card today-card" aria-label="오늘의 식사">
    <div className="today-head">
      <button type="button" className={`icon-button${refreshing ? ' spinning' : ''}`} onClick={refresh} aria-label="오늘 기록 새로고침">↻</button>
      <h3>오늘</h3><span className="today-date">{dateText} ({weekday})</span>
      <button type="button" className="icon-button today-calendar" onClick={onCalendar} aria-label="홈 주간 달력 보기">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 10h16"/></svg>
      </button>
    </div>
    <div className="today-overview">
      <div className="today-donut">
        <StreamlitChart kind="ring_percent" data={{value: eaten, target}} height={118} title={target ? `목표 대비 섭취 ${Math.round(ratio * 100)}%` : "목표 미설정"}/>
      </div>
      <div className="today-total">
        <small>총 섭취 칼로리</small>
        <p><b>{fmt(eaten)}</b> kcal</p>
        <small>{target ? `목표 ${fmt(target)} kcal` : '목표를 설정해 주세요'}</small>
      </div>
    </div>
    <ul className="today-meals-list">
      {mealRows.map(([type, label, icon]) => {
        const row = byType[type];
        const expanded = open === type;
        return <li key={type} className={`${type === activeType ? 'active' : ''}${expanded ? ' expanded' : ''}`}>
          <button type="button" onClick={() => setOpen(expanded ? null : type)} aria-expanded={expanded}>
            <span className={`meal-icon meal-icon-${type}`} aria-hidden="true">{icon}</span>
            <span className="meal-name">{label}</span>
            <span className="meal-kcal">{fmt(row.cal)} kcal</span>
            <span className="meal-chevron" aria-hidden="true">›</span>
          </button>
          {expanded && (row.items.length ? <ul className="meal-foods">{row.items.map(item => <li key={item.id}><span>{item.food_name}{item.consumption_ratio != null && item.consumption_ratio !== 1 && <small> {Math.round(item.consumption_ratio * 100)}%</small>}</span><span>{fmt(item.nutrition?.cal)} kcal</span></li>)}</ul>
            : <p className="meal-empty">아직 기록이 없어요.</p>)}
        </li>;
      })}
    </ul>
  </section>;
}

// 사진이 없거나 파일을 불러오지 못하면 깨진 이미지 대신 기본 아이콘을 보여 준다.
function RecentThumb({src}) {
  const [failed, setFailed] = useState(false);
  return src && !failed ? <img src={src} alt="" onError={() => setFailed(true)}/> : <span className="recent-thumb" aria-hidden="true">🍽</span>;
}

function RecentMealsMini({history}) {
  const rows = history.slice(0, 5);
  return <section className="chat-side-card" aria-label="최근 식사 히스토리">
    <h3>최근 식사 히스토리</h3>
    {rows.length ? <ul className="recent-meals">{rows.map(meal => <li key={meal.id}>
      <RecentThumb src={meal.image_urls?.[0]}/>
      <div><b>{meal.items.map(item => item.food_name).join(', ')}</b><small>{meal.meal_date} · {mealNames[meal.meal_type] || meal.meal_type}</small></div>
      <span>{fmt(meal.items.reduce((sum, item) => sum + item.nutrition.cal, 0))}<small>kcal</small></span>
    </li>)}</ul> : <p className="muted">아직 기록이 없어요.</p>}
  </section>;
}

export default function ChatRecord({api, today, history, onSaved, onNavigate}) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState(null);
  const [mealTypes, setMealTypes] = useState([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [failed, setFailed] = useState(null);
  const [shooting, setShooting] = useState(false);
  const camera = useRef(null), album = useRef(null), log = useRef(null), input = useRef(null);

  // 서버 메시지를 sequence 기준으로 합친다(중복 제거). 화면은 시간값이 아니라 서버 순서를 따른다.
  const merge = useCallback(list => setMessages(current => {
    const map = new Map(current.map(m => [m.id, m]));
    list.forEach(m => map.set(m.id, m));
    return [...map.values()].sort((a, b) => a.sequence - b.sequence);
  }), []);

  const restore = useCallback(async () => {
    const state = await api('/chat/conversation');
    setConversationId(state.conversation_id); setMealTypes(state.meal_types); setDraft(state.draft);
    setMessages(state.messages);
  }, [api]);
  useEffect(() => { restore().catch(e => setError(e.message)); }, [restore]);
  // 포커스 복귀 시 최신 대화·초안을 다시 불러온다(다른 탭·기기 반영 보조. 실시간 푸시는 B 범위).
  useEffect(() => {
    const refresh = () => { if (document.visibilityState === 'visible' && !busy) restore().catch(() => {}); };
    document.addEventListener('visibilitychange', refresh);
    return () => document.removeEventListener('visibilitychange', refresh);
  }, [restore, busy]);
  useEffect(() => { log.current?.scrollTo?.({top: log.current.scrollHeight, behavior: 'smooth'}); }, [messages, busy]);

  async function send(sentence, retryId) {
    const value = sentence.trim();
    if (!value || busy || !conversationId) return;
    const clientId = retryId || newRequestId();
    setBusy('message'); setError(''); setFailed(null);
    try {
      const result = await api('/chat/messages', {conversation_id: conversationId, client_message_id: clientId, text: value});
      merge(result.messages); setDraft(result.draft);
      if (result.messages.some(m => m.kind === 'saved' || m.kind === 'corrected')) onSaved?.();
    } catch (e) {
      // 서버에 도착하지 않았거나 처리 실패: 저장 완료로 표시하지 않고 같은 ID로 다시 보낼 수 있게 한다.
      setFailed({text: value, id: clientId});
      setError(e.status === 409 ? '기록이 변경됐어요. 최신 내용을 확인해 주세요.' : '아직 저장되지 않았어요. 다시 시도해 주세요.');
      if (e.status === 409) restore().catch(() => {});
    } finally { setBusy(''); }
  }

  async function submit(event) {
    event.preventDefault();
    const value = text; setText('');
    await send(value);
    input.current?.focus();
  }

  async function upload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    await uploadFile(file);
  }

  // 사진 찍기: 휴대폰(터치)은 기기 카메라 앱(capture 입력), PC는 웹캠 촬영 창(getUserMedia, localhost·HTTPS에서만).
  function takePhoto() {
    const touch = window.matchMedia?.('(pointer: coarse)').matches;
    if (touch || !navigator.mediaDevices?.getUserMedia || !window.isSecureContext) { camera.current?.click(); return; }
    setError(''); setShooting(true);
  }

  async function uploadFile(file) {
    if (!file || busy || !conversationId) return;
    setError(''); setFailed(null);
    let blob;
    try { blob = await toJpeg(file); }
    catch { setError('이 사진 형식은 열 수 없어요. JPG나 PNG 사진을 선택해 주세요.'); return; }
    setBusy('upload');
    try {
      const form = new FormData();
      form.append('file', blob, 'photo.jpg'); form.append('conversation_id', conversationId); form.append('upload_request_id', newRequestId());
      const uploaded = await api('/chat/attachments', form);
      merge(uploaded.messages); setDraft(uploaded.draft);
      setBusy('analysis');
      const analyzed = await api(`/chat/attachments/${uploaded.attachment_id}/analysis`, {});
      merge(analyzed.messages); setDraft(analyzed.draft);
    } catch (e) {
      setError(e.message);
      restore().catch(() => {});
    } finally { setBusy(''); }
  }

  function chip(item) {
    if (item.action === 'new_photo') { takePhoto(); return; }
    if (item.action === 'today') { onNavigate('홈'); return; }
    send(item.text);
  }

  const lastBot = [...messages].reverse().find(m => m.role === 'bot');
  const dateText = new Intl.DateTimeFormat('ko-KR', {timeZone:'Asia/Seoul', month:'long', day:'numeric', weekday:'short'}).format(new Date());

  return <div className="chat-record">
    <section className="chat-main" aria-label="채팅으로 식사 기록하기">
      <div className="chat-title"><div><p className="eyebrow">CHAT MEAL LOG</p><h1>채팅으로 식사 기록하기</h1></div><p className="muted">사진을 보내고 드신 양을 말하면 바로 기록돼요.</p></div>
      <ol className="chat-log" ref={log} aria-live="polite">
        <li className="chat-date"><span>{dateText}</span></li>
        {messages.map(message => {
          const payload = message.payload || {};
          const isLast = lastBot && message.id === lastBot.id;
          if (message.kind === 'photo') return <li key={message.id} className="chat-row chat-row-user"><img className="chat-photo" src={payload.image_url} alt="보낸 식사 사진"/></li>;
          return <li key={message.id} className={`chat-row chat-row-${message.role}`}>
            {message.role === 'bot' && <span className="chat-avatar" aria-hidden="true">🥗</span>}
            <div className={`chat-bubble chat-${message.role}${message.kind === 'saved' ? ' chat-done' : ''}${message.status === 'failed' ? ' chat-error' : ''}`}>
              {message.kind === 'saved' ? <SavedCard meal={payload.meal}/> : <p>{message.text}</p>}
              {payload.draft && <FoodCards draft={isLast && draft?.id === payload.draft.id ? draft : payload.draft}/>}
              {payload.cards && <CompareCards cards={payload.cards}/>}
              {isLast && (payload.chips?.length > 0 || payload.meal_chips) && <div className="reply-chips">
                {payload.chips?.map(item => <button type="button" key={item.label} className={item.action ? 'chip-nav' : ''} onClick={() => chip(item)} disabled={!!busy}>{item.label}</button>)}
                {payload.meal_chips && mealTypes.map(item => <button type="button" key={item.value} className={`chip-meal${draft?.meal_type === item.value ? ' selected' : ''}`} aria-pressed={draft?.meal_type === item.value} onClick={() => send(item.text)} disabled={!!busy || draft?.meal_type === item.value}>{item.label}</button>)}
              </div>}
            </div>
          </li>;
        })}
        {busy && <li className="chat-row chat-row-bot"><span className="chat-avatar" aria-hidden="true">🥗</span><div className="chat-bubble chat-bot chat-typing" role="status">{busy === 'upload' ? '사진을 올리고 있어요…' : busy === 'analysis' ? '사진 속 음식을 확인하고 있어요… (최대 1~2분)' : '확인하고 있어요…'}</div></li>}
      </ol>
      {error && <div className="chat-alert" role="alert">{error}{failed && <button type="button" onClick={() => send(failed.text, failed.id)}>다시 시도</button>}</div>}
      <form className="chat-input" onSubmit={submit}>
        <input ref={camera} type="file" accept="image/jpeg,image/png" capture="environment" hidden onChange={upload}/>
        <input ref={album} type="file" accept="image/jpeg,image/png" hidden onChange={upload}/>
        <button type="button" className="chat-tool" onClick={takePhoto} disabled={!!busy}>📷 사진 찍기</button>
        <button type="button" className="chat-tool" onClick={() => album.current?.click()} disabled={!!busy}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" style={{verticalAlign:'middle',marginRight:6}}><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>앨범에서 선택</button>
        <label className="sr-only" htmlFor="chat-text">메시지</label>
        <input id="chat-text" ref={input} maxLength={200} value={text} onChange={e => setText(e.target.value)} placeholder='예: 절반만 먹었어 올려줘' disabled={!conversationId}/>
        <button className="primary" disabled={!!busy || !text.trim()}>전송</button>
      </form>
    </section>
    <div className="chat-side">
      <TodayMiniSummary today={today} activeType={draft?.meal_type || currentMealType()} onRefresh={onSaved} onCalendar={() => onNavigate('홈')}/>
      <RecentMealsMini history={history}/>
    </div>
    {shooting && <WebcamCapture onClose={() => setShooting(false)}
      onCapture={blob => { setShooting(false); uploadFile(blob); }}
      onUnavailable={message => { setShooting(false); setError(message); album.current?.click(); }}/>}
  </div>;
}

// PC 웹캠 촬영 창. 미리보기에서 [촬영]하면 현재 화면을 JPEG로 만들어 업로드한다. 닫으면 카메라를 끈다.
// 촬영을 취소하면 서버 기록을 만들지 않는다. 카메라가 없거나 권한을 거부하면 앨범 선택으로 이어진다.
function WebcamCapture({onCapture, onClose, onUnavailable}) {
  const video = useRef(null);
  const stream = useRef(null);
  const [ready, setReady] = useState(false);
  const [devices, setDevices] = useState([]);
  const [deviceId, setDeviceId] = useState('');

  useEffect(() => {
    let active = true;
    const constraints = {audio: false, video: deviceId ? {deviceId: {exact: deviceId}} : {facingMode: 'environment', width: {ideal: 1920}, height: {ideal: 1080}}};
    setReady(false);
    navigator.mediaDevices.getUserMedia(constraints).then(async media => {
      if (!active) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current?.getTracks().forEach(track => track.stop());
      stream.current = media;
      if (video.current) { video.current.srcObject = media; await video.current.play().catch(() => {}); }
      setReady(true);
      const list = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput');
      if (active) setDevices(list);
    }).catch(error => {
      if (!active) return;
      onUnavailable(error?.name === 'NotAllowedError' ? '카메라 권한이 거부되었어요. 앨범에서 사진을 선택해 주세요.' : '사용할 수 있는 카메라가 없어요. 앨범에서 사진을 선택해 주세요.');
    });
    return () => { active = false; };
  }, [deviceId]);
  useEffect(() => () => stream.current?.getTracks().forEach(track => track.stop()), []);

  function shoot() {
    const v = video.current;
    if (!v?.videoWidth) return;
    const scale = Math.min(1, MAX_SIDE / Math.max(v.videoWidth, v.videoHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(v.videoWidth * scale); canvas.height = Math.round(v.videoHeight * scale);
    canvas.getContext('2d').drawImage(v, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(blob => { stream.current?.getTracks().forEach(track => track.stop()); if (blob) onCapture(blob); }, 'image/jpeg', 0.9);
  }

  return <div className="chat-edit-backdrop" role="presentation" onClick={event => event.target === event.currentTarget && onClose()}>
    <section className="webcam" role="dialog" aria-modal="true" aria-label="사진 찍기">
      <div className="webcam-view">
        <video ref={video} playsInline muted/>
        {!ready && <p className="webcam-wait" role="status">카메라를 켜고 있어요… 브라우저가 권한을 물으면 허용해 주세요.</p>}
      </div>
      <div className="webcam-actions">
        {devices.length > 1 && <select aria-label="카메라 선택" value={deviceId} onChange={event => setDeviceId(event.target.value)}>
          <option value="">기본 카메라</option>
          {devices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `카메라 ${i + 1}`}</option>)}
        </select>}
        <button type="button" className="text-button" onClick={onClose}>취소</button>
        <button type="button" className="primary webcam-shoot" onClick={shoot} disabled={!ready}>📷 촬영</button>
      </div>
    </section>
  </div>;
}
