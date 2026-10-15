// 히스토리 항목의 섭취량을 말로 수정하는 입력창(A0). 비율 버튼·저장 버튼 없이 문장만 받는다(R14).
// 해석·계산은 서버가 하고, 클라이언트는 직전 미리보기(비율·version·request_id)만 보관했다가 확정 발화 때 PUT 한다(5.1).
// A0는 대화를 서버에 저장하지 않으므로 이 창을 닫으면 대화 내용은 사라진다. 저장된 식사 변경은 서버 이력에 남는다.
import React, { useEffect, useRef, useState } from 'react';
import './chat-record.css';

const mealNames = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
const columns = [['cal','열량','kcal'], ['carbs','탄수화물','g'], ['protein','단백질','g'], ['fat','지방','g'], ['sugar','당류','g'], ['sodium','나트륨','mg']];
const format = value => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('ko-KR', {maximumFractionDigits:2});
const percent = ratio => `${Math.round(Number(ratio) * 100)}%`;
const clarifyText = {
  unsupported_expression: '"절반", "4분의 1"처럼 말씀해 주시겠어요?',
  ambiguous_target: '어떤 음식의 양을 바꿀까요?',
  missing_target: '수정할 음식을 먼저 골라 주세요.',
  empty_meal: '이 식사에는 음식이 없어요.',
};
const MISMATCH = '저장된 값이 현재 계산과 달라요. 저장하면 현재 기준으로 다시 계산돼요.';

// crypto.randomUUID가 없는 비보안 컨텍스트(LAN IP 접속)에서는 getRandomValues로 UUID v4를 만든다.
export function newRequestId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40; bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map(b => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}

// 수정 전·후 6개 영양값 비교 표.
function Compare({before, after, unit}) {
  return <div className="chat-compare">
    <p className="chat-compare-head"><span>섭취 {percent(before.consumption_ratio)} → <b>{percent(after.consumption_ratio)}</b></span>{unit&&<small>{unit} × {format(after.effective_multiplier)}</small>}</p>
    <table><thead><tr><th scope="col">영양</th><th scope="col">수정 전</th><th scope="col">수정 후</th></tr></thead>
      <tbody>{columns.map(([key, label, u]) => <tr key={key}><th scope="row">{label}<small>{u}</small></th><td>{format(before.nutrition?.[key])}</td><td>{format(after.nutrition?.[key])}</td></tr>)}</tbody></table>
  </div>;
}

