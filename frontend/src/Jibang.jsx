// 리워드 캐릭터 "지방이": 레벨별 몸 이미지 + 장착 아이템 SVG 오버레이 + 배경 장면.
// 2026-10-20 사용자 결정: 지시서 v3 §11-0의 "레벨별 체형 이미지 미사용"을 해제하고 시트의 LV.1~5 몸을 그대로 쓴다.
// 움직임은 CSS keyframes(숨쉬기·한숨·콩콩·반짝임)로만 하고 prefers-reduced-motion에서 멈춘다.
import React, {useLayoutEffect, useRef, useState} from 'react';
import JibangBackground from './JibangBackgrounds';
import {CLOTHING_SPRITES, dressedSprite} from './jibangClothing';

// 캐릭터 이름은 사용자 테스트 대상(TBD)이라 화면 문구는 이 상수 한 곳에서만 가져온다.
export const CHARACTER_NAME = '지방이';
const BASE = '/jibang/';
export const MOOD_IMAGES = {cheer: `${BASE}f_cheer.png`, happy: `${BASE}f_happy.png`, proud: `${BASE}f_proud.png`, wow: `${BASE}f_wow.png`, smile: `${BASE}f_smile.png`};

// 몸 이미지별 원본 크기와 아이템 기준점(원본 px). eyes=[왼눈 x,y, 오른눈 x,y], crown=정수리(모자 띠 중심)·배율·기울기,
// feet=[왼발 x, 오른발 x, 바닥 y, 배율], chest=목 아래 중심·배율, right/left=소품 자리.
// deco는 시트 좌표에서 오려낸 장식(몸 기준 상대 위치)이며 kind별로 CSS 움직임을 준다.
const FRONT = {src: `${BASE}front.png`, w: 176, h: 184, eyes: [61, 59, 114, 59], crown: [90, 26, 1, -6], feet: [57, 121, 176, 1], chest: [88, 120, 1], right: [158, 118], left: [14, 150], deco: []};
export const SPRITES = {
  front: FRONT,
  1: {src: `${BASE}lv1_gloomy.png`, w: 295, h: 206, eyes: [141, 79, 205, 64], crown: [172, 30, 1.15, -8], feet: [92, 252, 198, 1], chest: [177, 128, 1.2], right: [276, 112], left: [18, 150],
    deco: [{file: 'lv1_cloud', x: 136, y: -62, w: 60, h: 37, kind: 'cloud'}, {file: 'lv1_rain', x: 148, y: -26, w: 36, h: 22, kind: 'rain'}]},
  2: {src: `${BASE}lv2.png`, w: 242, h: 251, eyes: [101, 88, 170, 77], crown: [134, 42, 1.25, -6], feet: [85, 168, 240, 1.25], chest: [137, 168, 1.3], right: [228, 168], left: [16, 200],
    deco: [{file: 'lv2_d0', x: 4, y: 33, w: 19, h: 25, kind: 'lines'}, {file: 'lv2_d1', x: -13, y: 54, w: 25, h: 18, kind: 'lines'}]},
  3: {src: `${BASE}lv3.png`, w: 224, h: 273, eyes: [72, 83, 143, 71], crown: [112, 36, 1.15, -6], feet: [85, 150, 264, 1], chest: [110, 152, 1.1], right: [212, 160], left: [14, 182],
    deco: [{file: 'lv3_d0', x: 0, y: 28, w: 20, h: 27, kind: 'spark'}, {file: 'lv3_d1', x: -17, y: 51, w: 25, h: 19, kind: 'spark'}]},
  4: {src: `${BASE}lv4.png`, w: 193, h: 294, eyes: [51, 86, 117, 72], crown: [94, 40, 1, -6], feet: [70, 122, 286, 0.9], chest: [90, 162, 1], right: [178, 172], left: [10, 190],
    deco: [{file: 'lv4_d0', x: 154, y: 8, w: 18, h: 28, kind: 'spark'}, {file: 'lv4_d1', x: 170, y: 31, w: 24, h: 22, kind: 'spark'}, {file: 'lv4_d2', x: -47, y: 56, w: 30, h: 29, kind: 'heart'},
      {file: 'lv4_d3', x: 179, y: 57, w: 26, h: 15, kind: 'spark'}, {file: 'lv4_d4', x: -51, y: 157, w: 43, h: 41, kind: 'arrow'}]},
  5: {src: `${BASE}lv5.png`, w: 196, h: 329, eyes: [59, 92, 127, 109], crown: [86, 64, 1, -12], feet: [80, 125, 320, 0.85], chest: [95, 186, 1], right: [182, 192], left: [12, 212],
    deco: [{file: 'lv5_d0', x: 176, y: 41, w: 34, h: 51, kind: 'spark'}, {file: 'lv5_d1', x: -35, y: 85, w: 29, h: 28, kind: 'heart'}, {file: 'lv5_d2', x: 200, y: 94, w: 18, h: 25, kind: 'spark'},
      {file: 'lv5_d3', x: -33, y: 130, w: 29, h: 45, kind: 'spark'}, {file: 'lv5_d4', x: 173, y: 187, w: 33, h: 50, kind: 'spark'}, {file: 'lv5_d5', x: -17, y: 259, w: 28, h: 42, kind: 'spark'}]},
};
// 레벨 → 몸 이미지 매핑(교체 가능). 2026-10-20 사용자 결정으로 시트의 레벨별 몸을 연결한다.
export const LEVEL_SPRITES = {1: SPRITES[1].src, 2: SPRITES[2].src, 3: SPRITES[3].src, 4: SPRITES[4].src, 5: SPRITES[5].src};

