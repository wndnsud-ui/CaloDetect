// 레벨업 축하 창(지시서 v3 §11-4, 시안 4·14). 미확인 레벨업 이벤트가 있으면 다음 화면 진입 때 1번.
// 몸은 모든 레벨에서 같은 정면 이미지이고 해금된 레벨 배경으로만 차이를 보여 준다(§11-0).
import React, {useState} from 'react';
import Jibang, {CHARACTER_NAME} from './Jibang';
import RewardDialog from './RewardDialog';
import {fmt} from './RewardHomeCard';

export default function LevelUpDialog({api, event, equipment, onClose, onNavigate}) {
  const [busy, setBusy] = useState(false);
  const background = event.items.find(item => item.slot === 'background');
  async function seen() { try { await api(`/rewards/levelups/${event.id}/seen`, {}); } catch { /* 다음 진입 때 다시 보여 준다 */ } }
  async function close() { await seen(); onClose(); }
  async function apply() {
    setBusy(true);
    try { if (background) await api('/rewards/equipment', {slot: 'background', item_id: background.id}, 'PUT'); } finally { await seen(); setBusy(false); onClose(); onNavigate('리워드', 'room'); }
  }
  return <RewardDialog labelledBy="levelup-title" onClose={close} className="levelup">
    <p className="reward-eyebrow">LEVEL UP</p>
    <h2 id="levelup-title">LV.{event.level} {event.level_name} {CHARACTER_NAME}가 되었어요!</h2>
    <Jibang equipment={equipment} background={background?.id} level={event.level} figureWidth={140} motion="hop" bubble="같이 자랐네!"/>
    <ul className="levelup-unlocks">
      {event.items.map(item => <li key={item.id}>{item.slot === 'background' ? '새 배경' : item.slot === 'title' ? '칭호' : '전용 아이템'} · <b>{item.name}</b></li>)}
      {event.points > 0 && <li>레벨업 보상 · <b>+{fmt(event.points)}P</b></li>}
    </ul>
    {event.next && <p className="reward-small center">다음 LV.{event.next.level} {event.next.level_name}: {fmt(event.next.xp)} XP{event.next.points ? ` · +${fmt(event.next.points)}P` : ''}</p>}
    {background && <button type="button" className="primary" onClick={apply} disabled={busy}>배경 바로 적용하기</button>}
    <button type="button" className="text-button" onClick={close}>나중에</button>
  </RewardDialog>;
}
