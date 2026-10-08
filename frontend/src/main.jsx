// 회원 웹앱의 상태와 화면 전환을 조정하는 상위 컴포넌트.
// 세션 복원 → 음식/프로필/식단 조회 → 사진 분석/보정 → 서버 영양 미리보기 → 식단 저장 흐름을 연결한다.
// API 호출은 HttpOnly 쿠키와 CSRF 헤더를 사용하고 영양 계산·권한 판단은 Backend 결과를 따른다.
import React, { useEffect, useState } from 'react';
import { Brand, Bowl, MenuIcon } from './Visuals';
import Calculators from './Calculators';
import AccountInfo from './AccountInfo';
import Dashboard from './DailyHome';
import PhotoInput from './PhotoInput';
import SocialLogin from './SocialLogin';
import EmailAuthForm from './EmailAuthForm';
import {PasswordForm, takeResetToken} from './PasswordTools';
import ScanResult from './ScanResult';
import NutritionSummary from './NutritionSummary';
import GoalSetup from './GoalSetup';
import MealAnalytics from './MealAnalytics';
import MealHistory from './MealHistory';
import { readApiResponse } from './apiResponse';
import './style.css';
import './reference.css';

// HttpOnly 쿠키 원문 대신 서버가 준 CSRF 토큰만 모듈 메모리에 보관한다. 로그아웃/비밀번호 변경 시 비운다.
let csrf = '';
// 요청 본문 유무에 따라 조회/변경 호출을 구성하고 공통 응답 파서로 결과를 읽는다.
async function api(path, body, method = 'POST') {
  // 사진 업로드는 브라우저가 multipart boundary를 붙이도록 Content-Type을 직접 지정하지 않는다.
  const form = body instanceof FormData;
  // credentials: include로 세션 쿠키를 보내고 JSON 본문과 CSRF 헤더는 필요한 경우에만 추가한다.
  const response = await fetch(`/api${path}`, {credentials: 'include', method: body === undefined ? 'GET' : method,
    headers: {...(!form && body !== undefined ? {'Content-Type': 'application/json'} : {}), ...(csrf ? {'X-CSRF-Token': csrf} : {})},
    body: body === undefined ? undefined : form ? body : JSON.stringify(body)});
  const data = await readApiResponse(response);
  if (data.csrf_token) csrf = data.csrf_token;
  return data;
}
const meals = {breakfast:'아침',lunch:'점심',dinner:'저녁',snack:'간식'};
// 공통 영양 요약 컴포넌트에 서버 계산 결과를 전달한다.
function Nutrition({data}) {return <NutritionSummary data={data}/>}

