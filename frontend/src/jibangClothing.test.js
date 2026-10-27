import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {CLOTHING_SPRITES, dressedSprite} from './jibangClothing.js';

test('모든 몸통 의상은 LV.1~5에서 현재 레벨 몸을 유지한다', () => {
  for (const item of Object.keys(CLOTHING_SPRITES)) {
    for (let level = 1; level <= 5; level++) {
      const dressed = dressedSprite({outfit:item}, level);
      assert.equal(dressed.pose, level, `${item} LV.${level}`);
      assert.ok(existsSync(new URL(`../public${dressed.src}`, import.meta.url)), dressed.src);
      assert.equal(dressed.eyes.length, 4);
      assert.equal(dressed.crown.length, 2);
    }
  }
});

test('누락 레벨을 다른 레벨 몸으로 바꾸지 않고 기본 몸으로 돌린다', () => {
  assert.equal(dressedSprite({outfit:'costume_explorer'}, 6), null);
  assert.equal(dressedSprite({outfit:'outfit_lv3'}, undefined), null);
  assert.equal(dressedSprite({}, 1), null);
});

test('운동복 prop 호환과 전용 의상 우선순위를 유지한다', () => {
  assert.equal(dressedSprite({prop:'outfit_workout'}, 1).item, 'outfit_workout');
  assert.equal(dressedSprite({outfit:'outfit_lv3', prop:'outfit_workout'}, 1).item, 'outfit_lv3');
});
