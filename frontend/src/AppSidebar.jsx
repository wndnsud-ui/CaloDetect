import React from 'react';
import {Brand, MenuIcon} from './Visuals';
import './app-sidebar.css';

const Chevron = () => <svg className="sidebar-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>;

export default function AppSidebar({user, rewards, page, menus, accountPages, canUseDevDemo, onNavigate, onHomepage}) {
  const balance = rewards?.balance == null ? '—' : rewards.balance.toLocaleString();
  function menu([target, label, pages]) {
    const active = pages.includes(page);
    return <button type="button" key={target} className={`sidebar-menu-item${active ? ' active' : ''}${target === '리워드' ? ' sidebar-reward' : ''}`} aria-current={active ? 'page' : undefined} onClick={() => onNavigate(target)}>
      <MenuIcon page={target}/><strong>{label}{target === '리워드' && <small>포인트로 건강한 일상을</small>}</strong>
      {target === '식사 추천' && <em>맞춤</em>}
      {target === '리워드' && user ? <b className="sidebar-menu-balance">{balance}P</b> : <Chevron/>}
    </button>;
  }
  return <aside className="app-sidebar">
    <div className="sidebar-brand"><Brand onClick={onHomepage}/><p>식사 기록에서<br/>더 좋은 선택까지.</p></div>
    <nav aria-label="웹앱 메뉴">
      <p className="sidebar-group-title">메인 메뉴</p>
      {menus.slice(0, 4).map(menu)}
      <p className="sidebar-group-title">커뮤니티 & 리워드</p>
      {menus.slice(4).map(menu)}
    </nav>
    <div className="sidebar-utilities">
      <button type="button" className={accountPages.includes(page) ? 'active' : ''} onClick={() => onNavigate(user ? '마이페이지' : '로그인')}><MenuIcon page="마이페이지"/><strong>{user ? '내 정보 & 설정' : '로그인 / 회원가입'}</strong><Chevron/></button>
      {user?.role === 'admin' && <button type="button" onClick={() => onNavigate('관리자')}>관리자</button>}
      {canUseDevDemo && <button type="button" onClick={() => onNavigate('테스트')}>테스트 더미 설정</button>}
    </div>
    <div className="sidebar-closing" aria-hidden="true"><p>오늘도<br/>건강한 선택,<br/><b>CaloDetect</b></p></div>
    <button type="button" className="sidebar-homepage" onClick={onHomepage}>홈페이지 ↗</button>
  </aside>;
}
