import React, {useEffect, useLayoutEffect, useRef, useState, useId} from 'react';
import {createPortal} from 'react-dom';
import {displayFoodName, mealSummary, relativeTime} from './communityPresentation';
import './community.css';

const mealNames = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
const number = value => Number(value || 0).toLocaleString('ko-KR');
const signed = value => `${value > 0 ? '+' : ''}${number(value)}`;

// 모달의 포커스를 가두고 닫을 때 호출 버튼으로 돌려준다.
function Modal({title, children, onClose, alert=false, error=''}) {
  const ref = useRef(null), startY = useRef(null), id = useId();
  const closeRef = useRef(onClose); closeRef.current = onClose;
  useEffect(()=>{
    const previous = document.activeElement;
    const first = ref.current.querySelector('[data-initial-focus]') || ref.current.querySelector('button');
    first?.focus();
    const old = document.body.style.overflow; document.body.style.overflow = 'hidden';
    return ()=>{document.body.style.overflow=old;previous?.focus();};
  },[]);
  function keyboard(e) {
    if(e.key==='Escape'){e.stopPropagation();closeRef.current();}
    if(e.key==='Tab'){
      const nodes=[...ref.current.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]')];
      const first=nodes[0],last=nodes.at(-1);
      if(e.shiftKey && document.activeElement===first){e.preventDefault();last?.focus();}
      else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first?.focus();}
    }
  }
  return createPortal(<div className="community-backdrop" onClick={e=>{if(e.target===e.currentTarget)onClose();}}>
    <div className="community-modal" ref={ref} role={alert?'alertdialog':'dialog'} aria-modal="true" aria-labelledby={id} aria-describedby={`${id}-body`} onKeyDown={keyboard}>
      <div className="community-sheet-handle" onTouchStart={e=>{startY.current=e.touches[0].clientY;}} onTouchEnd={e=>{if(startY.current!==null&&e.changedTouches[0].clientY-startY.current>70)onClose();startY.current=null;}}/>
      <div className="community-modal-heading"><h2 id={id}>{title}</h2><button type="button" aria-label="닫기" onClick={onClose}>×</button></div>
      <div id={`${id}-body`}>{error&&<p className="community-error" role="alert">{error}</p>}{children}</div>
    </div></div>,document.body);
}

function RankingList({data}) {
  if(!data)return <p>랭킹을 불러오는 중이에요.</p>;
  return <><p className="community-eyebrow">이번 주</p><ol className="community-rank-list">{data.items.map((item,index)=><li className={item.is_me?'is-me':''} key={`${item.rank}-${index}`}><span>{item.rank<=3?['🥇','🥈','🥉'][item.rank-1]:item.rank}</span><strong>{item.nickname}{item.is_me?' · 나':''}</strong><span>{number(item.xp)} XP</span></li>)}</ol>
    {!data.items.length&&<p className="community-muted">이번 주 첫 기록으로 랭킹을 시작해 보세요.</p>}
    {!data.items.some(i=>i.is_me)&&<p className="community-my-rank">내 순위 {data.me.rank?`${data.me.rank}위`:'집계 전'} · {data.me.nickname} · {number(data.me.xp)} XP</p>}
    <small className="community-muted">{new Date(data.week_start).toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul',month:'long',day:'numeric',weekday:'short'})}부터 집계 · {data.notice}</small></>;
}

function Ranking({data,onRefresh}) {
  const [state,setState]=useState('closed'),[focus,setFocus]=useState(false);
  const timer=useRef(null), id=useId(), open=state!=='closed'||focus;
  const clear=()=>{clearTimeout(timer.current);timer.current=null;};
  useEffect(()=>clear,[]);
  useEffect(()=>{clear();},[state]);
  useEffect(()=>{if(open)onRefresh();},[open,onRefresh]);
  function hover(next,delay){if(state==='pinned'||!window.matchMedia('(hover: hover) and (pointer: fine)').matches)return;clear();timer.current=setTimeout(()=>{timer.current=null;setState(next);},delay);}
  return <section className="community-ranking" onMouseEnter={()=>hover('hovered',150)} onMouseLeave={()=>hover('closed',300)}
    onFocus={()=>setFocus(true)} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setFocus(false);}}
    onKeyDown={e=>{if(e.key==='Escape'){clear();setState('closed');setFocus(false);e.currentTarget.querySelector('button')?.blur();}}}>
    <button className="community-rank-toggle" aria-controls={id} aria-expanded={open} aria-pressed={state==='pinned'} onClick={()=>{clear();setFocus(false);setState(s=>s==='pinned'?'closed':'pinned');}}><strong>🏆 주간 랭킹</strong><span>{data?.me.rank?`내 순위 ${data.me.rank}위`:'집계 전'} · {number(data?.me.xp)} XP</span><span>{state==='pinned'?'📌':'⌄'}</span></button>
    <span className="community-sr" role="status">주간 랭킹 {open?'펼침':'접힘'}</span>
    <div id={id} hidden={!open} className="community-rank-panel"><RankingList data={data}/></div>
  </section>;
}

