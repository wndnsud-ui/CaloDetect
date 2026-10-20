// 개발용 테스트 페이지: 로컬 테스트 계정에 리워드 더미를 버튼 한 번으로 만들고 결과를 바로 확인한다.
// 서버가 로컬 개발 설정일 때만 /dev/demo 경로가 있고, 메뉴도 그때만 보인다(운영 화면에는 없음).
import React, {useState} from 'react';

const FIELDS = [
  ['points', '포인트(P)', 0, 5000, '리워드 몰에서 쓸 포인트'],
  ['xp', 'XP', 0, 10000, '300 → LV.2, 1,000 → LV.3, 2,500 → LV.4, 5,000 → LV.5'],
  ['streak', '연속 기록(일)', 0, 60, '어제까지 이어진 기록 일수. 오늘은 직접 기록해 확인'],
  ['protectors', '보호권(장)', 0, 10, '어제를 놓쳤을 때 쓰는 연속 기록 보호권'],
];
const PRESETS = [['처음 시작(LV.1)', {points: 30, xp: 0, streak: 0, protectors: 0}], ['LV.2 직전', {points: 60, xp: 290, streak: 4, protectors: 0}],
  ['LV.3', {points: 200, xp: 1200, streak: 5, protectors: 1}], ['LV.5 만렙', {points: 800, xp: 5200, streak: 13, protectors: 2}]];

export default function DevDemo({api, status, onChanged, onNavigate}) {
  const [form, setForm] = useState({points: 200, xp: 1200, streak: 5, protectors: 1}), [reset, setReset] = useState(true);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [result, setResult] = useState(null);
  async function run(path, body) {
    setBusy(true); setError(''); setResult(null);
    try { setResult(await api(path, body)); await onChanged(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  if (!status?.test_account) return <section className="panel dev-demo"><p className="eyebrow">DEV TEST</p><h1>테스트 페이지</h1>
    <p className="notice">테스트 계정({status?.account_email || 'test@calodetect.local'})으로 로그인하면 더미를 만들 수 있어요.</p></section>;
  return <div className="dev-demo">
    <p className="eyebrow">DEV TEST · 로컬 개발 전용</p><h1>리워드 더미 실행</h1>
    <p className="muted">테스트 계정에만 적용돼요. 같은 값으로 다시 눌러도 같은 날에는 중복으로 쌓이지 않아요.</p>
    <section className="panel">
      <div className="reward-chips" role="group" aria-label="빠른 설정">{PRESETS.map(([label, values]) => <button key={label} type="button" onClick={() => setForm(values)} disabled={busy}>{label}</button>)}</div>
      <div className="dev-demo-fields">{FIELDS.map(([key, label, min, max, help]) => <label key={key}>{label}
        <input type="number" min={min} max={max} value={form[key]} onChange={e => setForm(f => ({...f, [key]: Number(e.target.value)}))}/><small>{help}</small></label>)}</div>
      <label className="check"><input type="checkbox" checked={reset} onChange={e => setReset(e.target.checked)}/>기존 리워드 기록을 지우고 새로 넣기(식단·닉네임은 유지)</label>
      <div className="reward-actions">
        <button type="button" className="outline" disabled={busy} onClick={() => run('/dev/demo/rewards/reset', {})}>리워드 초기화</button>
        <button type="button" className="primary" disabled={busy} onClick={() => run('/dev/demo/rewards', {...form, reset})}>{busy ? '만드는 중…' : '더미 실행'}</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
    {result && <section className="panel dev-demo-result" role="status">
      <h2>만들었어요</h2>
      <dl><div><dt>포인트</dt><dd>{result.balance.toLocaleString()}P</dd></div><div><dt>레벨</dt><dd>LV.{result.level}</dd></div>
        <div><dt>XP</dt><dd>{result.xp_total.toLocaleString()}</dd></div><div><dt>연속 기록</dt><dd>{result.streak_days}일</dd></div><div><dt>보호권</dt><dd>{result.protectors}장</dd></div></dl>
      {result.new_levels.length > 0 && <p className="muted">LV.{result.new_levels.join(', LV.')} 달성 — 다음 화면에서 축하 창이 떠요.</p>}
      <div className="reward-actions">
        <button type="button" className="outline" onClick={() => onNavigate('홈')}>홈 카드 보기</button>
        <button type="button" className="outline" onClick={() => onNavigate('리워드', 'room')}>지방이 방</button>
        <button type="button" className="outline" onClick={() => onNavigate('리워드', 'growth')}>성장 · 랭킹</button>
        <button type="button" className="primary" onClick={() => onNavigate('리워드', 'mall')}>리워드 몰</button>
      </div>
    </section>}
  </div>;
}
