// 회원 웹앱의 상태와 화면 전환을 조정하는 상위 컴포넌트.
// 세션 복원 → 음식/프로필/식단 조회 → 사진 분석/보정 → 서버 영양 미리보기 → 식단 저장 흐름을 연결한다.
// API 호출은 HttpOnly 쿠키와 CSRF 헤더를 사용하고 영양 계산·권한 판단은 Backend 결과를 따른다.
// 10월 15일 박근수 수정: 추천 테마·영양 위험 표시·목표 미설정 처리를 Backend 계약과 일치시킨다.
import React, { useEffect, useState } from 'react';
import { Brand, Bowl, MenuIcon } from './Visuals';
import Calculators from './Calculators';
import AccountInfo from './AccountInfo';
import Dashboard from './HomeDashboard';
import PhotoInput from './PhotoInput';
import {MealScanHero, MealScanStep, MealScanFood, MealScanJibang} from './MealScanDesign';
import './menu-backgrounds.css';
import MenuPageHero from './MenuPageHero';
import FoodAutocomplete from './FoodAutocomplete';
import SocialLogin from './SocialLogin';
import EmailAuthForm from './EmailAuthForm';
import {saveRememberedEmail} from './rememberedEmail';
import {PasswordForm, takeResetToken} from './PasswordTools';
import ScanResult from './ScanResult';
import NutritionSummary from './NutritionSummary';
import GoalSetup from './GoalSetup';
import MealAnalytics from './MealAnalytics';
import MealHistory from './MealHistory';
import {CoachFab, CoachSheet} from './CoachChat';
import Community from './Community';
import Rewards from './Rewards';
import RewardGrantPanel from './RewardGrantPanel';
import FirstDecorate from './FirstDecorate';
import LevelUpDialog from './LevelUpDialog';
import NicknameStep from './NicknameStep';
import NicknamePromptCard from './NicknamePromptCard';
import DevDemo from './DevDemo';
import AdminPage from './AdminPage';
import { readApiResponse } from './apiResponse';
import {AccountActions, MobileTopBar, MobileTabBar, RecordSheet} from './MobileShell';
import useIsMobile from './useIsMobile';
import './style.css';
import './reference.css';
import './recommendation.css';
import './rewards.css';

// HttpOnly 쿠키 원문 대신 서버가 준 CSRF 토큰만 모듈 메모리에 보관한다. 로그아웃/비밀번호 변경 시 비운다.
let csrf = '';
// 요청 본문 유무에 따라 조회/변경 호출을 구성하고 공통 응답 파서로 결과를 읽는다.
async function api(path, body, method = 'POST', refreshSession = true) {
  // 사진 업로드는 브라우저가 multipart boundary를 붙이도록 Content-Type을 직접 지정하지 않는다.
  const form = body instanceof FormData;
  // credentials: include로 세션 쿠키를 보내고 JSON 본문과 CSRF 헤더는 필요한 경우에만 추가한다.
  const response = await fetch(`/api${path}`, {credentials: 'include', cache: 'no-store', method: body === undefined ? 'GET' : method,
    headers: {...(!form && body !== undefined ? {'Content-Type': 'application/json'} : {}), ...(csrf ? {'X-CSRF-Token': csrf} : {})},
    body: body === undefined ? undefined : form ? body : JSON.stringify(body)});
  let data;
  try {
    data = await readApiResponse(response);
  } catch (error) {
    // A different tab or a new login can replace the cookie while this page retains its old token.
    // This exact rejection occurs before the handler runs, so one retry cannot duplicate a saved meal.
    if (refreshSession && body !== undefined && error.status === 403 &&
        error.message === '세션을 새로고침한 뒤 다시 시도하세요.') {
      await api('/users/me');
      return api(path, body, method, false);
    }
    throw error;
  }
  if (data.csrf_token) csrf = data.csrf_token;
  return data;
}
const meals = {breakfast:'아침',lunch:'점심',dinner:'저녁',snack:'간식'};
// 가장 최근 기록 날짜의 마지막 끼니(간식 제외) 다음 끼니를 고른다. 아침→점심→저녁→아침, 기록이 없으면 아침.
const MAIN_MEALS = ['breakfast','lunch','dinner'];
function nextMealType(history) {
  const mains = (history || []).filter(meal => MAIN_MEALS.includes(meal.meal_type));
  if (!mains.length) return 'breakfast';
  const lastDate = mains.reduce((latest, meal) => meal.meal_date > latest ? meal.meal_date : latest, mains[0].meal_date);
  const lastIndex = Math.max(...mains.filter(meal => meal.meal_date === lastDate).map(meal => MAIN_MEALS.indexOf(meal.meal_type)));
  return MAIN_MEALS[(lastIndex + 1) % MAIN_MEALS.length];
}
// 가입 보너스가 실제로 지급된 경우에만(온보딩 시작일 이후 가입자) 첫 꾸미기 안내를 띄운다.
const earnedSignupPoints = account => account?.today_items?.some(row => row.key === 'onboarding:signup' && row.points > 0);
const calorieBandNames = {light:'가벼운 메뉴',medium:'보통 열량',high:'고열량 메뉴'};
// 공통 영양 요약 컴포넌트에 서버 계산 결과를 전달한다.
function Nutrition({data}) {return <NutritionSummary data={data}/>}

