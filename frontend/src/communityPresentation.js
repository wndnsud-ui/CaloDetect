// 카탈로그 원본은 유지하고 사용자에게 보일 때만 밑줄을 슬래시로 바꾼다.
export function displayFoodName(name) {
  return name.replaceAll('_', '/');
}

const sides = new Set(['반찬류', '김치류', '생채·무침류', '채소/나물', '안주/반찬']);
export function mealSummary(items) {
  const mains = items.filter(i => !sides.has(i.category));
  const sideItems = items.filter(i => sides.has(i.category));
  const shown = mains.length ? mains : sideItems;
  return shown.slice(0, 3).map(i => displayFoodName(i.food_name)).join(' · ')
    + (shown.length > 3 ? ` 외 ${shown.length - 3}개` : '')
    + (mains.length && sideItems.length ? ` + 반찬 ${sideItems.length}가지` : '');
}

export function relativeTime(value, now = Date.now()) {
  const date = new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`);
  const minutes = Math.max(0, Math.floor((now - date.getTime()) / 60000));
  if (minutes < 1) return '방금 전';
  if (minutes < 60) return `${minutes}분 전`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}시간 전`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}일 전`;
  return date.toLocaleDateString('ko-KR', {timeZone: 'Asia/Seoul'});
}
