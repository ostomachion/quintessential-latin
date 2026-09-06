import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {parseHex} from '../site/assets/unifont-model.mjs';

const root=fileURLToPath(new URL('../',import.meta.url)),output=path.join(root,'.tmp/unifont-font-review');
await mkdir(output,{recursive:true});
const maps=await Promise.all(['quintessential-latin.hex','font-companions.hex'].map(async name=>parseHex(await readFile(path.join(root,'resources/unifont',name),'utf8'))));
const glyphs=[...maps.flatMap(map=>[...map])].map(([point,glyph])=>({point,rows:glyph.rows}));
assert.equal(glyphs.length,1430);
const port=Number(process.env.QLAT_TEST_PORT||8774),base=process.env.QLAT_BASE_URL||`http://127.0.0.1:${port}/quintessential-latin/`;
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const checks=[],errors=[],fonts=[];
let server,browser;
try{
  if(!process.env.QLAT_BASE_URL){
    server=spawn(process.execPath,['tools/serve_site.mjs','--port',String(port)],{cwd:root,stdio:'ignore',windowsHide:true});
    server.on('error',error=>errors.push(error.message));
    for(let n=0;n<100;n++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(resolve=>setTimeout(resolve,100));}
  }
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,acceptDownloads:true});
  const page=await context.newPage();
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  page.on('response',response=>{if(response.url().startsWith(base)&&response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
  await page.goto(base+'downloads.html#unifont-font');
  for(const width of [1440,375]){
    await page.setViewportSize({width,height:1000});
    await page.locator('#unifont-font').scrollIntoViewIfNeeded();
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    assert.equal(await page.locator('#unifont-font a[download]').count(),3);
    await page.screenshot({path:path.join(output,`downloads-${width}.png`)});
    checks.push(`${width}px Downloads links visible without page overflow`);
  }
  for(const ext of ['ttf','woff2']){
    const filename=`QuintessentialUnifont-Regular.${ext}`,relative=`fonts/QuintessentialUnifont/${filename}`;
    const waiting=page.waitForEvent('download');
    await page.locator(`#unifont-font a[href="${relative}"]`).click();
    const download=await waiting;
    assert.equal(download.suggestedFilename(),filename);
    const file=path.join(output,filename);await download.saveAs(file);
    const source=await readFile(path.join(root,'resources',relative));
    assert.equal(hash(await readFile(file)),hash(source));
    checks.push(`${ext} browser download matches the compiled file`);
    const result=await page.evaluate(async({url,ext,glyphs})=>{
      const family='UnifontDownloadTest'+ext;
      const face=await new FontFace(family,`url("${url}")`,{style:'normal',weight:'400'}).load();
      document.fonts.add(face);
      const canvas=document.createElement('canvas');canvas.width=8;canvas.height=16;
      const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.font=`16px "${family}"`;ctx.textBaseline='alphabetic';ctx.fillStyle='#000';
      const failures=[];
      for(const glyph of glyphs){
        ctx.clearRect(0,0,8,16);ctx.fillText(String.fromCodePoint(glyph.point),0,14);
        const data=ctx.getImageData(0,0,8,16).data;
        let different=0;
        for(let y=0;y<16;y++)for(let x=0;x<8;x++)if(data[(y*8+x)*4+3]!==((glyph.rows[y]&(128>>x))?255:0))different++;
        if(different||ctx.measureText(String.fromCodePoint(glyph.point)).width!==8)failures.push({point:glyph.point,different});
      }
      // Verify a continuous mixed run: there must be no kerning or fallback shift.
      const mixed=[0x006e,0xf2a00,0x006f,0xf2d1a,0x0131,0xf2ebf,0x006d,0xf2ad6];
      canvas.width=mixed.length*8;
      ctx.font=`16px "${family}"`;ctx.textBaseline='alphabetic';ctx.fillStyle='#000';
      ctx.fillText(String.fromCodePoint(...mixed),0,14);
      const data=ctx.getImageData(0,0,canvas.width,16).data;
      let mixedDifferences=0;
      mixed.forEach((point,index)=>{const rows=glyphs.find(g=>g.point===point).rows;for(let y=0;y<16;y++)for(let x=0;x<8;x++)if(data[(y*canvas.width+index*8+x)*4+3]!==((rows[y]&(128>>x))?255:0))mixedDifferences++;});
      return {loaded:face.status,checked:glyphs.length,failures,mixedDifferences};
    },{url:base+relative,ext,glyphs});
    assert.equal(result.loaded,'loaded');assert.deepEqual(result.failures,[]);assert.equal(result.mixedDifferences,0);
    fonts.push({format:ext,sha256:hash(source),...result});
    checks.push(`${ext}: all1430 glyphs and mixed Latin/Quintessential run are pixel-exact at16px`);
  }
  assert.deepEqual(errors,[]);
  await writeFile(path.join(output,'report.json'),JSON.stringify({browser:await browser.version(),base,checks,errors,fonts},null,2)+'\n');
  console.log(`Verified both browser downloads, desktop/mobile layout, and ${glyphs.length*2} pixel-exact font renderings.`);
  await context.close();
}finally{if(browser)await browser.close();if(server)server.kill();}