const INK = '#4A3328';
// 오버레이는 정면 이미지(176×184) 좌표로 그리고, 몸마다 기준점(anchor)으로 옮겨 붙인다.
// [그림, 기준점 종류, 정면 기준점 x, y]
const OVERLAYS = {
  // 머리 아이템은 정수리 기준(0,0) 좌표: 이마를 가리지 않게 머리 위에 얹고 살짝 기울인다.
  starter_hat: [<g><path d="M-44 2 C-44 -30 -24 -42 0 -42 C24 -42 44 -30 44 2 Z" fill="#6FAF8E" stroke={INK} strokeWidth="2.5" strokeLinejoin="round"/>
    <path d="M-18 -37 C-12 -24 -12 -12 -14 -2 M10 -40 C14 -27 14 -14 12 -2" fill="none" stroke="#4F9474" strokeWidth="2" strokeLinecap="round"/>
    <rect x="-48" y="-5" width="96" height="14" rx="7" fill="#178366" stroke={INK} strokeWidth="2.5"/><circle cx="0" cy="-44" r="8" fill="#FFFFFF" stroke={INK} strokeWidth="2.5"/></g>, 'crown'],
  starter_glasses: [<g fill="rgba(255,255,255,0.12)" stroke={INK} strokeWidth="2.5" strokeLinecap="round">
    <circle cx="-26.5" cy="0" r="16.5"/><circle cx="26.5" cy="0" r="16.5"/>
    <path d="M-10 -1 Q0 -7 10 -1 M-43 -2 L-48 -5 M43 -2 L48 -5" fill="none"/>
  </g>, 'eyes'],
  starter_ribbon: [<g transform="translate(30 -6) rotate(14)"><path d="M0 0 L-18 -12 L-16 12 Z M0 0 L18 -12 L16 12 Z" fill="#CF7150" stroke={INK} strokeWidth="2.5" strokeLinejoin="round"/><circle r="6" fill="#A04A2C" stroke={INK} strokeWidth="2.5"/></g>, 'crown'],
  starter_shoes: [null, 'feet'],
  starter_sticker: [<path d="M150 74 l4 9 10 1 -7 7 2 10 -9 -5 -9 5 2 -10 -7 -7 10 -1 z" fill="#E9B949" stroke={INK} strokeWidth="2" strokeLinejoin="round"/>, 'right', 157, 88],
  prop_water: [<g><rect x="150" y="110" width="20" height="44" rx="6" fill="#BFE3F2" stroke={INK} strokeWidth="2.5"/><rect x="154" y="102" width="12" height="9" rx="2" fill="#178366" stroke={INK} strokeWidth="2"/><path d="M152 132h16" stroke="#7FC1DD" strokeWidth="3"/></g>, 'right', 158, 118],
  prop_salad: [<g><path d="M-8 150 h44 a22 18 0 0 1 -44 0 Z" fill="#F4F7F5" stroke={INK} strokeWidth="2.5"/><circle cx="4" cy="146" r="7" fill="#6DB58A"/><circle cx="16" cy="144" r="6" fill="#CF7150"/><circle cx="26" cy="147" r="6" fill="#8FCCA4"/></g>, 'left', 14, 150],
  prop_heart: [<path d="M150 160 c-14 -9 -18 -18 -13 -24 4 -5 10 -4 13 1 3 -5 9 -6 13 -1 5 6 1 15 -13 24 z" fill="#F29FB0" stroke={INK} strokeWidth="2.5" strokeLinejoin="round"/>, 'right', 158, 118],
  outfit_workout: [<g><path d="M-48 20 Q0 4 48 20" fill="none" stroke="#CF7150" strokeWidth="9" strokeLinecap="round"/><path d="M-48 20 Q0 4 48 20" fill="none" stroke={INK} strokeWidth="1.5" strokeDasharray="4 6"/></g>, 'crown'],
  season_set: [<path d="M0 -40 l5 10 11 1 -8 8 2 11 -10 -5 -10 5 2 -11 -8 -8 11 -1 z" fill="#E9B949" stroke={INK} strokeWidth="2"/>, 'crown'],
  outfit_lv3: [<g><path d="M40 112 Q88 132 136 112 L132 126 Q88 146 44 126 Z" fill="#6FA8DC" stroke={INK} strokeWidth="2.5" strokeLinejoin="round"/><path d="M118 122 l6 26 -12 -2 z" fill="#6FA8DC" stroke={INK} strokeWidth="2.5" strokeLinejoin="round"/></g>, 'chest', 88, 120],
  costume_lv4: [<g><path d="M-30 4 C-30 -26 30 -26 30 4 Z" fill="#E9D3A6" stroke={INK} strokeWidth="2.5"/><path d="M-60 6 Q0 -8 60 6 Q0 18 -60 6 Z" fill="#F1E0B8" stroke={INK} strokeWidth="2.5" strokeLinejoin="round"/><path d="M-29 -2 Q0 -8 29 -2" fill="none" stroke="#CF7150" strokeWidth="4"/></g>, 'crown'],
  title_lv5: [<g><rect x="-54" y="-74" width="108" height="22" rx="11" fill="#1C4B3A"/><text x="0" y="-59" textAnchor="middle" fontSize="11" fontWeight="800" fill="#FFFFFF">건강 습관</text></g>, 'crown'],
};
const SHOE_LEFT = <path d="M36 182 C36 166 52 162 70 166 C78 168 80 182 76 184 L38 184 Z" fill="#E9B949" stroke={INK} strokeWidth="2.5"/>;
const SHOE_RIGHT = <path d="M104 166 C122 162 140 166 140 182 L138 184 L102 184 C98 182 98 168 104 166 Z" fill="#E9B949" stroke={INK} strokeWidth="2.5"/>;
// 겹치는 순서(뒤 → 앞).
const LAYER_ORDER = ['prop', 'outfit', 'shoes', 'sticker', 'glasses', 'hat', 'ribbon', 'title'];

