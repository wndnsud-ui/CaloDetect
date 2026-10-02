import React, { useEffect, useState } from 'react';
import { Brand, Bowl, MenuIcon } from './Visuals';
import Calculators from './Calculators';
import AccountInfo from './AccountInfo';
import Dashboard from './Dashboard';
import PhotoInput from './PhotoInput';
import SocialLogin from './SocialLogin';
import EmailAuthForm from './EmailAuthForm';
import ScanResult from './ScanResult';
import './style.css';
import './reference.css';

let csrf = '';
async function api(path, body, method = 'POST') {
  const form = body instanceof FormData;
  const response = await fetch(`/api${path}`, {credentials: 'include', method: body === undefined ? 'GET' : method,
    headers: {...(!form && body !== undefined ? {'Content-Type': 'application/json'} : {}), ...(csrf ? {'X-CSRF-Token': csrf} : {})},
    body: body === undefined ? undefined : form ? body : JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) {const error=new Error(data.error?.message || '요청을 처리하지 못했습니다.');error.status=response.status;throw error;}
  if (data.csrf_token) csrf = data.csrf_token;
  return data;
}
const labels = {cal:'칼로리',carbs:'탄수화물',protein:'단백질',fat:'지방',sugar:'당류',sodium:'나트륨'};
const meals = {breakfast:'아침',lunch:'점심',dinner:'저녁',snack:'간식'};
function Nutrition({data}) {return <div className="nutrition-grid">{Object.entries(data || {}).map(([key,value]) => <div key={key}><span>{labels[key]}</span><strong>{Number(value).toLocaleString()}<small>{key === 'cal' ? ' kcal' : key === 'sodium' ? ' mg' : ' g'}</small></strong></div>)}</div>}

export default function App({initialPage='홈',onHomepage,onPageChange}) {
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
  const validMeal = rows.length > 0 && rows.length <= 100 && rows.every(row => Number.isFinite(Number(row.serving_multiplier)) && Number(row.serving_multiplier) > 0 && Number(row.serving_multiplier) <= 100 && foods.some(food => food.class_id === row.class_id));
  useEffect(()=>{
    let active=true;setTotals(null);setPreviewError('');setMealError('');
    if(rows.length && rows.every(r=>Number(r.serving_multiplier)>0 && Number(r.serving_multiplier)<=100)) {
      api('/nutrition/preview',{items:rows.map(r=>({class_id:r.class_id,serving_multiplier:Number(r.serving_multiplier)}))})
        .then(d=>{if(active)setTotals(d.totals);}).catch(e=>{if(active)setPreviewError(e.message);});
    }
    return()=>{active=false;};
  },[rows]);
  useEffect(()=>{onPageChange?.(page)},[page,onPageChange]);
  useEffect(() => {
    let active=true;
    Promise.all([api('/foods'),api('/auth/policy')]).then(([f,p]) => {if(active){setFoods(f.items);setPolicy(p)}}).catch(e => {if(active)setError(e.message)});
    async function restoreSession(){
      try {
        const d=await api('/users/me');if(!active)return;
        setUser(d.user);setPage(current=>current==='로그인'?'홈':current);
        try {await loadAccount();} catch(e){if(active)setError(e.message);}
      } catch(e){if(active&&e.status!==401)setError(e.message);}
      finally {if(active)setAuthLoading(false);}
    }
    restoreSession();return()=>{active=false;};
  }, []);
  async function loadAccount() {const [t,h,p,c] = await Promise.all([api('/analytics/today'),api('/meals/history'),api('/users/me/profile'),api('/users/me/consent')]);setToday(t);setHistory(h.items);setProfile(p.profile);setConsent(c.model_improvement_consent);}
  async function run(work) {setBusy(true);setError('');setMessage('');try {await work()} catch(e){setError(e.message)} finally {setBusy(false)}}
  function navigate(p){setPage(p);setError('');setMessage('')}
  async function authenticate(e){e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));if(signup){data.age=Number(data.age);data.service_consent=data.service_consent==='on';data.consent_text=policy.service_consent_text}
    await run(async()=>{const result=await api(signup ? '/auth/signup':'/auth/login',data);setUser(result.user);setPage(file?'음식 추가':'홈');await loadAccount()})}
  async function scan(e){e.preventDefault();if(!file)return;setScanStatus('working');setScanError('');await run(async()=>{try{const form=new FormData();form.append('file',file);const result=await api('/meals/detect',form);setImage(result);setScanStatus('success');setRows(result.detections.map(d=>({key:d.id,class_id:d.class_id,serving_multiplier:1,detection_id:d.id,confidence:d.confidence,bbox:d.bbox})));setMessage(result.detections.length ? `사진 분석을 완료했습니다. 인식된 음식 ${result.detections.length}개의 이름과 섭취량을 확인해 주세요.` : '분석은 완료되었지만 인식된 음식이 없습니다. 다른 사진으로 시도하거나 음식을 직접 추가해 주세요.')}catch(err){setScanStatus('error');setScanError(err.message);throw err;}})}
  function selectPhoto(next){setScanStatus('idle');setScanError('');setFile(next);setImage(null);setRows([]);setError('');setMessage('')}
  function addFood(){setRows(r=>[...r,{key:crypto.randomUUID(),class_id:foods[0]?.class_id||0,serving_multiplier:1,detection_id:null}])}
  function updateRow(key,changes){setRows(r=>r.map(row=>row.key===key?{...row,...changes}:row))}
  async function showSavedMeal(saved, text) {
    setHistory(current=>[saved,...current.filter(meal=>meal.id!==saved.id)]);
    setPage('히스토리');setMessage(text);
    try {await loadAccount();}
    catch {setError('식단은 저장되었습니다. 추가 정보를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.');}
  }
  async function saveMeal(){if(!validMeal||busy)return;setMealError('');await run(async()=>{try{const saved=await api('/meals',{meal_type:mealType,items:rows.map(r=>({class_id:r.class_id,serving_multiplier:Number(r.serving_multiplier),detection_id:r.detection_id}))});setRows([]);setImage(null);setFile(null);await showSavedMeal(saved,'식단을 저장했습니다.')}catch(err){setMealError(err.message);throw err;}})}
  async function saveProfile(e){e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));['age','height','weight','target_calories'].forEach(k=>data[k]=Number(data[k]));await run(async()=>{const preview=await api('/profiles/calorie-preview',data);setGoal(preview);if(user){await api('/users/me/profile',data,'PUT');await loadAccount();setMessage('목표가 저장되었습니다.')}})}
  async function generate(){await run(async()=>setRecommendation(await api('/recommendations/meals',{meal_type:mealType,exclude_foods:exclude})))}
  async function recordRecommended(item){await run(async()=>{const saved=await api('/meals',{meal_type:mealType,recommendation_id:recommendation.id,items:[{class_id:item.class_id,serving_multiplier:1,detection_id:null}]});setRecommendation(null);await showSavedMeal(saved,'추천 메뉴를 식단으로 저장했습니다.')})}
  async function logout(){await run(async()=>{await api('/auth/logout',{});csrf='';setUser(null);setToday(null);setHistory([]);setProfile(null);setFile(null);setRows([]);setImage(null);setRecommendation(null);setPage('홈')})}
  const authForm=<EmailAuthForm signup={signup} policy={policy} busy={busy} onSubmit={authenticate}/>;
  if(authLoading)return <div className="shell integrated-app"><main><p className="notice" role="status">로그인 상태를 확인하고 있습니다…</p></main></div>;
  return <div className="shell integrated-app"><aside><Brand onClick={onHomepage}/><p className="aside-caption">식사 기록에서 다음 선택까지.</p><nav aria-label="웹앱 메뉴">{['홈','음식 추가','목표 설정','식사 추천','히스토리','마이페이지'].map(p=><button key={p} className={page===p?'active':''} aria-current={page===p?'page':undefined} onClick={()=>navigate(p)}><MenuIcon page={p}/>{p}</button>)}</nav><div className="aside-bottom">{user?user.name:'나의 식단과 영양을 기록하세요.'}{user&&<button className="text-button" onClick={logout} disabled={busy}>로그아웃</button>}<p>Asia/Seoul · 칼로디텍트</p><button className="text-button" onClick={onHomepage}>홈페이지 ↗</button></div></aside><main><header><span>{user?`${user.name}님의 식단 기록`:'오늘 뭘 먹지? 데이터로 확인하세요.'}</span><button className="text-button" onClick={()=>navigate(user?'마이페이지':'로그인')}>{user?'내 계정':'로그인 / 회원가입'}</button></header>{error&&<div className="error" role="alert">{error}</div>}{message&&<div className="notice" role="status">{message}</div>}{busy&&<p role="status" className="muted">처리 중입니다. 사진 분석은 잠시 시간이 걸릴 수 있습니다.</p>}
    {page==='홈'&&<Dashboard user={user} today={today} onNavigate={navigate}/>}
    {(page==='로그인'||(!user&&['히스토리','식사 추천','마이페이지'].includes(page)))&&<div className="auth-card"><div className="auth-visual"><Brand onClick={onHomepage}/><h1>오늘의 한 끼가<br/>내일의 나를 만듭니다.</h1><p>나를 위한 건강한 선택, 지금 시작하세요.</p><Bowl/></div><div className="auth-form"><p className="eyebrow">WELCOME TO CALODETECT</p><h2>{signup?'회원가입':'로그인'}</h2><p className="muted">만 {policy?.age_min||18}세 이상부터 이용할 수 있습니다.</p><div className="segmented" role="group" aria-label="인증 방식"><button type="button" className={!signup?'selected':''} aria-pressed={!signup} disabled={busy} onClick={()=>setSignup(false)}>로그인</button><button type="button" className={signup?'selected':''} aria-pressed={signup} disabled={busy} onClick={()=>setSignup(true)}>회원가입</button></div><SocialLogin signup={signup} api={api} policy={policy} disabled={busy} onAuthenticated={async result=>{setUser(result.user);setPage(file?'음식 추가':'홈');await run(loadAccount)}}/>{authForm}</div></div>}
    {page==='음식 추가'&&!user&&<><p className="notice">가입 전에는 음식 선택과 영양 계산을 사용할 수 있습니다. 사진 분석과 저장은 로그인이 필요합니다.</p><section className="panel"><h2>사진으로 식단 기록하기</h2><PhotoInput file={file} busy={busy} onChange={selectPhoto}/><p className="muted">선택한 사진은 로그인 후 분석할 수 있습니다. 사진을 선택하면 미리보기를 확인할 수 있습니다.</p><button className="primary" onClick={()=>{setSignup(false);navigate('로그인')}}>로그인하고 사진 분석하기</button></section><div className="calculator-content"><Calculators initialTab="음식 추가"/></div></>}
    {page==='음식 추가'&&user&&<><p className="eyebrow">MEAL SCAN</p><h1>사진에서 식단 기록까지.</h1><div className="two-col"><form className="panel" onSubmit={scan}><h2>01 · 사진 분석</h2><PhotoInput file={file} busy={busy} onChange={selectPhoto}/><button className="primary" disabled={busy||!file}>{scanStatus==='working'?'사진 분석 중…':'사진 분석하기'}</button><ScanResult status={scanStatus} error={scanError} result={image}/><p className="muted">탐지는 추정 결과입니다. 음식명과 섭취량을 꼭 확인해 주세요.</p></form><section className="panel"><h2>02 · 음식 확인 / 수정</h2><label>식사 구분<select value={mealType} onChange={e=>setMealType(e.target.value)}>{Object.entries(meals).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>{rows.map((r,i)=><div key={r.key} className="food-row"><label>#{i+1} 음식 {r.confidence!=null&&`· 신뢰도 ${Math.round(r.confidence*100)}%`}<select value={r.class_id} onChange={e=>updateRow(r.key,{class_id:Number(e.target.value)})}>{foods.map(f=><option key={f.class_id} value={f.class_id}>{f.food_name}</option>)}</select></label><label>수량 · {foods.find(f=>f.class_id===r.class_id)?.unit}<input type="number" min="0.01" max="100" step="0.01" value={r.serving_multiplier} onChange={e=>updateRow(r.key,{serving_multiplier:e.target.value})}/></label><button className="text-button" onClick={()=>setRows(rows.filter(item=>item.key!==r.key))}>삭제</button></div>)}<button className="text-button" onClick={addFood} disabled={!foods.length}>+ 음식 직접 추가</button>{rows.length>0&&<><Nutrition data={totals}/>{!totals&&validMeal&&<p className="muted">{previewError ? '영양 미리보기를 불러오지 못했습니다. 저장 시 서버가 영양을 계산합니다.' : '영양 미리보기를 계산 중입니다. 식단 저장은 가능합니다.'}</p>}{!validMeal&&<p className="error" role="alert">음식과 수량을 확인해 주세요. 수량은 0보다 크고 100 이하여야 하며, 한 번에 100개까지 저장할 수 있습니다.</p>}<button className="primary" disabled={!validMeal||busy} onClick={saveMeal}>식단 저장하기</button>{mealError&&<p className="error" role="alert">식단 저장 실패: {mealError}</p>}</>}</section></div></>}
    {page==='목표 설정'&&<><p className="eyebrow">YOUR GOAL</p><h1>나의 목표를 설정해요.</h1><div className="two-col"><form key={profile?.updated_at||user?.id||'guest'} className="panel" onSubmit={saveProfile}><div className="form-grid">{[['height','키 (cm)',175],['weight','체중 (kg)',70],['age','나이',user?.age||30],['target_calories','목표 칼로리',2000]].map(([name,label,value])=><label key={name}>{label}<input name={name} type="number" min="1" step={name==='age'?'1':'0.1'} defaultValue={profile?.[name]??value} required/></label>)}</div><label>성별<select name="sex" defaultValue={profile?.sex||'male'}><option value="male">남성</option><option value="female">여성</option></select></label><label>활동 수준<select name="activity_level" defaultValue={profile?.activity_level||'sedentary'}>{[['sedentary','좌식 생활'],['light','가벼운 활동'],['moderate','보통 활동'],['active','활발한 활동']].map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>목표 유형<select name="goal_type" defaultValue={profile?.goal_type||'maintain'}><option value="weight_loss">감량</option><option value="maintain">유지</option><option value="muscle_gain">증가</option></select></label><button className="primary" disabled={busy}>{user?'계산하고 목표 저장':'목표 미리 계산'}</button></form><section className="panel"><h2>목표 칼로리 범위</h2>{(goal||profile)?<dl>{[['bmr','기초대사량'],['tdee','일일 에너지 소비량'],['minimum_calories','최소 허용값'],['recommended_calorie_min','권장 하한'],['recommended_calorie_max','권장 상한']].map(([k,v])=><div key={k}><dt>{v}</dt><dd>{(goal||profile)[k]} kcal</dd></div>)}</dl>:<p className="empty">정보를 입력해 주세요.</p>}<p className="muted">성인 대상 팀 회의 기준 계산이며 의료 진단이 아닙니다. 탄단지·당류·나트륨 목표 기준은 팀 확정 전입니다.</p></section></div></>}
    {page==='식사 추천'&&user&&<><p className="eyebrow">YOUR NEXT MEAL</p><h1>지금의 기록에 맞는 다음 식사.</h1><section className="panel"><label>식사 구분<select value={mealType} onChange={e=>setMealType(e.target.value)}>{Object.entries(meals).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>제외할 음식 · 여러 개 선택 가능<select multiple value={exclude.map(String)} onChange={e=>setExclude([...e.target.selectedOptions].map(o=>Number(o.value)))}>{foods.map(f=><option key={f.class_id} value={f.class_id}>{f.food_name}</option>)}</select></label><button className="primary" disabled={busy} onClick={generate}>식사 추천</button></section>{recommendation&&<><p className="notice">{recommendation.notice}</p><div className="cards">{recommendation.items.map(item=><article key={item.class_id}><span className="card-number">{item.category} · {item.unit}</span><h3>{item.food_name}</h3><strong>{item.nutrition.cal} kcal</strong><p>단백질 {item.nutrition.protein}g · 당류 {item.nutrition.sugar}g · 나트륨 {item.nutrition.sodium}mg</p><ul>{item.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul><button className="primary" disabled={busy} onClick={()=>recordRecommended(item)}>이 메뉴로 기록하기</button></article>)}</div></>}</>}
    {page==='히스토리'&&user&&<><p className="eyebrow">MEAL HISTORY</p><h1>한 끼씩 쌓이는 나의 기록.</h1><button className="text-button" onClick={()=>navigate('음식 추가')}>+ 식단 추가하기</button>{history.length?history.map(meal=><section className="panel" style={{marginBottom:15}} key={meal.id}><h2>{meal.meal_date} · {meals[meal.meal_type]}</h2>{meal.items.map(item=><div key={item.id}><div className="history-row"><div><strong>{item.food_name}</strong><p className="muted">기준량 × {item.serving_multiplier}</p></div></div><Nutrition data={item.nutrition}/></div>)}</section>):<p className="empty">아직 기록된 식단이 없습니다.</p>}</>}
    {page==='마이페이지'&&user&&<AccountInfo user={user} profile={profile} busy={busy} onGoals={()=>navigate('목표 설정')} onUpdate={name=>run(async()=>{const d=await api('/users/me',{name},'PUT');setUser(d.user);setMessage('회원정보를 수정했습니다.');})}/>}
    {page==='마이페이지'&&user&&<section className="panel"><h1>{user.name}님의 계정</h1><p>{user.email}</p><h2>모델 개선 활용 동의</h2><p className="notice">{policy?.model_improvement_consent_text||'동의 문구 확정 후 선택 동의를 활성화합니다.'}</p><p className="muted">선택 동의입니다. 동의한 사진의 음식 수정 이력은 관리자 QA 후 모델 개선 후보로 검토됩니다. 동의 철회 시 대기 샘플은 제외되며 식단 기록은 유지됩니다. 이미 승인된 데이터의 운영 처리 정책은 확정 전입니다.</p><label className="check"><input type="checkbox" checked={consent} disabled={busy||(!policy?.model_improvement_consent_text&&!consent)} onChange={e=>{const checked=e.target.checked;run(async()=>{await api('/users/me/consent',{model_improvement_consent:checked},'PUT');setConsent(checked);setMessage('동의 상태가 변경되었습니다.')})}}/>모델 개선에 업로드 이미지를 활용하는 데 동의</label><button className="primary" onClick={()=>navigate('목표 설정')}>목표 수정하기</button></section>}
    <footer>CaloDetect<span>영양 정보 확인과 식단 기록을 돕습니다. 의료 진단을 제공하지 않습니다.</span></footer>
  </main></div>
}
