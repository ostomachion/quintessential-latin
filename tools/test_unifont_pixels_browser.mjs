import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {inflateSync} from 'node:zlib';
import {chromium} from 'playwright';

const root=fileURLToPath(new URL('../',import.meta.url));
const output=path.join(root,'.tmp/unifont-device-pixels');
const metadata=JSON.parse(await readFile(path.join(root,'resources/unifont/glyphs.json'),'utf8'));
const glyphs=new Map(metadata.glyphs.map(g=>[g.codePoint,g]));
const donorInfo=JSON.parse(await readFile(path.join(root,'resources/unifont/donors.json'),'utf8'));
const port=Number(process.env.QLAT_TEST_PORT||8776);
const base=process.env.QLAT_BASE_URL||`http://127.0.0.1:${port}/quintessential-latin/`;
const checks=[],rasters=[],errors=[];
let server,browser;
await mkdir(output,{recursive:true});
const check=(name,value,details='')=>{assert.ok(value,details?`${name}: ${details}`:name);checks.push(name);};
const nearInteger=value=>Math.abs(value-Math.round(value))<=0.035;

// Decode Chromium's lossless screenshot bytes directly. Reading the physical
// PNG avoids resampling through a browser canvas, CSS, or an image viewer.
function decodePng(bytes){
  assert.deepEqual(bytes.subarray(0,8),Buffer.from([137,80,78,71,13,10,26,10]));
  let width,height,type,depth,interlace;const chunks=[];
  for(let offset=8;offset<bytes.length;){
    const length=bytes.readUInt32BE(offset),name=bytes.toString('ascii',offset+4,offset+8),data=bytes.subarray(offset+8,offset+8+length);
    if(name==='IHDR'){width=data.readUInt32BE(0);height=data.readUInt32BE(4);depth=data[8];type=data[9];interlace=data[12];}
    if(name==='IDAT')chunks.push(data);
    offset+=length+12;
  }
  assert.equal(depth,8);assert.equal(interlace,0);assert([2,6].includes(type),`Unsupported screenshot color type ${type}`);
  const channels=type===6?4:3,stride=width*channels,raw=inflateSync(Buffer.concat(chunks)),pixels=Buffer.alloc(height*stride);
  assert.equal(raw.length,height*(stride+1));
  const paeth=(a,b,c)=>{const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;};
  for(let y=0;y<height;y++){
    const filter=raw[y*(stride+1)];assert(filter<=4);
    for(let x=0;x<stride;x++){
      const i=y*stride+x,a=x>=channels?pixels[i-channels]:0,b=y?pixels[i-stride]:0,c=y&&x>=channels?pixels[i-stride-channels]:0;
      const predictor=[0,a,b,Math.floor((a+b)/2),paeth(a,b,c)][filter];
      pixels[i]=(raw[y*(stride+1)+x+1]+predictor)&255;
    }
  }
  return {width,height,pixel:(x,y)=>Array.from(pixels.subarray((y*width+x)*channels,(y*width+x)*channels+channels))};
}

