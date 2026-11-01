// 홈 '시작 가이드': 가입 → 닉네임 → 목표 칼로리 → 첫 식단 기록. 완료 여부는 /rewards/me의 onboarding.steps(서버 기록).
// 다음 단계 하나만 버튼을 강조한다. '나중에 하기'와 완료 축하 확인은 이 브라우저에만 기억한다(서버 저장 없음).
import React, {useEffect, useState} from 'react';
import {JibangFigure} from './Jibang';
import './start-guide.css';

const STEPS = {
  signup: {title: '가입 완료', action: null},
  nickname: {title: '닉네임 정하기', action: '정하러 가기', hint: '랭킹과 커뮤니티에 보일 이름을 정해 볼까요?'},
  goal: {title: '목표 칼로리 정하기', action: '정하러 가기', hint: '목표만 정하면 딱 맞는 메뉴를 추천해 줄게요!'},
  first_meal: {title: '첫 식단 기록하기', action: '기록하러 가기', hint: '사진 한 장이면 첫 기록 끝! 같이 시작해요.'},
};
const storageKey = userId => `calodetect:start-guide:${userId}`;
const readState = userId => { try { return localStorage.getItem(storageKey(userId)) || ''; } catch { return ''; } };
const writeState = (userId, value) => { try { localStorage.setItem(storageKey(userId), value); } catch { /* 저장 불가 브라우저는 이번 화면에서만 숨김 */ } };

export default function StartGuide({userId, onboarding, level, equipment, onStep}) {
  const [state, setState] = useState(() => readState(userId));
  const steps = (onboarding?.steps || []).filter(step => STEPS[step.key]);
  const doneCount = steps.filter(step => step.done).length;
  const next = steps.find(step => !step.done);
  // 진행 중인 가이드를 본 적이 있다고 기록해 두면, 모두 마쳤을 때 축하 카드를 한 번 보여 줄 수 있다.
  useEffect(() => { if (next && !state) { writeState(userId, 'started'); setState('started'); } }, [next, state, userId]);
  if (!steps.length || state === 'dismissed' || state === 'done') return null;
  function remember(value) { writeState(userId, value); setState(value); }

  // 모두 마쳤을 때: 가이드를 진행 중에 본 회원에게만 축하를 한 번 보여 준다(이미 다 한 기존 회원에게는 안 보임).
  if (!next) {
    if (state !== 'started') return null;
    return <section className="start-guide start-guide-done" aria-label="시작 가이드 완료">
      <div className="start-guide-jibang" aria-hidden="true"><JibangFigure level={level || 1} equipment={equipment || {}} width={86}/></div>
      <div><strong>준비 완료! 🎉</strong><p>이제 매 끼니 식단 기록으로 함께해요.</p></div>
      <button type="button" className="primary" onClick={() => { remember('done'); onStep('first_meal'); }}>식단 기록하기</button>
      <button type="button" className="start-guide-close" aria-label="시작 가이드 닫기" onClick={() => remember('done')}>×</button>
    </section>;
  }
  return <section className="start-guide" aria-label="CaloDetect 시작 가이드">
    <header>
      <div><p className="eyebrow">시작 가이드</p><h2>CaloDetect 시작하기</h2></div>
      <span className="start-guide-count">{doneCount}/{steps.length} 완료</span>
      <button type="button" className="start-guide-later" onClick={() => remember('dismissed')}>나중에 하기</button>
    </header>
    <div className="start-guide-bar" role="progressbar" aria-valuemin={0} aria-valuemax={steps.length} aria-valuenow={doneCount}><span style={{width: `${doneCount / steps.length * 100}%`}}/></div>
    <ol>{steps.map((step, index) => {
      const meta = STEPS[step.key];
      const current = step === next;
      return <li key={step.key} className={step.done ? 'is-done' : current ? 'is-current' : undefined}>
        <span className="start-guide-check" aria-hidden="true">{step.done ? '✓' : index + 1}</span>
        <b>{meta.title}</b>
        {step.points > 0 && <em>{step.done ? `+${step.points}P 받음` : `+${step.points}P`}</em>}
        {!step.done && meta.action && <button type="button" className={current ? 'primary' : 'outline'} onClick={() => onStep(step.key)}>{meta.action}</button>}
      </li>;
    })}</ol>
    <div className="start-guide-tip">
      <div className="start-guide-jibang" aria-hidden="true"><JibangFigure level={level || 1} equipment={equipment || {}} width={70}/></div>
      <p>{STEPS[next.key].hint}</p>
    </div>
  </section>;
}
