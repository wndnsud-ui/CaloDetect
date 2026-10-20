// 랭킹 "닉네임 바꾸기" 창(지시서 v3 §11-11 ④, Stage B). 같은 NicknameField, via=ranking.
import React, {useState} from 'react';
import NicknameField from './NicknameField';
import RewardDialog from './RewardDialog';

export default function NicknameDialog({api, current, nextChangeDate, onClose, onSaved}) {
  const [value, setValue] = useState(current || ''), [valid, setValid] = useState(false), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  async function save(event) {
    event.preventDefault();
    setBusy(true); setError('');
    try { await api('/rewards/nickname', {nickname: value.trim(), via: 'ranking'}, 'PUT'); onSaved(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <RewardDialog labelledBy="nickname-dialog-title" onClose={onClose}>
    <form className="nickname-dialog" onSubmit={save}>
      <h2 id="nickname-dialog-title">닉네임 바꾸기</h2>
      {nextChangeDate ? <p className="muted">{nextChangeDate.slice(5).replace('-', '월 ')}일부터 바꿀 수 있어요.</p>
        : <p className="muted">바꾸면 30일 동안 다시 바꿀 수 없어요.</p>}
      <NicknameField api={api} value={value} onChange={next => { setValue(next); setError(''); }} onValidity={setValid} serverError={error} autoFocus/>
      <div className="reward-actions"><button type="button" className="outline" onClick={onClose}>취소</button><button className="primary" disabled={!valid || busy || !!nextChangeDate}>저장</button></div>
    </form>
  </RewardDialog>;
}
