import {test,expect} from '@playwright/test';
test('email opens in an accessible modal and authenticates with existing API',async({page})=>{
 let authenticated=false,submitted;
 await page.route('**/api/**',async route=>{const path=new URL(route.request().url()).pathname;
  if(path.endsWith('/users/me'))return route.fulfill(authenticated?{json:{user:{id:99,name:'테스트',email:'test@example.com'}}}:{status:401,json:{error:{message:'로그인 필요'}}});
  if(path.endsWith('/auth/login')){submitted=route.request().postDataJSON();if(submitted.password==='wrongpass')return route.fulfill({status:401,json:{error:{message:'이메일 또는 비밀번호를 확인해 주세요.'}}});authenticated=true;return route.fulfill({json:{user:{id:99,name:'테스트',email:'test@example.com'}}});}
  if(path.endsWith('/auth/logout')){authenticated=false;return route.fulfill({json:{message:'로그아웃 완료'}});}
  const data=path.endsWith('/foods')?{items:[]}:path.endsWith('/auth/policy')?{age_min:18,signup_enabled:true,service_consent_text:'테스트 동의'}:path.endsWith('/auth/social/policy')?{google:{enabled:true,authorization_code_enabled:true}}:path.endsWith('/analytics/today')?{date:'2026-10-07',meals:[],totals:{cal:0,carbs:0,protein:0,fat:0,sugar:0,sodium:0}}:path.endsWith('/meals/history')?{items:[]}:path.endsWith('/users/me/profile')?{profile:null}:{};
  return route.fulfill({json:data});});
 await page.addInitScript(()=>sessionStorage.setItem('calodetect-page','로그인'));
 await page.goto('http://localhost:5174');
 await expect(page.locator('.auth-welcome')).toBeVisible();await expect(page.locator('.auth-garden canvas')).toBeVisible();
 await expect(page.getByRole('textbox',{name:'이메일',exact:true})).toBeHidden();
 await page.getByRole('button',{name:'이메일로 시작하기'}).click();
 const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();await expect(dialog.getByLabel('이메일',{exact:true})).toBeFocused();
 await page.keyboard.press('Escape');await expect(dialog).toBeHidden();await expect(page.getByRole('button',{name:'이메일로 시작하기'})).toBeFocused();
 await page.getByRole('button',{name:'이메일로 시작하기'}).click();await dialog.getByRole('button',{name:'회원가입',exact:true}).click();await expect(dialog.getByLabel('만 나이')).toBeVisible();
 await dialog.getByRole('button',{name:'로그인',exact:true}).first().click();await dialog.getByLabel('이메일',{exact:true}).fill('test@example.com');await dialog.getByLabel('비밀번호',{exact:true}).fill('wrongpass');await dialog.locator('button.primary').click();await expect(dialog.getByRole('alert')).toContainText('비밀번호를 확인');
 await page.screenshot({path:'test-results/email-modal.png',fullPage:true});
 await dialog.getByLabel('비밀번호',{exact:true}).fill('correctpass');await dialog.locator('button.primary').click();await expect(page.locator('.daily-home')).toBeVisible();expect(submitted.email).toBe('test@example.com');
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'마이페이지',exact:true}).click();await expect(page.locator('.account-logout')).toBeVisible();await page.locator('.account-logout').click();await expect(page.locator('.auth-welcome')).toBeVisible();expect(authenticated).toBe(false);await expect(page.locator('.account-logout')).toHaveCount(0);
});
test('welcome layout fits the mobile reference',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.route('**/api/**',route=>{const path=new URL(route.request().url()).pathname;if(path.endsWith('/users/me'))return route.fulfill({status:401,json:{error:{message:'로그인 필요'}}});return route.fulfill({json:path.endsWith('/foods')?{items:[]}:path.endsWith('/auth/social/policy')?{google:{enabled:true,authorization_code_enabled:true}}:{age_min:18}});});
 await page.addInitScript(()=>sessionStorage.setItem('calodetect-page','로그인'));await page.goto('http://localhost:5174');await expect(page.locator('.auth-garden canvas')).toBeVisible();const box=await page.locator('.auth-welcome').boundingBox();expect(box.x+box.width).toBeLessThanOrEqual(390);await page.screenshot({path:'test-results/auth-welcome-mobile.png',fullPage:true});
});