// 회원 세션·식단·프로필·사진 분석 상태를 관리하고 선택된 서비스 화면에 전달한다.
export default function App({initialPage='홈',onHomepage,onPageChange}) {
  const [resetToken, setResetToken] = useState(takeResetToken);
  const [authLoading,setAuthLoading] = useState(true);
  const [page,setPage] = useState(initialPage==='회원가입'?'로그인':initialPage), [user,setUser] = useState(null), [policy,setPolicy] = useState(null);
  const [foods,setFoods] = useState([]), [today,setToday] = useState(null), [history,setHistory] = useState([]);
  const [profile,setProfile] = useState(null), [recommendation,setRecommendation] = useState(null);
  const [error,setError] = useState(''), [message,setMessage] = useState(''), [busy,setBusy] = useState(false);
  const [signup,setSignup] = useState(initialPage==='회원가입'), [file,setFile] = useState(null), [image,setImage] = useState(null);
  const [scanStatus,setScanStatus] = useState('idle'), [scanError,setScanError] = useState('');
  const [rows,setRows] = useState([]), [mealType,setMealType] = useState('lunch'), [consent,setConsent] = useState(false);
  const [exclude,setExclude] = useState([]), [goal,setGoal] = useState(null);
  const [totals,setTotals] = useState(null), [previewError,setPreviewError] = useState(''), [mealError,setMealError] = useState('');
  // 빈 식단·100개 초과·잘못된 수량/음식 ID는 UI에서 저장을 막는다. 서버도 요청을 다시 검증한다.
  const validMeal = rows.length > 0 && rows.length <= 100 && rows.every(row => Number.isFinite(Number(row.serving_multiplier)) && Number(row.serving_multiplier) > 0 && Number(row.serving_multiplier) <= 100 && foods.some(food => food.class_id === row.class_id));
  // 음식 행/수량 변경 시 서버 영양 미리보기를 갱신한다. active는 이전 요청의 늦은 결과가 새 합계를 덮지 못하게 한다.
  useEffect(()=>{
    let active=true;setTotals(null);setPreviewError('');setMealError('');
    if(rows.length && rows.every(r=>Number(r.serving_multiplier)>0 && Number(r.serving_multiplier)<=100)) {
      api('/nutrition/preview',{items:rows.map(r=>({class_id:r.class_id,serving_multiplier:Number(r.serving_multiplier)}))})
        .then(d=>{if(active)setTotals(d.totals);}).catch(e=>{if(active)setPreviewError(e.message);});
    }
    return()=>{active=false;};
  },[rows]);
  // 화면 이름이 바뀌면 상위 진입점에 전달해 현재 탭의 마지막 화면을 기억한다. 이 effect는 자원 정리 함수가 필요하지 않다.
  useEffect(()=>{onPageChange?.(page)},[page,onPageChange]);
  // 최초 진입 시 음식/가입 정책을 병렬 조회하고 HttpOnly 쿠키로 로그인 상태를 복원한다.
  useEffect(() => {
    let active=true;
    Promise.all([api('/foods'),api('/auth/policy')]).then(([f,p]) => {if(active){setFoods(f.items);setPolicy(p)}}).catch(e => {if(active)setError(e.message)});
    // 401은 정상 비회원으로 처리한다. 로그인 복원 후 계정 조회만 실패한 경우 회원 상태를 유지하고 오류를 안내한다.
    async function restoreSession(){
      try {
        const d=await api('/users/me');if(!active)return;
        setUser(d.user);if(!resetToken)setPage(current=>current==='로그인'?'홈':current);
        try {await loadAccount();} catch(e){if(active)setError(e.message);}
      } catch(e){if(active&&e.status!==401)setError(e.message);}
      finally {if(active)setAuthLoading(false);}
    }
    restoreSession();return()=>{active=false;};
  }, []);
  // 현재 회원의 프로필·오늘 영양·히스토리·동의를 다시 조회한다.
  async function loadAccount() {const [t,h,p,c] = await Promise.all([api('/analytics/today'),api('/meals/history'),api('/users/me/profile'),api('/users/me/consent')]);setToday(t);setHistory(h.items);setProfile(p.profile);setConsent(c.model_improvement_consent);}
  // 비동기 작업의 진행/오류 상태를 공통 처리해 중복 제출과 사용자 안내를 관리한다.
  async function run(work) {setBusy(true);setError('');setMessage('');try {await work()} catch(e){setError(e.message)} finally {setBusy(false)}}
  // 상위 화면 선택을 바꾸고 페이지별 메시지/오류 상태를 정리한다.
  function navigate(p){setPage(p);setError('');setMessage('')}
  // 폼 값을 가입/로그인 요청 형태로 변환하고 성공 후 세션과 회원 데이터를 복원한다.
  async function authenticate(e){e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));if(signup){data.age=Number(data.age);data.service_consent=data.service_consent==='on';data.consent_text=policy.service_consent_text}
    await run(async()=>{const result=await api(signup ? '/auth/signup':'/auth/login',data);setUser(result.user);setPage(file?'음식 추가':'홈');await loadAccount()})}
  // 선택 사진을 FormData로 분석 요청하고 탐지 ID·클래스·신뢰도를 수정 가능한 음식 행으로 만든다.
  async function scan(e){e.preventDefault();if(!file)return;setScanStatus('working');setScanError('');await run(async()=>{try{const form=new FormData();form.append('file',file);const result=await api('/meals/detect',form);setImage(result);setScanStatus('success');setRows(result.detections.map(d=>({key:d.id,class_id:d.class_id,serving_multiplier:1,detection_id:d.id,confidence:d.confidence,bbox:d.bbox})));setMessage(result.detections.length ? `사진 분석을 완료했습니다. 인식된 음식 ${result.detections.length}개의 이름과 섭취량을 확인해 주세요.` : '분석은 완료되었지만 인식된 음식이 없습니다. 다른 사진으로 시도하거나 음식을 직접 추가해 주세요.')}catch(err){setScanStatus('error');setScanError(err.message);throw err;}})}
  // 새 사진을 선택할 때 이전 탐지·수정 행·분석 오류를 초기화해 서로 다른 사진 결과가 섞이지 않게 한다.
  function selectPhoto(next){setScanStatus('idle');setScanError('');setFile(next);setImage(null);setRows([]);setError('');setMessage('')}
  // 안정적인 UUID 행 키를 생성해 음식 직접 선택 행을 추가한다.
  function addFood(){setRows(r=>[...r,{key:crypto.randomUUID(),class_id:foods[0]?.class_id||0,serving_multiplier:1,detection_id:null}])}
  // 일치하는 행 키의 음식/섭취량만 갱신하고 다른 행은 유지한다.
  function updateRow(key,changes){setRows(r=>r.map(row=>row.key===key?{...row,...changes}:row))}
  // 저장 성공 식단을 먼저 반영하고 계정 재조회 실패는 저장 실패와 구분해 안내한다.
  async function showSavedMeal(saved, text) {
    setHistory(current=>[saved,...current.filter(meal=>meal.id!==saved.id)]);
    setPage('히스토리');setMessage(text);
    try {await loadAccount();}
    catch {setError('식단은 저장되었습니다. 추가 정보를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.');}
  }
  // 유효한 행을 서버 요청 형태로 보내 저장한다. 성공 후 사진/행을 비우고 저장된 식단 화면으로 이동한다.
  async function saveMeal(){if(!validMeal||busy)return;setMealError('');await run(async()=>{try{const saved=await api('/meals',{meal_type:mealType,items:rows.map(r=>({class_id:r.class_id,serving_multiplier:Number(r.serving_multiplier),detection_id:r.detection_id}))});setRows([]);setImage(null);setFile(null);await showSavedMeal(saved,'식단을 저장했습니다.')}catch(err){setMealError(err.message);throw err;}})}
  // 신체 정보 숫자를 변환해 서버 미리보기 후 로그인 회원의 프로필을 저장한다.
  async function saveProfile(e){e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));['age','height','weight','target_calories'].forEach(k=>data[k]=Number(data[k]));await run(async()=>{const preview=await api('/profiles/calorie-preview',data);setGoal(preview);if(user){await api('/users/me/profile',data,'PUT');await loadAccount();setMessage('목표가 저장되었습니다.')}})}
  // 식사 구분과 제외 음식으로 서버 추천을 요청한다.
  async function generate(){await run(async()=>setRecommendation(await api('/recommendations/meals',{meal_type:mealType,exclude_foods:exclude})))}
  // 추천 ID와 선택 음식으로 식단을 저장해 서버가 추천 선택 상태도 함께 기록하도록 한다.
  async function recordRecommended(item){await run(async()=>{const saved=await api('/meals',{meal_type:mealType,recommendation_id:recommendation.id,items:[{class_id:item.class_id,serving_multiplier:1,detection_id:null}]});setRecommendation(null);await showSavedMeal(saved,'추천 메뉴를 식단으로 저장했습니다.')})}
  // 서버 세션을 종료하고 회원·사진·식단·추천 상태와 CSRF를 비운다.
  async function logout(){await run(async()=>{await api('/auth/logout',{});csrf='';setUser(null);setToday(null);setHistory([]);setProfile(null);setFile(null);setRows([]);setImage(null);setRecommendation(null);setPage('홈')})}
  // 비밀번호 변경으로 무효화된 회원 상태를 비우고 새 비밀번호 로그인 화면을 표시한다.
  function passwordChanged(text){csrf='';setResetToken(null);setUser(null);setToday(null);setHistory([]);setProfile(null);setFile(null);setRows([]);setImage(null);setRecommendation(null);setConsent(false);setSignup(false);setPage('로그인');setError('');setMessage(text);}
  const authForm=<EmailAuthForm signup={signup} policy={policy} busy={busy} onSubmit={authenticate} api={api}/>;
  if(resetToken&&!authLoading)return <div className="shell integrated-app"><main><PasswordForm api={api} token={resetToken}
    onChanged={passwordChanged} onCancel={()=>{setResetToken(null);setSignup(false);setPage('로그인');}}/></main></div>;
  if(authLoading)return <div className="shell integrated-app"><main><p className="notice" role="status">로그인 상태를 확인하고 있습니다…</p></main></div>;
  return <div className="shell integrated-app"><aside><Brand onClick={onHomepage}/><p className="aside-caption">식사 기록에서 다음 선택까지.</p><nav aria-label="웹앱 메뉴">{['홈','음식 추가','목표 설정','식사 추천','식단 분석','히스토리','마이페이지'].map(p=><button key={p} className={page===p?'active':''} aria-current={page===p?'page':undefined} onClick={()=>navigate(p)}><MenuIcon page={p}/>{p}</button>)}</nav><div className="aside-bottom">{user?user.name:'나의 식단과 영양을 기록하세요.'}{user&&<button className="text-button" onClick={logout} disabled={busy}>로그아웃</button>}<p>Asia/Seoul · 칼로디텍트</p><button className="text-button" onClick={onHomepage}>홈페이지 ↗</button></div></aside><main><header><span>{user?`${user.name}님의 식단 기록`:'오늘 뭘 먹지? 데이터로 확인하세요.'}</span><button className="text-button" onClick={()=>navigate(user?'마이페이지':'로그인')}>{user?'내 계정':'로그인 / 회원가입'}</button></header>{error&&<div className="error" role="alert">{error}</div>}{message&&<div className="notice" role="status">{message}</div>}{busy&&<p role="status" className="muted">처리 중입니다. 사진 분석은 잠시 시간이 걸릴 수 있습니다.</p>}
    {page==='홈'&&<Dashboard user={user} today={today} api={api} onNavigate={navigate} onAddMeal={type=>{setMealType(type);navigate('음식 추가')}}/>}
    {(page==='로그인'||(!user&&['히스토리','식사 추천','식단 분석','마이페이지'].includes(page)))&&<div className="auth-card"><div className="auth-visual"><Brand onClick={onHomepage}/><h1>오늘의 한 끼가<br/>내일의 나를 만듭니다.</h1><p>나를 위한 건강한 선택, 지금 시작하세요.</p><Bowl/></div><div className="auth-form"><p className="eyebrow">WELCOME TO CALODETECT</p><h2>{signup?'회원가입':'로그인'}</h2><p className="muted">만 {policy?.age_min||18}세 이상부터 이용할 수 있습니다.</p><div className="segmented" role="group" aria-label="인증 방식"><button type="button" className={!signup?'selected':''} aria-pressed={!signup} disabled={busy} onClick={()=>setSignup(false)}>로그인</button><button type="button" className={signup?'selected':''} aria-pressed={signup} disabled={busy} onClick={()=>setSignup(true)}>회원가입</button></div><SocialLogin signup={signup} api={api} policy={policy} disabled={busy} onAuthenticated={async result=>{setUser(result.user);setPage(file?'음식 추가':'홈');await run(loadAccount)}}/>{authForm}</div></div>}
    {page==='음식 추가'&&!user&&<><p className="notice">가입 전에는 음식 선택과 영양 계산을 사용할 수 있습니다. 사진 분석과 저장은 로그인이 필요합니다.</p><section className="panel"><h2>사진으로 식단 기록하기</h2><PhotoInput file={file} busy={busy} onChange={selectPhoto}/><p className="muted">선택한 사진은 로그인 후 분석할 수 있습니다. 사진을 선택하면 미리보기를 확인할 수 있습니다.</p><button className="primary" onClick={()=>{setSignup(false);navigate('로그인')}}>로그인하고 사진 분석하기</button></section><div className="calculator-content"><Calculators initialTab="음식 추가"/></div></>}
    {page==='음식 추가'&&user&&<><p className="eyebrow">MEAL SCAN</p><h1>사진에서 식단 기록까지.</h1><div className="two-col"><form className="panel" onSubmit={scan}><h2>01 · 사진 분석</h2><PhotoInput file={file} busy={busy} onChange={selectPhoto}/><button className="primary" disabled={busy||!file}>{scanStatus==='working'?'사진 분석 중…':'사진 분석하기'}</button><ScanResult status={scanStatus} error={scanError} result={image}/><p className="muted">탐지는 추정 결과입니다. 음식명과 섭취량을 꼭 확인해 주세요.</p></form><section className="panel"><h2>02 · 음식 확인 / 수정</h2><label>식사 구분<select value={mealType} onChange={e=>setMealType(e.target.value)}>{Object.entries(meals).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>{rows.map((r,i)=><div key={r.key} className="food-row"><label>#{i+1} 음식 {r.confidence!=null&&`· 신뢰도 ${Math.round(r.confidence*100)}%`}<select value={r.class_id} onChange={e=>updateRow(r.key,{class_id:Number(e.target.value)})}>{foods.map(f=><option key={f.class_id} value={f.class_id}>{f.food_name}</option>)}</select></label><label>수량 · {foods.find(f=>f.class_id===r.class_id)?.unit}<input type="number" min="0.01" max="100" step="0.01" value={r.serving_multiplier} onChange={e=>updateRow(r.key,{serving_multiplier:e.target.value})}/></label><button className="text-button" onClick={()=>setRows(rows.filter(item=>item.key!==r.key))}>삭제</button></div>)}<button className="text-button" onClick={addFood} disabled={!foods.length}>+ 음식 직접 추가</button>{rows.length>0&&<><Nutrition data={totals}/>{!totals&&validMeal&&<p className="muted">{previewError ? '영양 미리보기를 불러오지 못했습니다. 저장 시 서버가 영양을 계산합니다.' : '영양 미리보기를 계산 중입니다. 식단 저장은 가능합니다.'}</p>}{!validMeal&&<p className="error" role="alert">음식과 수량을 확인해 주세요. 수량은 0보다 크고 100 이하여야 하며, 한 번에 100개까지 저장할 수 있습니다.</p>}<button className="primary" disabled={!validMeal||busy} onClick={saveMeal}>식단 저장하기</button>{mealError&&<p className="error" role="alert">식단 저장 실패: {mealError}</p>}</>}</section></div></>}
    {page==='목표 설정'&&<GoalSetup key={user?.id||'guest'} profile={profile} user={user} busy={busy} api={api} onSaved={async data=>{await api('/users/me/profile',data,'PUT');try{await loadAccount();}catch{setError('Saved. Please reload account information.');}}}/>}
    {page==='식사 추천'&&user&&<><p className="eyebrow">YOUR NEXT MEAL</p><h1>지금의 기록에 맞는 다음 식사.</h1><section className="panel"><label>식사 구분<select value={mealType} onChange={e=>setMealType(e.target.value)}>{Object.entries(meals).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>제외할 음식 · 여러 개 선택 가능<select multiple value={exclude.map(String)} onChange={e=>setExclude([...e.target.selectedOptions].map(o=>Number(o.value)))}>{foods.map(f=><option key={f.class_id} value={f.class_id}>{f.food_name}</option>)}</select></label><button className="primary" disabled={busy} onClick={generate}>식사 추천</button></section>{recommendation&&<><p className="notice">{recommendation.notice}</p><div className="cards">{recommendation.items.map(item=><article key={item.class_id}><span className="card-number">{item.category} · {item.unit}</span><h3>{item.food_name}</h3><strong>{item.nutrition.cal} kcal</strong><p>단백질 {item.nutrition.protein}g · 당류 {item.nutrition.sugar}g · 나트륨 {item.nutrition.sodium}mg</p><ul>{item.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul><button className="primary" disabled={busy} onClick={()=>recordRecommended(item)}>이 메뉴로 기록하기</button></article>)}</div></>}</>}
    {page==='식단 분석'&&user&&<MealAnalytics api={api}/>}
    {page==='히스토리'&&user&&<MealHistory history={history} onAdd={()=>navigate('음식 추가')}/>}
    {page==='마이페이지'&&user&&<AccountInfo user={user} profile={profile} busy={busy} onGoals={()=>navigate('목표 설정')} onUpdate={name=>run(async()=>{const d=await api('/users/me',{name},'PUT');setUser(d.user);setMessage('회원정보를 수정했습니다.');})}/>}
    {page==='마이페이지'&&user&&(user.password_login_enabled ? <PasswordForm api={api} onChanged={passwordChanged}/>
      : <section className="panel"><h2>비밀번호 관리</h2><p className="muted">Google 계정의 비밀번호는 Google 계정 설정에서 변경해 주세요.</p></section>)}
    {page==='마이페이지'&&user&&<section className="panel"><h1>{user.name}님의 계정</h1><p>{user.email}</p><h2>모델 개선 활용 동의</h2><p className="notice">{policy?.model_improvement_consent_text||'동의 문구 확정 후 선택 동의를 활성화합니다.'}</p><p className="muted">선택 동의입니다. 동의한 사진의 음식 수정 이력은 관리자 QA 후 모델 개선 후보로 검토됩니다. 동의 철회 시 대기 샘플은 제외되며 식단 기록은 유지됩니다. 이미 승인된 데이터의 운영 처리 정책은 확정 전입니다.</p><label className="check"><input type="checkbox" checked={consent} disabled={busy||(!policy?.model_improvement_consent_text&&!consent)} onChange={e=>{const checked=e.target.checked;run(async()=>{await api('/users/me/consent',{model_improvement_consent:checked},'PUT');setConsent(checked);setMessage('동의 상태가 변경되었습니다.')})}}/>모델 개선에 업로드 이미지를 활용하는 데 동의</label><button className="primary" onClick={()=>navigate('목표 설정')}>목표 수정하기</button></section>}
    <footer>CaloDetect<span>영양 정보 확인과 식단 기록을 돕습니다. 의료 진단을 제공하지 않습니다.</span></footer>
  </main></div>
}