export default function ChatConsumptionEdit({api, meal, item, onClose, onSaved}) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  // 보관한 미리보기: {ratio, version, requestId, before, after, unit}. 새 비율을 말하면 새로 만든다.
  const pending = useRef(null);
  const info = useRef(null);
  const listRef = useRef(null);
  const add = (role, content) => setMessages(list => [...list, {id: newRequestId(), role, ...content}]);

  // 진입 시 현재 비율로 미리보기를 불러와 version과 값 불일치 여부를 확인한다. 진입만으로는 쓰기가 없다.
  useEffect(() => {
    let active = true;
    api(`/meals/items/${item.id}/consumption/preview`, {consumption_ratio: item.consumption_ratio ?? 1}).then(data => {
      if (!active) return;
      info.current = data;
      add('bot', {text: `${data.meal_date} ${mealNames[data.meal_type] || data.meal_type} · ${data.food_name} 기록이에요 (현재 섭취 ${percent(data.before.consumption_ratio)}, ${format(data.before.nutrition.cal)} kcal). 얼마나 드셨는지 말씀해 주세요. 예: "절반만 먹었어", "4분의 1"`});
      if (!data.stored_matches_calculation) add('bot', {text: MISMATCH, tone: 'warn'});
    }).catch(error => active && add('bot', {text: error.message, tone: 'error'}));
    return () => { active = false; };
  }, [api, item.id]);
  useEffect(() => { listRef.current?.scrollTo?.({top: listRef.current.scrollHeight}); }, [messages]);

  async function makePreview(ratio) {
    const data = await api(`/meals/items/${item.id}/consumption/preview`, {consumption_ratio: ratio});
    info.current = data;
    pending.current = {ratio, version: data.version, requestId: newRequestId(), before: data.before, after: data.after, unit: data.unit};
    return data;
  }

  async function save() {
    const draft = pending.current;
    try {
      const result = await api(`/meals/items/${item.id}/consumption`, {consumption_ratio: draft.ratio, expected_version: draft.version, request_id: draft.requestId}, 'PUT');
      pending.current = null;
      add('bot', {text: `기록을 바꿨어요. ${item.food_name} 섭취 ${percent(result.after.consumption_ratio)} · ${format(result.after.nutrition.cal)} kcal`, card: {before: result.before, after: result.after, unit: draft.unit}, tone: 'done'});
      onSaved?.();
    } catch (error) {
      if (error.status === 409) {
        pending.current = null;
        add('bot', {text: '기록이 변경됐어요. 최신 내용을 확인해 주세요.', tone: 'warn'});
        onSaved?.();
      } else {
        // 같은 미리보기의 재시도에는 같은 request_id를 쓴다. 성공으로 표시하지 않는다.
        add('bot', {text: '아직 저장되지 않았어요. 다시 시도하려면 "저장해줘"라고 말씀해 주세요.', tone: 'error'});
      }
    }
  }

  async function send(event) {
    event.preventDefault();
    const sentence = text.trim();
    if (!sentence || sending) return;
    setSending(true); setText('');
    add('user', {text: sentence});
    try {
      const result = await api('/meals/consumption/interpret', {text: sentence, item_id: item.id, pending_question: pending.current ? 'save_confirm' : 'none'});
      if (result.intent === 'update_consumption' || result.intent === 'update_and_confirm') {
        const data = await makePreview(result.consumption_ratio);
        if (result.intent === 'update_and_confirm') { await save(); return; }
        add('bot', {text: `${item.food_name} ${percent(result.consumption_ratio)}(약 ${format(data.after.nutrition.cal)} kcal)로 바꿀까요? 맞으면 "응" 또는 "저장해줘"라고 말씀해 주세요.`, card: {before: data.before, after: data.after, unit: data.unit}});
        if (!data.stored_matches_calculation) add('bot', {text: MISMATCH, tone: 'warn'});
      } else if (result.intent === 'confirm_save') {
        if (pending.current) await save();
        else add('bot', {text: '어느 정도 드셨는지 먼저 말씀해 주세요.'});
      } else if (result.intent === 'affirm') {
        add('bot', {text: '어느 정도 드셨는지 먼저 말씀해 주세요. 예: "절반만 먹었어"'});
      } else if (result.intent === 'cancel') {
        pending.current = null;
        add('bot', {text: '수정을 멈췄어요. 기록은 그대로예요. 양을 다시 말씀해 주시면 이어서 바꿀게요.'});
      } else {
        add('bot', {text: clarifyText[result.clarification_reason] || clarifyText.unsupported_expression});
      }
    } catch (error) {
      add('bot', {text: error.message, tone: 'error'});
    } finally {
      setSending(false);
    }
  }

  return <div className="chat-edit-backdrop" role="presentation" onClick={event => event.target === event.currentTarget && onClose()}>
    <section className="chat-edit" role="dialog" aria-modal="true" aria-labelledby="chat-edit-title">
      <header><div><p className="eyebrow">CHAT EDIT</p><h2 id="chat-edit-title">챗으로 수정 · {item.food_name}</h2><p className="muted">{meal.meal_date} {mealNames[meal.meal_type] || meal.meal_type}</p></div><button type="button" className="text-button" onClick={onClose} aria-label="닫기">닫기 ✕</button></header>
      <ol className="chat-edit-log" ref={listRef} aria-live="polite">
        {messages.map(message => <li key={message.id} className={`chat-bubble chat-${message.role}${message.tone ? ` chat-${message.tone}` : ''}`}>
          <p>{message.text}</p>
          {message.card && <Compare {...message.card}/>}
        </li>)}
        {sending && <li className="chat-bubble chat-bot chat-typing" role="status">확인하고 있어요…</li>}
      </ol>
      <form className="chat-edit-input" onSubmit={send}>
        <label className="sr-only" htmlFor="chat-edit-text">섭취량 말하기</label>
        <input id="chat-edit-text" autoFocus maxLength={200} placeholder='예: 절반만 먹었어, 4분의 1, 저장해줘' value={text} onChange={event => setText(event.target.value)} disabled={sending}/>
        <button className="primary" disabled={sending || !text.trim()}>전송</button>
      </form>
      <p className="chat-edit-note">말로만 수정해요. "저장해줘" 또는 확인 질문 뒤의 "응"이 있어야 기록이 바뀌어요. 영양값은 서버가 CSV 기준으로 계산합니다.</p>
    </section>
  </div>;
}
