// 투명 배경 착용 이미지. 원본 레벨 이미지는 의상 해제 시 그대로 사용한다.
const BASE = '/jibang/clothing/';
export const CLOTHING_SPRITES = {
  outfit_workout: {
    front: `${BASE}workout-front.png`,
    1: `${BASE}workout-lv1.png`, 2: `${BASE}workout-lv2.png`,
    3: `${BASE}workout-lv3.png`, 4: `${BASE}workout-lv4.png`, 5: `${BASE}workout-lv5.png`,
  },
  outfit_lv3: {1: `${BASE}sailor-lv1.png`, 2: `${BASE}sailor-lv2.png`, 3: `${BASE}sailor-lv3.png`, 4: `${BASE}sailor-lv4.png`, 5: `${BASE}sailor-lv5.png`},
  costume_lv4: {1: `${BASE}garden-lv1.png`, 2: `${BASE}garden-lv2.png`, 3: `${BASE}garden-lv3.png`, 4: `${BASE}garden-lv4.png`, 5: `${BASE}garden-lv5.png`},
  costume_explorer: {1: `${BASE}explorer-lv1.png`, 2: `${BASE}explorer-lv2.png`, 3: `${BASE}explorer-lv3.png`, 4: `${BASE}explorer-lv4.png`, 5: `${BASE}explorer-lv5-concept.png`},
};

// 착용 이미지의 실제 눈 중심을 원본 몸 좌표계로 환산한 값(왼눈 x/y, 오른눈 x/y).
// 생성 이미지마다 얼굴 위치가 조금 달라 원본의 기준점을 그대로 쓰지 않는다.
const CLOTHING_EYES = {
  outfit_workout: {
    front: [68.5, 55, 111, 55], 1: [137, 74, 198, 61], 2: [98, 86, 165, 74],
    3: [73, 78, 142, 67], 4: [51, 84, 115, 70], 5: [59, 91, 126, 108],
  },
  outfit_lv3: {1: [141, 79, 205, 64], 2: [101, 88, 170, 77], 3: [73, 78, 139, 67], 4: [48, 81, 112, 68], 5: [59, 93, 127, 110]},
  costume_lv4: {1: [141, 79, 205, 64], 2: [101, 88, 170, 77], 3: [72, 83, 143, 71], 4: [49, 82, 112, 68], 5: [59, 89, 126, 105]},
  costume_explorer: {1: [141, 79, 205, 64], 2: [101, 88, 170, 77], 3: [72, 83, 143, 71], 4: [51, 86, 117, 72], 5: [59, 94, 131, 115]},
};

// 모자 띠가 닿는 이마 윗부분 중심(이미지 너비/높이 비율).
const CLOTHING_CROWNS = {
  outfit_workout: {front: [0.51, 0.13], 1: [0.53, 0.11], 2: [0.48, 0.14], 3: [0.45, 0.13], 4: [0.43, 0.13], 5: [0.48, 0.17]},
  outfit_lv3: {1: [0.58, 0.15], 2: [0.55, 0.17], 3: [0.45, 0.13], 4: [0.43, 0.13], 5: [0.48, 0.17]},
  costume_lv4: {1: [0.58, 0.15], 2: [0.55, 0.17], 3: [0.5, 0.13], 4: [0.43, 0.13], 5: [0.48, 0.17]},
  costume_explorer: {1: [0.58, 0.15], 2: [0.55, 0.17], 3: [0.5, 0.13], 4: [0.49, 0.14], 5: [0.47, 0.13]},
};

export function dressedSprite(equipment, level) {
  // 기존 운동복은 prop 슬롯이다. 전용 의상과 동시에 보유/장착된 경우 의상 슬롯을 우선한다.
  const item = [equipment.outfit, equipment.prop].find(id => CLOTHING_SPRITES[id]);
  if (!item) return null;
  const variants = CLOTHING_SPRITES[item];
  // 옷을 입어도 현재 성장 단계의 몸을 유지한다. 다른 레벨 이미지로 대체하지 않는다.
  const pose = variants[level] ? level : level == null && variants.front ? 'front' : null;
  if (pose == null) return null;
  return {item, pose, src: variants[pose], eyes: CLOTHING_EYES[item][pose], crown: CLOTHING_CROWNS[item][pose]};
}
