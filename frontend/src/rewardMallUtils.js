// 리워드몰 v1.3 화면 계산 도우미(순수 함수). 가격·잔액·사유는 서버 값을 쓰고, 여기서는 표시용 변환만 한다.

// 수량 스테퍼: 1 ~ max_qty 사이로 자른다(max_qty가 없거나 1보다 작으면 1).
export function clampQty(value, maxQty) {
  const max = Math.max(1, Math.floor(Number(maxQty) || 1));
  const n = Math.floor(Number(value) || 1);
  return Math.min(max, Math.max(1, n));
}

// 쿠폰함 상태 탭(지시서 §3-3): 서버 state(active/pending/closed)와 1:1. 'all'은 전체.
export const COUPON_TABS = [['all', '전체'], ['active', '사용 가능'], ['pending', '발급 중'], ['closed', '지난 쿠폰']];
export function couponsFor(items, tab) {
  return tab === 'all' ? items : items.filter(item => item.state === tab);
}

// 쿠폰 카드 상태 칩: 발급 중(held면 운영자 확인 중), 사용 가능, 지난 쿠폰은 closed_reason별.
const CLOSED_LABEL = {used: '사용 완료', expired: '만료', canceled: '취소', failed: '발급 실패'};
export function couponChip(coupon) {
  if (coupon.state === 'pending') return coupon.status === 'held' ? '운영자 확인 중' : '발급 중';
  if (coupon.state === 'active') return '사용 가능';
  return CLOSED_LABEL[coupon.closed_reason] || '지난 쿠폰';
}

// 프로모션 슬라이더 자동 넘김: 움직임 줄이기 설정·일시정지·마우스 올림·포커스 중이면 멈춘다.
export function shouldAutoplay({reducedMotion, paused, hovering, focused, count}) {
  return !reducedMotion && !paused && !hovering && !focused && count > 1;
}
export function nextSlide(index, step, count) {
  if (!count) return 0;
  return ((index + step) % count + count) % count;
}

// 이미지 키 → 공개 경로(frontend/public/rewards/). 확장자 없는 옛 키는 products/<키>.webp. 키가 없으면 null(자리표시 그림).
export function imageUrl(key) {
  if (!key) return null;
  // 영상이 없는 상품은 이미지에 합성돼 있던 재생 안내를 제거한 버전을 사용한다.
  if (/^products\/(energy_bar|protein_bar|chicken_sandwich|energy_drink|greek_yogurt|pita_sandwich|salad_box)\/hero\.jpg$/.test(key)) {
    return `/rewards/${key.replace('hero.jpg', 'hero-no-video.png')}`;
  }
  return /\.[a-z0-9]+$/i.test(key) ? `/rewards/${key}` : `/rewards/products/${key}.webp`;
}

// 포인트 내역의 정산 대상일 표기: "(10.20)"
export function targetSuffix(targetDate) {
  if (!targetDate) return '';
  const [, m, d] = targetDate.split('-');
  return ` (${m}.${d})`;
}

// 교환 신청 후 다음 교환 가능 달(월 1회 사용 시): "11월"
export function nextMonthLabel(month) {
  return `${(Number(month) % 12) + 1}월`;
}
