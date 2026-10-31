// 모바일(760px 이하) 전용 앱 틀: 상단바, 하단 탭바, ＋기록 바텀시트.
// 데스크톱에서는 CSS(mobile-shell.css)로 숨기고, 화면 이동은 main.jsx의 navigate를 그대로 쓴다.
import React, {useEffect, useRef} from 'react';
import {Brand} from './Visuals';
import './mobile-shell.css';

const Icon = ({children, size = 24, width = 1.8}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={width}
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);

const ICONS = {
  home: <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>,
  journal: <><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 10h18"/></>,
  community: <><circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2 21v-3a6 6 0 0 1 12 0v3M15 15a5 5 0 0 1 7 4v2"/></>,
  rewards: <path d="M4 9h16v12H4zM2 6h20v3H2zM12 6v15"/>,
  user: <><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  camera: <><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></>,
  chat: <><path d="M4 5h16v11H9l-5 4Z"/><path d="M8 9h8M8 12h5"/></>,
  logout: <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 8l-4 4 4 4M6 12h10"/></>,
};

// [탭 이름, 이동할 화면, 활성으로 볼 화면들, 아이콘]
export const MOBILE_TABS = [
  ['홈', '홈', ['홈'], 'home'],
  ['식단관리', '히스토리', ['히스토리', '식단 분석'], 'journal'],
  null, // 가운데 ＋기록 버튼 자리
  ['커뮤니티', '커뮤니티', ['커뮤니티'], 'community'],
  ['리워드', '리워드', ['리워드'], 'rewards'],
];
const RECORD_PAGES = ['음식 추가', '채팅으로 식사기록'];

// 로고는 데스크톱 사이드바와 같은 Brand를 쓰고, 누르면 소개(초기) 페이지로 이동한다.
// 오른쪽: 비로그인은 로그인 버튼, 로그인 상태는 포인트 · 로그아웃 · 내 정보 아이콘.
export function MobileTopBar({user, rewards, page, busy, onNavigate, onHomepage, onLogout}) {
  const accountActive = ['마이페이지', '목표 설정'].includes(page);
  return <div className="m-topbar">
    <Brand onClick={onHomepage}/>
    <div className="m-topbar-actions">
      {user ? <>
        {rewards && <button type="button" className="m-points" onClick={() => onNavigate('리워드')}
          aria-label={`보유 포인트 ${rewards.balance.toLocaleString()}P, 리워드몰로 이동`}>{rewards.balance.toLocaleString()}P</button>}
        <button type="button" className="m-auth" onClick={onLogout} disabled={busy}><Icon size={15} width={2}>{ICONS.logout}</Icon>로그아웃</button>
        <button type="button" className={'m-icon-button' + (accountActive ? ' is-active' : '')}
          aria-label="내 정보 & 설정" aria-current={accountActive ? 'page' : undefined}
          onClick={() => onNavigate('마이페이지')}><Icon>{ICONS.user}</Icon></button>
      </> : <button type="button" className="m-auth is-login" onClick={() => onNavigate('로그인')}>로그인</button>}
    </div>
  </div>;
}

export function MobileTabBar({page, onNavigate, onRecord}) {
  const recording = RECORD_PAGES.includes(page);
  return <nav className="m-tabbar" aria-label="하단 메뉴">
    {MOBILE_TABS.map((tab, index) => {
      if (!tab) return <button key="record" type="button" className={'m-record' + (recording ? ' is-active' : '')}
        aria-label="식사 기록하기" aria-haspopup="dialog" onClick={onRecord}><Icon size={28} width={2.2}>{ICONS.plus}</Icon></button>;
      const [label, target, pages, icon] = tab;
      const active = pages.includes(page);
      return <button key={label} type="button" className={'m-tab' + (active ? ' is-active' : '')}
        aria-current={active ? 'page' : undefined} onClick={() => onNavigate(target)}>
        <Icon>{ICONS[icon]}</Icon><span>{label}</span>
      </button>;
    })}
  </nav>;
}

// 기록 방식 선택 바텀시트. Esc·배경 터치로 닫히고, 열리면 첫 버튼에 포커스를 준다.
export function RecordSheet({open, chatEnabled, onClose, onNavigate}) {
  const firstButton = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    firstButton.current?.focus();
    const onKey = event => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = previous; };
  }, [open, onClose]);
  if (!open) return null;
  const go = target => { onClose(); onNavigate(target); };
  return <div className="m-sheet-backdrop" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="m-sheet" role="dialog" aria-modal="true" aria-labelledby="m-sheet-title">
      <span className="m-sheet-handle" aria-hidden="true"/>
      <h2 id="m-sheet-title">어떻게 기록할까요?</h2>
      <button ref={firstButton} type="button" className="m-sheet-option" onClick={() => go('음식 추가')}>
        <span className="m-sheet-icon"><Icon>{ICONS.camera}</Icon></span>
        <span><strong>사진 · 직접 기록</strong><small>사진을 찍거나 음식을 검색해서 기록해요</small></span>
      </button>
      {chatEnabled && <button type="button" className="m-sheet-option" onClick={() => go('채팅으로 식사기록')}>
        <span className="m-sheet-icon is-chat"><Icon>{ICONS.chat}</Icon></span>
        <span><strong>칼로T코치와 채팅으로</strong><small>먹은 음식을 말로 알려주면 정리해 줘요</small></span>
      </button>}
      <button type="button" className="m-sheet-cancel" onClick={onClose}>닫기</button>
    </div>
  </div>;
}
