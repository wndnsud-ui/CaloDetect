import assert from 'node:assert/strict';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const browser=await chromium.launch({channel:'msedge',headless:true});
const base=process.env.PREVIEW_URL||'http://localhost:5174';
try{
  for(const width of [1440,390]){
    const page=await browser.newPage({viewport:{width,height:900}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`${base}/tests/meal-history.html`);
    const original=JSON.parse(await page.getByTestId('history-snapshot').textContent())[0];
    await page.locator('.history-toolbar select').first().selectOption('lunch');
    await page.getByRole('combobox',{name:'쌀밥 식사 구분 변경'}).selectOption('dinner');
    await page.getByText('점심에서 저녁으로 변경했어요.',{exact:true}).waitFor();
    assert.equal(await page.getByRole('combobox',{name:'추어탕 식사 구분 변경'}).inputValue(),'dinner');
    assert.equal(await page.locator('.history-toolbar select').first().inputValue(),'all');
    const saved=JSON.parse(await page.getByTestId('history-snapshot').textContent())[0];
    assert.equal(saved.meal_type,'dinner');assert.deepEqual(saved.items,original.items);
    const calls=await page.evaluate(()=>window.__historyCalls);
    assert.equal(calls.length,1);assert.deepEqual(calls[0].body,{meal_type:'dinner',expected_version:1});
    assert.equal(calls[0].method,'PATCH');
    await page.getByRole('combobox',{name:'추어탕 식사 구분 변경'}).selectOption('breakfast');
    await page.getByText('저녁에서 아침으로 변경했어요.',{exact:true}).waitFor();
    assert.equal(await page.getByRole('combobox',{name:'쌀밥 식사 구분 변경'}).inputValue(),'breakfast');
    await page.screenshot({path:`.runtime-logs/meal-history-type-${width}.png`,fullPage:true});
    await page.goto(`${base}/tests/meal-history.html?failure`);
    await page.getByRole('combobox',{name:'쌀밥 식사 구분 변경'}).selectOption('dinner');
    await page.getByRole('alert').waitFor();
    assert.equal(await page.getByRole('combobox',{name:'쌀밥 식사 구분 변경'}).inputValue(),'lunch');
    assert.equal(await page.getByRole('combobox',{name:'추어탕 식사 구분 변경'}).inputValue(),'lunch');
    assert.deepEqual(errors,[]);console.log(`PASS ${width}px: lunch -> dinner directly in history, shared meal rows, zero-consumption preserved, stale version refresh, failure rollback`);
    await page.close();
  }
}finally{await browser.close();}
