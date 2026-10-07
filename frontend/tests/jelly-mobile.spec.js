import {test,expect} from '@playwright/test';
test('GLB jelly works with touch, reduced motion and model fallback',async({browser})=>{
 const context=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',route=>{const path=new URL(route.request().url()).pathname;let data={};if(path.endsWith('/users/me'))data={user:{id:99,name:'테스트',email:'test@example.com'}};else if(path.endsWith('/foods')||path.endsWith('/meals/history'))data={items:[]};else if(path.endsWith('/users/me/profile'))data={profile:null};return route.fulfill({json:data});});
 await page.addInitScript(()=>sessionStorage.setItem('calodetect-page','내 지방이'));await page.goto('http://localhost:5174');
 const host=page.locator('.interactive .jibangi-canvas'),canvas=host.locator('canvas');await expect(host).toHaveAttribute('data-model','glb');await canvas.scrollIntoViewIfNeeded();
 const box=await canvas.boundingBox(),x=box.x+box.width/2,y=box.y+box.height/2;const cdp=await context.newCDPSession(page);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+85,y}]});await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await page.getByRole('button',{name:'정면',exact:true}).click();await page.touchscreen.tap(x,y);
 await expect.poll(()=>host.getAttribute('data-fps')).not.toBeNull();console.log('Jelly viewer mobile emulation browser FPS:',await host.getAttribute('data-fps'));
 await page.emulateMedia({reducedMotion:'reduce'});const before=await canvas.screenshot();await page.getByRole('button',{name:'오른쪽 회전'}).click();await expect.poll(async()=>Buffer.compare(before,await canvas.screenshot())).not.toBe(0);
 const controls=await page.locator('.model-controls').boundingBox(),caption=await page.locator('.character-stage h2').boundingBox();expect(controls.y+controls.height).toBeLessThan(caption.y);
 await page.screenshot({path:'test-results/jelly-touch-mobile.png',fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await page.route('**/models/**',route=>route.abort());await page.reload();await expect(page.locator('.interactive .jibangi-canvas')).toHaveAttribute('data-model','fallback');await expect(page.getByText('모델을 불러오지 못해 기본 3D로 표시하고 있어요.')).toBeVisible();expect(errors).toEqual([]);await context.close();
});
