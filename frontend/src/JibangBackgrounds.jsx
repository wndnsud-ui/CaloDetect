// 지방이 방 배경 장면(시안 BG LV.1~5 + 판매형 기본 배경). 360×480 좌표계 SVG이며 장식용이라 aria-hidden.
import React from 'react';

const Sprout = ({x, y, s = 1}) => <g transform={`translate(${x} ${y}) scale(${s})`}>
  <path d="M0 0v-16" stroke="#2E8B5A" strokeWidth="3" strokeLinecap="round" fill="none"/>
  <path d="M0 -12c-9-1-12-8-10-13 7 0 10 5 10 13zM0 -15c7-4 12-10 10-15-7 2-10 7-10 15z" fill="#4FA77A"/>
</g>;

const Flower = ({x, y, petal, center}) => <g>
  <g fill={petal}><circle cx={x - 6} cy={y} r="5"/><circle cx={x + 2} cy={y - 6} r="5"/><circle cx={x + 6} cy={y + 4} r="5"/><circle cx={x - 2} cy={y + 8} r="5"/></g>
  <circle cx={x} cy={y + 1} r="3.5" fill={center}/>
</g>;

function Lv1() {
  return <>
    <rect width="360" height="480" fill="#F7F1E6"/><path d="M0 0h360v40H0z" fill="#F1E7D6"/>
    <rect x="198" y="72" width="124" height="148" rx="10" fill="#FFE9C9"/><circle cx="260" cy="196" r="46" fill="#F9C77A"/>
    <rect x="198" y="176" width="124" height="44" fill="#FBD9A8" opacity="0.6"/>
    <rect x="198" y="72" width="124" height="148" rx="10" fill="none" stroke="#C9A67A" strokeWidth="7"/>
    <path d="M260 72v148M198 146h124" stroke="#C9A67A" strokeWidth="5"/>
    <path d="M188 72c10 40 6 110 -4 160M332 72c-10 40 -6 110 4 160" fill="none" stroke="#E7CBB5" strokeWidth="14" strokeLinecap="round"/>
    <rect x="186" y="226" width="148" height="10" rx="5" fill="#C9A67A"/><path d="M222 236h30l-4 28h-22z" fill="#CF7150"/>
    <path d="M237 236c0-14 0-20 0-26" stroke="#2E8B5A" strokeWidth="3" strokeLinecap="round"/>
    <path d="M237 214c-10-2-14-10-12-16 8 0 12 6 12 16zM237 210c8-4 14-12 12-18-8 2-12 8-12 18z" fill="#4FA77A"/>
    <rect x="40" y="104" width="78" height="62" rx="6" fill="#EAF5EE" stroke="#C9A67A" strokeWidth="5"/>
    <path d="M79 148c-12-8-16-15-12-20 3-4 9-3 12 2 3-5 9-6 12-2 4 5 0 12-12 20z" fill="#E9A4A0"/>
    <rect y="352" width="360" height="128" fill="#E9DAC1"/><rect y="344" width="360" height="10" fill="#D9C4A2"/>
    <ellipse cx="180" cy="420" rx="140" ry="30" fill="#EAF5EE"/><ellipse cx="180" cy="420" rx="112" ry="22" fill="none" stroke="#BFDDCB" strokeWidth="4"/>
  </>;
}

function Lv2() {
  return <>
    <rect width="360" height="480" fill="#E6F3EC"/><circle cx="292" cy="78" r="34" fill="#FFF1C9"/>
    <g fill="#FFFFFF"><ellipse cx="74" cy="92" rx="34" ry="14"/><ellipse cx="98" cy="82" rx="22" ry="14"/><ellipse cx="208" cy="128" rx="26" ry="10"/></g>
    <path d="M0 270 C70 236 140 250 200 262 C260 274 310 250 360 240 V480 H0 Z" fill="#C8E5D2"/>
    <path d="M0 330 C90 310 180 318 260 326 C300 330 330 324 360 318 V480 H0 Z" fill="#9FD3B0"/>
    <path d="M20 296v44M56 290v46M92 288v46M268 292v42M304 288v44M340 284v44" stroke="#FFFFFF" strokeWidth="6" strokeLinecap="round"/>
    <path d="M14 306h86M262 302h84" stroke="#FFFFFF" strokeWidth="5"/>
    {[[50, 400], [118, 446], [252, 448], [318, 398]].map(([x, y]) => <Sprout key={x} x={x} y={y}/>)}
    <Sprout x={86} y={362} s={0.75}/><Sprout x={286} y={360} s={0.75}/>
    <g fill="#FFFFFF"><circle cx="160" cy="456" r="4"/><circle cx="206" cy="462" r="3"/><circle cx="30" cy="440" r="3"/><circle cx="336" cy="452" r="4"/></g>
    <ellipse cx="180" cy="430" rx="96" ry="14" fill="#7FBE95" opacity="0.6"/>
  </>;
}

