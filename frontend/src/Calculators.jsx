// 비회원도 사용할 수 있는 음식 영양·목표 칼로리 미리보기 화면.
// 입력 숫자를 변환해 Backend 계산 API에 전달하며 프로필 저장은 전달된 콜백이 있을 때만 수행한다.
import React, { useEffect, useState } from 'react';
import { readApiResponse } from './apiResponse';
import './style.css';

// 요청 본문 유무에 따라 조회/변경 호출을 구성하고 공통 응답 파서로 결과를 읽는다.
async function api(path, body) {
  const response = await fetch(`/api${path}`, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
  });
  const data = await readApiResponse(response);
  return data;
}

const sections = ['홈', '음식 추가', '목표 설정', '식사 추천', '히스토리'];
// 비회원도 사용할 수 있는 음식 영양·목표 칼로리 미리보기 화면.
export default function Calculators({ initialTab = '음식 추가', onSaveProfile, profile }) {
  const [tab, setTab] = useState(initialTab);
  const [foods, setFoods] = useState([]);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(0);
  const [portion, setPortion] = useState(1);
  const [nutrition, setNutrition] = useState(null);
  const [goal, setGoal] = useState(null);
  const [busy, setBusy] = useState(false);
  // 의존값 변경/마운트에 맞춰 외부 데이터 또는 브라우저 자원을 동기화한다. 반환하는 정리 함수는 이전 작업/자원을 해제한다.
  useEffect(() => {
    let active = true;
    Promise.all([api('/foods'), api('/system/status')]).then(([catalog, system]) => {
      if (active) {setFoods(catalog.items); setStatus(system);}
    }).catch(e => {if (active) setError(`서버 연결 실패: ${e.message} FastAPI 실행 상태를 확인하세요.`);});
    return () => {active = false;};
  }, []);
  // 선택 음식과 숫자로 변환한 기준량 배율을 Backend 계산 API로 보낸다.
  async function calculate(e) {
    e.preventDefault(); setBusy(true); setError(''); setNutrition(null);
    try {setNutrition(await api('/nutrition/calculate', {class_id: selected, serving_multiplier: Number(portion)}));}
    catch (e) {setError(e.message);} finally {setBusy(false);}
  }
  // 신체 정보 숫자를 변환해 권장 범위를 조회하고 저장 버튼일 때만 전달된 저장 콜백을 실행한다.
  async function preview(e) {
    e.preventDefault(); setBusy(true); setError(''); setGoal(null);
    const data = Object.fromEntries(new FormData(e.currentTarget));
    ['height', 'weight', 'age', 'target_calories'].forEach(key => {data[key] = Number(data[key]);});
    try {
      setGoal(await api('/profiles/calorie-preview', data));
      if (e.nativeEvent.submitter?.value === 'save' && onSaveProfile) await onSaveProfile(data);
    }
    catch (e) {setError(e.message);} finally {setBusy(false);}
  }
  return <div className="calculator-content">
    <aside><a className="brand" href="#" onClick={e => {e.preventDefault();setTab('홈');}}><span className="mark">C</span>CaloDetect</a><p className="aside-caption">매일의 식사, 더 선명하게.</p>
      <nav aria-label="주 메뉴">{sections.map((name, i) => <button key={name} aria-current={tab === name ? 'page' : undefined} className={tab === name ? 'active' : ''} onClick={() => {setTab(name);setError('');}}><span>0{i+1}</span>{name}<b>↗</b></button>)}</nav>
      <div className="aside-bottom"><span className="dot"/>{status ? '서버 연결됨' : '서버 연결 확인 중'}<p>칼로디텍트 · 팀 개발 환경</p></div>
    </aside>
    <main><header><span>나의 식사와 영양 기록</span><span className="badge">개발 미리보기</span></header>
      {error && <div className="error" role="alert">{error}</div>}
      {tab === '홈' && <>
        <section className="hero"><div><p className="eyebrow">YOUR EVERYDAY NUTRITION</p><h1>한 끼의 기록이<br/>다음 선택의 기준이 되도록.</h1><p>음식을 확인하고 섭취량에 따른 영양 구성을 살펴보세요.<br/>당신의 일상에 맞는 식단 기록을 준비하고 있습니다.</p><button className="primary" onClick={() => setTab('음식 추가')}>음식 확인하기 <span>↗</span></button></div><div className="plate" aria-hidden="true"><div className="leaf l1"/><div className="leaf l2"/><div className="leaf l3"/><div className="tomato t1"/><div className="tomato t2"/><div className="grain"/><span>ONE MEAL<br/>AT A TIME</span></div></section>
        <div className="section-heading"><h2>오늘을 위한 작은 시작</h2><span>Asia/Seoul 기준</span></div>
        <div className="cards"><article><span className="card-number">01 / FOOD</span><h3>{status ? `${status.food_count}종 음식` : '음식 목록'}</h3><p>기존 모델과 연결된 음식·영양 데이터를 조회합니다.</p><button onClick={() => setTab('음식 추가')}>영양 구성 확인 →</button></article><article><span className="card-number">02 / GOAL</span><h3>나에게 맞는 목표</h3><p>신체 정보와 활동 수준으로 목표 칼로리 범위를 계산합니다.</p><button onClick={() => setTab('목표 설정')}>목표 미리 계산 →</button></article><article className="soft"><span className="card-number">03 / NEXT</span><h3>기록에서 추천까지</h3><p>회원·기록 저장·추천 기능은 팀 정책 확정 후 연결됩니다.</p><span className="badge">연결 준비 중</span></article></div>
        <div className="notice"><b>현재 확인할 수 있는 기능</b><p>음식 목록, 섭취량별 영양 계산, 목표 칼로리 계산. 회원가입·사진 업로드·식단 저장·추천은 아직 사용할 수 없습니다.</p></div>
      </>}
      {tab === '음식 추가' && <><p className="eyebrow">FOOD & NUTRITION</p><h1>음식의 영양을 확인하세요.</h1><p className="intro">음식명과 기준 섭취량을 확인한 후 수량을 조절해보세요.</p><div className="two-col"><form className="panel" onSubmit={calculate}><h2>음식 직접 선택</h2><label>음식<select value={selected} onChange={e => {setSelected(Number(e.target.value));setNutrition(null);}} disabled={!foods.length}>{foods.map(f => <option key={f.class_id} value={f.class_id}>{f.food_name} · {f.category}</option>)}</select></label><label>기준량 배율 · {foods.find(f => f.class_id === selected)?.unit || '기준량 확인 중'}<input type="number" min="0.01" max="100" step="0.01" required value={portion} onChange={e => {setPortion(e.target.value);setNutrition(null);}}/></label><button className="primary" disabled={busy || !foods.length}>영양 계산하기</button><p className="muted">사진 분석과 식단 저장은 로그인 후 사용할 수 있습니다.</p></form><section className="panel"><h2>영양 구성</h2>{nutrition ? <><h3>{nutrition.food_name}</h3><div className="nutrition-grid">{Object.entries(nutrition.nutrition).map(([key, value]) => <div key={key}><span>{{cal:'칼로리', carbs:'탄수화물',protein:'단백질',fat:'지방',sugar:'당류',sodium:'나트륨'}[key]}</span><strong>{value}<small>{key === 'cal' ? ' kcal' : key === 'sodium' ? ' mg' : ' g'}</small></strong></div>)}</div></> : <p className="empty">음식과 섭취량을 선택해 계산해주세요.</p>}</section></div></>}
      {tab === '목표 설정' && <><p className="eyebrow">YOUR CALORIE RANGE</p><h1>하루의 목표를 살펴보세요.</h1><p className="intro">성인 대상 팀 회의 기준의 계산 미리보기입니다. 로그인 후 프로필에 저장할 수 있습니다.</p><div className="two-col"><form className="panel" onSubmit={preview}><h2>신체 정보</h2><div className="form-grid">{[['height','키 (cm)',175],['weight','체중 (kg)',70],['age','나이',30],['target_calories','목표 칼로리 (kcal)',2000]].map(([key,label,value]) => <label key={key}>{label}<input name={key} type="number" min="1" step={key === 'age' ? '1' : '0.1'} required defaultValue={profile?.[key] ?? value}/></label>)}</div><label>성별<select name="sex"><option value="male">남성</option><option value="female">여성</option></select></label><label>활동 수준<select name="activity_level"><option value="sedentary">좌식 생활</option><option value="light">가벼운 활동</option><option value="moderate">보통 활동</option><option value="active">활발한 활동</option></select></label><label>목표<select name="goal_type"><option value="maintain">유지</option><option value="weight_loss">감량</option><option value="muscle_gain">증가</option></select></label><button className="primary" disabled={busy}>목표 범위 계산</button>{onSaveProfile && <button className="outline spaced" name="action" value="save" disabled={busy}>프로필 저장</button>}</form><section className="panel"><h2>계산 결과</h2>{goal ? <><dl>{[['bmr','기초대사량'],['tdee','일일 에너지 소비량'],['minimum_calories','최소 허용값'],['recommended_calorie_min','권장 하한'],['recommended_calorie_max','권장 상한']].map(([key,label]) => <div key={key}><dt>{label}</dt><dd>{goal[key]} kcal</dd></div>)}</dl>{goal.outside_recommended_range && <p className="notice">입력 목표가 권장 범위 밖입니다.</p>}<p className="muted">{goal.notice}</p></> : <p className="empty">정보를 입력하면 권장 범위를 확인할 수 있어요.</p>}</section></div></>}
      {['식사 추천','히스토리'].includes(tab) && <section className="panel pending"><p className="eyebrow">COMING NEXT</p><h1>{tab === '식사 추천' ? '기록에 맞춘 다음 식사.' : '한 끼씩 쌓이는 나의 기록.'}</h1><p>{tab === '식사 추천' ? '추천 데이터 출처와 영양 목표 기준 확정 후 실제 기록을 바탕으로 연결합니다.' : '회원 인증과 PostgreSQL 식단 저장이 연결되면 날짜별 기록을 확인할 수 있습니다.'}</p><span className="badge">아직 연결되지 않은 기능</span><button onClick={() => setTab('음식 추가')}>음식 영양 확인하기 →</button></section>}
      <footer>CaloDetect <span>식사 기록과 영양 정보 확인을 위한 서비스 · 의료 진단을 제공하지 않습니다.</span></footer>
    </main>
  </div>;
}
