// Internal experiment settings; rewards are not redeemable or a production policy.
export const EXPERIMENT={mealPoints:20,thresholds:[0,60,140,260]};
export const challenges=[{id:'record3',title:'한 끼씩, 3일 기록',description:'서로 다른 3일에 식단을 기록해요.',days:3,reward:40},{id:'record7',title:'나의 일주일 만들기',description:'서로 다른 7일의 식단을 모아보세요.',days:7,reward:80},{id:'record14',title:'차곡차곡 14일',description:'14일의 기록으로 내 습관을 살펴봐요.',days:14,reward:140}];
export function streak(history,today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}).format(new Date())){
 const dates=new Set(history.map(meal=>meal.meal_date));const day=new Date(`${today}T12:00:00Z`);
 if(!dates.has(today))day.setUTCDate(day.getUTCDate()-1);
 let count=0;while(dates.has(day.toISOString().slice(0,10))){count++;day.setUTCDate(day.getUTCDate()-1);}return count;
}
export function progress(history,joined=[]){const unique=new Map(history.map(meal=>[meal.id,meal]));const dates=new Set([...unique.values()].map(meal=>meal.meal_date));const completed=challenges.filter(c=>joined.includes(c.id)&&dates.size>=c.days);const ledger=[...unique.values()].map(meal=>({id:`meal-${meal.id}`,title:'식단 기록',date:meal.meal_date,points:EXPERIMENT.mealPoints})).concat(completed.map(c=>({id:c.id,title:c.title,date:'챌린지 완료',points:c.reward})));const points=ledger.reduce((sum,event)=>sum+event.points,0);const level=EXPERIMENT.thresholds.filter(n=>points>=n).length;return {points,level,dates:dates.size,ledger,completed,next:EXPERIMENT.thresholds[level]??null};}
export function readJoined(user){try{const parsed=JSON.parse(localStorage.getItem(`calodetect-challenges-${user?.id||'guest'}`)||'[]');return Array.isArray(parsed)?parsed.filter(id=>challenges.some(c=>c.id===id)):[];}catch{return [];}}