function Points({data}) {
  if(!data)return <p>포인트를 불러오는 중이에요.</p>;
  if(data.reward_view) {
    const reward=data.reward_view;
    return <section className="community-points"><p className="community-eyebrow">MY CALO POINT</p><h2>내 포인트</h2>
      <p className="community-balance">{number(reward.balance)} <span>P</span></p>
      <p className="community-week">리워드 몰과 같은 전체 보유 포인트예요.</p>
      <div className="community-point-rules"><small>커뮤니티 지급 기준</small>
        <div><span>식단 공유 · 하루 1회</span><strong>+{reward.share_points} P · +{reward.share_xp} XP</strong></div>
        <div><span>좋아요 받기</span><strong>+{reward.like_xp} XP</strong></div>
        <div><span>추천 받기</span><strong>+{reward.recommend_xp} XP</strong></div>
        <div><span>좋아요·추천 누르기</span><strong>+{reward.given_xp} XP</strong></div>
      </div><p className="community-muted">반응은 포인트 대신 XP를 받아요. 하루 받기 최대 {reward.received_daily_cap} XP, 누르기 최대 {reward.given_daily_cap} XP예요.</p>
      <details><summary>최근 포인트 내역</summary><ul className="community-transactions">{reward.recent.map(row=><li key={`${row.type}-${row.id}`}><span>{row.label}<small>{relativeTime(row.at)}</small></span><strong className={row.amount<0?'community-negative':''}>{signed(row.amount)} P</strong></li>)}</ul>{!reward.recent.length&&<p>아직 적립 내역이 없어요.</p>}</details></section>;
  }
  const labels={like_received:'좋아요 받기',recommend_received:'추천 받기',like_given:'좋아요 누르기',recommend_given:'추천 누르기'};
  return <section className="community-points"><p className="community-eyebrow">MY CALO POINT</p><h2>내 포인트</h2><p className="community-balance">{number(data.balance)} <span>P</span></p>
    <p className="community-week">이번 주 <strong>+{number(data.earned_this_week)} P</strong><span className="community-negative">감점 {signed(data.deducted_this_week)} P</span></p>
    <div className="community-point-rules"><small>개발 중 지급 기준</small>{Object.entries(data.rules).map(([key,value])=><div key={key}><span>{labels[key]}</span><strong>+{value} P</strong></div>)}</div>
    <details><summary>최근 포인트 내역</summary><ul className="community-transactions">{data.recent.map(row=><li key={row.id}><span>{row.reason.endsWith('_revoked')?(row.reason==='post_deleted_revoked'?'게시물 삭제로 감점':'반응 취소로 감점'):labels[row.reason]}<small>{relativeTime(row.created_at)}</small></span><strong className={row.amount<0?'community-negative':''}>{signed(row.amount)} P</strong></li>)}</ul>{!data.recent.length&&<p>아직 적립 내역이 없어요.</p>}</details></section>;
}

