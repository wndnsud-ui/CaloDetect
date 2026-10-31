// 소개 페이지의 주요 기능 소개. 메뉴 구성(식단 기록·오늘 뭐먹지?·식단 관리·커뮤니티·리워드몰)대로 카드를 나누고, 누르면 해당 화면으로 연결한다.
// 카드 안의 메뉴·게시물·포인트는 화면 예시다. 리워드 가격은 포인트 정책(기획안 부록 A) 범위를 따른다.
import React from 'react';
import './features.css';

const IMG = '/images/features/';
const menus = [
  {tag: '든든한 한식', name: '닭가슴살 비빔밥', kcal: '520 kcal', img: 'menu-chicken-bibimbap.jpg'},
  {tag: '단백질 가득', name: '고등어구이 정식', kcal: '610 kcal', img: 'menu-mackerel.jpg'},
  {tag: '따뜻한 한 끼', name: '순두부찌개 정식', kcal: '560 kcal', img: 'menu-sundubu.jpg'},
];
const posts = [
  {user: '하루한끼', time: '2시간 전', img: 'post-dosirak.jpg', alt: '잡곡밥과 고등어구이 도시락', text: '오늘 점심은 직접 싼 도시락! 잡곡밥에 고등어까지 챙겼어요 :)', likes: 124, comments: 28},
  {user: '건강지향이', time: '5시간 전', img: 'post-bulgogi.jpg', alt: '불고기 정식', text: '저녁은 불고기 정식으로 든든하게 마무리했어요', likes: 86, comments: 12},
];
const rewards = [
  {name: '지방이 꾸미기', points: '3P부터', img: 'jibangi-front.png', fit: 'contain'},
  {name: '프로틴바', points: '200P', img: 'reward-bar.jpg'},
  {name: '단백질 쉐이크', points: '400P', img: 'reward-shake.jpg'},
  {name: '식단 피드백 코칭', points: '1,500P', img: 'jibangi-cheer.png', fit: 'contain'},
];

