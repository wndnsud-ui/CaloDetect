// Deterministic browser fixture. Does not call real DB, storage, or OpenAI.
import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import MealRecorder from '../src/MealRecorder';
import '../src/style.css';
import '../src/reference.css';
let saved=null;
async function api(path,body,method){
  (window.__recorderCalls ||= []).push(path);
  if(path.startsWith('/foods/search'))return {items:path.includes('missing')?[]:[{reference_food_id:'fixture',food_name:'순대국',serving_grams:500,unit:'1회 제공량',nutrition:{cal:400,carbs:20,protein:30,fat:20},nutrition_source:'TEST FIXTURE'}]};
  if(path==='/foods/estimate')throw new Error('Food LLM estimation is prohibited');
  if(path==='/foods/portion'){const ratio=body.amount_unit==='serving'?Number(body.amount):Number(body.amount)/500;const cal=body.class_id===1?280:400;return {nutrition:{cal:cal*ratio,carbs:20*ratio,protein:30*ratio,fat:20*ratio}};}
  if(path.startsWith('/meals/detect'))return {image_group_id:'photo-fixture',analysis_status:path.includes('false')?'skipped':location.search.includes('low')?'analyzed':'failed',detections:location.search.includes('low')?[{id:'detection',class_id:0,predicted_label:'첫 후보',confidence:.2,candidates:[{class_id:0,predicted_label:'첫 후보'},{class_id:1,predicted_label:'다른 후보'},{class_id:2,predicted_label:'세 번째 후보'}]}]:[]};
  if(path.startsWith('/meals')){
    saved={...body,id:'fixture-meal',version:(saved?.version||0)+1,nutrition_pending:!body.items.length,items:body.items.map((r,i)=>({...r,id:r.id||`item-${i}`,version:(r.version||0)+1,nutrition:r.nutrition||{cal:400,carbs:20,protein:30,fat:20},is_edited:method==='PATCH'}))};
    return saved;
  }
  throw new Error('Unexpected fixture request');
}
function Harness(){
  const [meal,setMeal]=useState(null),[result,setResult]=useState(null),[generation,setGeneration]=useState(0);
  return <><button onClick={()=>{setMeal(null);setResult(null);setGeneration(n=>n+1);}}>New record</button>
    <MealRecorder key={generation} api={api} meal={meal} onSaved={data=>setResult(data)}/>
    {result&&<><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}} data-testid="saved">{JSON.stringify(result)}</pre><button onClick={()=>{setMeal(result);setGeneration(n=>n+1);}}>저장한 식단 수정</button></>}
  </>;
}
createRoot(document.getElementById('root')).render(<Harness/>);
