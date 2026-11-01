import React, {useEffect, useRef, useState} from 'react';
import PhotoInput from './PhotoInput';
import {MealScanFood, MealScanJibang} from './MealScanDesign';
import {toJpeg} from './imageUpload';
import './meal-recorder.css';

const nutrients = [['cal','칼로리','kcal'],['carbs','탄수화물','g'],['protein','단백질','g'],['fat','지방','g'],['sugar','당류','g'],['sodium','나트륨','mg']];
const types = {breakfast:'아침',lunch:'점심',dinner:'저녁',snack:'간식'};
const today = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Seoul'}).format(new Date());
const empty = () => ({key:crypto.randomUUID(),food_name:'',amount:1,amount_unit:'serving',serving_multiplier:1,nutrition:{}});
function existingRow(item){
  const basis=item.reference_serving_amount;
  const base=item.amount_unit==='serving'?(item.amount??item.serving_multiplier):basis?item.amount/basis:item.serving_multiplier;
  const amount=base*(item.consumption_ratio??1);
  return {...item,key:item.id,serving_unit:item.reference_unit,serving_amount:basis,amount,amount_unit:'serving',serving_multiplier:amount};
}
const fields = row => ({...(row.id?{id:row.id,version:row.version}:{}),class_id:row.class_id??null,
  reference_food_id:row.reference_food_id??null,food_name:row.food_name,
  amount:Number(row.amount),amount_unit:row.amount_unit,serving_multiplier:Number(row.serving_multiplier),
  detection_id:row.detection_id??null,is_llm_estimated:!!row.is_llm_estimated,
  ...(row.nutrition&&row.nutrition_override!==false?{nutrition:Object.fromEntries(nutrients.map(([k])=>[k,row.nutrition[k]==null||row.nutrition[k]===''?null:Number(row.nutrition[k])]))}:{})});

function RecorderIcon({kind}) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{kind==='plus'?<path d="M12 5v14M5 12h14"/>:kind==='trash'?<><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/></>:<><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/><path d="M20 2v4M18 4h4"/></>}</svg>;
}