async function settle(page){
  await page.evaluate(async()=>{for(let i=0;i<8;i++)await new Promise(requestAnimationFrame);});
}
async function geometry(page,label){
  await settle(page);
  const result=await page.evaluate(()=>{
    const vv=visualViewport,density=devicePixelRatio*(vv?.scale||1);
    const visible=[];let unmarked=0;
    for(const el of document.querySelectorAll('svg.bitmap')){
      if(!el.hasAttribute('data-bitmap-scale')||!el.hasAttribute('data-bitmap-width'))unmarked++;
      if(!el.checkVisibility({visibilityProperty:true,opacityProperty:true,contentVisibilityAuto:true})||el.closest('details:not([open])'))continue;
      const r=el.getBoundingClientRect();
      const clip={left:vv?.offsetLeft||0,top:vv?.offsetTop||0};
      clip.right=clip.left+(vv?.width||innerWidth);clip.bottom=clip.top+(vv?.height||innerHeight);
      for(let parent=el.parentElement;parent;parent=parent.parentElement){
        const css=getComputedStyle(parent),box=parent.getBoundingClientRect();
        if(css.overflowX!=='visible'){clip.left=Math.max(clip.left,box.left);clip.right=Math.min(clip.right,box.right);}
        if(css.overflowY!=='visible'){clip.top=Math.max(clip.top,box.top);clip.bottom=Math.min(clip.bottom,box.bottom);}
      }
      if(!r.width||!r.height||r.bottom<=clip.top||r.top>=clip.bottom||r.right<=clip.left||r.left>=clip.right||clip.right<=clip.left||clip.bottom<=clip.top)continue;
      const scale=Number(el.dataset.bitmapScale),width=Number(el.dataset.bitmapWidth),step=Math.max(1,Math.round(scale*density));
      const coordinate=el.closest('.coordinate-proof');
      visible.push({identity:el.closest('[data-unifont-code]')?.dataset.unifontCode||el.closest('[id]')?.id||el.closest('article')?.querySelector('h2')?.textContent,translate:el.style.translate,parentTranslate:el.parentElement.style.translate,scale,width,step,x:(r.x-(vv?.offsetLeft||0))*density,y:(r.y-(vv?.offsetTop||0))*density,w:r.width*density,h:r.height*density,
        axes:coordinate?{x:[...coordinate.querySelectorAll('.pixel-x-axis span')].map(n=>n.getBoundingClientRect().width*density),y:[...coordinate.querySelectorAll('.pixel-y-axis span')].map(n=>n.getBoundingClientRect().height*density)}:null});
    }
    return {density,unmarked,visible};
  });
  check(`${label}: every bitmap declares its nominal source grid`,result.unmarked===0);
  check(`${label}: visible bitmap sample exists`,result.visible.length>0);
  for(const [i,g] of result.visible.entries()){
    const context=`bitmap ${i}: ${JSON.stringify(g)}`;
    check(`${label}: ${i} dimensions follow integer physical cells`,Math.abs(g.w-g.width*g.step)<=0.035&&Math.abs(g.h-16*g.step)<=0.035,context);
    check(`${label}: ${i} origin is device aligned`,nearInteger(g.x)&&nearInteger(g.y),context);
    if(g.axes){
      check(`${label}: ${i} coordinate labels track the enlarged pixel width`,g.axes.x.length===g.width&&g.axes.x.every(v=>Math.abs(v-g.step)<=0.035),context);
      check(`${label}: ${i} coordinate labels track the enlarged pixel height`,g.axes.y.length===16&&g.axes.y.every(v=>Math.abs(v-g.step)<=0.035),context);
    }
  }
  return result;
}

