// Fictional preview records: never sent to the member database.
const records=[
 ['salad','초록한끼','오늘은 연어 샐러드 한 그릇','아삭한 채소에 연어를 곁들였어요. 여러분의 오늘 한 끼는 어떤가요?','meal','/images/feature-meal.webp.png',24,12],
 ['bowl','한끼연구소','바쁜 날에도 든든하게','좋아하는 재료로 간단한 한 그릇을 만들었어요. 색깔이 예뻐서 기록으로 남겨봅니다.','meal','/images/cta-poke.webp.png',38,19],
 ['walk','산책하는날','점심 먹고 동네 한 바퀴','오늘은 잠깐이라도 밖으로 나왔어요. 가까운 산책 코스를 찾는 재미가 있네요.','exercise','/images/feature-nearby.webp.png',17,8],
 ['challenge','꾸준한새싹','일주일 기록 챌린지, 함께해요','완벽한 식단보다 꾸준히 기록하는 습관부터! 오늘도 작은 목표 하나를 채웠어요.','challenge','/images/feature-nutrition.webp.png',31,15],
 ['menu','맛있는습관','다음 한 끼 아이디어 모으기','매일 뭘 먹을지 고민될 때 참고할 메뉴를 모으고 있어요. 좋아하는 한 끼를 추천해주세요.','meal','/images/feature-recommendation.webp.png',12,22],
];
export function samplePosts(){return records.map(([id,author,title,text,category,image_url,likes,recommendations],i)=>({id:`sample-${id}`,sample:true,author,title,text,category,image_url,likes,recommendations,visibility:'public',owned:false,liked:false,recommended:false,created_at:`2026-10-07T0${5-i}:00:00Z`,comments:1,comment_items:[{id:`sample-comment-${id}`,author:'응원하는새싹',text:'작은 습관을 함께 만들어가요 🌱',owned:false}]}));}