export default function MealRecorder({api, meal=null, onSaved, onClose, defaultType='lunch', level, equipment}) {
  const [rows,setRows] = useState(()=>meal?.items.map(existingRow)||[]);
  const [file,setFile] = useState(null), [image,setImage] = useState(meal?.image_upload_id||meal?.image_urls?.[0]?.split('/').pop()||null);
  const [date,setDate] = useState(meal?.meal_date||today), [time,setTime] = useState(meal?.meal_time||'');
  const [type,setType] = useState(meal?.meal_type||defaultType), [status,setStatus] = useState(meal?.analysis_status||'pending');
  const [busy,setBusy] = useState(false), [error,setError] = useState(''), [notice,setNotice] = useState('');
  const [query,setQuery] = useState(''), [results,setResults] = useState(null);
  const [searchBusy,setSearchBusy] = useState(false);
  const [fallbackOpen,setFallbackOpen] = useState(false), [analyzing,setAnalyzing] = useState(false);
  const [selectedFood,setSelectedFood] = useState(null);
  const selectionTarget=useRef(null);
  const lock=useRef(false), searchSequence=useRef(0), searchInput=useRef(null);
  function addManual(){const blank=rows.find(r=>!r.food_name.trim());const row=blank?{...blank,food_name:query.trim()}:{...empty(),food_name:query.trim()};setRows(old=>blank?old.map(r=>r.key===row.key?row:r):[...old,row]);requestAnimationFrame(()=>document.getElementById(`recorder-name-${row.key}`)?.focus());}
  function change(key, patch){setRows(old=>old.map(r=>r.key===key?{...r,...patch}:r));}
  function openSearch(key=null){selectionTarget.current=key;setSelectedFood(null);setFallbackOpen(true);requestAnimationFrame(()=>searchInput.current?.focus());}
  function setAmount(row,value,unit=row.amount_unit){
    change(row.key,{amount:value,amount_unit:unit,serving_multiplier:unit==='serving'?value:1,
      nutrition:null,nutrition_override:false,is_llm_estimated:false,portionPending:row.class_id!=null||!!row.reference_food_id});
  }
  useEffect(()=>{const timer=setTimeout(()=>{rows.filter(r=>r.portionPending&&Number(r.amount)>0).forEach(portion);},250);return()=>clearTimeout(timer);},[rows]);
  async function task(work){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{await work();}catch(e){setError(e.message);}finally{lock.current=false;setBusy(false);}}
  async function upload(analyze,selected=file){
    const form=new FormData();form.append('file',await toJpeg(selected),'photo.jpg');
    const response=await api(`/meals/detect?analyze=${analyze}`,form);
    setImage(response.image_group_id);setStatus(response.analysis_status);
    return response;
  }
  function choosePhoto(next){setFile(next);setImage(null);setStatus('pending');setNotice('');setError('');selectionTarget.current=null;setSelectedFood(null);if(!meal){setRows([]);setFallbackOpen(false);}}
  function scan(selected=file){task(async()=>{
    setAnalyzing(true);
    try {
    const response=await upload(true,selected);
    const threshold=response.low_confidence_threshold??0.5;
    setRows(response.detections.length?response.detections.map(d=>({...empty(),class_id:d.class_id,food_name:d.predicted_label,
      nutrition:null,portionPending:true,detection_id:d.id,confidence:d.confidence,candidates:d.candidates||[],low:d.confidence<threshold})):[empty()]);
    setFallbackOpen(!response.detections.length);
    setNotice(response.detections.length?'음식명과 섭취량을 확인해 주세요. 인식 결과가 확실하지 않다면 ‘음식 추가’를 눌러 음식을 검색하거나 직접 입력할 수 있어요.':'🌱 음식을 찾지 못했어요. 지방이와 함께 검색하거나 직접 입력해 기록해요.');
    if(!response.detections.length)requestAnimationFrame(()=>searchInput.current?.focus());
    } catch(error) {setFallbackOpen(true);setRows(old=>old.length?old:[empty()]);setStatus('failed');throw error;}
    finally {setAnalyzing(false);}
  });}
  async function save(photoOnly=false){await task(async()=>{
    let photo=image, analysis=status;
    if(file&&!image){const uploaded=await upload(false);photo=uploaded.image_group_id;analysis=uploaded.analysis_status;}
    if(photoOnly)analysis='skipped';
    const payload={meal_type:type,meal_date:date,meal_time:time||null,image_upload_id:photo,
      analysis_status:analysis,items:photoOnly?[]:rows.map(fields),...(meal?{expected_version:meal.version}:{})};
    const saved=await api(meal?`/meals/${meal.id}`:'/meals',payload,meal?'PATCH':'POST');
    await onSaved(saved);
    if(!meal){setRows([]);setFile(null);setImage(null);setStatus('pending');setFallbackOpen(false);}
  });}
  async function search(event){event.preventDefault();const sequence=++searchSequence.current;if(!query.trim())return;
    setSearchBusy(true);setSelectedFood(null);setError('');try{const response=await api(`/foods/search?q=${encodeURIComponent(query.trim())}`);if(sequence===searchSequence.current)setResults(response.items);}
    catch(e){if(sequence===searchSequence.current){setError(e.message);setResults([]);}}finally{if(sequence===searchSequence.current)setSearchBusy(false);}}
  function select(food){
    const target=rows.find(r=>r.key===selectionTarget.current)||rows.find(r=>r.low)||rows.find(r=>!r.food_name.trim());
    const unit=food.serving_unit||'g', basis=food.serving_amount||food.serving_grams;
    const row={...empty(),...food,...(target?{key:target.key,id:target.id,version:target.version,detection_id:target.detection_id}:{}),
      amount:1,amount_unit:'serving',serving_multiplier:1,
      serving_amount:basis,serving_unit:unit,nutrition_override:false,low:false,candidates:[],portionPending:true};
    selectionTarget.current=row.key;
    setRows(old=>target?old.map(r=>r.key===target.key?row:r):[...old,row]);
    setFallbackOpen(false);setResults(null);setSelectedFood(null);setNotice('');
    requestAnimationFrame(()=>document.getElementById(`recorder-name-${row.key}`)?.scrollIntoView({block:'nearest'}));
  }
  async function portion(row){
    if(row.class_id==null&&!row.reference_food_id)return;
    try{const response=await api('/foods/portion',{class_id:row.class_id??null,reference_food_id:row.reference_food_id??null,
      amount:Number(row.amount),amount_unit:row.amount_unit,serving_multiplier:Number(row.serving_multiplier)});
      setRows(old=>old.map(r=>r.key===row.key&&r.amount===row.amount&&r.amount_unit===row.amount_unit&&r.class_id===row.class_id&&r.reference_food_id===row.reference_food_id&&!r.nutrition_override?{...r,nutrition:response.nutrition,portionPending:false}:r));
    }catch{setRows(old=>old.map(r=>r.key===row.key&&r.amount===row.amount&&r.amount_unit===row.amount_unit?{...r,portionPending:false}:r));}
  }
  const start=!meal&&!fallbackOpen&&!analyzing&&!rows.length&&!image;
  return <section className="meal-recorder" aria-label={meal?'식단 전체 수정':'식단 기록'}>
    <div className="recorder-heading"><div><h2>{meal?'식단 전체 수정':'사진으로 식단 기록'}</h2>{!meal&&<p>사진을 선택한 뒤 사진 분석하기를 눌러 주세요.</p>}</div>{onClose&&<button type="button" onClick={onClose} disabled={busy}>닫기</button>}</div>
    <div className={start?'recorder-split':undefined}>
    <fieldset disabled={busy} className={!meal&&!file&&!image?'recorder-has-guide':undefined}><legend>식사 정보</legend><div className="recorder-meta">
      <label>날짜<input type="date" required value={date} onChange={e=>setDate(e.target.value)}/></label>
      <label>식사 시간<input type="time" value={time} onChange={e=>setTime(e.target.value)}/></label>
      <label>식사 구분<select value={type} onChange={e=>setType(e.target.value)}>{Object.entries(types).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
    </div><PhotoInput file={file} busy={busy} onChange={choosePhoto}/>
      {image&&!file&&<><img className="recorder-photo" src={`/api/meals/images/${image}`} alt="식단 사진"/><button type="button" onClick={()=>setImage(null)}>사진 제거</button></>}
      {!meal&&<button type="button" className="primary recorder-scan" disabled={busy||!file} onClick={()=>scan()}>{analyzing?'사진 분석 중…':image?'다시 사진 분석하기':'사진 분석하기'}</button>}
      {!meal&&!file&&!image&&<MealScanFood/>}
      {file&&!analyzing&&<details className="recorder-options"><summary>사진 기록 옵션</summary><div><button type="button" onClick={()=>save(true)}>사진만 저장</button></div></details>}
    </fieldset>
    {start&&<div className="recorder-start"><div><strong>사진이 없나요?</strong><p>음식을 검색하거나 음식명과 양을 직접 입력해 기록할 수 있어요.</p></div><div className="recorder-start-actions"><button type="button" className="recorder-add" disabled={busy} onClick={()=>openSearch()}>음식 검색</button><button type="button" className="recorder-add" disabled={busy} onClick={()=>{setFallbackOpen(true);addManual();}}><RecorderIcon kind="plus"/>직접 입력하기</button></div><MealScanJibang level={level} equipment={equipment}/></div>}
    </div>
    {analyzing&&<p className="notice recorder-analyzing" role="status">사진 속 음식을 분석하고 있어요. 잠시만 기다려 주세요.</p>}
    {notice&&<p className="notice" role="status">{notice}</p>}
    {!fallbackOpen&&!analyzing&&(rows.length>0||meal||image)&&<button type="button" className="recorder-add" disabled={busy} onClick={()=>openSearch()}><RecorderIcon kind="plus"/>음식 추가</button>}
    {fallbackOpen&&!analyzing&&<div className="recorder-fallback">
    <form onSubmit={search} className="recorder-search"><label>음식 검색<input ref={searchInput} type="search" maxLength={120} placeholder="예: 순대국" value={query} onChange={e=>{setQuery(e.target.value);++searchSequence.current;setSearchBusy(false);setResults(null);setSelectedFood(null);}}/></label><button disabled={busy||searchBusy||!query.trim()}>{searchBusy?'검색 중…':'검색'}</button></form>
    {results&&<><p className="recorder-result-hint">음식을 더블클릭하거나 선택 후 적용해 주세요.</p><div className="recorder-results" aria-live="polite">{results.length?results.map((f,i)=><button type="button" disabled={busy} key={i} aria-pressed={selectedFood===f} onClick={()=>setSelectedFood(f)} onDoubleClick={()=>select(f)} onKeyDown={event=>{if(event.key==='Enter'){event.preventDefault();select(f);}}}><strong>{f.food_name}</strong><span>{f.unit}{(f.serving_amount||f.serving_grams)?` (${f.serving_amount||f.serving_grams}${f.serving_unit||'g'})`:''} · {f.nutrition?.cal??'—'} kcal</span><small>탄수화물 {f.nutrition?.carbs??'—'} g · 단백질 {f.nutrition?.protein??'—'} g · 지방 {f.nutrition?.fat??'—'} g</small></button>):<p>검색 결과가 없어요. 직접 입력해서 기록할 수 있어요.</p>}</div>{results.length>0&&<button type="button" className="recorder-apply" disabled={busy||!selectedFood} onClick={()=>select(selectedFood)}>선택한 음식 적용</button>}</>}
    <div className="recorder-manual-entry"><div><strong>찾는 음식이 없나요?</strong><p>음식명과 양만 입력해도 기록할 수 있어요.</p></div><button type="button" className="recorder-add" disabled={busy||rows.length>=100} onClick={addManual}><RecorderIcon kind="plus"/>직접 입력하기</button></div>
    </div>}
    {rows.map((row,index)=><fieldset key={row.key} disabled={busy} className="recorder-item"><legend className="recorder-sr-only">음식 {index+1}</legend>
      <div className="recorder-item-heading"><div><span className="recorder-item-number">{String(index+1).padStart(2,'0')}</span><strong>선택한 음식</strong></div><button type="button" className="recorder-delete" aria-label={`음식 ${index+1} 삭제`} onClick={()=>{setRows(old=>old.filter(r=>r.key!==row.key));}}><RecorderIcon kind="trash"/><span>삭제</span></button></div>
      {row.low&&<div className="notice">확실하지 않아요 · 신뢰도 {Math.round(row.confidence*100)}%
        {row.candidates.map(c=><button type="button" key={c.class_id} onClick={()=>change(row.key,{class_id:c.class_id,reference_food_id:null,food_name:c.predicted_label,low:false,nutrition:null,nutrition_override:false,portionPending:true,amount_unit:'serving',serving_multiplier:Number(row.amount),is_llm_estimated:false})}>{c.predicted_label}</button>)}
        <button type="button" onClick={()=>{setQuery(row.food_name);openSearch(row.key);}}>다른 음식이에요 · 검색</button>
      </div>}
      <div className="recorder-meta recorder-food-meta"><label>음식명<input id={`recorder-name-${row.key}`} required maxLength={120} placeholder="예: 순대국" value={row.food_name} onChange={e=>change(row.key,{food_name:e.target.value})}/></label>
      <label>섭취량<div className="recorder-amount"><button type="button" aria-label={`음식 ${index+1} 인분 줄이기`} disabled={Number(row.amount)<=.5} onClick={()=>setAmount(row,Math.max(.5,Number(row.amount)-.5),'serving')}>−</button><input aria-label="섭취량 (인분)" type="number" min="0.01" max="100" step="0.5" value={row.amount} onChange={e=>setAmount(row,e.target.value,'serving')}/><span>인분</span><button type="button" aria-label={`음식 ${index+1} 인분 늘리기`} disabled={Number(row.amount)>=100} onClick={()=>setAmount(row,Math.min(100,Number(row.amount)+.5),'serving')}>+</button></div></label></div>
      <div className="recorder-nutrition-summary" aria-live="polite">{nutrients.slice(0,4).map(([key,label,unit])=><span key={key}>{label}<strong>{row.portionPending?'…':row.nutrition?.[key]??'—'} <small>{unit}</small></strong></span>)}</div>
      <details className="recorder-nutrition-edit"><summary>영양 정보 수정{row.is_llm_estimated?' · 기존 추정값':''}</summary><div className="recorder-nutrients">{nutrients.map(([key,label,unit])=><label key={key}>{label} <span>{unit}</span><input type="number" min="0" max={key==='sodium'?1000000:100000} step="any" placeholder="미입력" aria-label={`${label} (${unit})`} value={row.nutrition?.[key]??''} onChange={e=>change(row.key,{portionPending:false,nutrition_override:true,nutrition:{...(row.nutrition||{}),[key]:e.target.value}})}/></label>)}</div></details>
    </fieldset>)}
    {error&&<div className="error" role="alert"><p>{error} 검색·직접 입력으로 계속할 수 있어요.</p>{(file||image)&&<button type="button" disabled={busy} onClick={()=>{setFile(null);setImage(null);setNotice('사진 없이 음식을 기록할 수 있어요.');}}>사진 없이 계속하기</button>}</div>}
    {(rows.length>0||meal)&&<button type="button" className="primary" disabled={busy||!date||(!rows.length&&!image&&!file)||rows.some(r=>!r.food_name.trim()||!(Number(r.amount)>0))} onClick={()=>save()}>{busy?'처리 중…':meal?'변경 내용 저장':'식단 기록하기'}</button>}
  </section>;
}
