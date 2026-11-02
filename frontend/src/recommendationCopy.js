// 추천 판단은 서버 응답을 유지하고, 화면에서 반복 문구만 정리한다.
const redundant = new Set([
  '오늘 섭취량과 끼니 목표 열량을 반영했습니다.',
  '최근 식사와 중복이 적습니다.',
  '상대적으로 가벼운 열량의 메뉴를 우선했습니다.',
  '식약처 음식 DB의 1인분 기준 영양값입니다.',
]);
const replacements = {
  '끼니 목표 열량에 가까운 메뉴입니다.':'끼니 목표에 딱 맞는 양이에요.',
  '끼니별 목표 열량에 맞춰 비교한 메뉴입니다.':'끼니 목표에 딱 맞는 양이에요.',
  '오늘 나트륨 섭취량을 고려하면 이 메뉴는 섭취량 조절이 필요합니다.':'오늘 나트륨이 많아요. 조금 덜어 드세요.',
};
export const recommendationReasons = (reasons = []) => [...new Set(reasons.filter(reason=>!redundant.has(reason)).map(reason=>replacements[reason]||reason))];
export const recommendationNotice = notice => notice === '가벼운 식단: 끼니 목표보다 가벼운 메뉴로만 골랐어요. 샐러드 등은 식약처 음식 DB 1인분 기준입니다.' ? '끼니 목표보다 가벼운 메뉴만 골랐어요 · 식약처 DB 1인분 기준' : notice;
