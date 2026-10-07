import {test,expect} from '@playwright/test';
import {progress,streak} from '../src/engagement.js';
test('duplicate records do not duplicate rewards; challenge rewards require participation',()=>{
 const meals=[{id:1,meal_date:'2026-10-01'},{id:2,meal_date:'2026-10-02'},{id:3,meal_date:'2026-10-03'}];
 expect(progress([...meals,meals[0]]).points).toBe(60);
 expect(progress(meals,['record3']).points).toBe(100);
 expect(progress(meals.slice(0,2),['record3']).points).toBe(40);
 expect(progress(Array.from({length:13},(_,i)=>({id:i,meal_date:'2026-10-01'}))).level).toBe(4);
 expect(streak([{meal_date:'2026-09-30'},{meal_date:'2026-10-01'}],'2026-10-02')).toBe(2);
 expect(streak([{meal_date:'2026-10-01'}],'2026-10-03')).toBe(0);
});
test('3D scene renders, rotates, pauses and challenge navigation works',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/api/**',route=>{const path=new URL(route.request().url()).pathname;let data={};
  if(path.endsWith('/users/me'))data={user:{id:99,name:'테스트',email:'test@example.com'}};
  else if(path.endsWith('/foods'))data={items:[]};
  else if(path.endsWith('/auth/policy'))data={age_min:18};
  else if(path.endsWith('/meals/history'))data={items:[{id:1,meal_date:'2026-10-01',items:[]},{id:2,meal_date:'2026-10-02',items:[]},{id:3,meal_date:'2026-10-03',items:[]}]};
  else if(path.endsWith('/users/me/profile'))data={profile:null};
  else if(path.endsWith('/analytics/today'))data={date:'2026-10-07',totals:{cal:0},meals:[]};
  return route.fulfill({json:data});});
 await page.addInitScript(()=>sessionStorage.setItem('calodetect-page','내 지방이'));
 await page.goto('http://localhost:5174');
 await expect(page.locator('.jibangi-canvas canvas')).toHaveCount(4);
 await expect(page.locator('.interactive .jibangi-canvas')).toHaveAttribute('data-model','glb');
 await expect(page.getByRole('button',{name:'정면',exact:true})).toBeVisible();
 const canvas=page.locator('.interactive canvas');const box=await canvas.boundingBox();
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+90,box.y+box.height/2);await page.mouse.up();
 await page.getByRole('button',{name:'정면',exact:true}).click();await page.getByRole('button',{name:'손 흔들기',exact:true}).click();
 await page.getByRole('button',{name:'톡 점프',exact:true}).click();
 await expect.poll(()=>page.locator('.interactive .jibangi-canvas').getAttribute('data-fps')).not.toBeNull();
 console.log('Jelly viewer desktop browser FPS:',await page.locator('.interactive .jibangi-canvas').getAttribute('data-fps'));
 await page.getByRole('button',{name:'동작 멈춤',exact:true}).click();await expect(page.getByRole('button',{name:'움직이기',exact:true})).toBeVisible();
 await page.locator('.outfit-options').scrollIntoViewIfNeeded();await expect(page.locator('.outfit-options [data-model="glb"]')).toHaveCount(3);await page.locator('.interactive').scrollIntoViewIfNeeded();await page.screenshot({path:'test-results/character-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'챌린지',exact:true}).click();await page.getByRole('button',{name:'챌린지 참여하기'}).first().click();await expect(page.getByRole('button',{name:'완료했어요 ✓'})).toBeVisible();
 await page.getByRole('button',{name:'코치 추천',exact:true}).click();await page.getByRole('button',{name:'코칭 내용 살펴보기'}).first().click();await expect(page.getByRole('heading',{name:'함께 살펴볼 내용'})).toBeVisible();
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'내 지방이',exact:true}).click();await expect(page.locator('.interactive canvas')).toBeVisible();await page.screenshot({path:'test-results/character-mobile.png',fullPage:true});
 expect(errors).toEqual([]);
});

test('menu input fills the panel and local activity/feed actions persist',async({page})=>{
 await page.route('**/api/**',route=>{const path=new URL(route.request().url()).pathname;let data={};if(path.endsWith('/users/me'))data={user:{id:99,name:'테스트',email:'test@example.com'}};else if(path.endsWith('/foods'))data={items:[]};else if(path.endsWith('/meals/history'))data={items:[]};else if(path.endsWith('/users/me/profile'))data={profile:null};return route.fulfill({json:data});});
 await page.addInitScript(()=>sessionStorage.setItem('calodetect-page','메뉴판 분석'));
 await page.goto('http://localhost:5174');
 const input=page.getByRole('textbox',{name:'한 줄에 메뉴 한 개'});await expect(input).toBeVisible();const box=await input.boundingBox();expect(box.width).toBeGreaterThan(350);await input.fill('김치찌개\n비빔밥');await expect(page.getByText('2개 이름 · 기존 데이터와 일치한 메뉴 0개')).toBeVisible();
 await page.getByRole('button',{name:'운동·활동',exact:true}).click();await page.getByRole('button',{name:'완료한 활동 기록'}).first().click();await expect(page.getByRole('status')).toContainText('기록을 저장');
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'메뉴판 분석',exact:true}).click();await expect(input).toBeVisible();const mobile=await input.boundingBox();expect(mobile.width).toBeGreaterThan(200);expect(mobile.x+mobile.width).toBeLessThanOrEqual(391);await page.screenshot({path:'test-results/menu-mobile.png',fullPage:true});
});