// 회원 세션·식단·프로필·사진 분석 상태를 관리하고 선택된 서비스 화면에 전달한다.
export default function App({initialPage='홈',onHomepage,onPageChange}) {
  const [resetToken, setResetToken] = useState(takeResetToken);
  const [authLoading,setAuthLoading] = useState(true);
  const [page,setPage] = useState(initialPage==='회원가입'?'로그인':initialPage==='채팅으로 식사기록'?'홈':initialPage), [user,setUser] = useState(null), [policy,setPolicy] = useState(null);
  const [mallKey,setMallKey] = useState(0), [signedUpEmail,setSignedUpEmail] = useState('');
  const [foods,setFoods] = useState([]), [today,setToday] = useState(null), [history,setHistory] = useState([]);
  const [profile,setProfile] = useState(null), [recommendation,setRecommendation] = useState(null);
  const [recommendTheme,setRecommendTheme] = useState('balance');
  const [error,setError] = useState(''), [message,setMessage] = useState(''), [busy,setBusy] = useState(false);
  const [signup,setSignup] = useState(initialPage==='회원가입'), [file,setFile] = useState(null), [image,setImage] = useState(null);
  const [scanStatus,setScanStatus] = useState('idle'), [scanError,setScanError] = useState('');
  const [rows,setRows] = useState([]), [mealType,setMealType] = useState('breakfast');
  const [goal,setGoal] = useState(null), [recommendationLoading,setRecommendationLoading] = useState(false);
  const [totals,setTotals] = useState(null), [previewError,setPreviewError] = useState(''), [mealError,setMealError] = useState('');
  // 리워드(지시서 v3): /rewards/me 요약, 리워드 탭, 기록 직후 보상 패널, 첫날 꾸미기, 레벨업 창, 가입 마지막 단계 닉네임.
  const [rewards,setRewards] = useState(null), [accountTab,setAccountTab] = useState('profile'), [grantMeal,setGrantMeal] = useState(null);
  const [communityMeal,setCommunityMeal] = useState(null);
  // 모바일(760px 이하) 앱 틀: 하단 탭바의 ＋기록 바텀시트 열림 상태.
  const isMobile = useIsMobile(), [recordSheet,setRecordSheet] = useState(false);
  // 칼로티 코치 채팅 시트(업무지시서 v1.2): 예전 '채팅으로 식사기록' 페이지 대신 어느 화면에서나 같은 시트를 연다.
  // coachEdit는 식단 기록의 '챗으로 수정' 대상 {meal, item}이며 같은 시트 안에서 수정 대화를 보여 준다.
  const [coachOpen,setCoachOpen] = useState(initialPage==='채팅으로 식사기록'), [coachEdit,setCoachEdit] = useState(null);
  const closeCoach = React.useCallback(()=>setCoachOpen(false),[]);
  function openCoach(edit=null){setCoachEdit(edit);setRecordSheet(false);setCoachOpen(true);}
  const recordPages = ['음식 추가', '채팅으로 식사기록'];
  const managementPages = ['히스토리', '식단 분석'];
  const accountPages = ['마이페이지', '목표 설정'];
  const mainMenus = [
    ['홈', '홈', ['홈']], ['음식 추가', '식단 기록', recordPages],
    ['식사 추천', '오늘 뭐먹지?', ['식사 추천']], ['히스토리', '식단 관리', managementPages],
    ['커뮤니티', '커뮤니티', ['커뮤니티']], ['리워드', '리워드몰', ['리워드']],
  ];
  const [firstPending,setFirstPending] = useState(false), [firstDecorate,setFirstDecorate] = useState(false), [levelSkip,setLevelSkip] = useState([]);
  const [nicknameStep,setNicknameStep] = useState(null), [nicknameEdit,setNicknameEdit] = useState(false);
  const signupFlow = React.useRef(false);
  // 로컬 개발 테스트 계정 본인에게만 테스트 메뉴와 화면을 표시한다.
  const [devDemo,setDevDemo] = useState(null);
  const canUseDevDemo = user?.email === 'test@calodetect.local' && devDemo?.enabled === true && devDemo?.test_account === true;
  useEffect(()=>{let active=true;setDevDemo(null);if(user?.email !== 'test@calodetect.local'){return;}api('/dev/demo/status').then(d=>{if(active)setDevDemo(d)}).catch(()=>{if(active)setDevDemo(null)});return()=>{active=false};},[user]);
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
  // 브라우저 뒤로/앞으로 가기: 화면과 내 정보 탭을 기록 항목의 calo에 남긴다. 처음 한 번은 현재 항목을 바꾸고, 이후 바뀔 때만 새 항목을 쌓는다.
  // 리워드몰 하위 화면 기록(rewardMall)은 같은 항목 위에 쌓이므로 화면이 같으면 새 항목을 만들지 않는다.
  const historyReady = React.useRef(false), userRef = React.useRef(user);
  userRef.current = user;
  useEffect(()=>{
    const entry={page,accountTab}, current=window.history.state?.calo;
    try {
      if(!historyReady.current){historyReady.current=true;window.history.replaceState({...(window.history.state||{}),calo:entry},'');}
      else if(!current||current.page!==page||current.accountTab!==accountTab)window.history.pushState({calo:entry},'');
    } catch {}
  },[page,accountTab]);
  // 기록 항목의 화면으로 돌아간다. 로그인한 상태에서 로그인 화면 항목으로 돌아오면 홈으로 바꾼다.
  useEffect(()=>{
    const pop=event=>{
      const saved=event.state?.calo;if(!saved)return;
      let next=saved.page;
      if(userRef.current&&next==='로그인'){next='홈';try {window.history.replaceState({...event.state,calo:{...saved,page:next}},'');} catch {}}
      setPage(next);setAccountTab(saved.accountTab||'profile');setError('');setMessage('');
      if(userRef.current&&['리워드','홈','마이페이지'].includes(next))loadRewards();
    };
    window.addEventListener('popstate',pop);
    return()=>window.removeEventListener('popstate',pop);
  },[]);
  // 오늘 뭐먹지? 진입·기록 변경 시 마지막 기록 다음 끼니를 기본 선택한다. 화면 안에서 직접 바꾼 선택은 덮지 않는다.
  useEffect(()=>{
    if(page!=='식사 추천')return;
    const next=nextMealType(history);
    if(next!==mealType){setMealType(next);setRecommendation(null);}
  },[page,history]);
  // 최초 진입 시 음식/가입 정책을 병렬 조회하고 HttpOnly 쿠키로 로그인 상태를 복원한다.
  useEffect(() => {
    let active=true;
    Promise.all([api('/foods'),api('/auth/policy')]).then(([f,p]) => {if(active){setFoods(f.items);setPolicy(p)}}).catch(e => {if(active)setError(e.message)});
    // 401은 정상 비회원으로 처리한다. 로그인 복원 후 계정 조회만 실패한 경우 회원 상태를 유지하고 오류를 안내한다.
    async function restoreSession(){
      try {
        const d=await api('/users/me');if(!active)return;
        setUser(d.user);if(!resetToken)setPage(current=>current==='로그인'?'홈':current);
        // 로그인 여부가 확인되면 바로 화면을 보여 주고, 식단·프로필·리워드는 이어서 채운다(첫 화면 대기 단축).
        setAuthLoading(false);
        try {await loadAccount();} catch(e){if(active)setError(e.message);}
      } catch(e){if(active&&e.status!==401)setError(e.message);}
      finally {if(active)setAuthLoading(false);}
    }
    restoreSession();return()=>{active=false;};
  }, []);
  // 현재 회원의 프로필·오늘 영양·히스토리·동의를 다시 조회한다.
  // 채팅 식사기록은 서버 기능 플래그가 켜져 /chat/status가 있을 때만 메뉴에 보인다.
  const [chatEnabled,setChatEnabled] = useState(false);
  useEffect(()=>{let active=true;if(!user){setChatEnabled(false);return;}api('/chat/status').then(()=>{if(active)setChatEnabled(true)}).catch(()=>{if(active)setChatEnabled(false)});return()=>{active=false};},[user]);
  async function loadAccount() {const [t,h,p,r] = await Promise.all([api('/analytics/today'),api('/meals/history'),api('/users/me/profile'),loadRewards()]);setToday(t);setHistory(h.items);setProfile(p.profile);return r;}
  // 리워드 요약은 식단·계정 화면과 독립이라 실패해도 다른 화면을 막지 않는다. 가입 단계 닉네임이 필요하면 홈보다 먼저 띄운다.
  async function loadRewards() {try {const data=await api('/rewards/me');setRewards(data);if(data.nickname_prompt==='signup')setNicknameStep(current=>current||(signupFlow.current?'signup':'relogin'));return data;} catch {return null;}}
  // 비동기 작업의 진행/오류 상태를 공통 처리해 중복 제출과 사용자 안내를 관리한다.
  async function run(work) {setBusy(true);setError('');setMessage('');try {await work()} catch(e){setError(e.message)} finally {setBusy(false)}}
  const closeRecordSheet = React.useCallback(()=>setRecordSheet(false),[]);
  // 상위 화면 선택을 바꾸고 페이지별 메시지/오류 상태를 정리한다.
  function navigate(p,tab){
    if(p==='채팅으로 식사기록'){openCoach();return;}
    const personalReward=p==='리워드'&&['room','growth','coupons','ledger'].includes(tab);
    setPage(personalReward?'마이페이지':p);setError('');setMessage('');
    // 리워드몰 메뉴를 다시 누르면 상품 상세·기획전·코치 상세에서 몰 첫 화면으로 돌아간다.
    if(p==='리워드'&&!personalReward)setMallKey(key=>key+1);
    if(personalReward)setAccountTab(tab);
    else if(p==='마이페이지')setAccountTab('profile');
    if(['리워드','홈','마이페이지'].includes(p))loadRewards();
  }
  // 폼 값을 가입/로그인 요청 형태로 변환하고 성공 후 세션과 회원 데이터를 복원한다.
  async function authenticate(e){e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));const rememberEmail=data.remember_email==='on';delete data.remember_email;if(signup){if(data.password!==data.password_confirm){setError('비밀번호가 일치하지 않아요.');return}delete data.password_confirm;data.age=Number(data.age);data.service_consent=data.service_consent==='on';data.consent_text=policy.service_consent_text}
    await run(async()=>{signupFlow.current=signup;const result=await api(signup ? '/auth/signup':'/auth/login',data);if(!signup)saveRememberedEmail(data.email,rememberEmail);else setSignedUpEmail(data.email.trim());setUser(result.user);setPage(file?'음식 추가':'홈');const account=await loadAccount();if(signup&&earnedSignupPoints(account))setFirstDecorate('signup')})}
  // 선택 사진을 FormData로 분석 요청하고 탐지 ID·클래스·신뢰도를 수정 가능한 음식 행으로 만든다.
  async function scan(e){e.preventDefault();if(!file)return;setScanStatus('working');setScanError('');await run(async()=>{try{const form=new FormData();form.append('file',file);const result=await api('/meals/detect',form);setImage(result);setScanStatus('success');setRows(result.detections.map(d=>({key:d.id,class_id:d.class_id,serving_multiplier:1,detection_id:d.id,confidence:d.confidence,bbox:d.bbox})));setMessage(result.detections.length ? `사진 분석을 완료했습니다. 인식된 음식 ${result.detections.length}개의 이름과 섭취량을 확인해 주세요.` : '분석은 완료되었지만 인식된 음식이 없습니다. 다른 사진으로 시도하거나 음식을 직접 추가해 주세요.')}catch(err){setScanStatus('error');setScanError(err.message);throw err;}})}
  // 새 사진을 선택할 때 이전 탐지·수정 행·분석 오류를 초기화해 서로 다른 사진 결과가 섞이지 않게 한다.
  function selectPhoto(next){setScanStatus('idle');setScanError('');setFile(next);setImage(null);setRows([]);setError('');setMessage('')}
  // 안정적인 UUID 행 키를 생성해 음식 직접 선택 행을 추가한다.
  function addFood(){setRows(r=>[...r,{key:crypto.randomUUID(),class_id:null,serving_multiplier:1,detection_id:null}])}
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
  async function saveMeal(){if(!validMeal||busy)return;setMealError('');await run(async()=>{try{const saved=await api('/meals',{meal_type:mealType,items:rows.map(r=>({class_id:r.class_id,serving_multiplier:Number(r.serving_multiplier),detection_id:r.detection_id}))});setRows([]);setImage(null);setFile(null);setGrantMeal(saved.id);await showSavedMeal(saved,'식단을 저장했습니다.')}catch(err){setMealError(err.message);throw err;}})}
  // 신체 정보 숫자를 변환해 서버 미리보기 후 로그인 회원의 프로필을 저장한다.
  async function saveProfile(e){e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));['age','height','weight','target_calories'].forEach(k=>data[k]=Number(data[k]));await run(async()=>{const preview=await api('/profiles/calorie-preview',data);setGoal(preview);if(user){await api('/users/me/profile',data,'PUT');await loadAccount();setMessage('목표가 저장되었습니다.')}})}
  // 선택한 테마·끼니와 직전 결과를 제외해 새 메뉴를 요청한다. 처리 중에는 조건 UI도 비활성화된다.
  async function generate(theme){if(busy)return;const exclude_foods=recommendation?.items.map(item=>item.class_id)||[];setRecommendation(null);setRecommendationLoading(true);try{await run(async()=>setRecommendation(await api('/recommendations/meals',{meal_type:mealType,theme,exclude_foods})))}finally{setRecommendationLoading(false)}}
  // 선택한 테마를 다시 눌러도 새 추천을 요청하고 진행 중에는 늦은 응답 경합을 방지한다.
  async function changeRecommendTheme(theme){if(busy)return;setRecommendTheme(theme);setRecommendation(null);await generate(theme);}
  // 서버 세션을 종료하고 회원·사진·식단·추천 상태와 CSRF를 비운 뒤 로그인 화면으로 이동한다(홈은 로그인 후 화면).
  async function logout(){await run(async()=>{await api('/auth/logout',{});csrf='';setUser(null);setRewards(null);setNicknameStep(null);setGrantMeal(null);setToday(null);setHistory([]);setProfile(null);setFile(null);setRows([]);setImage(null);setRecommendation(null);setSignup(false);setCoachOpen(false);setCoachEdit(null);setPage('로그인')})}
  // 비밀번호 변경으로 무효화된 회원 상태를 비우고 새 비밀번호 로그인 화면을 표시한다.
  function passwordChanged(text){csrf='';setResetToken(null);setUser(null);setToday(null);setHistory([]);setProfile(null);setFile(null);setRows([]);setImage(null);setRecommendation(null);setSignup(false);setPage('로그인');setError('');setMessage(text);}
  // 인증 화면은 header를 숨기므로 오류를 폼 안에 직접 표시한다.
  const authForm=<EmailAuthForm signup={signup} policy={policy} busy={busy} error={error} onSubmit={authenticate} api={api} signedUpEmail={signedUpEmail}/>;
  if(resetToken&&!authLoading)return <div className="shell integrated-app"><main><PasswordForm api={api} token={resetToken}
    onChanged={passwordChanged} onCancel={()=>{setResetToken(null);setSignup(false);setPage('로그인');}}/></main></div>;
  if(authLoading)return <div className="shell integrated-app"><main><p className="notice" role="status">로그인 상태를 확인하고 있습니다…</p></main></div>;
  // 화면에 보이는 회원 이름은 닉네임으로 통일한다. 닉네임을 불러오기 전에만 계정 이름을 쓴다.
  const displayName = rewards?.nickname?.nickname || user?.name;
  const menuBackground = accountPages.includes(page) ? 'account' : {'홈':'home','식사 추천':'recommend','히스토리':'management','식단 분석':'management','커뮤니티':'community','리워드':'rewards'}[page];
  const recordTabs = <div className="section-tabs" role="group" aria-label="식단 기록 방식"><button type="button" className={page==='음식 추가'?'active':''} aria-pressed={page==='음식 추가'} onClick={()=>navigate('음식 추가')}>사진 & 직접 기록</button>{chatEnabled&&<button type="button" onClick={()=>openCoach()}>칼로티 코치</button>}</div>;
  const managementTabs = <div className="section-tabs" role="group" aria-label="식단 관리 메뉴">{[['히스토리','나의 기록'],['식단 분석','영양 분석 리포트']].map(([target,label])=><button type="button" key={target} className={page===target?'active':''} aria-pressed={page===target} onClick={()=>navigate(target)}>{label}</button>)}</div>;
  const authLayout = page === '로그인' || (!user && ['커뮤니티', '히스토리', '식사 추천', '식단 분석', '마이페이지', '리워드'].includes(page));
  // 지방이 버튼은 앱 화면 어디에나 둔다. 비로그인은 로그인 안내, 로그인 회원은 서버 채팅 기능이 켜졌을 때만.
  const coachAvailable = !authLayout && (!user || chatEnabled);
  return <div className={'shell integrated-app' + (authLayout ? ' auth-layout' : ' has-mobile-shell') + (coachAvailable ? ' has-coach' : '')}><aside><Brand onClick={onHomepage}/><p className="aside-caption">식사 기록에서 다음 선택까지.</p><nav aria-label="웹앱 메뉴">{mainMenus.map(([target,label,pages])=><button key={target} className={pages.includes(page)?'active':''} aria-current={pages.includes(page)?'page':undefined} onClick={()=>navigate(target)}><MenuIcon page={target}/>{label}{target==='리워드'&&user&&rewards&&<span className="menu-points">{rewards.balance.toLocaleString()}P</span>}</button>)}</nav><div className="app-utilities" aria-label="내 정보 및 도구"><button type="button" className={accountPages.includes(page)?'utility-account active':'utility-account'} aria-current={accountPages.includes(page)?'page':undefined} onClick={()=>navigate(user?'마이페이지':'로그인')}><MenuIcon page="마이페이지"/><span>{user?'내 정보 & 설정':'로그인 / 회원가입'}</span></button>{user?.role==='admin'&&<button type="button" onClick={()=>navigate('관리자')}>관리자</button>}{canUseDevDemo&&<button type="button" onClick={()=>navigate('테스트')}>테스트</button>}</div><div className="aside-bottom"><p>Asia/Seoul · 칼로디텍트</p><button className="text-button" onClick={onHomepage}>홈페이지 ↗</button></div></aside><main>{!authLayout&&<MobileTopBar user={user} rewards={rewards} page={page} busy={busy} onNavigate={navigate} onHomepage={onHomepage} onLogout={logout}/>}<header><span className={page==='마이페이지'&&user?'account-page-title':undefined}>{user?(page==='마이페이지'?`${displayName}님의 계정`:`${displayName}님의 식단 기록`):'오늘 뭘 먹지? 데이터로 확인하세요.'}</span><AccountActions user={user} rewards={rewards} page={page} busy={busy} onNavigate={navigate} onLogout={logout}/></header><div className={user?`member-page-content${menuBackground ? ` menu-ambient menu-ambient-${menuBackground}` : ''}`:"page-content-pass-through"}>{error&&<div className="error" role="alert">{error}</div>}{message&&<div className="notice" role="status">{message}</div>}{busy&&<p role="status" className="muted">처리 중입니다. 사진 분석은 잠시 시간이 걸릴 수 있습니다.</p>}
    {user&&menuBackground&&!['community','rewards','account'].includes(menuBackground)&&!(isMobile&&page==='홈')&&<MenuPageHero kind={menuBackground}>
      {menuBackground==='home'&&<button type="button" className="primary" onClick={()=>navigate('음식 추가')}>＋ 식단 기록하기</button>}
      {menuBackground==='management'&&<div className="management-hero-actions">{managementTabs}{page==='히스토리'&&<button type="button" className="primary" onClick={()=>navigate('음식 추가')}>+ 식단 추가하기</button>}</div>}
      {menuBackground==='recommend'&&<div className="section-tabs" role="group" aria-label="추천 테마 선택">{[['balance','기본 맞춤 추천'],['protein','단백질 충전'],['light','가벼운 식단']].map(([key,label])=><button type="button" key={key} className={recommendTheme===key?'active':''} aria-pressed={recommendTheme===key} disabled={busy} onClick={()=>changeRecommendTheme(key)}>{label}</button>)}</div>}
    </MenuPageHero>}
    {recordPages.includes(page)&&(user?<MealScanHero>{recordTabs}</MealScanHero>:recordTabs)}
    {user&&accountPages.includes(page)&&<><MenuPageHero kind="account"><div className="section-tabs" role="group" aria-label="내 정보 및 설정 메뉴"><button type="button" className={page==='목표 설정'||accountTab==='profile'?'active':''} aria-pressed={page==='목표 설정'||accountTab==='profile'} onClick={()=>navigate('마이페이지')}>회원정보 & 건강 목표</button><button type="button" className={page==='마이페이지'&&['room','growth'].includes(accountTab)?'active':''} aria-pressed={page==='마이페이지'&&['room','growth'].includes(accountTab)} onClick={()=>navigate('리워드','growth')}>지방이 성장</button>{rewards?.exchange&&<button type="button" className={page==='마이페이지'&&['coupons','ledger'].includes(accountTab)?'active':''} aria-pressed={page==='마이페이지'&&['coupons','ledger'].includes(accountTab)} onClick={()=>navigate('리워드','coupons')}>쿠폰함</button>}</div></MenuPageHero>{(page==='목표 설정'||accountTab==='profile')&&<div className="section-tabs sub-tabs" role="group" aria-label="회원정보 및 건강 목표"><button type="button" className={page==='마이페이지'?'active':''} aria-pressed={page==='마이페이지'} onClick={()=>navigate('마이페이지')}>회원정보</button><button type="button" className={page==='목표 설정'?'active':''} aria-pressed={page==='목표 설정'} onClick={()=>navigate('목표 설정')}>건강 목표</button></div>}</>}
    {page==='홈'&&<Dashboard user={user} displayName={displayName} today={today} api={api} me={user?rewards:null} onRewardsChanged={loadRewards} onNavigate={navigate} onOpenCoach={coachAvailable?()=>openCoach():undefined} onAddMeal={type=>{setMealType(type);navigate('음식 추가')}}
      homeCard={user&&rewards?.nickname_prompt==='card'&&<NicknamePromptCard api={api} nickname={rewards.nickname.nickname} onChoose={()=>{setNicknameEdit(true);navigate('마이페이지')}} onDismissed={loadRewards}/>}/>}
    {(page==='로그인'||(!user&&['커뮤니티','히스토리','식사 추천','식단 분석','마이페이지','채팅으로 식사기록','리워드'].includes(page)))&&<div className={signup ? 'auth-card auth-card-signup' : 'auth-card auth-card-login'}><div className="auth-visual"><Brand onClick={onHomepage}/><h1>오늘의 한 끼가<br/>내일의 나를 만듭니다.</h1><p>나를 위한 건강한 선택, 지금 시작하세요.</p><img className="auth-bowl" src="/images/cta-poke.webp.png" alt="신선한 채소와 토핑을 담은 포케 보울"/></div><div className="auth-form"><p className="eyebrow">WELCOME TO CALODETECT</p><h2>{signup?'회원가입':'로그인'}</h2><p className="muted">만 {policy?.age_min||18}세 이상부터 이용할 수 있습니다.</p><div className="segmented" role="group" aria-label="인증 방식"><button type="button" className={!signup?'selected':''} aria-pressed={!signup} disabled={busy} onClick={()=>{setSignup(false);setError('')}}>로그인</button><button type="button" className={signup?'selected':''} aria-pressed={signup} disabled={busy} onClick={()=>{setSignup(true);setError('')}}>회원가입</button></div><SocialLogin signup={signup} api={api} policy={policy} disabled={busy} onAuthenticated={async (result,registered)=>{signupFlow.current=true;setUser(result.user);setPage(file?'음식 추가':'홈');await run(async()=>{const account=await loadAccount();if(registered&&earnedSignupPoints(account))setFirstDecorate('signup')})}}/>{authForm}</div></div>}
    {page==='음식 추가'&&!user&&<><p className="notice">가입 전에는 음식 선택과 영양 계산을 사용할 수 있습니다. 사진 분석과 저장은 로그인이 필요합니다.</p><section className="panel"><h2>사진으로 식단 기록하기</h2><PhotoInput file={file} busy={busy} onChange={selectPhoto}/><p className="muted">선택한 사진은 로그인 후 분석할 수 있습니다. 사진을 선택하면 미리보기를 확인할 수 있습니다.</p><button className="primary" onClick={()=>{setSignup(false);navigate('로그인')}}>로그인하고 사진 분석하기</button></section><div className="calculator-content"><Calculators initialTab="음식 추가"/></div></>}
    {page==='음식 추가'&&user&&<><div className="two-col meal-scan-workspace"><form className={'panel meal-scan-card meal-scan-photo'+(!file?' is-empty':'')} onSubmit={scan}><MealScanStep kind="camera" title="01 · 사진 분석">사진을 올리면 음식과 영양 정보를 확인해요.</MealScanStep><PhotoInput file={file} busy={busy} onChange={selectPhoto}/><button className="primary" disabled={busy||!file}>{scanStatus==='working'?'사진 분석 중…':'사진 분석하기'}</button><ScanResult status={scanStatus} error={scanError} result={image}/><p className="muted">탐지는 추정 결과입니다. 음식명과 섭취량을 꼭 확인해 주세요.</p>{!file&&<MealScanFood/>}</form><section className="panel meal-scan-card meal-scan-confirm"><MealScanStep kind="meal" title="02 · 음식 확인 / 수정">분석 결과를 확인하고, 필요한 경우 수정할 수 있어요.</MealScanStep><label>식사 구분<select value={mealType} onChange={e=>setMealType(e.target.value)}>{Object.entries(meals).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>{rows.map((r,i)=><div key={r.key} className="food-row"><label>#{i+1} 음식 {r.confidence!=null&&`· 신뢰도 ${Math.round(r.confidence*100)}%`}<FoodAutocomplete foods={foods} value={r.class_id} onChange={class_id=>updateRow(r.key,{class_id})} autoFocus={r.detection_id===null}/></label><label>수량 · {foods.find(f=>f.class_id===r.class_id)?.unit}<input type="number" min="0.5" max="100" step="0.5" value={r.serving_multiplier} onChange={e=>updateRow(r.key,{serving_multiplier:e.target.value})}/></label><button className="text-button" onClick={()=>setRows(rows.filter(item=>item.key!==r.key))}>삭제</button></div>)}<button className="text-button" onClick={addFood} disabled={!foods.length}>+ 음식 직접 추가</button>{rows.length>0&&<><Nutrition data={totals}/>{!totals&&validMeal&&<p className="muted">{previewError ? '영양 미리보기를 불러오지 못했습니다. 저장 시 서버가 영양을 계산합니다.' : '영양 미리보기를 계산 중입니다. 식단 저장은 가능합니다.'}</p>}{!validMeal&&<p className="error" role="alert">음식과 수량을 확인해 주세요. 수량은 0보다 크고 100 이하여야 하며, 한 번에 100개까지 저장할 수 있습니다.</p>}<button className="primary" disabled={!validMeal||busy} onClick={saveMeal}>식단 저장하기</button>{mealError&&<p className="error" role="alert">식단 저장 실패: {mealError}</p>}</>}{rows.length===0&&<MealScanJibang level={rewards?.level} equipment={rewards?.equipment}/>}</section></div></>}
    {page==='목표 설정'&&<GoalSetup key={user?.id||'guest'} profile={profile} user={user} busy={busy} api={api} onSaved={async data=>{const firstGoal=!profile;await api('/users/me/profile',data,'PUT');try{const updated=await loadAccount();if(firstGoal&&updated?.today_items?.some(row=>row.key==='onboarding:goal'&&row.points>0))setFirstDecorate('goal');}catch{setError('Saved. Please reload account information.');}}}/>}
    {page==='식사 추천'&&user&&<><section className="panel">
      <fieldset className="meal-type-fieldset" disabled={busy}>
        <legend>식사 구분</legend>
        <div className="meal-type-options" role="radiogroup" aria-label="식사 구분">
          {Object.entries(meals).map(([key,label])=><label key={key} className={`meal-type-option${mealType===key?' selected':''}`}>
            <input type="radio" name="recommend-meal-type" value={key} checked={mealType===key} onChange={()=>{setMealType(key);setRecommendation(null)}}/>
            <span className="meal-radio-indicator" aria-hidden="true"/>
            <span>{label}</span>
          </label>)}
        </div>
      </fieldset>
      <p className="recent-meals-note">최근 7일간 식단 기록에 포함된 음식은 추천 메뉴에서 자동으로 제외됩니다.</p>
      <div>
        {[
          {key:'balance',name:'기본 맞춤 추천',description:'오늘 섭취량과 남은 칼로리를 고려한 기본 추천'},
          {key:'protein',name:'단백질 충전',description:'단백질을 보완하는 메뉴를 우선 추천'},
          {key:'light',name:'가벼운 식단',description:'상대적으로 가벼운 열량의 메뉴를 우선 추천'}
        ].map(theme=><p key={theme.key} className="recommendation-helper" hidden={recommendTheme!==theme.key}>{theme.description}</p>)}
      </div>
      {recommendationLoading?<p className="recommendation-helper" role="status">추천 메뉴를 불러오고 있습니다…</p>:recommendation?<p className="recommendation-helper" role="status">추천 메뉴가 아래에 표시됩니다.</p>:<p className="recommendation-helper">추천 테마를 선택하면 메뉴 3개가 아래에 표시됩니다.</p>}
    </section>{recommendation&&<><p className="notice">{recommendation.notice}</p><div className="recommend-card-grid">{recommendation.items.map(item=>{
      const nutrition=item.nutrition;
      const eatenValue=recommendation.snapshot?.totals?.cal;
      const targetValue=recommendation.snapshot?.target_calories;
      const eatenCalories=Number(eatenValue);
      const targetCalories=Number(targetValue);
      const menuCalories=Number(nutrition.cal);
      const canSimulate=eatenValue!=null&&targetValue!=null&&Number.isFinite(eatenCalories)&&Number.isFinite(targetCalories)&&Number.isFinite(menuCalories)&&targetCalories>0;
      const currentWidth=canSimulate?Math.min(100,Math.max(0,eatenCalories/targetCalories*100)):0;
      const expectedWidth=canSimulate?Math.min(Math.max(0,menuCalories/targetCalories*100),100-currentWidth):0;
      const exceedsTarget=canSimulate&&eatenCalories+menuCalories>targetCalories;
      return <article key={item.class_id} className="recommend-card">
        {item.warning&&<span className="recommendation-warning" role="status">주의 · {item.warning}</span>}
        <div className="card-badge-row">
          <span className={`tag-badge ${item.calorie_band==='light'?'badge-green':item.calorie_band==='high'?'badge-orange':'badge-gray'}`}>{calorieBandNames[item.calorie_band]}</span>
          {nutrition.protein>=20&&<span className="tag-badge badge-blue">고단백</span>}
          {nutrition.cal<=350&&<span className="tag-badge badge-green">저칼로리</span>}
          {item.warning&&<span className="tag-badge badge-orange">영양 주의</span>}
          <span className="tag-badge badge-gray">{item.category}</span>
        </div>
        <h3 className="card-food-title">{item.food_name}</h3>
        <p className="card-food-unit">기준 제공량 · {item.unit}</p>
        <div className="card-nutrition-box">
          <div className="main-calorie"><strong>{nutrition.cal}</strong><span>kcal</span></div>
          <div className="sub-nutrients">
            <span>탄수화물 <b>{nutrition.carbs}g</b></span>
            <span>단백질 <b>{nutrition.protein}g</b></span>
            <span>지방 <b>{nutrition.fat}g</b></span>
            <span>당류 <b>{nutrition.sugar}g</b></span>
            <span>나트륨 <b>{nutrition.sodium}mg</b></span>
          </div>
        </div>
        {canSimulate&&<div className={`preview-simulation${exceedsTarget?' simulation-over':''}`}>
          <div className="simulation-header"><span>오늘 섭취 후 예상</span><strong className={exceedsTarget?'text-warn':''}>{(eatenCalories+menuCalories).toLocaleString()} / {targetCalories.toLocaleString()} kcal</strong></div>
          <div className="simulation-bar-track" role="img" aria-label={`오늘 섭취량 ${eatenCalories} kcal에 이 메뉴 ${menuCalories} kcal를 더하면 목표 ${targetCalories} kcal ${exceedsTarget?'초과':'이하'}입니다`}>
            <span className="bar-current" style={{width:`${currentWidth}%`}}/>
            <span className={`bar-expected${exceedsTarget?' bar-over':''}`} style={{left:`${currentWidth}%`,width:`${expectedWidth}%`}}/>
          </div>
          <small className="simulation-caption">현재 {eatenCalories.toLocaleString()} kcal + 이 메뉴 {menuCalories.toLocaleString()} kcal</small>
        </div>}
        <ul className="card-reasons">{item.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul>
      </article>;
    })}</div></>}</>}
    {page==='식단 분석'&&user&&<MealAnalytics api={api} targetCalories={profile?.target_calories}/>}
    {page==='커뮤니티'&&user&&<Community api={api} onNavigate={navigate} initialMealId={communityMeal} onRewardsChanged={loadRewards} onShareOpened={()=>setCommunityMeal(null)}/>}
    {page==='관리자'&&user?.role==='admin'&&<AdminPage api={api}/>}
    {page==='마이페이지'&&canUseDevDemo&&<button type="button" className="outline" onClick={()=>navigate('테스트')}>테스트 더미 설정</button>}
    {page==='테스트'&&canUseDevDemo&&<DevDemo api={api} status={devDemo} onChanged={loadRewards} onNavigate={navigate}/>}
    {page==='리워드'&&user&&<Rewards key={mallKey} api={api} me={rewards} tab="mall" showTabs={false} onTab={tab=>navigate('리워드',tab)} onChanged={loadRewards}/>}
    {page==='히스토리'&&user&&<MealHistory history={history} onAdd={()=>navigate('음식 추가')} api={api} onChanged={()=>loadAccount().catch(e=>setError(e.message))} onChatEdit={chatEnabled?edit=>openCoach(edit):undefined}/>}
    {page==='마이페이지'&&user&&<>
      {accountTab!=='profile'&&<Rewards api={api} me={rewards} tab={accountTab} showTabs={false} onTab={tab=>tab==='mall'?navigate('리워드','mall'):setAccountTab(tab)} onChanged={loadRewards}/>}
    </>}
    {page==='마이페이지'&&user&&accountTab==='profile'&&<AccountInfo key={nicknameEdit?'edit':'view'} api={api} rewards={rewards} onRewardsChanged={()=>{setNicknameEdit(false);loadRewards();}} startNicknameOpen={nicknameEdit} user={user} profile={profile} onGoals={()=>navigate('목표 설정')}/>}
    {page==='마이페이지'&&user&&accountTab==='profile'&&(user.password_login_enabled ? <PasswordForm api={api} onChanged={passwordChanged}/>
      : <section className="panel"><h2>비밀번호 관리</h2><p className="muted">Google 계정의 비밀번호는 Google 계정 설정에서 변경해 주세요.</p></section>)}
    {user&&grantMeal&&!nicknameStep&&<RewardGrantPanel key={grantMeal} api={api} mealId={grantMeal} onLoaded={data=>{setFirstPending(!!data.first_meal);loadRewards();}} onNavigate={navigate} onShare={mealId=>{setGrantMeal(null);setFirstPending(false);setCommunityMeal(mealId);loadRewards();navigate('커뮤니티');}} onClose={()=>{setGrantMeal(null);loadRewards();if(firstPending){setFirstPending(false);setFirstDecorate('meal');}}}/>}
    {user&&firstDecorate&&!grantMeal&&!nicknameStep&&<FirstDecorate api={api} reason={firstDecorate} onClose={()=>setFirstDecorate(false)} onDone={()=>{setFirstDecorate(false);loadRewards();navigate('리워드','room');}}/>}
    {user&&rewards?.pending_levelup&&!grantMeal&&!firstDecorate&&!nicknameStep&&!levelSkip.includes(rewards.pending_levelup.id)&&<LevelUpDialog api={api} event={rewards.pending_levelup} equipment={rewards.equipment}
      onNavigate={navigate} onClose={()=>{setLevelSkip(ids=>[...ids,rewards.pending_levelup.id]);loadRewards();}}/>}
    {user&&nicknameStep&&<NicknameStep api={api} allowClose={nicknameStep==='relogin'} onDone={()=>{setNicknameStep(null);signupFlow.current=false;loadRewards();}}/>}
    </div>
    <footer>CaloDetect<span>영양 정보 확인과 식단 기록을 돕습니다. 의료 진단을 제공하지 않습니다.</span></footer>
  </main>
    {!authLayout&&<MobileTabBar page={page} onNavigate={navigate} onRecord={()=>setRecordSheet(true)}/>}
    {!authLayout&&<RecordSheet open={recordSheet} chatEnabled={chatEnabled} onClose={closeRecordSheet} onNavigate={navigate}/>}
    {coachAvailable&&<CoachFab hidden={coachOpen||recordSheet} onOpen={()=>openCoach()}/>}
    {coachAvailable&&<CoachSheet open={coachOpen} user={user} api={api} editTarget={coachEdit} onClose={closeCoach} onBackToChat={()=>setCoachEdit(null)}
      onLogin={()=>{setCoachOpen(false);navigate('로그인');}} onNavigate={navigate}
      onSaved={mealId=>{if(mealId)setGrantMeal(mealId);loadAccount().catch(e=>setError(e.message))}}/>}
  </div>
}
