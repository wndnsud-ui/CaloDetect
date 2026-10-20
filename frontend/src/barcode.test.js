import {test} from 'node:test';
import assert from 'node:assert/strict';
import {code128Bars, code128Values, CODE128_PATTERNS} from './barcode.js';

test('CODE128 pattern table is complete and each symbol is 11 modules', () => {
  assert.equal(CODE128_PATTERNS.length, 107);
  CODE128_PATTERNS.slice(0, 106).forEach(p => assert.equal([...p].reduce((s, d) => s + Number(d), 0), 11, p));
  assert.equal([...CODE128_PATTERNS[106]].reduce((s, d) => s + Number(d), 0), 13);
});

test('Code Set B values and checksum', () => {
  // 위키백과 예시 "Wikipedia" → 체크 값 6 (Start B 104 기준)
  const values = code128Values('Wikipedia');
  assert.equal(values[0], 104);
  assert.equal(values.at(-2), (104 + [...'Wikipedia'].reduce((s, ch, i) => s + (ch.charCodeAt(0) - 32) * (i + 1), 0)) % 103);
  assert.equal(values.at(-1), 106);
  assert.throws(() => code128Values('쿠폰'));
});

test('bar layout width = quiet + 11 per symbol + stop + quiet', () => {
  const {bars, width} = code128Bars('CALO-0001');
  assert.equal(width, 10 + 11 * (9 + 2) + 13 + 10);
  assert.ok(bars.every(bar => bar.w >= 1 && bar.w <= 4));
});
