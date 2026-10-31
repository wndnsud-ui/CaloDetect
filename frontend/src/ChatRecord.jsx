// 칼로티 코치 대화 본문(develop A1 채팅 식사기록 이식). 플로팅 채팅 시트(CoachChat.jsx) 안에 들어가며 별도 페이지는 없다.
// 사진 촬영·선택 → 서버 분석 → 대화로 섭취량을 말하면 서버가 기록한다. 비율 버튼·저장 버튼은 없다(R14).
// 영양값·합계·확정은 모두 서버 응답을 표시하며, 대화·사진·초안은 서버에 저장돼 시트를 닫았다 열어도 이어진다.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { newRequestId } from './ChatConsumptionEdit';
import './chat-record.css';

export const COACH_FACE = '/jibang/f_happy.png';
// 업무지시서 v1.2 UI: 빠른 질문 5개. 누르면 일반 메시지로 보낸다.
const QUICK_QUESTIONS = ['오늘 뭐 먹지?', '오늘 식사 어땠어?', '단백질 많은 메뉴 추천', '가볍게 먹을 메뉴', '방금 음식 기록 수정'];
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

// 시트 안의 대화 본문. 첫 화면에는 지방이 인사와 빠른 질문을 두고, 그 아래로 서버 대화를 이어 붙인다.
export default function ChatRecord({api, onSaved, onNavigate}) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState(null);
  const [mealTypes, setMealTypes] = useState([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [failed, setFailed] = useState(null);
  const [shooting, setShooting] = useState(false);
  const [photoMenu, setPhotoMenu] = useState(false);
  // LLM 사용 상태(업무지시서 v1.2): 외부 AI 전송 고지 동의 여부와 오늘 남은 질문 수. 서버가 정하고 센다.
  const [llm, setLlm] = useState({llm: false, consent_required: false, notice: null, usage: null});
  const [agreeing, setAgreeing] = useState(false);
  const album = useRef(null), log = useRef(null), input = useRef(null);

  const takeLlm = useCallback(data => { if (data && 'llm' in data) setLlm({llm: data.llm, consent_required: data.consent_required, notice: data.notice, usage: data.usage}); }, []);
  // 서버 메시지를 sequence 기준으로 합친다(중복 제거). 화면은 시간값이 아니라 서버 순서를 따른다.
  const merge = useCallback(list => setMessages(current => {
    const map = new Map(current.map(m => [m.id, m]));
    list.forEach(m => map.set(m.id, m));
    return [...map.values()].sort((a, b) => a.sequence - b.sequence);
  }), []);

  const restore = useCallback(async () => {
    const state = await api('/chat/conversation');
    setConversationId(state.conversation_id); setMealTypes(state.meal_types); setDraft(state.draft);
    setMessages(state.messages); takeLlm(state);
  }, [api]);
  useEffect(() => { restore().catch(e => setError(e.message)); }, [restore]);
  // 포커스 복귀 시 최신 대화·초안을 다시 불러온다(다른 탭·기기 반영 보조. 실시간 푸시는 B 범위).
  useEffect(() => {
    const refresh = () => { if (document.visibilityState === 'visible' && !busy) restore().catch(() => {}); };
    document.addEventListener('visibilitychange', refresh);
    return () => document.removeEventListener('visibilitychange', refresh);
  }, [restore, busy]);
  useEffect(() => { log.current?.scrollTo?.({top: log.current.scrollHeight, behavior: 'smooth'}); }, [messages, busy]);

  // chip=true는 직전 답장 칩을 누른 경우다. 서버가 칩 문장과 같은지 확인하고 질문 횟수에서 뺀다.
  async function send(sentence, retryId, chip = false) {
    const value = sentence.trim();
    if (!value || busy || !conversationId) return;
    const clientId = retryId || newRequestId();
    setBusy('message'); setError(''); setFailed(null);
    try {
      const result = await api('/chat/messages', {conversation_id: conversationId, client_message_id: clientId, text: value, chip});
      merge(result.messages); setDraft(result.draft); takeLlm(result);
      if (result.messages.some(m => m.kind === 'saved' || m.kind === 'corrected')) onSaved?.(result.messages.find(m => m.kind === 'saved')?.payload?.meal?.meal_id);
    } catch (e) {
      if (e.status === 429) { setError(e.message); setLlm(current => ({...current, usage: current.usage && {...current.usage, used: current.usage.limit, remaining: 0}})); return; }
      if (e.status === 403) { setLlm(current => ({...current, consent_required: true})); return; }
      // 서버에 도착하지 않았거나 처리 실패: 저장 완료로 표시하지 않고 같은 ID로 다시 보낼 수 있게 한다.
      setFailed({text: value, id: clientId, chip});
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

  // 터치 여부와 관계없이 실제 카메라 촬영 창을 연다.
  function takePhoto() {
    setPhotoMenu(false);
    if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) {
      setError('카메라 촬영은 HTTPS 또는 localhost에서 지원됩니다. 보안 연결로 접속하거나 앨범에서 사진을 선택해 주세요.'); return;
    }
    setError(''); setShooting(true);
  }
  function pickAlbum() { setPhotoMenu(false); album.current?.click(); }

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
    if (item.action === 'type') { input.current?.focus(); return; }
    send(item.text, undefined, true);
  }

  async function agree() {
    if (agreeing) return;
    setAgreeing(true); setError('');
    try { takeLlm(await api('/chat/consent', {})); }
    catch (e) { setError(e.message); }
    finally { setAgreeing(false); }
  }

  const lastBot = [...messages].reverse().find(m => m.role === 'bot');
  // 빠른 질문은 진행 중인 사진 기록이 없고, 마지막 답에 답장 칩이 없을 때만 그 아래에 보여 준다.
  const showQuick = !!conversationId && !draft && !busy && !(lastBot?.payload?.chips?.length || lastBot?.payload?.meal_chips);
  const usage = llm.llm ? llm.usage : null, exhausted = !!usage && usage.remaining <= 0;
  const dateText = new Intl.DateTimeFormat('ko-KR', {timeZone:'Asia/Seoul', month:'long', day:'numeric', weekday:'long'}).format(new Date());

  return <div className="chat-record">
    <section className="chat-main" aria-label="칼로티 코치 대화">
      <ol className="chat-log" ref={log} aria-live="polite">
        <li className="coach-welcome">
          <img src="/jibang/front.png" alt=""/>
          <strong>안녕! 나 지방이야</strong>
          <p>식사 기록을 보고 메뉴 추천이나<br/>영양 분석을 도와줄게요.</p>
        </li>
        <li className="chat-date"><span>{dateText}</span></li>
        {messages.map(message => {
          const payload = message.payload || {};
          const isLast = lastBot && message.id === lastBot.id;
          if (message.kind === 'photo') return <li key={message.id} className="chat-row chat-row-user"><img className="chat-photo" src={payload.image_url} alt="보낸 식사 사진"/></li>;
          return <li key={message.id} className={`chat-row chat-row-${message.role}`}>
            {message.role === 'bot' && <img className="chat-avatar" src={COACH_FACE} alt=""/>}
            <div className={`chat-bubble chat-${message.role}${message.kind === 'saved' ? ' chat-done' : ''}${message.status === 'failed' ? ' chat-error' : ''}`}>
              {message.kind === 'saved' ? <SavedCard meal={payload.meal}/> : <p>{message.text}</p>}
              {payload.draft && <FoodCards draft={isLast && draft?.id === payload.draft.id ? draft : payload.draft}/>}
              {payload.cards && <CompareCards cards={payload.cards}/>}
              {isLast && (payload.chips?.length > 0 || payload.meal_chips) && <div className="reply-chips">
                {payload.chips?.map(item => <button type="button" key={item.label} className={item.action ? 'chip-nav' : ''} onClick={() => chip(item)} disabled={!!busy}>{item.label}</button>)}
                {payload.meal_chips && mealTypes.map(item => <button type="button" key={item.value} className={`chip-meal${draft?.meal_type === item.value ? ' selected' : ''}`} aria-pressed={draft?.meal_type === item.value} onClick={() => send(item.text, undefined, true)} disabled={!!busy || draft?.meal_type === item.value}>{item.label}</button>)}
              </div>}
            </div>
          </li>;
        })}
        {showQuick && <li className="coach-quick">
          <p>이렇게 물어볼 수 있어요</p>
          <div className="reply-chips">{QUICK_QUESTIONS.map((question, index) => <button type="button" key={question} className={index === 0 ? 'chip-nav' : ''} onClick={() => send(question)} disabled={exhausted}>{question}</button>)}</div>
        </li>}
        {busy && <li className="chat-row chat-row-bot"><img className="chat-avatar" src={COACH_FACE} alt=""/><div className="chat-bubble chat-bot chat-typing" role="status">{busy === 'upload' ? '사진을 올리고 있어요…' : busy === 'analysis' ? '사진 속 음식을 확인하고 있어요… (최대 1~2분)' : '확인하고 있어요…'}</div></li>}
      </ol>
      {error && <div className="chat-alert" role="alert">{error}{failed && <button type="button" onClick={() => send(failed.text, failed.id, failed.chip)}>다시 시도</button>}</div>}
      {usage && <p className={`coach-usage${exhausted ? ' is-empty' : ''}`} role="status">{exhausted ? '오늘 질문을 다 썼어요. 내일 다시 만나요!' : <>오늘 남은 질문 <b>{usage.remaining}/{usage.limit}</b></>}</p>}
      <form className="chat-input" onSubmit={submit}>
        <input ref={album} type="file" accept="image/jpeg,image/png" hidden onChange={upload}/>
        <div className="coach-photo">
          <button type="button" className="coach-photo-button" onClick={() => setPhotoMenu(open => !open)} disabled={!!busy || !conversationId} aria-label="음식 사진 보내기" aria-expanded={photoMenu}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>
          </button>
          {photoMenu && <div className="coach-photo-menu">
            <button type="button" onClick={takePhoto}>사진 찍기</button>
            <button type="button" onClick={pickAlbum}>앨범에서 선택</button>
          </div>}
        </div>
        <label className="sr-only" htmlFor="chat-text">메시지</label>
        <input id="chat-text" ref={input} maxLength={200} value={text} onChange={e => setText(e.target.value)} placeholder={exhausted ? '내일 다시 물어봐 주세요.' : '오늘 뭐 먹을지 물어보세요.'} disabled={!conversationId || exhausted}/>
        <button className="primary" disabled={!!busy || !text.trim() || exhausted}>보내기</button>
      </form>
    </section>
    {llm.llm && llm.consent_required && <div className="coach-consent" role="dialog" aria-modal="true" aria-labelledby="coach-consent-title">
      <div>
        <img src={COACH_FACE} alt=""/>
        <h3 id="coach-consent-title">지방이와 대화하기 전에</h3>
        <p>{llm.notice}</p>
        <button type="button" className="primary" onClick={agree} disabled={agreeing}>{agreeing ? '저장하고 있어요…' : '동의하고 시작'}</button>
      </div>
    </div>}
    {shooting && <WebcamCapture onClose={() => setShooting(false)}
      onCapture={blob => { setShooting(false); uploadFile(blob); }}
      onUnavailable={message => { setShooting(false); setError(message); }}/>}
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
    const constraints = {audio: false, video: deviceId ? {deviceId: {exact: deviceId}} : {facingMode: {ideal: 'environment'}, width: {ideal: 1920}, height: {ideal: 1080}}};
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