async function raster(page,locator,rows,label){
  assert.equal(await locator.count(),1,label);
  assert.equal(await locator.locator('.bitmap-grid, .bitmap-metrics').count(),0,'Raster comparison excludes guides and overlays');
  await locator.scrollIntoViewIfNeeded();
  // Use neutral contrasting colors while preserving the production geometry,
  // source path, positioning, and browser rasterization.
  await locator.evaluate(el=>{el.style.color='#000';el.style.backgroundColor='#fff';});
  await settle(page);
  const rect=await locator.evaluate(el=>{
    const r=el.getBoundingClientRect(),v=visualViewport,density=devicePixelRatio*(v?.scale||1);
    return {x:(r.x-(v?.offsetLeft||0))*density,y:(r.y-(v?.offsetTop||0))*density,width:r.width*density,height:r.height*density,
      step:Math.max(1,Math.round(Number(el.dataset.bitmapScale)*density)),sourceWidth:Number(el.dataset.bitmapWidth),density,cssRect:{x:r.x,y:r.y,width:r.width,height:r.height},visual:{x:v?.offsetLeft||0,y:v?.offsetTop||0,scale:v?.scale||1},translate:el.style.translate};
  });
  check(`${label}: raster origin is integral`,nearInteger(rect.x)&&nearInteger(rect.y),JSON.stringify(rect));
  const file=label.replace(/[^a-z0-9-]+/gi,'-')+'.png';
  const bytes=await page.screenshot({path:path.join(output,file),scale:'device',animations:'disabled'}),png=decodePng(bytes);
  const left=Math.round(rect.x),top=Math.round(rect.y),width=rect.sourceWidth*rect.step,height=16*rect.step;
  check(`${label}: complete glyph is captured`,left>=0&&top>=0&&left+width<=png.width&&top+height<=png.height,JSON.stringify({rect,png:[png.width,png.height]}));
  const mismatches=[];
  for(let py=0;py<height;py++)for(let px=0;px<width;px++){
    const x=Math.floor(px/rect.step),y=Math.floor(py/rect.step),ink=Boolean(rows[y]&(1<<(rect.sourceWidth-1-x))),expected=ink?0:255;
    const actual=png.pixel(left+px,top+py);
    if(actual[0]!==expected||actual[1]!==expected||actual[2]!==expected||(actual.length===4&&actual[3]!==255)){
      if(mismatches.length<12)mismatches.push({source:[x,y],device:[left+px,top+py],expected,actual});
    }
  }
  const after=await locator.evaluate(el=>{const r=el.getBoundingClientRect();return{x:r.x,y:r.y,translate:el.style.translate};});
  if(mismatches.length&&process.env.QLAT_PIXEL_LAYOUT_DIAGNOSTIC&&!label.endsWith('-layout-probe')){
    await locator.evaluate(el=>{const clone=el.cloneNode(true),[x,y]=el.style.translate.split(' ');clone.classList.remove('bitmap');clone.dataset.devicePixelProbe='true';clone.style.translate='none';clone.style.position='relative';clone.style.left=x;clone.style.top=y;el.replaceWith(clone);});
    await raster(page,page.locator('[data-device-pixel-probe="true"]'),rows,label+'-layout-probe');
    console.log(`${label}: relative-position diagnostic passed`);
  }
  check(`${label}: raw screenshot has exact uniform HEX cells`,mismatches.length===0,JSON.stringify({rect,after,mismatches}));
  rasters.push({label,file,rect,png:{width:png.width,height:png.height},comparedPhysicalPixels:width*height});
}

