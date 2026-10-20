// 리워드 캐릭터 이미지 검사. 2026-10-20 사용자 결정으로 지시서 v3 §11-0을 해제해 LV.1~5에 시트의 레벨별 몸을 연결한다.
// 시트 문구("예뻐지는", "가벼워진 몸")와 §11-10에서 뺀 문구는 계속 화면에 쓰지 않는다.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync, readdirSync} from 'node:fs';

const source = readFileSync(new URL('./Jibang.jsx', import.meta.url), 'utf8');

test('each level uses its own sheet body and the files exist', () => {
  const body = source.match(/LEVEL_SPRITES = \{([^}]*)\}/)[1];
  for (const level of [1, 2, 3, 4, 5]) assert.ok(body.includes(`${level}: SPRITES[${level}].src`), `LV.${level}`);
  for (const file of ['lv1_gloomy', 'lv2', 'lv3', 'lv4', 'lv5', 'front']) {
    assert.ok(source.includes('${BASE}' + file + '.png'), file);
    assert.ok(existsSync(new URL(`../public/jibang/${file}.png`, import.meta.url)), file);
  }
});

test('screens do not use the sheet wording or removed notices', () => {
  for (const file of readdirSync(new URL('.', import.meta.url)).filter(name => name.endsWith('.jsx'))) {
    const text = readFileSync(new URL(`./${file}`, import.meta.url), 'utf8');
    assert.doesNotMatch(text, /예뻐지는|가벼워진 몸|알림을 보내요|화면 밝기 최대/, file);
  }
});
