"""React가 전달한 표시용 영양값을 ECharts로 렌더링한다. DB/인증에는 접근하지 않는다."""
import json
import math
import streamlit as st
import streamlit.components.v1 as components
from streamlit_echarts import st_echarts

st.set_page_config(page_title='CaloDetect 그래프', layout='wide', initial_sidebar_state='collapsed')
st.html('''<style>
header,[data-testid="stToolbar"],footer{display:none!important}
.stMainBlockContainer{padding:0!important;max-width:none!important}
[data-testid="stVerticalBlock"]{gap:0!important}
</style>''')

def number(value):
    result=float(value or 0)
    if not math.isfinite(result) or result<0:
        raise ValueError('Invalid value')
    return result

def options(data):
    kind=data['kind']
    base={'animation':False,'aria':{'enabled':True},'textStyle':{'fontFamily':'sans-serif','color':'#385f50'},'tooltip':{'trigger':'item'}}
    if kind=='bars':
        items=data['items']
        if len(items)>31: raise ValueError('Too many days')
        values=[None if item.get('value') is None else number(item['value']) for item in items]
        target=number(data.get('target'))
        maximum=max(1,target,*[v or 0 for v in values])
        series={'type':'bar','data':values,'barMaxWidth':18 if data.get('monthly') else 64,
                'showBackground':True,'backgroundStyle':{'color':'#edf3eb','borderRadius':4},
                'itemStyle':{'color':'#268461','borderRadius':[4,4,0,0]},
                'label':{'show':True,'position':'top','fontSize':10}}
        if target:
            series['markLine']={'symbol':'none','label':{'show':False},'lineStyle':{'color':'#956b25','type':'dashed'},'data':[{'yAxis':target}]}
        base.update({'tooltip':{'trigger':'axis'},'grid':{'left':42,'right':12,'top':28,'bottom':32},
                     'xAxis':{'type':'category','data':[item['label'] for item in items],'axisLabel':{'interval':0,'fontSize':9},'axisTick':{'show':False}},
                     'yAxis':{'type':'value','max':maximum,'axisLabel':{'fontSize':10},'splitLine':{'lineStyle':{'color':'#edf3eb'}}},'series':[series]})
    elif kind=='ring':
        value=number(data.get('value')); target=number(data.get('target'))
        fraction=min(1,value/target) if target else 0
        base.update({'series':[{'type':'pie','radius':['66%','74%'],'center':['50%','45%'],'silent':True,'label':{'show':False},
                     'data':[{'value':fraction,'itemStyle':{'color':'#268461'}},{'value':1-fraction,'itemStyle':{'color':'#e6eeea'}}]}],
                     'graphic':[{'type':'text','left':'center','top':'34%','style':{'text':f'{value:,.0f}','fontSize':24,'fontWeight':'bold','fill':'#193c32'}},
                                {'type':'text','left':'center','top':'51%','style':{'text':f'/ {target:g} kcal' if target else '목표 설정 전','fontSize':11,'fill':'#788b83'}},
                                {'type':'text','left':'center','top':'88%','style':{'text':f'{fraction*100:.0f}%' if target else '—','fontSize':13,'fill':'#268461'}}]})
    elif kind=='macros':
        values=[number(data.get(k))*factor for k,factor in [('carbs',4),('protein',4),('fat',9)]]
        total=sum(values)
        base.update({'grid':{'left':0,'right':0,'top':0,'bottom':0},'xAxis':{'type':'value','max':total or 1,'show':False},
                     'yAxis':{'type':'category','data':['탄단지'],'show':False},
                     'series':[{'name':name,'type':'bar','stack':'macro','data':[value],'barWidth':30,'itemStyle':{'color':color},
                                'label':{'show':value>0,'position':'inside','formatter':f'{value/total*100:.0f}%' if total else ''}}
                               for name,value,color in zip(['탄수화물','단백질','지방'],values,['#79af81','#e5b76f','#63b6ae'])]})
    else: raise ValueError('Unknown chart')
    return base

try:
    raw=st.query_params.get('payload','{}')
    if len(raw)>12000: raise ValueError('Payload too large')
    data=json.loads(raw)
    spec=options(data)
    events={'click':'function(params){return params.dataIndex;}'} if data['kind']=='bars' and data.get('monthly') else {}
    selection=st_echarts(spec,height='250px' if data['kind']=='bars' else '180px' if data['kind']=='ring' else '46px',events=events,key='chart')
    if events and isinstance(selection,int) and 0<=selection<len(data['items']):
        origin=st.query_params.get('parent_origin','')
        if origin in ('http://localhost:5174','http://127.0.0.1:5174'):
            message={'type':'calodetect-chart-select','chartId':st.query_params.get('chart_id'),'date':data['items'][selection].get('date')}
            # 정적 스크립트에 JSON만 삽입한다. 사용자 문자열의 HTML 종료 태그를 이스케이프한다.
            encoded=json.dumps(message).replace('<','\\u003c')
            components.html(f'<script>window.parent.parent.postMessage({encoded},{json.dumps(origin)});</script>',height=0)
except (ValueError,TypeError,KeyError):
    st.error('그래프 데이터를 확인해 주세요.')
