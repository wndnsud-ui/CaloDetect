// 칼로티 코치(Calo-T Coach) 플로팅 버튼과 채팅 시트. 업무지시서 v1.2 UI 절.
// 앱 최상위(shell)에 한 번만 두고 position: fixed로 고정해, 어느 화면에서 눌러도 같은 대화가 열린다.
// 시트는 처음 열 때 만들고, 닫으면 숨기기만 해서 진행 중인 사진 분석·입력 내용이 이어진다(대화 자체는 서버가 복원).
import React, { useEffect, useRef, useState } from 'react';
import ChatRecord, { COACH_FACE } from './ChatRecord';
import { ConsumptionEditChat } from './ChatConsumptionEdit';
import './coach-chat.css';

const HINT_KEY = 'calodetect.coachHintSeen';
const mealNames = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};

function readHintSeen() { try { return localStorage.getItem(HINT_KEY) === '1'; } catch { return true; } }
function saveHintSeen() { try { localStorage.setItem(HINT_KEY, '1'); } catch {} }

// 오른쪽 아래 지방이 버튼. 첫 진입 때만 말풍선 힌트를 몇 초 띄운다.
export function CoachFab({hidden, onOpen}) {
  const [hint, setHint] = useState(false);
  useEffect(() => {
    if (readHintSeen()) return undefined;
    const show = setTimeout(() => { setHint(true); saveHintSeen(); }, 800);
    const hide = setTimeout(() => setHint(false), 7800);
    return () => { clearTimeout(show); clearTimeout(hide); };
  }, []);
  if (hidden) return null;
  return <div className="coach-fab-wrap">
    {hint && <p className="coach-fab-hint" aria-hidden="true">뭐 먹을지 고민돼요?<br/>저한테 물어봐요!</p>}
    <button type="button" className="coach-fab" onClick={() => { setHint(false); saveHintSeen(); onOpen(); }} aria-label="칼로티 코치 열기">
      <img src="/jibang/front.png" alt=""/>
    </button>
  </div>;
}

// 채팅 시트. 비로그인이면 로그인 안내만 보여 주고 대화(서버 호출)를 만들지 않는다.
// editTarget({meal, item})이 있으면 식단 기록의 '챗으로 수정' 대화를 같은 시트 안에서 보여 준다.
export function CoachSheet({open, user, api, editTarget, onClose, onLogin, onSaved, onNavigate, onBackToChat}) {
  const [mounted, setMounted] = useState(open);
  const [drag, setDrag] = useState(0);
  const start = useRef(null), closeButton = useRef(null);
  useEffect(() => { if (open) setMounted(true); }, [open]);
  useEffect(() => {
    if (!open) return undefined;
    closeButton.current?.focus({preventScroll: true});
    const key = event => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', key);
    document.body.classList.add('coach-sheet-open');
    return () => { document.removeEventListener('keydown', key); document.body.classList.remove('coach-sheet-open'); };
  }, [open, onClose]);
  if (!mounted) return null;

  // 손잡이·머리글을 아래로 끌면 시트가 따라 내려오고, 충분히 끌면 닫힌다.
  const down = event => { if (event.button !== 0 || event.target.closest('button')) return; start.current = event.clientY; event.currentTarget.setPointerCapture?.(event.pointerId); };
  const move = event => { if (start.current != null) setDrag(Math.max(0, event.clientY - start.current)); };
  const up = () => { if (start.current == null) return; start.current = null; if (drag > 110) onClose(); setDrag(0); };

  const status = !user ? '로그인하면 함께 식사를 고민할 수 있어요.'
    : editTarget ? `${editTarget.meal.meal_date} ${mealNames[editTarget.meal.meal_type] || editTarget.meal.meal_type} · ${editTarget.item.food_name} 섭취량 수정`
    : '오늘 식사도 같이 고민해볼까요?';

  return <div className="coach-sheet-layer" hidden={!open}>
    <div className="coach-sheet-backdrop" onClick={onClose} aria-hidden="true"/>
    <section className="coach-sheet" role="dialog" aria-modal="true" aria-labelledby="coach-sheet-title"
      style={drag ? {transform: `translateY(${drag}px)`, transition: 'none'} : undefined}>
      <div className="coach-sheet-grab" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
        <span className="coach-sheet-handle" aria-hidden="true"/>
        <header className="coach-sheet-head">
          <img src={COACH_FACE} alt=""/>
          <div>
            <p className="coach-sheet-eyebrow">CALO-T COACH</p>
            <h2 id="coach-sheet-title">칼로티 코치 <span>· 지방이</span></h2>
            <p className="coach-sheet-status">{status}</p>
          </div>
          <button type="button" ref={closeButton} className="coach-sheet-close" onClick={onClose} aria-label="채팅 닫기">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
          </button>
        </header>
      </div>
      {!user ? <div className="coach-login">
        <img src="/jibang/front.png" alt=""/>
        <strong>로그인하면 지방이와 대화할 수 있어요</strong>
        <p>식사 기록을 바탕으로 메뉴 추천과 영양 분석을 도와드려요.</p>
        <button type="button" className="primary" onClick={onLogin}>로그인 / 회원가입</button>
      </div> : <>
        {editTarget && <div className="coach-edit">
          <button type="button" className="coach-edit-back" onClick={onBackToChat}>‹ 대화로 돌아가기</button>
          <ConsumptionEditChat key={editTarget.item.id} api={api} item={editTarget.item} onSaved={onSaved}/>
        </div>}
        <div className="coach-chat" hidden={!!editTarget}>
          <ChatRecord key={user.id} api={api} onSaved={onSaved} onNavigate={target => { onClose(); onNavigate(target); }}/>
        </div>
      </>}
    </section>
  </div>;
}