function Post({post,busy,onReact,onDelete}) {
  const [expanded,setExpanded]=useState(false),[full,setFull]=useState(false);
  const commentRef=useRef(null),[overflow,setOverflow]=useState(false);
  useLayoutEffect(()=>{
    const element=commentRef.current;
    if(!element||full)return;
    const measure=()=>setOverflow(element.scrollHeight>element.clientHeight+1);
    measure();const observer=new ResizeObserver(measure);observer.observe(element);
    return()=>observer.disconnect();
  },[post.comment,full]);
  const totals=post.meal.totals;
  return <article className="community-post"><div className="community-avatar" aria-hidden="true">{post.author.name.slice(0,1)}</div><div className="community-post-body">
    <div className="community-post-meta"><strong>{post.author.name}</strong>{post.is_mine&&<small className="community-me">나</small>}<time dateTime={post.created_at}>{relativeTime(post.created_at)}</time><span className="community-meal-tag">{mealNames[post.meal.meal_type]}</span></div>
    {post.comment&&<><p ref={commentRef} className={`community-comment ${full?'':'is-clamped'}`}>{post.comment}</p>{(overflow||full)&&<button className="community-text" onClick={()=>setFull(v=>!v)}>{full?'접기':'더보기'}</button>}</>}
    <div className="community-meal"><strong>{mealSummary(post.meal.items)}</strong><button className="community-text" aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>{expanded?'구성 접기':'구성 보기'}</button>
      <p className="community-nutrition"><strong>{number(totals.cal)} kcal</strong><span>탄 {number(totals.carbs)}g</span><span>단 {number(totals.protein)}g</span><span>지 {number(totals.fat)}g</span></p>
      {expanded&&<ul className="community-food-list">{post.meal.items.map((item,index)=><li key={`${item.class_id}-${index}`}><span>{displayFoodName(item.food_name)}</span><span>{item.unit} × {number(item.serving_multiplier)}</span></li>)}</ul>}</div>
    {post.show_photo===true&&post.image_urls.map(url=><img className="community-post-photo" key={url} src={url} alt="공개한 식단 사진" loading="lazy"/>)}
    <div className="community-reactions">{['like','recommend'].map(kind=><button key={kind} disabled={busy||post.is_mine} aria-busy={busy} aria-pressed={post.my_reactions.includes(kind)} aria-label={`${kind==='like'?'좋아요':'추천'} ${post.counts[kind]}개`} className={`community-reaction ${kind} ${post.my_reactions.includes(kind)?'is-active':''}`} onClick={()=>onReact(post,kind)}><span aria-hidden="true">{kind==='like'?(post.my_reactions.includes(kind)?'♥':'♡'):(post.my_reactions.includes(kind)?'★':'☆')}</span>{post.counts[kind]}</button>)}{post.is_mine&&<button className="community-delete" disabled={busy} aria-busy={busy} onClick={()=>onDelete(post)}>삭제</button>}</div>
  </div></article>;
}

