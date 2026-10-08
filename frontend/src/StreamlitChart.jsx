import React, {useEffect, useId, useRef} from 'react';

// 인증된 화면에서 조회한 표시값만 전달한다. 쿠키와 인증 토큰은 전달하지 않는다.
export default function StreamlitChart({kind, data, height=280, title, onSelect}) {
  const id=useId(), frame=useRef(null);
  const base=new URL(import.meta.env.VITE_STREAMLIT_URL || `http://${window.location.hostname}:8502/`);
  const payload=JSON.stringify({kind,...data});
  base.searchParams.set('payload',payload);
  base.searchParams.set('chart_id',id);
  base.searchParams.set('parent_origin',window.location.origin);
  base.searchParams.set('embed','true');
  useEffect(()=>{
    function select(event){
      if(event.origin!==base.origin || event.data?.type!=='calodetect-chart-select' || event.data.chartId!==id)return;
      const item=data?.items?.find(item=>item.date===event.data.date);
      if(item)onSelect?.(item);
    }
    window.addEventListener('message',select);
    return()=>window.removeEventListener('message',select);
  },[id,payload,onSelect,base.origin]);
  return <iframe ref={frame} className="streamlit-chart" src={base.href} title={title || '식단 그래프'} height={height} referrerPolicy="no-referrer"/>;
}
