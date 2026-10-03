import React, {useEffect, useState} from 'react';
import { readApiResponse } from './apiResponse';

export default function LandingAccount({onOpen}) {
  const [session,setSession]=useState({loading:true,user:null,error:false});
  useEffect(()=>{
    let active=true, latest=0;
    async function refresh(){
      const request=++latest;
      try {
        const response=await fetch('/api/users/me',{credentials:'include',cache:'no-store'});
        if(response.status===401){if(active&&request===latest)setSession({loading:false,user:null,error:false});return;}
        if(!response.ok)throw new Error('session');
        const data=await readApiResponse(response);
        if(active&&request===latest)setSession({loading:false,user:data.user,error:false});
      } catch {if(active&&request===latest)setSession(current=>({...current,loading:false,error:true}));}
    }
    refresh();window.addEventListener('focus',refresh);
    return()=>{active=false;window.removeEventListener('focus',refresh);};
  },[]);
  if(session.loading)return <div className="header-actions"><span role="status">로그인 확인 중…</span></div>;
  return <div className="header-actions landing-account">
    {session.user?<><span className="welcome-message">{session.user.name}님 환영합니다</span><button className="primary" onClick={()=>onOpen('마이페이지')}>내 계정</button></>:
      session.error?<><span role="status">로그인 상태 확인이 필요합니다.</span><button className="outline" onClick={()=>onOpen('로그인')}>계정 확인</button></>:
      <><button className="outline" onClick={()=>onOpen('로그인')}>로그인</button><button className="primary" onClick={()=>onOpen('회원가입')}>회원가입</button></>}
  </div>;
}
