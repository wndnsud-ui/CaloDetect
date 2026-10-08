// 소개 페이지의 계정 진입 영역. 현재 세션을 조회해 회원 환영/계정 버튼 또는 로그인·가입 진입 버튼을 표시한다.
import React, {useEffect, useState} from 'react';
import { readApiResponse } from './apiResponse';

// 소개 페이지의 계정 진입 영역. 현재 세션을 조회해 회원 환영/계정 버튼 또는 로그인·가입 진입 버튼을 표시한다.
export default function LandingAccount({onOpen}) {
  const [session,setSession]=useState({loading:true,user:null,error:false});
  // 의존값 변경/마운트에 맞춰 외부 데이터 또는 브라우저 자원을 동기화한다. 반환하는 정리 함수는 이전 작업/자원을 해제한다.
  useEffect(()=>{
    let active=true, latest=0;
    // 세션을 다시 조회해 최신 요청의 회원 상태만 반영한다. 401은 비회원, 다른 실패는 조회 오류로 구분한다.
    async function refresh(){
      // focus 재조회가 겹치면 가장 최근 요청 결과만 반영해 로그인 상태가 오래된 응답으로 되돌아가지 않게 한다.
      const request=++latest;
      try {
        const response=await fetch('/api/users/me',{credentials:'include',cache:'no-store'});
        if(response.status===401){if(active&&request===latest)setSession({loading:false,user:null,error:false});return;}
        if(!response.ok)throw new Error('session');
        const data=await readApiResponse(response);
        if(active&&request===latest)setSession({loading:false,user:data.user,error:false});
      } catch {if(active&&request===latest)setSession(current=>({...current,loading:false,error:true}));}
    }
    // 다른 화면/탭에서 로그인한 뒤 소개 화면으로 돌아오는 경우 창 focus에서 세션을 다시 확인한다.
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
