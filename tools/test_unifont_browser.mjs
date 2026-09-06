import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {chromium} from 'playwright';
import {sha256} from './build_unifont_glyphs.mjs';
import {bitmapSvg} from '../site/assets/unifont-model.mjs';

const root=fileURLToPath(new URL('../',import.meta.url));
const metadata=JSON.parse(await readFile(path.join(root,'resources/unifont/glyphs.json'),'utf8'));
const output=path.join(root,'.tmp/unifont-review');await mkdir(output,{recursive:true});
const port=Number(process.env.QLAT_TEST_PORT||8773),base=process.env.QLAT_BASE_URL||`http://127.0.0.1:${port}/quintessential-latin/`;
let browser,server;
const checks=[],errors=[],images=[];
const check=(name,condition)=>{assert.ok(condition,name);checks.push(name);};
try{
  if(!process.env.QLAT_BASE_URL){
    server=spawn(process.execPath,['tools/serve_site.mjs','--port',String(port)],{cwd:root,stdio:'ignore',windowsHide:true});
    server.on('error',error=>errors.push(error.message));
    for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(resolve=>setTimeout(resolve,100));}
  }
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const page=await context.newPage();
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{if(response.url().startsWith(base)&&response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
  const navigate=async file=>{await page.goto(new URL(file,base).href);await page.evaluate(()=>document.fonts.ready);};
  const interactive=async hash=>{await navigate('unifont.html'+hash);await page.waitForFunction(()=>document.body.dataset.unifont==='ready');};
  for(const width of [1440,375]){
    await page.setViewportSize({width,height:1000});await interactive('#bitmap-f2ebf');
    check(`${width}px direct link selects dense shared spine`,await page.locator('#unifont-inspector #bitmap-f2ebf').count()===1);
    check(`${width}px selected chart sheet opens`,await page.locator('.unifont-sheet').last().getAttribute('open')!==null);
    check(`${width}px direct link reveals inspector`,await page.locator('#unifont-inspector').evaluate(element=>{const r=element.getBoundingClientRect();return r.top>=0&&r.top<innerHeight/2;}));
    check(`${width}px page fits viewport`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.screenshot({path:path.join(output,`inspector-${width}.png`)});
    await interactive('#bitmap-f2a03');
    await page.locator('[data-unifont-code="F2A03"] .bitmap-cell').focus();await page.keyboard.press('ArrowDown');
    check(`${width}px keyboard follows row order`,new URL(page.url()).hash==='#bitmap-f2a04'&&await page.locator('[data-unifont-code="F2A04"] .bitmap-cell').evaluate(el=>el===document.activeElement));
    await page.goBack();await page.waitForFunction(()=>document.querySelector('#unifont-inspector #bitmap-f2a03'));
    check(`${width}px history restores selection`,await page.locator('.bitmap-cell[aria-current="true"]').getAttribute('href')==='unifont/proofs/stems.html#bitmap-f2a03');
  }
  await page.setViewportSize({width:1440,height:1000});
  for(const proof of ['primitives','pairs','stress','expansions']){
    await navigate(`unifont/proofs/${proof}.html`);
    const cards=page.locator('.foundation-card');
    if(proof==='expansions')check('Complete first-group proof contains all 136 drawings',await cards.count()===136);
    for(let i=0;i<await cards.count();i++){
      const card=cards.nth(i),id=await card.getAttribute('data-proof-glyph'),glyph=metadata.glyphs.find(g=>g.glyphId===id);
      if(images.some(image=>image.glyphId===id))continue;
      const d=await card.locator('.foundation-drawings .bitmap').first().locator('path').first().getAttribute('d');
      check(`${glyph.codePoint.toString(16)} proof agrees with HEX pixels`,d===bitmapSvg(glyph).match(/ d="([^"]*)"/)[1]);
      const sizes=await card.locator('.foundation-drawings .bitmap, .foundation-small figure:nth-child(-n+2) .bitmap').evaluateAll(elements=>elements.map(el=>[el.getBoundingClientRect().width,el.getBoundingClientRect().height]));
      assert.deepEqual(sizes,[[64,128],[64,128],[8,16],[16,32]],'Integer proof sizes');
      check(`${glyph.codePoint.toString(16)} frozen outline font loaded`,await card.locator('.outline-reference').evaluate(el=>document.fonts.check('52px "Unifont outline reference"',el.textContent)));
      await card.evaluate(el=>el.scrollIntoView({block:'start'}));
      const clip=await card.evaluate(el=>{const a=el.getBoundingClientRect(),b=el.querySelector('.foundation-donors').getBoundingClientRect();return{x:Math.floor(a.x),y:Math.floor(a.y),width:Math.ceil(a.width),height:Math.ceil(b.bottom-a.y+8)};});
      const file=`${glyph.codePoint.toString(16)}.png`,bytes=await page.screenshot({path:path.join(output,file),clip});
      images.push({glyphId:id,codePoint:glyph.codePoint,page:proof,file,sha256:sha256(bytes),bitmapSha256:glyph.bitmapSha256,proofSha256:glyph.proofSha256});
    }
    await page.setViewportSize({width:375,height:1000});
    check(`${proof} proof fits mobile`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.setViewportSize({width:1440,height:1000});
  }
  check('Every drawing captured once',images.length===metadata.drawn&&new Set(images.map(i=>i.glyphId)).size===metadata.drawn);
  await context.close();
  const noJs=await browser.newContext({javaScriptEnabled:false,viewport:{width:375,height:1000}});
  const staticPage=await noJs.newPage();await staticPage.goto(new URL('unifont.html',base).href);
  await staticPage.locator('[data-unifont-code="F2A03"] a').click();
  check('Chart link opens complete static proof without JavaScript',await staticPage.locator('#bitmap-f2a03').count()===1&&new URL(staticPage.url()).pathname.endsWith('/proofs/stems.html'));
  await staticPage.goto(new URL('unifont/proofs/donors.html',base).href);
  check('All 40 native donors are browsable without JavaScript',await staticPage.locator('.donor-cards article').count()===40);
  check('Donor proof fits mobile',await staticPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await noJs.close();
  check('No browser errors or failed local assets',errors.length===0);
  await writeFile(path.join(output,'report.json'),JSON.stringify({base,checks,errors,images},null,2)+'\n');
  console.log(`Passed ${checks.length} Unifont browser checks; ${images.length} individual proof captures in .tmp/unifont-review.`);
}finally{if(browser)await browser.close();if(server)server.kill();}
