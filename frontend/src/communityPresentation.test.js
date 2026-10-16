import test from 'node:test';
import assert from 'node:assert/strict';
import {mealSummary,displayFoodName,relativeTime} from './communityPresentation.js';

test('한식 한 상: 주메뉴 3개, 반찬 묶음, 넘침, 반찬만 있는 식단',()=>{
  const mains=['잡곡밥','된장찌개','제육볶음','곰탕_설렁탕'].map(food_name=>({food_name,category:'밥류'}));
  const sides=['배추김치','감자조림','나물','깍두기'].map(food_name=>({food_name,category:'반찬류'}));
  assert.equal(mealSummary([...mains.slice(0,3),...sides.slice(0,3)]),'잡곡밥 · 된장찌개 · 제육볶음 + 반찬 3가지');
  assert.equal(mealSummary(mains),'잡곡밥 · 된장찌개 · 제육볶음 외 1개');
  assert.equal(mealSummary(sides),'배추김치 · 감자조림 · 나물 외 1개');
  assert.equal(mealSummary([{food_name:'비빔밥',category:'밥류'}]),'비빔밥');
  assert.equal(displayFoodName('곰탕_설렁탕'),'곰탕/설렁탕');
  assert.equal(mealSummary([]),'');
});
test('상대 시각은 UTC와 미래 시각을 안전하게 표시',()=>{
  const now=Date.parse('2026-10-16T00:00:00Z');
  assert.equal(relativeTime('2026-10-16T00:00:00',now),'방금 전');
  assert.equal(relativeTime('2026-10-15T23:30:00Z',now),'30분 전');
  assert.equal(relativeTime('2026-10-15T21:00:00Z',now),'3시간 전');
  assert.equal(relativeTime('2026-10-17T00:00:00Z',now),'방금 전');
});
