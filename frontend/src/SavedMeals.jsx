// 아침·점심·저녁·간식별 저장된 식단과 인증된 이미지 URL을 표시하는 공통 카드.
// 사진 없는 직접 기록과 미기록을 구분하고 식단 추가는 전달받은 콜백으로 처리한다.
import React, {useState} from 'react';

// 아침·점심·저녁·간식별 저장된 식단과 인증된 이미지 URL을 표시하는 공통 카드.
function SavedPhoto({url, name}) {
  const [failed,setFailed]=useState(false);
  return failed ? <div className="saved-photo-empty">사진을 불러올 수 없습니다</div> : <img className="saved-meal-photo" src={url} alt={`${name} 저장한 식단 사진`} onError={()=>setFailed(true)}/>;
}

// 사진 삭제 확인 문구. 서버는 사진 파일·이 식단을 올린 게시물을 지우고 기록 포인트·XP를 회수한다.
export const PHOTO_DELETE_CONFIRM = '사진을 삭제할까요?\n식단 기록은 남지만 이 끼니로 받은 포인트·XP는 회수되고, 커뮤니티에 올린 글도 함께 삭제돼요.';

// 식단 전체 삭제. 서버는 사진·게시물을 지우고 이 끼니로 받은 포인트·XP(조건이 깨진 미션·3끼 보너스 포함)를 회수한다.
export const MEAL_DELETE_CONFIRM = '이 식단을 삭제할까요?\n삭제하면 되돌릴 수 없고, 이 끼니로 받은 포인트·XP는 회수되며 커뮤니티에 올린 글과 사진도 함께 삭제돼요.';
export const deleteMeal = (api, meal) => api(`/meals/${meal.id}?expected_version=${meal.version}`, {}, 'DELETE');

// 식단 사진 삭제 요청. 음식이 없는 사진만 기록은 사진을 지우면 빈 기록이 되므로 호출하지 않는다.
export const deleteMealPhoto = (api, meal) => api(`/meals/${meal.id}`, {image_upload_id: null, expected_version: meal.version}, 'PATCH');

// 아침·점심·저녁·간식별 저장된 식단과 인증된 이미지 URL을 표시하는 공통 카드.
export default function SavedMeals({meals=[],onNavigate,onAddMeal,title='오늘의 식단',onDeletePhoto}) {
  const Card = onNavigate ? 'button' : 'div';
  const [deleting,setDeleting]=useState(null),[photoError,setPhotoError]=useState('');
  async function deletePhoto(meal){
    if(deleting||!window.confirm(PHOTO_DELETE_CONFIRM))return;
    setDeleting(meal.id);setPhotoError('');
    try{await onDeletePhoto(meal);}catch(e){setPhotoError(e.message);}finally{setDeleting(null);}
  }
  return <section className="panel today-meals"><div className="section-heading"><h2>{title}</h2>{onNavigate&&<button className="text-button" onClick={()=>onNavigate('히스토리')}>전체 기록 보기 →</button>}</div>
    {photoError&&<p className="error" role="alert">사진을 삭제하지 못했어요. {photoError}</p>}
    <div className="saved-meal-grid">{[['breakfast','아침'],['lunch','점심'],['dinner','저녁'],['snack','간식']].map(([key,label])=>{
      const records=meals.filter(meal=>meal.meal_type===key);
      return <section key={key} className="saved-meal-slot"><h3><span className="meal-time-icon" aria-hidden="true">{{breakfast:'🌅',lunch:'☀️',dinner:'🌙',snack:'🍎'}[key]}</span>{label}</h3>{records.length?records.map(meal=>{
        const name=meal.items.map(item=>item.food_name).join(', ');
        const calories=Math.round(meal.items.reduce((sum,item)=>sum+item.nutrition.cal,0)*100)/100;
        const removable=onDeletePhoto&&meal.image_urls?.length>0&&meal.items.length>0;
        return <div key={meal.id} className="saved-meal-item"><Card className="saved-meal-card" onClick={onNavigate?()=>onNavigate('히스토리'):undefined}>
          {meal.image_urls?.length?<div className="saved-photo-list">{meal.image_urls.map(url=><SavedPhoto key={url} url={url} name={name}/>)}</div>:<div className="saved-photo-empty">✓<span>직접 기록한 식단</span></div>}
          <span className="saved-meal-status">✓ {meal.image_urls?.length?'사진 · 식단 저장 완료':'식단 저장 완료'}</span><strong>{name}</strong><span>{calories.toLocaleString()} kcal</span>
        </Card>{removable&&<button type="button" className="saved-photo-delete" disabled={deleting===meal.id} aria-label={`${name} 사진 삭제`} onClick={()=>deletePhoto(meal)}>{deleting===meal.id?'삭제 중…':'사진 삭제'}</button>}</div>;
      }):onNavigate?<button className="saved-meal-add" aria-label={`${label} 식사 기록하기`} onClick={()=>onAddMeal?onAddMeal(key):onNavigate('음식 추가')}><span>＋</span>식사 기록하기</button>:<div className="saved-photo-empty">미기록</div>}</section>;
    })}</div></section>;
}