function Lv3() {
  return <>
    <rect width="360" height="480" fill="#DDEEF5"/>
    <g fill="#FFFFFF"><ellipse cx="260" cy="70" rx="38" ry="14"/><ellipse cx="284" cy="60" rx="24" ry="14"/><ellipse cx="70" cy="118" rx="28" ry="10"/></g>
    <path d="M150 96q6-6 12 0q6-6 12 0M188 114q5-5 10 0q5-5 10 0" fill="none" stroke="#6E8C99" strokeWidth="2.5" strokeLinecap="round"/>
    <path d="M0 250 C80 220 150 236 220 230 C280 226 320 214 360 220 V480 H0 Z" fill="#CFE6D6"/>
    <rect y="300" width="360" height="180" fill="#A8D5B5"/>
    <path d="M150 300 C140 340 110 380 60 480 H300 C250 380 220 340 210 300 Z" fill="#EADBBE"/>
    <path d="M178 312v14M176 350v18M172 398v22M168 446v26" stroke="#F6EEDC" strokeWidth="5" strokeLinecap="round"/>
    <rect x="44" y="196" width="14" height="110" rx="5" fill="#8B6B4E"/>
    <circle cx="51" cy="178" r="44" fill="#6DB58A"/><circle cx="22" cy="206" r="30" fill="#5BA87C"/><circle cx="80" cy="204" r="28" fill="#7FC59A"/>
    <rect x="300" y="210" width="12" height="96" rx="5" fill="#8B6B4E"/>
    <circle cx="306" cy="192" r="38" fill="#5BA87C"/><circle cx="334" cy="214" r="26" fill="#6DB58A"/>
    <g fill="#B9875B"><rect x="248" y="330" width="86" height="10" rx="4"/><rect x="248" y="312" width="86" height="8" rx="4"/><rect x="256" y="340" width="8" height="22" rx="3"/><rect x="318" y="340" width="8" height="22" rx="3"/></g>
    <g fill="#FFFFFF"><circle cx="40" cy="420" r="4"/><circle cx="96" cy="372" r="3"/><circle cx="330" cy="430" r="4"/></g>
    <g fill="#F2B880"><circle cx="34" cy="350" r="5"/><circle cx="320" cy="396" r="5"/></g>
  </>;
}

function Lv4({uid}) {
  return <>
    <defs><pattern id={`${uid}-check`} width="20" height="20" patternUnits="userSpaceOnUse"><rect width="20" height="20" fill="#FFFFFF"/><rect width="10" height="10" fill="#F2C6B4"/><rect x="10" y="10" width="10" height="10" fill="#F2C6B4"/></pattern></defs>
    <rect width="360" height="480" fill="#FFF3DE"/><circle cx="70" cy="80" r="36" fill="#F9C96B"/><circle cx="70" cy="80" r="52" fill="#F9C96B" opacity="0.25"/>
    <path d="M0 220 C90 196 170 210 250 204 C300 200 330 192 360 196 V480 H0 Z" fill="#B7DB9F"/>
    <path d="M-10 250 C100 236 260 236 370 246M-10 286 C100 270 260 270 370 282M-10 324 C100 306 260 306 370 320" fill="none" stroke="#8FC27A" strokeWidth="10" strokeLinecap="round"/>
    {[40, 110].map(x => <g key={x}><path d={`M${x} 244l8 22h-16z`} fill="#E8893B"/><path d={`M${x} 244c-4-8 0-12 0-16M${x} 244c4-8 8-10 10-14`} stroke="#4FA77A" strokeWidth="3" fill="none" strokeLinecap="round"/></g>)}
    {[[250, 276], [296, 272]].map(([x, y]) => <g key={x}><circle cx={x} cy={y} r="11" fill="#CF7150"/><path d={`M${x - 6} ${y - 10}l6 4 6-4`} stroke="#4FA77A" strokeWidth="3" fill="none" strokeLinecap="round"/></g>)}
    {[[70, 310, 15], [320, 312, 15], [180, 236, 13]].map(([x, y, r]) => <g key={x}><circle cx={x} cy={y} r={r} fill="#6DB58A"/><circle cx={x - 6} cy={y - 4} r={r / 2} fill="#8FCCA4"/></g>)}
    <rect y="350" width="360" height="130" fill="#A6D18F"/>
    <path d="M70 380 L300 380 L330 470 L40 470 Z" fill={`url(#${uid}-check)`} stroke="#E7A992" strokeWidth="3"/>
    <rect x="262" y="384" width="54" height="34" rx="8" fill="#C99A62"/><path d="M270 384 C270 362 308 362 308 384" fill="none" stroke="#A9794A" strokeWidth="5"/>
    <circle cx="280" cy="380" r="7" fill="#CF7150"/><circle cx="296" cy="378" r="7" fill="#E9B949"/>
  </>;
}

