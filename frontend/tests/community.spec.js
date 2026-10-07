import {test,expect} from '@playwright/test';
test('card board supports creation, reactions, comment editing and mobile',async({page})=>{
 let posts=[{id:'one',title:'오늘의 샐러드',text:'맛있게 먹었어요',category:'meal',visibility:'public',author:'다른 회원',owned:false,created_at:'2026-10-07T01:00:00Z',image_url:null,likes:2,recommendations:1,comments:0,liked:false,recommended:false,comment_items:[]}];
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname,method=request.method();let data={};
  if(path.endsWith('/users/me'))data={user:{id:99,name:'테스트',email:'test@example.com'}};
  else if(path.endsWith('/foods')||path.endsWith('/meals/history'))data={items:[]};
  else if(path.endsWith('/users/me/profile'))data={profile:null};
  else if(path==='/api/community/posts'){
   if(method==='POST'){posts.unshift({...posts[0],id:'two',title:'새 기록',text:'오늘 운동',author:'테스트',owned:true,likes:0,recommendations:0,comments:0,comment_items:[]});data=posts[0];}
   else data={items:posts.filter(p=>url.searchParams.get('scope')==='mine'?p.owned:url.searchParams.get('scope')==='others'?!p.owned:true),has_more:false};
  }else if(path.startsWith('/api/community/posts/')){
   const parts=path.split('/'),post=posts.find(p=>p.id===parts[4]);
   if(parts[5]==='reactions'){const active=request.postDataJSON().active,key=parts[6]==='like'?'liked':'recommended',count=key==='liked'?'likes':'recommendations';post[count]+=active?1:-1;post[key]=active;}
   if(parts[5]==='comments'){
    if(parts[7]==='delete'){post.comment_items=[];post.comments=0;}
    else if(method==='PUT')post.comment_items[0].text=request.postDataJSON().text;
    else if(method==='POST'){post.comment_items.push({id:'c1',text:request.postDataJSON().text,author:'테스트',owned:true});post.comments++;}
   }
   data=post;
  }
  await route.fulfill({json:data});
 });
 await page.addInitScript(()=>sessionStorage.setItem('calodetect-page','커뮤니티'));
 await page.goto('http://localhost:5174');
 await page.getByRole('button',{name:'다른 회원 둘러보기'}).click();
 await expect(page.getByRole('button',{name:'다른 회원 둘러보기'})).toHaveAttribute('aria-pressed','true');
 const sample=page.getByRole('button',{name:'오늘은 연어 샐러드 한 그릇 게시글 보기'});
 await expect(sample).toBeVisible();
 await expect(sample.locator('img')).toBeVisible();
 await sample.scrollIntoViewIfNeeded();await expect.poll(()=>sample.locator('img').evaluate(img=>img.complete&&img.naturalWidth>0)).toBe(true);
 await sample.click();const preview=page.getByRole('dialog',{name:'오늘은 연어 샐러드 한 그릇'});
 await expect(preview.getByText('예시 게시글',{exact:true})).toBeVisible();
 await preview.getByLabel('댓글 내용').fill('예시 응원');await preview.getByRole('button',{name:'댓글 남기기'}).click();await expect(preview.locator('.board-comments')).toContainText('예시 응원');
 await preview.getByRole('button',{name:'팝업 닫기'}).click();
 await page.getByRole('button',{name:'내가 쓴 글',exact:true}).click();await expect(sample).toHaveCount(0);
 await page.getByRole('button',{name:'전체 기록',exact:true}).click();
 await expect(page.getByRole('button',{name:'오늘의 샐러드 게시글 보기'})).toBeVisible();
 await page.getByRole('button',{name:'오늘의 샐러드 좋아요'}).click();
 await expect(page.getByRole('button',{name:'오늘의 샐러드 좋아요'})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'오늘의 샐러드 추천',exact:true}).click();
 await page.locator('.board-sort select').selectOption('best');
 await expect(page.getByText('좋아요가 많은 기록부터 보여드려요.')).toBeVisible();
 await page.getByRole('button',{name:'오늘의 샐러드 댓글 보기'}).click();
 const dialog=page.getByRole('dialog',{name:'오늘의 샐러드'});
 await dialog.getByLabel('댓글 내용').fill('응원해요');await dialog.getByRole('button',{name:'댓글 남기기'}).click();
 await expect(dialog.locator('.board-comment')).toContainText('응원해요');
 await dialog.getByRole('button',{name:'수정',exact:true}).click();await dialog.getByLabel('댓글 수정').fill('함께해요');await dialog.getByRole('button',{name:'수정 저장'}).click();
 await expect(dialog.locator('.board-comment')).toContainText('함께해요');
 await dialog.getByRole('button',{name:'삭제',exact:true}).click();await expect(dialog.locator('.board-comment')).toHaveCount(0);
 await dialog.getByRole('button',{name:'팝업 닫기'}).click();
 await page.getByRole('button',{name:'＋ 글쓰기'}).click();const composer=page.getByRole('dialog',{name:'오늘의 이야기 남기기'});
 await composer.getByLabel('제목', {exact:true}).fill('새 기록');await composer.getByLabel('내용',{exact:true}).fill('오늘 운동');await expect(composer.getByLabel('공개 범위')).toHaveValue('private');await composer.getByLabel('공개 범위').selectOption('public');await composer.getByRole('button',{name:'게시글 저장'}).click();
 await expect(page.getByRole('button',{name:'새 기록 게시글 보기'})).toBeVisible();
 await page.screenshot({path:'test-results/community-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'test-results/community-mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);expect(errors).toEqual([]);
});
