// CODE128(B) 바코드 막대 계산(지시서 v3 §11-7: 쿠폰 번호로 CODE128 생성, 라이브러리 추가 없음).
// 쿠폰 번호는 서버가 영문·숫자·-만 허용하므로 Code Set B(ASCII 32~127)로 충분하다.
const PATTERNS = ('212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 ' +
  '123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 232121 111323 ' +
  '131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 231131 213113 ' +
  '213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 ' +
  '112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 ' +
  '421211 212141 214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 2331112').split(' ');
const START_B = 104, STOP = 106, QUIET = 10;

// 값 목록(시작·데이터·체크·정지). 범위 밖 문자는 오류.
export function code128Values(text) {
  const data = [...text].map(ch => {
    const code = ch.charCodeAt(0);
    if (code < 32 || code > 127) throw new Error('CODE128B로 표현할 수 없는 문자예요.');
    return code - 32;
  });
  const check = (START_B + data.reduce((sum, value, index) => sum + value * (index + 1), 0)) % 103;
  return [START_B, ...data, check, STOP];
}

// 막대 목록 [{x, w}] 과 전체 모듈 폭(앞뒤 여백 포함).
export function code128Bars(text) {
  let x = QUIET;
  const bars = [];
  for (const value of code128Values(text)) {
    [...PATTERNS[value]].forEach((digit, index) => {
      const width = Number(digit);
      if (index % 2 === 0) bars.push({x, w: width});
      x += width;
    });
  }
  return {bars, width: x + QUIET};
}

export const CODE128_PATTERNS = PATTERNS;
