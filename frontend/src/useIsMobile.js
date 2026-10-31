// 모바일 화면 여부를 알려주는 훅. 모바일 기준 폭은 MOBILE_QUERY 한 곳에서만 관리한다.
// CSS의 @media(max-width:760px)와 반드시 같은 값을 쓴다 (mobile-shell.css, mobile-home.css).
import {useEffect, useState} from 'react';

export const MOBILE_QUERY = '(max-width: 760px)';

const matches = () => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(MOBILE_QUERY).matches;

export default function useIsMobile() {
  const [mobile, setMobile] = useState(matches);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined;
    const query = window.matchMedia(MOBILE_QUERY);
    const update = () => setMobile(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  return mobile;
}