try{
  if(!process.env.QLAT_BASE_URL){
    server=spawn(process.execPath,['tools/serve_site.mjs','--port',String(port)],{cwd:root,stdio:'ignore',windowsHide:true});
    server.on('error',e=>errors.push(e.message));
    let ready=false;
    for(let i=0;i<100;i++){
      try{if((await fetch(base)).ok){ready=true;break;}}catch{}
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    assert(ready,'The local preview server did not start');
  }
  browser=await chromium.launch({headless:true,...(process.env.QLAT_BROWSER_CHANNEL?{channel:process.env.QLAT_BROWSER_CHANNEL}:{})});
  for(const dpr of [1,1.25,1.5,2])for(const mobile of [false,true]){
    const width=mobile?375:1440,label=`${mobile?'mobile':'desktop'}-dpr-${dpr}`;
    if(process.env.QLAT_PIXEL_CASE&&label!==process.env.QLAT_PIXEL_CASE)continue;
    const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:dpr,isMobile:mobile,hasTouch:mobile});
    const page=await context.newPage();
    page.on('pageerror',e=>errors.push(`${label}: ${e.message}`));
    page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
    const navigate=async file=>{await page.goto(new URL(file,base).href);await page.evaluate(()=>document.fonts.ready);await settle(page);};
    try{
      await navigate('unifont.html');
      await page.waitForFunction(()=>document.body.dataset.unifont==='ready');
      const stem=page.locator('[data-unifont-code="F2A03"] svg.bitmap');
      await stem.scrollIntoViewIfNeeded();
      await geometry(page,`${label}-chart`);
      await raster(page,stem,glyphs.get(0xf2a03).rows,`${label}-chart-stem`);

      await page.locator('[data-unifont-code="F2A03"] .bitmap-cell').click();
      await page.locator('#unifont-inspector svg.bitmap').first().scrollIntoViewIfNeeded();
      await page.locator('#unifont-inspector').evaluate(el=>{el.style.transform='translate(0.37px, 0.29px)';});
      await geometry(page,`${label}-fractional-inspector`);
      await raster(page,page.locator('#unifont-inspector .bitmap-native svg.bitmap').first(),glyphs.get(0xf2a03).rows,`${label}-inspector-native`);

      // Replacing the selected card exercises observer registration on entirely
      // new SVG elements, rather than merely resizing existing ones.
      await page.evaluate(()=>{location.hash='#bitmap-f2a00';});
      await page.waitForFunction(()=>document.querySelector('#unifont-inspector #bitmap-f2a00'));
      await geometry(page,`${label}-inspector-replaced`);
      await raster(page,page.locator('#unifont-inspector .bitmap-native svg.bitmap').nth(1),glyphs.get(0xf2a00).rows,`${label}-inspector-bowl-2x`);

      await page.evaluate(()=>{
        const scroll=document.querySelector('.unifont-scroll'),outer=document.createElement('div');
        outer.style.cssText='height:195px;overflow:auto;margin-left:0.37px;transform:translateY(0.23px)';
        scroll.before(outer);outer.append(scroll);scroll.style.minWidth='0';
        outer.scrollIntoView({block:'center'});outer.scrollTop=21.7;scroll.scrollLeft=39.3;
      });
      await geometry(page,`${label}-nested-scroll`);
      await page.setViewportSize({width:width+13,height:987});
      await geometry(page,`${label}-resize`);
      await page.setViewportSize({width,height:1000});

      await navigate('unifont/proofs/primitives.html');
      const bowl=page.locator('#bitmap-f2a00');
      await bowl.scrollIntoViewIfNeeded();
      await geometry(page,`${label}-static-primitives`);
      await raster(page,bowl.locator('.foundation-drawings figure').nth(1).locator('svg.bitmap'),glyphs.get(0xf2a00).rows,`${label}-proof-bowl-8x`);
      await raster(page,bowl.locator('.foundation-small .bitmap-sequence svg.bitmap').first(),glyphs.get(0xf2a00).rows,`${label}-repeated-native`);

      await page.evaluate(async()=>{
        const main=document.querySelector('.proof-main');
        main.style.paddingTop='30.37px';main.style.letterSpacing='.13px';
        const font=new FontFace('Device pixel late font',`url(${new URL('../../fonts/SourceSans3/SourceSans3-Regular.ttf',location.href)})`);
        document.fonts.add(font);main.style.fontFamily='"Device pixel late font", monospace';
        await font.load();await document.fonts.ready;
      });
      await geometry(page,`${label}-late-font-layout`);

      await navigate('unifont/proofs/donors.html');
      const donor=page.locator('.donor-cards article').filter({has:page.getByRole('heading',{name:/^U\+0073 /})});
      await donor.scrollIntoViewIfNeeded();
      await geometry(page,`${label}-native-donors`);
      const donorRows=donorInfo.donors.find(g=>g.codePoint==='0073').hex.match(/../g).map(x=>parseInt(x,16));
      await raster(page,donor.locator('.bitmap-sequence svg.bitmap').first(),donorRows,`${label}-native-s-donor`);

      // CDP page scaling changes visualViewport.scale without changing DPR,
      // exercising real browser pinch/page-scale geometry and its reset path.
      const cdp=await context.newCDPSession(page);
      await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1.3});
      await settle(page);
      check(`${label}: pinch scale is exercised`,Math.abs(await page.evaluate(()=>visualViewport.scale)-1.3)<.02);
      await donor.scrollIntoViewIfNeeded();
      await geometry(page,`${label}-pinch-1.3`);
      await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1});
      await geometry(page,`${label}-pinch-reset`);
      await raster(page,donor.locator('.bitmap-sequence svg.bitmap').nth(1),donorRows,`${label}-donor-after-pinch-2x`);
      await cdp.detach();
    }finally{await context.close();}
  }
  check('No page errors or failed local requests',errors.length===0,JSON.stringify(errors));
  console.log(`Passed ${checks.length} physical-grid checks and ${rasters.length} raw PNG raster comparisons across 8 viewport/DPR contexts.`);
}finally{
  await writeFile(path.join(output,'report.json'),JSON.stringify({base,checks,rasters,errors},null,2)+'\n');
  if(browser)await browser.close();
  if(server)server.kill();
}