const Icon = ({name, ...rest}) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
  {name === 'camera' && <><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></>}
  {name === 'chat' && <><path d="M4 5h16v11H9l-5 4z"/><path d="M9 10h.01M12 10h.01M15 10h.01"/></>}
  {name === 'meal' && <path d="M7 3v8M5 3v4a2 2 0 0 0 4 0V3M7 11v10M16 3c-2 1-3 4-3 7h3v11"/>}
  {name === 'chart' && <path d="M6 20v-6M12 20V8M18 20V4" strokeWidth="2.4"/>}
  {name === 'calendar' && <><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/></>}
  {name === 'people' && <><circle cx="9" cy="8" r="3.5"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14c2 .8 3 3 3 6"/></>}
  {name === 'gift' && <><rect x="4" y="9" width="16" height="11" rx="1"/><path d="M3 9h18M12 9v11M12 9c-2-4-6-4-6-1s6 1 6 1zM12 9c2-4 6-4 6-1s-6 1-6 1z"/></>}
  {name === 'arrow' && <path d="M5 12h14M13 6l6 6-6 6" strokeWidth="2.2"/>}
  {name === 'heart' && <path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z" fill="currentColor" stroke="none"/>}
</svg>;

function CardHead({icon, title, onGo, goLabel}) {
  return <div className="fx-head">
    <span className="fx-icon"><Icon name={icon}/></span>
    <h3>{title}</h3>
    {onGo && <button type="button" className="fx-go" aria-label={goLabel} onClick={onGo}><Icon name="arrow"/></button>}
  </div>;
}

export default function FeatureSection({onOpen}) {
  return <section className="landing-section fx" id="features" aria-labelledby="features-title">
    <header className="fx-top">
      <div>
        <p className="fx-kicker">매일 한 끼, 더 건강한 나로</p>
        <h2 id="features-title">CaloDetect가 함께합니다.</h2>
        <p className="fx-sub">기록하고, 분석하고, 추천받고, 함께하고, 보상받는 건강한 식습관 여정</p>
      </div>
      <div className="fx-top-art" aria-hidden="true">
        <p className="fx-hand">작은 기록이<br/>건강한 변화를 만듭니다.</p>
        <img src={`${IMG}jibangi-love.png`} alt="" width="115" height="133"/>
      </div>
    </header>

    <div className="fx-row fx-row-3">
      <article className="fx-card fx-record">
        <CardHead icon="camera" title="식단 기록" goLabel="식단 기록 바로가기" onGo={() => onOpen('음식 추가')}/>
        <div className="fx-body">
          <div className="fx-copy"><h4>사진 한 장부터 대화까지, 간편하게 식단 기록</h4><p>사진으로 바로 기록하거나, 칼로티 코치에게 먹은 내용을 이야기해 간편하게 남겨보세요.</p></div>
          <img className="fx-scan" src={`${IMG}scan.jpg`} alt="비빔밥을 찍어 칼로리를 분석하는 앱 화면" loading="lazy" width="900" height="675"/>
        </div>
        <div className="fx-chips">
          <button type="button" onClick={() => onOpen('음식 추가')}><Icon name="camera"/>사진 &amp; 직접 기록</button>
          <button type="button" className="is-coach" onClick={() => onOpen('채팅으로 식사기록')}><Icon name="chat"/>칼로티 코치</button>
        </div>
      </article>

      <article className="fx-card fx-menu">
        <CardHead icon="meal" title="메뉴 추천 받기" goLabel="오늘 뭐먹지? 바로가기" onGo={() => onOpen('식사 추천')}/>
        <div className="fx-body">
          <div className="fx-copy"><h4>지금 내 상태에 맞는 오늘의 메뉴 추천</h4><p>목표와 식사 기록을 바탕으로 지금 먹기 좋은 메뉴를 추천해드려요.</p></div>
          <div className="fx-menu-art" aria-hidden="true"><p className="fx-hand">지금 나에게<br/>이런 메뉴가 좋아요!</p><img src={`${IMG}jibangi-salad.png`} alt="" width="184" height="112"/></div>
        </div>
        <ul className="fx-menus">{menus.map(m => <li key={m.name}><button type="button" onClick={() => onOpen('식사 추천')}>
          <img src={IMG + m.img} alt={m.name} loading="lazy"/><span>{m.tag}</span><strong>{m.name}</strong><b>{m.kcal}</b>
        </button></li>)}</ul>
        <div className="fx-chips">
          <button type="button" onClick={() => onOpen('식사 추천')}><Icon name="meal"/>오늘 뭐먹지?</button>
        </div>
      </article>

      <article className="fx-card fx-manage">
        <CardHead icon="chart" title="식단 관리"/>
        <div className="fx-body">
          <div className="fx-copy"><h4>기록을 모아보고 영양까지 한눈에 관리</h4><p>지난 식사 기록과 영양 분석 리포트를 함께 확인하며 식습관 변화를 관리해보세요.</p></div>
          <div className="fx-phone" aria-hidden="true"><div className="fx-phone-screen">
            <strong>오늘의 영양 상태</strong>
            <div className="fx-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="48" stroke="#E8EEF5"/><circle cx="60" cy="60" r="48" stroke="#2F8FD6" strokeDasharray="210 302" transform="rotate(-90 60 60)"/><circle cx="60" cy="60" r="48" stroke="#F07A4A" strokeDasharray="60 302" strokeDashoffset="-218" transform="rotate(-90 60 60)"/></svg><span><b>1,620</b>kcal</span></div>
            {[['탄수화물', 52, '#3FA36B'], ['단백질', 28, '#F07A4A'], ['지방', 20, '#D6455A']].map(([label, value, color]) => <div className="fx-bar" key={label}>
              <span><span>{label}</span><span>{value}%</span></span><i><i style={{width: `${value}%`, background: color}}/></i></div>)}
          </div></div>
        </div>
        <div className="fx-chips">
          <button type="button" onClick={() => onOpen('히스토리')}><Icon name="calendar"/>나의 기록</button>
          <button type="button" onClick={() => onOpen('식단 분석')}><Icon name="chart"/>영양 분석 리포트</button>
        </div>
      </article>
    </div>

    <div className="fx-row fx-row-2">
      <article className="fx-card fx-community">
        <div className="fx-side">
          <CardHead icon="people" title="커뮤니티"/>
          <h4>함께 기록하고 <br/>식단 경험을 나눠요</h4>
          <p>다른 사용자와 식단을 공유하고 건강한 습관을 서로 응원해보세요.</p>
          <button type="button" className="fx-cta" onClick={() => onOpen('커뮤니티')}>커뮤니티 둘러보기</button>
        </div>
        <div className="fx-posts" aria-hidden="true">{posts.map(p => <div className="fx-post" key={p.user}>
          <div className="fx-post-user"><span/><div><strong>{p.user}</strong><small>{p.time}</small></div></div>
          <img src={IMG + p.img} alt={p.alt} loading="lazy"/>
          <p>{p.text}</p>
          <div className="fx-post-meta"><span className="is-like"><Icon name="heart"/>{p.likes}</span><span><Icon name="chat"/>{p.comments}</span></div>
        </div>)}</div>
      </article>

      <article className="fx-card fx-reward">
        <div className="fx-side">
          <CardHead icon="gift" title="리워드몰"/>
          <h4>꾸준히 쌓은 포인트로 <br/>나를 위한 리워드 받기</h4>
          <p>식단 기록으로 포인트를 모아 지방이를 꾸미고, 다양한 상품과 코칭 이용권으로 교환해보세요.</p>
          <button type="button" className="fx-cta" onClick={() => onOpen('리워드')}>리워드몰 바로가기</button>
        </div>
        <div className="fx-reward-me" aria-hidden="true">
          <img src={`${IMG}jibangi-lv5.png`} alt="" width="196" height="329"/>
          <div><span>보유 포인트</span><strong>1,087 <em>P</em></strong></div>
        </div>
        <ul className="fx-rewards">{rewards.map(r => <li key={r.name}>
          <img src={IMG + r.img} alt="" className={r.fit === 'contain' ? 'is-contain' : ''} loading="lazy"/><span>{r.name}</span><strong>{r.points}</strong>
        </li>)}</ul>
      </article>
    </div>
  </section>;
}
