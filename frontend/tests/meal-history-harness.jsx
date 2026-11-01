// Read/write fixture stays in memory and never accesses the shared database.
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import MealHistory from '../src/MealHistory';
import '../src/style.css';
import '../src/reference.css';
let records=[{id:'meal-1',meal_date:'2026-11-01',meal_type:'lunch',version:1,items:[
  {id:'rice',food_name:'쌀밥',class_id:0,version:1,serving_multiplier:1,consumption_ratio:0,effective_multiplier:0,nutrition:{cal:0},chat_editable:true},
  {id:'soup',food_name:'추어탕',class_id:1,version:1,serving_multiplier:1,consumption_ratio:.5,effective_multiplier:.5,nutrition:{cal:150},chat_editable:true}]}];
async function api(path,body,method){
  (window.__historyCalls ||= []).push({path,body,method});
  if(location.search.includes('failure'))throw Object.assign(new Error('fixture unavailable'),{status:503});
  const index=records.findIndex(m=>path===`/meals/${m.id}`);
  if(index<0||method!=='PATCH'||Object.keys(body).some(k=>!['meal_type','expected_version'].includes(k)))throw new Error('Only metadata PATCH expected');
  if(body.expected_version!==records[index].version)throw Object.assign(new Error('fixture conflict'),{status:409});
  records=records.map((m,i)=>i===index?{...m,meal_type:body.meal_type,version:m.version+1}:m);
  return structuredClone(records[index]);
}
function Harness(){
  const [history,setHistory]=useState(structuredClone(records));
  return <><MealHistory history={history} api={api} onChanged={()=>setHistory(structuredClone(records))}/><pre data-testid="history-snapshot" style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(history)}</pre></>;
}
createRoot(document.getElementById('root')).render(<Harness/>);