function Lv5({uid}) {
  const star = (x, y, r, delay) => <path className="bg5-tw" style={{animationDelay: delay}} d={`M${x} ${y} Q${x + r * 0.15} ${y + r * 0.9} ${x + r} ${y + r} Q${x + r * 0.15} ${y + r * 1.1} ${x} ${y + r * 2} Q${x - r * 0.15} ${y + r * 1.1} ${x - r} ${y + r} Q${x - r * 0.15} ${y + r * 0.9} ${x} ${y} Z`}/>;
  return <>
    <defs><linearGradient id={`${uid}-sky`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#FCE2A4"/><stop offset="1" stopColor="#FFF8E8"/></linearGradient></defs>
    <rect width="360" height="480" fill={`url(#${uid}-sky)`}/>
    <g className="bg5-spin" fill="#FFFFFF" opacity="0.35"><path d="M180 190 L170 20 L190 20 Z"/><path d="M180 190 L300 70 L314 84 Z"/><path d="M180 190 L350 180 L350 200 Z"/><path d="M180 190 L60 70 L46 84 Z"/><path d="M180 190 L10 200 L10 180 Z"/></g>
    <circle cx="180" cy="190" r="62" fill="#FFD36E"/><circle cx="180" cy="190" r="84" fill="#FFD36E" opacity="0.25"/>
    <path d="M0 270 C70 230 130 236 190 250 C250 264 310 236 360 226 V480 H0 Z" fill="#8CCB9F"/>
    <path d="M0 330 C80 300 160 304 230 316 C290 326 330 318 360 310 V480 H0 Z" fill="#4FA77A"/>
    <path d="M0 400 C90 384 200 388 360 396 V480 H0 Z" fill="#2E8B5A"/>
    <Flower x={46} y={356} petal="#FFFFFF" center="#F6B26B"/><Flower x={306} y={350} petal="#F29FB0" center="#FFF3C4"/>
    <Flower x={96} y={430} petal="#FFFFFF" center="#F6B26B"/><Flower x={276} y={436} petal="#F6B26B" center="#FFFFFF"/>
    <g fill="#FFFFFF">{star(60, 120, 14, '0s')}{star(300, 130, 10, '.6s')}{star(120, 250, 9, '1.1s')}</g>
  </>;
}

// 판매형 기본 배경(starter_bg): 민트 벽과 러그가 있는 단정한 방.
function Starter() {
  return <>
    <rect width="360" height="480" fill="#DCEFE3"/>
    <g fill="#FFFFFF" opacity="0.7"><circle cx="60" cy="70" r="6"/><circle cx="300" cy="110" r="5"/><circle cx="210" cy="56" r="4"/><circle cx="120" cy="150" r="4"/></g>
    <rect x="132" y="70" width="96" height="84" rx="14" fill="#FFFFFF" stroke="#B9D3C5" strokeWidth="5"/><path d="M180 70v84M132 112h96" stroke="#B9D3C5" strokeWidth="4"/>
    <rect y="340" width="360" height="140" fill="#C8E2D2"/><rect y="332" width="360" height="10" fill="#A9CDB8"/>
    <ellipse cx="180" cy="420" rx="128" ry="26" fill="#FFFFFF" opacity="0.8"/>
  </>;
}

const SCENES = {bg_lv1: Lv1, bg_lv2: Lv2, bg_lv3: Lv3, bg_lv4: Lv4, bg_lv5: Lv5, starter_bg: Starter};
export const BACKGROUND_LABELS = {bg_lv1: '포근한 아침 방', bg_lv2: '새싹 정원', bg_lv3: '산책 공원', bg_lv4: '텃밭 피크닉', bg_lv5: '햇살 언덕', starter_bg: '기본 배경'};

// 배경 장면 1개. 컨테이너를 꽉 채우며 비율은 3:4(slice로 자른다).
export default function JibangBackground({id = 'bg_lv1'}) {
  const uid = React.useId().replace(/:/g, '');
  const Scene = SCENES[id] || Lv1;
  return <svg className="jb-bg" viewBox="0 0 360 480" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false"><Scene uid={uid}/></svg>;
}