export default function Community({api,onNavigate,initialMealId,onShareOpened,onRewardsChanged}) {
  const [items,setItems]=useState([]),[cursor,setCursor]=useState(null),[mine,setMine]=useState(false),[loading,setLoading]=useState(true);
  const [points,setPoints]=useState(null),[rank,setRank]=useState(null),[error,setError]=useState(''),[toast,setToast]=useState('');
  const [sheet,setSheet]=useState(null),[eligible,setEligible]=useState(null),[meal,setMeal]=useState(''),[comment,setComment]=useState(''),[photo,setPhoto]=useState(false);
  const [confirm,setConfirm]=useState(null),[busy,setBusy]=useState(false),[pending,setPending]=useState(null);
  const lock=useRef(false),request=useRef(0),rankFetched=useRef(0),alive=useRef(true);
  useEffect(()=>()=>{alive.current=false;request.current++;},[]);
  async function loadFeed(append=false) {
    const ticket=++request.current;setLoading(true);
    try {const params=new URLSearchParams({mine:String(mine),limit:'20'});if(append&&cursor)params.set('cursor',cursor);
      const data=await api(`/community/posts?${params}`);if(ticket!==request.current)return;
      setItems(old=>append?[...old,...data.items.filter(i=>!old.some(o=>o.id===i.id))]:data.items);setCursor(data.next_cursor);
    }catch(e){if(ticket===request.current)setError(e.message);}finally{if(ticket===request.current)setLoading(false);}
  }
  const refreshRank=React.useCallback(async(force=false)=>{if(!force&&Date.now()-rankFetched.current<30000)return;try{const data=await api('/rewards/ranking');if(alive.current){setRank(data);rankFetched.current=Date.now();}}catch(e){if(alive.current)setError(e.message);}},[api]);
  async function refreshStats(){const data=await api('/community/points/me');if(alive.current)setPoints({...data,balance:data.reward_view?.balance ?? data.balance});await refreshRank(true);}
  useEffect(()=>{setError('');setItems([]);setCursor(null);loadFeed();},[mine]);
  useEffect(()=>{refreshStats().catch(e=>setError(e.message));},[]);
  useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(''),5000);return()=>clearTimeout(timer);},[toast]);
  async function action(work){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{await work();}catch(e){setError(e.message);}finally{await onRewardsChanged?.();lock.current=false;setBusy(false);setPending(null);}}
  async function preview(post,kind){await action(async()=>{setPending(post.id);try{
    const path=`/community/posts/${post.id}${kind?`/reactions/${kind}/revoke-preview`:'/delete-preview'}`;
    const data=await api(path);setConfirm({post,kind,...data});
  }catch(e){if(e.status===404)await loadFeed();else throw e;}});}
  async function react(post,kind){if(post.my_reactions.includes(kind)){await preview(post,kind);return;}
    await action(async()=>{setPending(post.id);const updated=await api(`/community/posts/${post.id}/reactions/${kind}`,{});setItems(old=>old.map(p=>p.id===post.id?updated:p));await refreshStats();});}
  async function remove(){if(!confirm)return;await action(async()=>{const {post,kind}=confirm;setPending(post.id);
    const result=await api(`/community/posts/${post.id}${kind?`/reactions/${kind}`:''}`,{},'DELETE');
    setConfirm(null);setToast(`${kind?'반응을 취소했어요':'게시물을 삭제했어요'} · ${signed(result.deducted.me)} P 감점`);
    if(kind)setItems(old=>old.map(p=>p.id===post.id?result:p));else await loadFeed();await refreshStats();});}
  const shareRequest=useRef(null);
  useEffect(()=>{
    if(!initialMealId || shareRequest.current===initialMealId)return;
    shareRequest.current=initialMealId;
    openShareMeal(initialMealId);
    onShareOpened?.();
  },[initialMealId]);
  function openShare(){return openShareMeal(null);}
  async function openShareMeal(targetMealId){setError('');setSheet('share');setEligible(null);setMeal('');setPhoto(false);setComment('');try{const data=await api('/community/eligible-meals');if(alive.current){setEligible(data.items);if(targetMealId){const match=data.items.find(item=>String(item.meal_id)===String(targetMealId));if(match)setMeal(String(match.meal_id));else setError('방금 기록한 식단은 이미 공유했거나 공유할 수 없는 상태예요. 다른 식단을 선택해 주세요.');}}}catch(e){if(alive.current){setError(e.message);setSheet(null);}}}
  async function share(e){e.preventDefault();if(!selected)return;const showPhoto=photo===true&&selected.has_photo===true;await action(async()=>{await api('/community/posts',{meal_id:meal,comment,show_photo:showPhoto});setSheet(null);setToast(showPhoto?'사진과 함께 식단을 공유했어요.':'사진 없이 식단 정보만 공유했어요.');await loadFeed();await refreshStats();});}
  const selected=eligible?.find(m=>m.meal_id===meal);
  return <div className="community-page"><div className="community-heading"><div><p className="community-eyebrow">TOGETHER, A BETTER MEAL</p><h1>커뮤니티</h1><p>오늘의 한 끼를 나누고, 함께 건강해져요.</p></div><div className="community-mobile-chips"><button onClick={()=>setSheet('points')}>{number(points?.balance)} P</button><button onClick={()=>{setSheet('ranking');refreshRank();}}>이번 주 {rank?.me.rank?`${rank.me.rank}위`:'집계 전'}</button></div></div>
    {error&&<p className="community-error" role="alert">{error}</p>}{toast&&<p className="community-toast" role="status">{toast}</p>}
    <div className="community-layout"><section className="community-feed" aria-label="식단 공유 피드"><div className="community-tabs" role="group" aria-label="피드 선택"><button aria-pressed={!mine} className={!mine?'selected':''} onClick={()=>setMine(false)}>전체</button><button aria-pressed={mine} className={mine?'selected':''} onClick={()=>setMine(true)}>내 게시물</button></div>
      {items.map(post=><Post key={post.id} post={post} busy={pending===post.id||confirm?.post.id===post.id} onReact={react} onDelete={post=>preview(post,null)}/>)}
      {loading&&<p className="community-empty" role="status">식단을 불러오는 중이에요.</p>}{!loading&&!items.length&&<div className="community-empty"><span>♧</span><h2>{mine?'아직 공유한 식단이 없어요':'첫 번째 한 끼를 나눠 주세요'}</h2><p>나의 식단이 누군가에게 좋은 영감이 될 수 있어요.</p><button onClick={openShare}>식단 공유하기</button></div>}
      {!loading&&cursor&&<button className="community-more" onClick={()=>loadFeed(true)}>더 보기</button>}</section>
      <aside className="community-sidebar"><Points data={points}/><Ranking data={rank} onRefresh={refreshRank}/></aside></div>
    <button className="community-fab" aria-label="식단 공유하기" onClick={openShare}>+</button>
    {sheet==='share'&&<Modal error={error} title="나의 한 끼 공유하기" onClose={()=>{if(!busy)setSheet(null);}}>
      <ShareMealForm eligible={eligible} meal={meal} comment={comment} photo={photo} busy={busy}
        onMeal={value=>{setMeal(value);setPhoto(false);}} onComment={setComment} onPhoto={setPhoto} onSubmit={share}
        onRecord={()=>{setSheet(null);onNavigate('음식 추가');}}/>
    </Modal>}
    {(sheet==='points'||sheet==='ranking')&&<Modal error={error} title={sheet==='points'?'내 포인트':'주간 랭킹'} onClose={()=>setSheet(null)}>{sheet==='points'?<Points data={points}/>:<RankingList data={rank}/>}</Modal>}
    {confirm&&<Modal error={error} alert title={confirm.kind?'반응을 취소하면 포인트가 감점돼요':'게시물을 삭제하면 받은 포인트가 감점돼요'} onClose={()=>{if(!busy)setConfirm(null);}}>
      {confirm.me!==0?<p className="community-confirm-amount">내 포인트 <strong>{signed(confirm.me)} P</strong> <small>감점 예정</small></p>:<p>이 게시물로 받은 포인트가 없어요.</p>}
      {confirm.kind?<p>작성자 포인트 {signed(confirm.author)} P 감점 예정</p>:<><p>반응한 회원의 포인트는 그대로 유지돼요.</p><p>삭제한 게시물의 식단은 다시 공유할 수 없어요.</p></>}
      <p className="community-muted">지난주에 {confirm.kind?'누른 반응':'받은 포인트'}도 이번 주 점수에서 감점돼요. 실제 감점액은 처리 시점에 달라질 수 있어요.</p>
      <div className="community-confirm-buttons"><button data-initial-focus disabled={busy} onClick={()=>setConfirm(null)}>{confirm.kind?'취소하지 않기':'삭제하지 않기'}</button><button className="community-danger" disabled={busy} onClick={remove}>{busy?'처리 중…':confirm.kind?'감점하고 취소':'감점하고 삭제'}</button></div>
    </Modal>}
  </div>;
}

