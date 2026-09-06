import assert from 'node:assert/strict';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {chromium} from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const catalogue = JSON.parse(await readFile(path.join(root,'resources/catalogue.json'),'utf8'));
const output = path.join(root,'.tmp/browser-review');
await mkdir(output,{recursive:true});
const port = Number(process.env.QLAT_TEST_PORT || 8768);
const remoteBase = process.env.QLAT_BASE_URL;
const base = remoteBase || `http://127.0.0.1:${port}/quintessential-latin/`;
let server, browser;
const failures=[], checks=[], responses=[];
const check=(name,condition)=>{assert.ok(condition,name);checks.push(name);};
try {
  if(!remoteBase){
    server=spawn(process.execPath,['tools/serve_site.mjs','--port',String(port)],{cwd:root,stdio:['ignore','pipe','pipe'],windowsHide:true});
    let serverLog='';
    server.stdout.on('data',data=>{serverLog+=data;});
    server.stderr.on('data',data=>{serverLog+=data;});
    server.on('error',error=>failures.push(error.message));
    let ready=false;
    for(let attempt=0;attempt<100;attempt++){
      try{if((await fetch(base)).ok){ready=true;break;}}catch{}
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    assert.ok(ready,`Local preview did not start: ${serverLog}`);
  }
  browser=await chromium.launch({headless:true,...(process.env.QLAT_BROWSER_CHANNEL?{channel:process.env.QLAT_BROWSER_CHANNEL}:{})});
  const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});
  const page=await context.newPage();
  page.on('pageerror',error=>failures.push(error.message));
  page.on('response',response=>{if(response.url().startsWith(base)&&response.status()>=400)responses.push(`${response.status()} ${response.url()}`);});
  const navigate=async file=>{
    await page.goto(new URL(file,base).href,{waitUntil:'load'});
    await page.waitForFunction(()=>document.body.dataset.fonts==='ready',{timeout:20000});
    await page.evaluate(()=>document.fonts.ready);
  };
  for(const file of ['index.html','charts.html','proposal.html','downloads.html']){
    await navigate(file);
    check(`${file}: page title`,await page.locator('h1').count()===1);
    check(`${file}: shared weight control`,await page.locator('#font-weight').count()===1);
    check(`${file}: shared italic control`,await page.locator('#font-italic').count()===1);
    check(`${file}: native script font loaded`,await page.evaluate(()=>Array.from(document.fonts).some(face=>face.family.replace(/[''""]/g," ").trim()==="Quintessential Serif" && face.status==="loaded")));
    check(`${file}: document fits desktop`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.screenshot({path:path.join(output,file.replace('.html','-desktop.png')),fullPage:file!=='charts.html'});
  }
  await navigate('index.html');
  const romanHeader=await page.locator('.brand-icon').screenshot();
  const romanHero=await page.locator('.emblem-glyph').screenshot();
  check('Header and hero show the actual logo character',await page.locator('.brand-icon .glyph').textContent()===String.fromCodePoint(0xf2b18)&&await page.locator('.emblem-glyph .glyph').textContent()===String.fromCodePoint(0xf2b18));
  await page.locator('#font-weight').focus();await page.keyboard.press('End');
  await page.waitForFunction(()=>document.body.dataset.fonts==='ready');
  check('Weight changes the header logo outline',!romanHeader.equals(await page.locator('.brand-icon').screenshot()));
  check('Weight changes the hero logo outline',!romanHero.equals(await page.locator('.emblem-glyph').screenshot()));
  await page.locator('#font-weight').focus();await page.keyboard.press('Home');
  await navigate('charts.html');
  check('Four numeric screen grids',await page.locator('table[data-chart-kind="screen"]').count()===4);
  check('Eight print grids',await page.locator('table[data-chart-kind="print"]').count()===8);
  const screenCells=page.locator('table[data-chart-kind="screen"] td[data-codepoint]');
  check('All 1024 code positions represented',await page.locator('table[data-chart-kind="screen"] td').count()===1024);
  const assigned=page.locator('table[data-chart-kind="screen"] td [data-glyph]');
  check('All 832 assigned positions represented',await assigned.count()===832);
  const names=page.locator('[data-name-codepoint]');
  check('All 832 names represented',await names.count()===832);
  const ordering=await names.evaluateAll(elements=>elements.map(element=>element.getAttribute('data-name-codepoint')));
  const parseCode=value=> /^[0-9]+$/.test(value)&&Number(value)>0xffff ? Number(value) : parseInt(value.replace(/^U\+/i,''),16);
  check('Formal names are in numeric order',ordering.map(parseCode).join()===catalogue.entries.map(entry=>entry.codePoint).sort((a,b)=>a-b).join());
  check('Initial posture is Roman',await page.locator('html').getAttribute('data-posture')==='Roman');
  const controls=()=>page.locator('.weight-control,.italic-control').evaluateAll(elements=>elements.map(element=>{const {x,y,width,height}=element.getBoundingClientRect();return {x,y,width,height};}));
  const romanControls=await controls();
  await page.locator('#font-weight').focus();
  await page.keyboard.press('End');
  check('Weight responds to real keyboard input',await page.locator('#font-weight').inputValue()==='700');
  await page.locator('#font-italic').check();
  await page.waitForFunction(()=>document.body.dataset.fonts==='ready');
  check('Native Italic selected',await page.locator('html').getAttribute('data-posture')==='Italic');
  const visiblePending=await page.locator('table[data-chart-kind="screen"] .pending-label').evaluateAll(elements=>elements.filter(element=>element.getClientRects().length>0).length);
  check('600 Italic pending variants clearly shown',visiblePending===600);
  const native=await page.locator('table[data-chart-kind="screen"] .glyph-wrap[data-italic="true"] .glyph').first().evaluate(element=>({weight:getComputedStyle(element).fontWeight,style:getComputedStyle(element).fontStyle,synthesis:getComputedStyle(element).fontSynthesis}));
  check('Selected weight and native posture reach chart glyphs',native.weight==='700'&&native.style==='italic'&&native.synthesis==='none');
  check('Successful font loading leaves no status beside Italic',await page.locator('#font-status').textContent()===''&&!(await page.locator('#font-status').isVisible()));
  check('Changing posture keeps controls in place',JSON.stringify(await controls())===JSON.stringify(romanControls));
  await navigate('index.html');
  check('Preferences persist across navigation',await page.locator('#font-weight').inputValue()==='700'&&await page.locator('#font-italic').isChecked());
  await page.reload({waitUntil:'load'});
  await page.waitForFunction(()=>document.body.dataset.fonts==='ready');
  check('Preferences persist across reload',await page.locator('#font-weight').inputValue()==='700'&&await page.locator('#font-italic').isChecked());
  check('Missing native Italic logo uses the shared pending state',await page.locator('.brand-icon .pending-label').isVisible()&&await page.locator('.emblem-glyph .pending-label').isVisible()&&!(await page.locator('.brand-icon .glyph').isVisible())&&!(await page.locator('.emblem-glyph .glyph').isVisible()));
  const logoStyles=await page.locator('.brand-icon .glyph,.emblem-glyph .glyph').evaluateAll(elements=>elements.map(element=>({weight:getComputedStyle(element).fontWeight,style:getComputedStyle(element).fontStyle,synthesis:getComputedStyle(element).fontSynthesis})));
  check('Both project marks share the selected weight and native posture',logoStyles.every(style=>style.weight==='700'&&style.style==='italic'&&style.synthesis==='none'));
  await page.locator('#font-italic').uncheck();
  await page.locator('#font-weight').focus();
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowRight');
  check('Intermediate weight supported',await page.locator('#font-weight').inputValue()==='401');
  await navigate('charts.html');
  await page.locator('#character-search').fill('U+F2B00');
  await page.waitForTimeout(180);
  const result=page.locator('#search-results [data-glyph]');
  check('Code search finds one exact character',await result.count()===1);
  await result.first().click();
  check('Character details open',await page.locator('#character-dialog').isVisible());
  await page.locator('#copy-character').click();
  const copied=await page.evaluate(()=>navigator.clipboard.readText());
  check('Copy preserves supplementary-plane scalar',copied===String.fromCodePoint(0xF2B00));
  await page.locator('#copy-code').click();
  check('Copy code uses Unicode notation',await page.evaluate(()=>navigator.clipboard.readText())==='U+F2B00');
  await page.keyboard.press('Escape');
  check('Escape closes character details',!(await page.locator('#character-dialog').isVisible()));
  await page.locator('#character-search').fill('xyz-no-such-construction');
  await page.waitForTimeout(180);
  check('Empty search is explained',/no|0/i.test(await page.locator('#result-count').innerText()));
  await page.locator('#character-search').fill('');
  await page.waitForTimeout(180);
  await assigned.first().focus();
  await page.keyboard.press('ArrowRight');
  const focused=await page.evaluate(()=>document.activeElement?.getAttribute('data-glyph'));
  check('Arrow navigation moves one hexadecimal column',focused===catalogue.entries.find(entry=>entry.codePoint===0xF2A10).glyphId);
  await page.locator('table[data-chart-kind="screen"] td[data-codepoint="F2A0F"] .chart-cell').focus();
  await page.keyboard.press('ArrowDown');
  check('ArrowDown stops at row F within its hexadecimal column',await page.evaluate(()=>document.activeElement.getAttribute('data-code'))===String(0xF2A0F));
  await page.locator('table[data-chart-kind="screen"] td[data-codepoint="F2A10"] .chart-cell').focus();
  await page.keyboard.press('ArrowUp');
  check('ArrowUp stops at row 0 within its hexadecimal column',await page.evaluate(()=>document.activeElement.getAttribute('data-code'))===String(0xF2A10));
  await navigate('charts.html#u-f2b00');
  check('Character deep link resolves',await page.locator('#u-f2b00').count()===1);
  if(await page.locator('#character-dialog').isVisible())await page.keyboard.press('Escape');

  for(const width of [375,768,1440]){
    await page.setViewportSize({width,height:1000});
    for(const file of ['index.html','charts.html','proposal.html','downloads.html']){
      await navigate(file);
      check(`${file}: fits ${width}px viewport`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      if(file==='index.html'){
        const before=await controls(),headerBounds=await page.locator('.brand-icon').boundingBox(),heroBounds=await page.locator('.emblem-glyph').boundingBox();
        await page.locator('#font-italic').check();
        await page.waitForFunction(()=>document.body.dataset.fonts==='ready');
        const after={controls:await controls(),header:await page.locator('.brand-icon').boundingBox(),hero:await page.locator('.emblem-glyph').boundingBox()},expected={controls:before,header:headerBounds,hero:heroBounds};
        assert.deepEqual(after,expected,`${width}px: posture keeps controls and logo spaces stable`);
        checks.push(`${width}px: posture keeps controls and logo spaces stable`);
        await page.locator('#font-italic').uncheck();
        await page.waitForFunction(()=>document.body.dataset.fonts==='ready');
      }
      await page.screenshot({path:path.join(output,file.replace('.html',`-${width}.png`)),fullPage:file!=='charts.html'});
    }
  }
  await page.setViewportSize({width:1440,height:1000});
  await navigate('charts.html');
  await page.locator('#font-weight').focus();await page.keyboard.press('End');
  await page.locator('#font-italic').check();
  await page.waitForFunction(()=>document.body.dataset.fonts==='ready');
  await page.screenshot({path:path.join(output,'charts-italic-700.png')});
  await page.emulateMedia({media:'print'});
  check('Printed control bar is hidden',!(await page.locator('.font-bar').isVisible()));
  check('Print posture annotation is current',/Italic/.test(await page.locator('[data-print-posture]').first().innerText()));
  check('Print weight annotation is current',/700/.test(await page.locator('[data-print-weight]').first().innerText()));
  await page.emulateMedia({media:'screen'});
  check('No JavaScript exceptions',failures.length===0);
  check('No failed same-site asset requests',responses.length===0);
  await context.close();

  const noJs=await browser.newContext({javaScriptEnabled:false,viewport:{width:1024,height:900}});
  const staticPage=await noJs.newPage();
  await staticPage.goto(new URL('charts.html',base).href);
  check('Charts work without JavaScript',await staticPage.locator('table[data-chart-kind="screen"] td [data-glyph]').count()===832);
  await noJs.close();

  const fontFailure=await browser.newContext();
  const failedPage=await fontFailure.newPage();
  await failedPage.route('**/QuintessentialSerif/*.woff2',route=>route.abort());
  await failedPage.goto(new URL('index.html',base).href);
  await failedPage.waitForFunction(()=>document.body.dataset.fonts==='error',{timeout:20000});
  check('Font load failure is explicit',await failedPage.locator('#font-status').isVisible()&&/load|unavailable|failed/i.test(await failedPage.locator('#font-status').innerText()));
  await fontFailure.close();
  await writeFile(path.join(output,'report.json'),JSON.stringify({base,checks:checks.length,passed:checks,errors:failures,failedResponses:responses},null,2));
  console.log(`Passed ${checks.length} browser checks; screenshots in .tmp/browser-review.`);
} finally {
  if(browser)await browser.close();
  if(server)server.kill();
}
