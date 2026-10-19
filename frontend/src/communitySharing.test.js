import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {buildSync} from 'esbuild';

// Vite가 사용하는 esbuild로 실제 JSX를 읽어 별도 DOM 의존성 없이 폼을 검증한다.
const compiled=buildSync({entryPoints:[fileURLToPath(new URL('./Community.jsx',import.meta.url))],
  bundle:true,write:false,platform:'node',format:'cjs',packages:'external',loader:{'.css':'empty'}});
const loaded={exports:{}};
new Function('require','module','exports',compiled.outputFiles[0].text)(createRequire(import.meta.url),loaded,loaded.exports);
const {ShareMealForm}=loaded.exports;
const meal={meal_id:'saved',meal_date:'2026-10-19',meal_type:'lunch',has_photo:true,
  items:[{food_name:'비빔밥',category:'밥류'}]};
function render(overrides={}) {
  return renderToStaticMarkup(React.createElement(ShareMealForm,{
    eligible:[meal],meal:'saved',comment:'',photo:false,busy:false,
    onMeal:()=>{},onComment:()=>{},onPhoto:()=>{},onSubmit:()=>{},onRecord:()=>{},...overrides}));
}

test('기록이 없어도 같은 공유 폼과 기록 안내를 표시하고 제출을 막는다',()=>{
  const html=render({eligible:[],meal:''});
  for(const label of ['공유할 식단','한 끼 이야기','식단 사진도 함께 공개합니다','식단 기록하러 가기'])assert.ok(html.includes(label));
  assert.match(html,/<select[^>]*disabled/);
  assert.match(html,/<textarea[^>]*disabled/);
  assert.match(html,/<button[^>]*disabled[^>]*>사진 없이 식단 공유하기/);
  assert.ok(html.includes('기록한 식단을 이미 공유했어요'));
});

test('사진이 있는 식단도 기본 미동의이며 사진 없이 공유한다고 표시한다',()=>{
  const html=render();
  assert.ok(html.includes('사진 비공개: 사진을 제외한 식단 정보만 공유합니다.'));
  assert.ok(html.includes('사진 없이 식단 공유하기'));
  assert.doesNotMatch(html,/<input[^>]*checked/);
});

test('사진이 있는 식단에 동의한 경우에만 사진 포함으로 표시한다',()=>{
  const html=render({photo:true});
  assert.match(html,/<input[^>]*checked/);
  assert.ok(html.includes('사진과 함께 공유하기'));
});

test('선택 해제·사진 없는 식단에서는 남아 있는 동의 값도 적용하지 않는다',()=>{
  for(const overrides of [{meal:''},{eligible:[{...meal,has_photo:false}]}]){
    const html=render({...overrides,photo:true});
    assert.match(html,/<input[^>]*disabled/);
    assert.doesNotMatch(html,/<input[^>]*checked/);
    assert.ok(html.includes('사진 없이 식단 공유하기'));
  }
});

test('로딩·처리 중에는 입력과 제출을 막는다',()=>{
  for(const overrides of [{eligible:null,meal:''},{busy:true}]){
    const html=render(overrides);
    assert.match(html,/aria-busy="true"/);
    assert.match(html,/<select[^>]*disabled/);
    assert.match(html,/<button[^>]*disabled/);
  }
});
