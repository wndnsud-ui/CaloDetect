// React 브라우저 진입점. 소개 화면과 회원 앱을 선택하고 현재 탭의 화면을 sessionStorage에 기억한다.
// 비밀번호 재설정·소셜 로그인 반환 URL은 로그인 흐름으로 연결한다.
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import App from './main';
import Landing from './Landing';
// 현재 탭의 선택 화면만 기억한다. 회원 인증 데이터나 비밀번호를 저장하지 않는다.
const pageKey='calodetect-page';
const pages=['홈','음식 추가','목표 설정','식사 추천','히스토리','식단 분석','마이페이지','로그인','회원가입'];
// 재설정·소셜 반환 URL을 우선 처리하고 허용된 화면 이름만 sessionStorage에서 복원한다.
function storedPage(){try {if(new URLSearchParams(window.location.hash.slice(1)).has('password_reset'))return '로그인';const params=new URLSearchParams(window.location.search);if(['social_signup','social_error','social_success'].some(key=>params.has(key))){sessionStorage.setItem(pageKey,'로그인');if(params.has('social_success'))window.history.replaceState({},'',window.location.pathname);return '로그인';}const value=sessionStorage.getItem(pageKey);return pages.includes(value)?value:null;} catch {return null;}}
// 소개/회원 화면을 선택하며 탭 안에서 마지막 선택 화면을 기억한다.
function Entry(){
  const[page,setPage]=useState(storedPage);
  // 현재 화면을 sessionStorage에 기록한다. 브라우저 저장소 제한 시에도 화면 사용은 계속된다.
  function rememberPage(value){try {if(value===null)sessionStorage.removeItem(pageKey);else sessionStorage.setItem(pageKey,value);} catch {}}
  // 화면 선택을 저장하고 React 상태를 함께 갱신한다.
  function open(value){rememberPage(value);setPage(value);}
  return page===null?<Landing onOpen={open}/>:<App initialPage={page} onPageChange={rememberPage} onHomepage={()=>open(null)}/>;
}
// index.html의 root 요소에 앱을 한 번 마운트한다.
createRoot(document.getElementById('root')).render(<Entry/>);
