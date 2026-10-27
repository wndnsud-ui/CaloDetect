import {test} from 'node:test';
import assert from 'node:assert/strict';
import {clampQty, couponsFor, couponChip, COUPON_TABS, shouldAutoplay, nextSlide, targetSuffix, nextMonthLabel, imageUrl, productGallery} from './rewardMallUtils.js';

test('이미지 키는 public/rewards 경로로 바뀐다', () => {
  assert.equal(imageUrl('products/pita_sandwich/hero.jpg'), '/rewards/products/pita_sandwich/hero-hd.png?v=20261027-hd');
  assert.equal(imageUrl('collab/lineup_bristick15.jpg'), '/rewards/products/bristick15/hero-hd.png?v=20261027-hd');
  assert.equal(imageUrl('pita/hero'), '/rewards/products/pita/hero.webp?v=20261027-hd');
  assert.equal(imageUrl(null), null);
});

test('고해상도 갤러리는 저해상도 썸네일을 노출하지 않는다', () => {
  assert.deepEqual(productGallery({id:'energy_bar',hero:'products/energy_bar/hero.jpg',content:{thumbs:['products/energy_bar/t1.jpg']}}),
    ['products/energy_bar/hero-hd.png','products/energy_bar/hero-no-video.png']);
  assert.deepEqual(productGallery({id:'bristick15',hero:'products/bristick15/hero.jpg',content:{thumbs:['products/bristick15/t1.jpg']}}),
    ['products/bristick15/hero-hd.png']);
  assert.deepEqual(productGallery({id:'other',hero:'other.jpg',content:{thumbs:['other.jpg','extra.jpg']}}), ['other.jpg','extra.jpg']);
});

test('수량 스테퍼는 1 ~ max_qty 경계를 지킨다', () => {
  assert.equal(clampQty(0, 3), 1);
  assert.equal(clampQty(4, 3), 3);
  assert.equal(clampQty(2, 3), 2);
  assert.equal(clampQty(5, 1), 1);
  assert.equal(clampQty(2, undefined), 1);
});

test('쿠폰 상태 탭은 서버 state와 1:1로 매핑된다', () => {
  assert.deepEqual(COUPON_TABS.map(([key]) => key), ['all', 'active', 'pending', 'closed']);
  const items = [{state: 'active'}, {state: 'pending', status: 'held'}, {state: 'closed', closed_reason: 'expired'}];
  assert.equal(couponsFor(items, 'all').length, 3);
  assert.deepEqual(couponsFor(items, 'pending'), [items[1]]);
  assert.equal(couponChip(items[1]), '운영자 확인 중');
  assert.equal(couponChip({state: 'pending', status: 'requested'}), '발급 중');
  assert.equal(couponChip(items[2]), '만료');
  assert.equal(couponChip({state: 'closed', closed_reason: 'used'}), '사용 완료');
});

test('슬라이더는 움직임 줄이기·일시정지·포커스 때 자동 넘김을 멈춘다', () => {
  const base = {reducedMotion: false, paused: false, hovering: false, focused: false, count: 5};
  assert.equal(shouldAutoplay(base), true);
  assert.equal(shouldAutoplay({...base, reducedMotion: true}), false);
  assert.equal(shouldAutoplay({...base, paused: true}), false);
  assert.equal(shouldAutoplay({...base, focused: true}), false);
  assert.equal(shouldAutoplay({...base, count: 1}), false);
  assert.equal(nextSlide(4, 1, 5), 0);
  assert.equal(nextSlide(0, -1, 5), 4);
});

test('정산 대상일과 다음 교환 달 표기', () => {
  assert.equal(targetSuffix('2026-10-20'), ' (10.20)');
  assert.equal(targetSuffix(null), '');
  assert.equal(nextMonthLabel(10), '11월');
  assert.equal(nextMonthLabel(12), '1월');
});