const place = (x, y, scale, fx, fy, key, art) =>
  <g key={key} transform={`translate(${x} ${y}) scale(${scale}) translate(${-fx} ${-fy})`}>{art}</g>;

function overlay(id, sprite, eyes = sprite.eyes, crown = sprite.crown) {
  const [art, anchor, fx, fy] = OVERLAYS[id];
  if (anchor === 'feet') {
    const [left, right, bottom, scale] = sprite.feet;
    return [place(left, bottom, scale, 57, 176, `${id}-l`, SHOE_LEFT), place(right, bottom, scale, 121, 176, `${id}-r`, SHOE_RIGHT)];
  }
  if (anchor === 'eyes') {
    const [lx, ly, rx, ry] = eyes;
    const angle = Math.atan2(ry - ly, rx - lx) * 180 / Math.PI;
    const scale = Math.hypot(rx - lx, ry - ly) / 53;
    return <g key={id} transform={`translate(${(lx + rx) / 2} ${(ly + ry) / 2}) rotate(${angle}) scale(${scale})`}>{art}</g>;
  }
  if (anchor === 'crown') {
    const [x, y, scale] = crown;
    const [lx, ly, rx, ry] = eyes;
    const angle = Math.atan2(ry - ly, rx - lx) * 180 / Math.PI;
    return <g key={id} transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`}>{art}</g>;
  }
  if (anchor === 'right' || anchor === 'left') {
    const [x, y] = sprite[anchor];
    return place(x, y, 1, fx, fy, id, art);
  }
  const [x, y, scale] = sprite[anchor];
  return place(x, y, scale, fx, fy, id, art);
}

// 캐릭터와 장착 아이템. equipment는 {slot: item_id}. width는 정면 이미지 기준 너비이며 레벨 몸은 원본 비율로 맞춘다.
export function JibangFigure({equipment = {}, level, width = 176, motion = 'breathe', label}) {
  const dressed = dressedSprite(equipment, level);
  const sprite = SPRITES[dressed?.pose ?? level] || FRONT;
  const crown = dressed ? [dressed.crown[0] * sprite.w, dressed.crown[1] * sprite.h, sprite.crown[2]] : sprite.crown;
  const scale = width / FRONT.w * (sprite === FRONT ? 1 : 0.68);
  const layers = LAYER_ORDER.map(slot => equipment[slot]).filter(id => {
    if (!OVERLAYS[id]) return false;
    if (!CLOTHING_SPRITES[id]) return true;
    // 스카프는 착용 이미지에 포함되어 있다. 선택한 의상의 머리띠/모자만 별도로 표시한다.
    return dressed?.item === id && id !== 'outfit_lv3';
  });
  const kind = motion === 'none' ? 'none' : motion === 'hop' ? 'hop' : `lv${level || 0}`;
  return <div className={`jb-figure jb-move-${kind}`} style={{width: sprite.w * scale, height: sprite.h * scale}} role="img"
    aria-label={label || `LV.${level || 1} ${CHARACTER_NAME}${dressed || layers.length ? ' · 꾸민 모습' : ''}`}>
    <img src={dressed?.src || sprite.src} alt="" draggable="false"/>
    {sprite.deco.map((d, index) => <img key={d.file} className={`jb-deco jb-deco-${d.kind}`} src={`${BASE}${d.file}.png`} alt="" draggable="false"
      style={{left: `${d.x / sprite.w * 100}%`, top: `${d.y / sprite.h * 100}%`, width: `${d.w / sprite.w * 100}%`, animationDelay: `${index * 0.3}s`}}/>)}
    <svg viewBox={`0 0 ${sprite.w} ${sprite.h}`} aria-hidden="true" focusable="false">{layers.map(id => overlay(id, sprite, dressed?.eyes || sprite.eyes, crown))}</svg>
  </div>;
}

// 배경 장면 + 캐릭터 + 말풍선(손글씨). 배경은 background slot 아이템.
export default function Jibang({equipment = {}, level = 1, background, bubble, figureWidth = 150, className = '', motion = 'breathe', badge, children}) {
  const scene = background || equipment.background || 'bg_lv1';
  const sceneRef = useRef(null), figureRef = useRef(null);
  const [placement, setPlacement] = useState({bottom:'12.5%', transform:'translateX(-50%)'});
  useLayoutEffect(() => {
    const update = () => {
      const box = sceneRef.current, figure = figureRef.current?.firstElementChild;
      if (!box || !figure || !box.clientWidth || !box.clientHeight) return;
      // 배경 SVG의 xMidYMax slice와 같은 좌표계로 카펫 중심에 발을 맞춘다.
      const scale = Math.max(box.clientWidth / 360, box.clientHeight / 480);
      const floor = scene === 'bg_lv2' ? 430 : scene === 'bg_lv4' ? 440 : 420;
      const bottom = (480 - floor) * scale;
      const rugWidth = (scene === 'bg_lv2' ? 192 : scene === 'bg_lv4' ? 240 : 256) * scale;
      const fit = Math.max(0, Math.min(1, Math.min(box.clientWidth * .8, rugWidth * .85) / figure.offsetWidth,
        (box.clientHeight - bottom - 45) / figure.offsetHeight));
      setPlacement({bottom:`${bottom}px`, transform:`translateX(-50%) scale(${fit})`});
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(sceneRef.current);
    if (figureRef.current?.firstElementChild) observer.observe(figureRef.current.firstElementChild);
    return () => observer.disconnect();
  }, [scene, level, figureWidth, equipment.outfit, equipment.prop]);
  return <div ref={sceneRef} className={`jb-scene ${className}`}>
    <JibangBackground id={scene}/>
    {badge && <span className="jb-scene-badge">{badge}</span>}
    {bubble && <p className="jb-bubble">{bubble}</p>}
    <div ref={figureRef} className="jb-scene-figure" style={{...placement,left:'50%',transformOrigin:'50% 100%'}}><JibangFigure equipment={equipment} level={level} width={figureWidth} motion={motion}/></div>
    {children}
  </div>;
}
