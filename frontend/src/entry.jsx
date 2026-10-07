import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import App from './main';
import Landing from './Landing';
const pageKey='calodetect-page';
const pages=['홈','음식 추가','목표 설정','식사 추천','히스토리','식단 분석','마이페이지','로그인','회원가입'];
function storedPage(){try {if(new URLSearchParams(window.location.hash.slice(1)).has('password_reset'))return '로그인';const params=new URLSearchParams(window.location.search);if(['social_signup','social_error','social_success'].some(key=>params.has(key))){sessionStorage.setItem(pageKey,'로그인');if(params.has('social_success'))window.history.replaceState({},'',window.location.pathname);return '로그인';}const value=sessionStorage.getItem(pageKey);return pages.includes(value)?value:null;} catch {return null;}}
function Entry(){
  const[page,setPage]=useState(storedPage);
  function rememberPage(value){try {if(value===null)sessionStorage.removeItem(pageKey);else sessionStorage.setItem(pageKey,value);} catch {}}
  function open(value){rememberPage(value);setPage(value);}
  return page===null?<Landing onOpen={open}/>:<App initialPage={page} onPageChange={rememberPage} onHomepage={()=>open(null)}/>;
}
createRoot(document.getElementById('root')).render(<Entry/>);
