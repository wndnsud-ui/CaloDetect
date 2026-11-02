import test from 'node:test';
import assert from 'node:assert/strict';
import {mealAt,homePrompt,homeNumber,mealFeedback} from './homePresentation.js';

test('meal prompts follow KST boundaries independently of host timezone',()=>{
  for(const [time,type] of [['01:59','breakfast'],['02:00','lunch'],['05:59','lunch'],['06:00','snack'],['08:00','dinner'],['12:59','dinner'],['13:00','snack'],['15:00','breakfast']]) {
    assert.equal(mealAt(new Date(`2026-11-02T${time}:00Z`)),type);
  }
});
test('second meal prompt and completed slot use actual records; past dates omit current-time CTA wording',()=>{
  const now=new Date('2026-11-02T03:00:00Z');
  assert.match(homePrompt([{meal_type:'breakfast'}],true,now).title,/두 번째/);
  assert.match(homePrompt([{meal_type:'lunch'}],true,now).title,/기록 완료/);
  assert.equal(homePrompt([],false,now).title,'선택한 날의 식단을 돌아보세요.');
});
test('unknown nutrition does not invent feedback and displayed numbers use one decimal',()=>{
  assert.equal(homeNumber(20.81),'20.8');
  assert.equal(homeNumber(null),'—');
  assert.doesNotMatch(mealFeedback([{items:[{food_name:'직접 입력',nutrition:{protein:null}}]}]),/단백질 .*g/);
  assert.match(mealFeedback([{meal_type:'breakfast',items:[{food_name:'계란찜',nutrition:{protein:8}}]}]),/계란찜으로 단백질 8g/);
});