// 기록 유무와 관계없이 같은 폼을 보여 주고, 사진 동의와 식단 정보 공유를 구분한다.
export function ShareMealForm({eligible,meal,comment,photo,busy,onMeal,onComment,onPhoto,onSubmit,onRecord}) {
  const loading=eligible===null, empty=!loading&&eligible.length===0;
  const selected=eligible?.find(item=>item.meal_id===meal);
  const showPhoto=photo===true&&selected?.has_photo===true;
  const photoHint=!selected?'식단을 선택하면 사진 공개 여부를 설정할 수 있어요.'
    :!selected.has_photo?'이 식단에는 사진이 없어요. 식단 정보만 공유됩니다.'
    :showPhoto?'사진 공개: 식단 정보와 사진을 함께 공유합니다.'
    :'사진 비공개: 사진을 제외한 식단 정보만 공유합니다.';
  return <form onSubmit={onSubmit} aria-busy={loading||busy}>
    {loading&&<p role="status">공유할 식단을 불러오는 중이에요.</p>}
    {empty&&<div className="community-share-empty"><p>공유할 수 있는 식단이 없어요. 식사 기록이 없거나, 기록한 식단을 이미 공유했어요.</p><button className="community-primary" type="button" onClick={onRecord}>식단 기록하러 가기</button></div>}
    <label>공유할 식단<select required value={meal} disabled={loading||empty||busy} onChange={e=>onMeal(e.target.value)}>
      <option value="">{empty?'공유할 수 있는 식단이 없어요':'식단을 선택해 주세요'}</option>
      {eligible?.map(item=><option key={item.meal_id} value={item.meal_id}>{item.meal_date} {mealNames[item.meal_type]} · {mealSummary(item.items)}</option>)}
    </select></label>
    <label>한 끼 이야기<textarea disabled={loading||empty||busy} maxLength={300} value={comment} onChange={e=>onComment(e.target.value)} placeholder="오늘의 식사는 어땠나요?"/></label>
    <p className="community-counter">{comment.length} / 300</p>
    <label className="community-photo-check"><input type="checkbox" checked={showPhoto} disabled={busy||!selected?.has_photo} onChange={e=>onPhoto(e.target.checked)}/>식단 사진도 함께 공개합니다 (선택)</label>
    <p className="community-photo-status" role="status">{photoHint}</p>
    <p className="community-disclosure">공유하기를 누르면 이름, 식단 날짜·구분, 음식과 영양 정보, 작성한 이야기가 로그인한 회원에게 공개됩니다. 사진은 위 항목을 체크한 경우에만 공개되며, 위치 등 사진 정보는 지운 뒤 공개됩니다. 공유한 뒤 식단을 수정하면 게시물에도 바로 반영됩니다.</p>
    <button className="community-primary" disabled={busy||!selected}>{busy?'공유 중…':showPhoto?'사진과 함께 공유하기':'사진 없이 식단 공유하기'}</button>
  </form>;
}
