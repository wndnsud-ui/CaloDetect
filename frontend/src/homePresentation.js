export const MEAL_LABELS = {breakfast:'아침', lunch:'점심', dinner:'저녁', snack:'간식'};
export const homeNumber = value => Number.isFinite(value) ? value.toLocaleString('ko-KR', {maximumFractionDigits:1}) : '—';

export function mealAt(instant = new Date()) {
  const hour = Number(new Intl.DateTimeFormat('en-US', {timeZone:'Asia/Seoul', hour:'2-digit', hourCycle:'h23'}).format(instant));
  return hour <= 10 ? 'breakfast' : hour <= 14 ? 'lunch' : hour >= 17 && hour <= 21 ? 'dinner' : 'snack';
}

export function homePrompt(meals = [], currentDay = true, instant = new Date()) {
  const type = mealAt(instant), label = MEAL_LABELS[type];
  const count = new Set(meals.map(meal => meal.meal_type)).size;
  const recorded = meals.some(meal => meal.meal_type === type);
  return {type, label, recorded, title: !currentDay ? '선택한 날의 식단을 돌아보세요.' : recorded
    ? `${label} 기록 완료! 다음 메뉴가 고민되면 지방이에게 물어보세요.`
    : `${label} 시간이에요! ${count === 0 ? '오늘 첫 끼를' : count === 1 ? '오늘 두 번째 끼니를' : '다음 한 끼를'} 남겨볼까요?`};
}

export function mealFeedback(meals = [], targets) {
  const meal = meals.find(row => row.items?.some(item => Number.isFinite(item.nutrition?.protein)));
  if (!meal) return meals.length ? '식단을 남겼어요! 알고 있는 영양값을 더하면 섭취량을 확인할 수 있어요.' : '첫 끼를 기록하면 먹은 음식과 영양을 함께 살펴볼 수 있어요.';
  const protein = meal.items.reduce((sum,item) => sum + (item.nutrition?.protein || 0), 0);
  const name = meal.items.filter(item => Number.isFinite(item.nutrition?.protein)).map(item=>item.food_name).filter(Boolean).join('·') || '식사';
  const totals = meals.flatMap(row => row.items || []).reduce((sum,item) => ({carbs:sum.carbs+(item.nutrition?.carbs||0), protein:sum.protein+(item.nutrition?.protein||0), fat:sum.fat+(item.nutrition?.fat||0)}), {carbs:0,protein:0,fat:0});
  const short = Object.entries(targets || {}).filter(([key,value]) => value > 0 && totals[key] != null && totals[key] < value).sort(([a,av],[b,bv]) => totals[a]/av-totals[b]/bv)[0];
  const advice = short ? `다음 끼니는 ${{carbs:'탄수화물',protein:'단백질',fat:'지방'}[short[0]]}도 함께 살펴보세요.` : '다음 끼니엔 채소도 함께 챙겨 보세요.';
  return `${MEAL_LABELS[meal.meal_type] || '식사'} ${name}으로 단백질 ${homeNumber(protein)}g을 기록했어요! ${advice}`;
}
