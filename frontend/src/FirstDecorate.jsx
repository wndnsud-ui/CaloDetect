// 첫날 꾸미기(지시서 v3 §11-3, 시안 2). 첫 식단 기록 직후 1회: 온보딩 내역, 스타터 6종 미리보기, 구매 후 착용.
import React, {useEffect, useState} from 'react';
import Jibang from './Jibang';
import RewardDialog from './RewardDialog';
import {fmt} from './RewardHomeCard';

export default function FirstDecorate({api, onClose, onDone}) {
  const [me, setMe] = useState(null), [items, setItems] = useState([]), [picked, setPicked] = useState(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  useEffect(() => {
    Promise.all([api('/rewards/me'), api('/rewards/items')]).then(([profile, catalog]) => {
      setMe(profile);
      const starters = catalog.items.filter(item => item.stage === 'A' && item.sellable);
      setItems(starters);
      setPicked(starters.find(item => item.id === 'starter_hat') || starters[0]);
    }).catch(e => setError(e.message));
  }, [api]);
  const preview = picked ? {...me?.equipment, [picked.slot]: picked.id} : me?.equipment;
  const remain = me && picked ? me.balance - picked.price : 0;
  async function buy() {
    if (!picked || busy) return;
    setBusy(true); setError('');
    try {
      if (!picked.owned) await api(`/rewards/items/${picked.id}/purchase`, {});
      await api('/rewards/equipment', {slot: picked.slot, item_id: picked.id}, 'PUT');
      onDone();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  const earned = me?.today_items?.filter(row => row.points > 0) || [];
  return <RewardDialog labelledBy="first-decorate-title" onClose={onClose} className="first-decorate">
    <p className="reward-eyebrow">DAY 1 · 첫 기록 완료</p>
    <h2 id="first-decorate-title">첫 포인트를 받았어요.<br/>지방이를 꾸며 볼까요?</h2>
    {earned.length > 0 && <div className="first-earned">{earned.map(row => <div key={row.key}><span>{row.label}</span><b>+{row.points}P</b></div>)}</div>}
    {me && <Jibang equipment={preview} level={me.level} figureWidth={132} bubble="나 어때?" className="first-preview"
      badge={`보유 ${fmt(me.balance)}P`}/>}
    <p className="reward-section-title">스타터 아이템</p>
    <div className="first-items" role="group" aria-label="스타터 아이템">{items.map(item => <button type="button" key={item.id} aria-pressed={picked?.id === item.id}
      className={picked?.id === item.id ? 'selected' : ''} onClick={() => setPicked(item)}><span>{item.name}</span><b>{item.owned ? '보유' : `${item.price}P`}</b></button>)}</div>
    {picked && me && <p className="reward-small center">{picked.owned ? '이미 가진 아이템이라 바로 착용해요.' : remain < 0 ? `${fmt(-remain)}P가 더 필요해요.` : remain >= 10 ? `구매 후 ${fmt(remain)}P가 남아요. 하나 더 살 수 있어요.` : `구매 후 ${fmt(remain)}P가 남아요. 내일 기록하면 더 모여요.`}</p>}
    {picked && me && !picked.owned && me.deco_only > 0 && <p className="reward-small center">가입 보너스 {fmt(Math.min(picked.price, me.deco_only))}P가 먼저 사용돼요.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <button type="button" className="primary" onClick={buy} disabled={!picked || busy || (!picked.owned && remain < 0)}>{picked ? (picked.owned ? `${picked.name} 착용하기` : `${picked.price}P로 ${picked.name} 착용하기`) : '불러오는 중'}</button>
    <button type="button" className="text-button" onClick={onClose}>나중에 할게요</button>
  </RewardDialog>;
}
