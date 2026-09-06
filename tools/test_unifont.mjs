import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp,cp,appendFile,rm} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {test} from 'node:test';
import {buildUnifont,constructUnifont,sha256} from './build_unifont_glyphs.mjs';
import {parseHex,bitmapSvg} from '../site/assets/unifont-model.mjs';
import {assessBitmap,hasPixel,pixelDiff,rowsFromDrawing} from './unifont_geometry.mjs';

const metadata=await buildUnifont({check:true}),byId=new Map(metadata.glyphs.map(glyph=>[glyph.glyphId,glyph]));
const allocation=JSON.parse(await readFile(new URL('../resources/quintessential-latin-allocation.json',import.meta.url),'utf8'));
const byAllocation=new Map(allocation.entries.map(entry=>[entry.glyphId,entry]));
const donorInfo=JSON.parse(await readFile(new URL('../resources/unifont/donors.json',import.meta.url),'utf8'));
await test('Complete 1216-character repertoire, all 8px',()=>{
  assert.equal(metadata.total,1216);assert.equal(metadata.drawn,1216);assert.equal(metadata.stage,'complete-repertoire');assert.equal(metadata.userApproval,null);
  assert.equal(metadata.glyphs.filter(glyph=>glyph.parts.length===1).length,16);
  assert.equal(metadata.glyphs.filter(glyph=>!glyph.parts.some(part=>part.middle)).length,136);
  assert.equal(metadata.foundationIds.length,39);
  assert.equal(metadata.glyphs.filter(glyph=>!glyph.parts.some(p=>p.middle)&&!metadata.foundationIds.includes(glyph.glyphId)&&glyph.recipe).length,109);
  assert.equal(metadata.groups.filter(group=>group.glyphIds.length===2).length,156);
  assert.equal(metadata.groups.filter(group=>group.glyphIds.length===4).length,192);
  assert.equal(new Set(metadata.groups.flatMap(group=>group.glyphIds)).size,1080);
  assert.equal(new Set(metadata.glyphs.map(g=>g.familyId)).size,30);
  for(const glyph of metadata.glyphs){
    assert.equal(glyph.width,8);assert.equal(glyph.rows.length,16);assert(glyph.rows.every(row=>row>=0&&row<=127));
    assert.equal(glyph.codePoint,byAllocation.get(glyph.glyphId).codePoint);assert.deepEqual(glyph.parts,byAllocation.get(glyph.glyphId).parts);
    assert.equal(glyph.assessment.components,1);assert(glyph.assessment.inkPixels>0);
    assert.equal(glyph.bitmapSha256,sha256(glyph.line+'\n'));
  }
});
await test('Shared CSS changes invalidate inspected proofs without changing donor pixels',async()=>{
  const root=fileURLToPath(new URL('../',import.meta.url)),temporary=path.join(root,'.tmp');
  await mkdir(temporary,{recursive:true});
  const fixture=await mkdtemp(path.join(temporary,'unifont-invalidation-'));
  try{
    for(const source of Object.keys(metadata.sources)){
      const target=path.join(fixture,source);await mkdir(path.dirname(target),{recursive:true});await cp(path.join(root,source),target);
    }
    const records=Object.fromEntries(metadata.glyphs.map(g=>[g.glyphId,{bitmapSha256:g.bitmapSha256,proofSha256:g.proofSha256,status:'inspected'}]));
    await writeFile(path.join(fixture,'resources/unifont/review.json'),JSON.stringify({records,userApproval:null}));
    assert.equal((await constructUnifont(fixture)).inspected,metadata.drawn);
    await appendFile(path.join(fixture,'site/assets/style.css'),'\n/* proof dependency mutation */\n');
    const changed=await constructUnifont(fixture);assert.equal(changed.inspected,0);
    assert.deepEqual(changed.glyphs.map(g=>g.bitmapSha256),metadata.glyphs.map(g=>g.bitmapSha256));
    assert(changed.glyphs.every((g,i)=>g.proofSha256!==metadata.glyphs[i].proofSha256));
  }finally{
    assert.equal(path.dirname(path.resolve(fixture)),path.resolve(temporary));
    assert(path.basename(fixture).startsWith('unifont-invalidation-'));
    await rm(fixture,{recursive:true,force:true});
  }
});
await test('Native donor bits including corrected dotless i are exact and independently pinned',()=>{
  assert.equal(donorInfo.sourceCompressedSha256,'2ae5311c8e123e9e85f5331cd012aa99757071df23243f1487fdbf8f3acd86be');
  assert.equal(byId.get('stem').line,'0F2A03:000000000000180808080808083E0000');
  assert.equal(byId.get('special-ring').line,'0F2A00:0000000000003C4242424242423C0000');
  assert.equal(byId.get('arch').hex,donorInfo.donors.find(d=>d.codePoint==='006E').hex);
  assert.equal(byId.get('turned-arch').hex,donorInfo.donors.find(d=>d.codePoint==='0075').hex);
  for(const [id,point] of [['special-turned-open-bowl','0254'],['special-turned-double-open-bowl','025C'],['special-spine','0073'],['turned-bowled-spine','0061'],['bowled-spine','0250']])assert.equal(byId.get(id).hex,donorInfo.donors.find(d=>d.codePoint===point).hex);
  assert.equal(byId.get('opposed-bowls-0-0').recipe.baseGlyphId,'turned-bowled-spine');
});
await test('HEX validity, MSB orientation, and SVG pixels roundtrip exactly',()=>{
  for(const glyph of metadata.glyphs){
    const decoded=parseHex(glyph.line).get(glyph.codePoint);assert.deepEqual(decoded.rows,glyph.rows);
    const svg=bitmapSvg(glyph),coords=[...svg.matchAll(/M(\d+) (\d+)h1v1h-1z/g)].map(match=>[Number(match[1]),Number(match[2])]);
    const pixels=Array.from({length:16},()=>'.'.repeat(8).split(''));
    for(const [x,y] of coords)pixels[y][x]='#';
    assert.deepEqual(rowsFromDrawing(pixels.map(row=>row.join(''))),glyph.rows);
  }
  assert.equal(parseHex('0F2A00:8001'+'0000'.repeat(15)).get(0xf2a00).width,16);
  for(const bad of ['F2A00:'+'00'.repeat(16),'D800:'+'00'.repeat(16),'110000:'+'00'.repeat(16),'0131:FF',byId.get('stem').line+'\n'+byId.get('stem').line])assert.throws(()=>parseHex(bad));
});
await test('Every pair and quartet changes only independently selected extension pixels',()=>{
  for(const group of metadata.groups){
    const glyphs=group.glyphIds.map(id=>byId.get(id)),base=glyphs[0];
    assert.deepEqual(glyphs.map(g=>g.extensionState),group.glyphIds.length===2?[[false],[true]]:[[false,false],[true,false],[false,true],[true,true]]);
    for(const glyph of glyphs){
      const expectedRows=[...base.rows];
      for(const [x,y] of glyph.extensionPixels)expectedRows[y]|=1<<(7-x);
      assert.deepEqual(glyph.rows,expectedRows,glyph.glyphId);
      const actualState=glyph.parts.filter(part=>part.middle).map(part=>part.upper!=='none'||part.lower!=='none');
      assert.deepEqual(glyph.extensionState,actualState,glyph.glyphId);
      assert(glyph.rows.every((row,y)=>(row&base.rows[y])===base.rows[y]),'Extension must not erase its base');
    }
    if(glyphs.length===4){const combined=glyphs[1].rows.map((row,y)=>row|glyphs[2].rows[y]);assert.deepEqual(combined,glyphs[3].rows);}
  }
});
await test('Long bowl closes at the immediate arm only; remote ascender leaves it open',()=>{
  const group=metadata.groups.find(group=>group.id==='adjacent-long-bowl-closure');
  group.glyphIds.forEach((id,index)=>{
    const glyph=byId.get(id),closed=index===1||index===3;
    assert.equal(glyph.parts[0].closingNeighbor,1);assert.equal(glyph.parts[0].returnContact,closed);
    assert.equal(hasPixel(glyph.rows,8,3,5),closed);
    const enclosesSeed=glyph.assessment.counterPixels.some(region=>region.some(([x,y])=>x===2&&y===7));
    assert.equal(enclosesSeed,closed);assert.equal(glyph.assessment.counters,closed?1:0);
  });
});
await test('Shared spine retains both counters under either attached middle extension',()=>{
  const group=metadata.groups.find(group=>group.id==='dense-shared-spine'),glyphs=group.glyphIds.map(id=>byId.get(id));
  for(const glyph of glyphs){assert.equal(glyph.assessment.counters,2);assert.deepEqual(glyph.rows.slice(6,14),glyphs[0].rows.slice(6,14));assert(hasPixel(glyph.rows,8,4,9));assert(!hasPixel(glyph.rows,8,4,10));assert.deepEqual(glyph.assessment.counterPixels.map(c=>c.length),[2,3]);}
});
await test('Ordinary shared spines balance both native donor connections and preserve the common body',()=>{
  const shared=byId.get('opposed-bowls-0-0'),body=shared.rows.slice(6,14);
  const reverse=value=>parseInt(value.toString(2).padStart(8,'0').split('').reverse().join(''),2);
  assert.deepEqual(body,[...body].reverse().map(reverse));
  assert.deepEqual(shared.assessment.counterPixels.map(region=>region.length),[9,9]);
  assert.deepEqual(shared.rows.slice(6,9),byId.get('bowled-spine').rows.slice(6,9));
  assert.deepEqual(shared.rows.slice(11,14),byId.get('turned-bowled-spine').rows.slice(11,14));
  const variants=metadata.glyphs.filter(g=>g.familyId==='opposed-bowls');assert.equal(variants.length,36);
  for(const glyph of variants){
    assert.equal(glyph.assessment.counters,2);
    assert.deepEqual(glyph.rows.slice(7,13),shared.rows.slice(7,13));
  }
});
await test('All new recipes preserve their base outside documented extension and join pixels',()=>{
  for(const glyph of metadata.glyphs.filter(g=>g.recipe)){
    const {baseGlyphId,addPixels,removePixels,joinPixels}=glyph.recipe;
    const base=byId.get(baseGlyphId),permitted=new Set([...addPixels,...removePixels].map(p=>p.join(',')));
    const actual=pixelDiff(base.rows,glyph.rows);
    assert(actual.every(p=>permitted.has(p.join(','))),glyph.glyphId);
    const joins=new Set(joinPixels.map(p=>p.join(',')));
    assert(actual.filter(([,y])=>y>=6&&y<=13).every(p=>joins.has(p.join(','))),glyph.glyphId);
  }
});
await test('New long bowls close only when their designated adjacent stem is extended',()=>{
  const glyphs=metadata.glyphs.filter(g=>g.parts.some(p=>p.long));assert.equal(glyphs.length,84);
  for(const glyph of glyphs){
    const bowl=glyph.parts.find(part=>part.long),checks=glyph.structuralChecks;
    const closureGap=checks.closure?.openPixel||checks.closureGap,counterSeed=checks.closure?.counterSeed||checks.counterSeed;
    assert.equal(checks.closure?.closingPartIndex??checks.closingNeighbor,bowl.closingNeighbor);
    assert.equal(hasPixel(glyph.rows,8,...closureGap),bowl.returnContact);
    const enclosed=glyph.assessment.counterPixels.some(region=>region.some(([x,y])=>x===counterSeed[0]&&y===counterSeed[1]));
    assert.equal(enclosed,bowl.returnContact,glyph.glyphId);
  }
});
await test('Every new middle extension follows its allocation direction and visual position',()=>{
  const glyphs=metadata.glyphs.filter(g=>g.layout&&g.parts.some(p=>p.middle));assert.equal(glyphs.length,1068);
  for(const glyph of glyphs){
    const positions=glyph.layout.middleParts||glyph.layout.parts.filter(p=>glyph.parts[p.partIndex].middle);
    assert(positions.every((p,i)=>i===0||p.column>positions[i-1].column),glyph.glyphId);
    const expected=[];
    for(const position of positions){
      const part=glyph.parts[position.partIndex];assert(part.middle);assert.equal(part.kind,position.kind);
      if(part.upper==='straight')for(const y of [3,4,5])expected.push([position.column,y]);
      if(part.lower==='straight')for(const y of [14,15])expected.push([position.column,y]);
    }
    const sort=pixels=>pixels.map(p=>p.join(',')).sort();
    assert.deepEqual(sort(glyph.extensionPixels),sort(expected),glyph.glyphId);
  }
});
await test('All compact shared spines preserve their counters and document natural hook contacts',()=>{
  for(const glyph of metadata.glyphs.filter(g=>g.layout&&g.familyId.includes('opposed'))){
    const checks=glyph.structuralChecks;
    if(checks.counterSeeds){
      checks.counterSeeds.forEach(([sx,sy],i)=>{
        const counter=glyph.assessment.counterPixels.find(region=>region.some(([x,y])=>x===sx&&y===sy));
        assert.equal(counter?.length,checks.counterAreas[i],glyph.glyphId);
      });
      const contact=checks.terminalContact;
      assert.equal(glyph.assessment.counters,contact?3:2,glyph.glyphId);
      if(contact){
        assert(!glyph.parts.some(p=>p.returnContact));
        assert(glyph.assessment.counterPixels.some(region=>region.some(([x,y])=>x===contact.counterSeed[0]&&y===contact.counterSeed[1])));
      }
    }else{
      assert.deepEqual(glyph.assessment.counterPixels.map(region=>region.length),checks.counterAreas,glyph.glyphId);
    }
  }
});
await test('All new end extensions match the ordered allocation parts and shared terminal masks',()=>{
  for(const glyph of metadata.glyphs.filter(g=>g.recipe&&!g.parts.some(p=>p.middle))){
    const pixels=new Set(),add=(x,y)=>pixels.add(`${x},${y}`);
    glyph.parts.forEach((part,index)=>{
      const x=index===0?1:6;
      if(['stem','leg','arm'].includes(part.kind)){
        if(part.upper==='straight')for(const y of [3,4,5])add(x,y);
        if(part.upper==='curved'){assert.equal(x,1);for(const [px,py] of [[2,3],[3,3],[1,4],[1,5]])add(px,py);}
        if(part.lower==='straight')for(const y of [14,15])add(x,y);
        if(part.lower==='curved'){assert.equal(x,6);for(const [px,py] of [[6,14],[4,15],[5,15]])add(px,py);}
      }
      if(part.kind==='bowl'&&part.long){
        const points=part.closingEnd==='lower'?[[6,14],[2,15],[3,15],[4,15],[5,15]]:[[2,3],[3,3],[4,3],[5,3],[1,4],[6,4],[1,5]];
        for(const [px,py] of points)add(px,py);
      }
    });
    for(const y of [0,1,2,3,4,5,14,15])for(let x=0;x<8;x++)assert.equal(hasPixel(glyph.rows,8,x,y),pixels.has(`${x},${y}`),`${glyph.glyphId} at ${x},${y}`);
  }
});
await test('Native diagonal topology is accepted, exact duplicate identities are absent',()=>{
  assert.equal(assessBitmap(byId.get('special-ring').rows,8).counters,1);
  assert.equal(new Set(metadata.glyphs.map(g=>g.hex)).size,metadata.drawn);
  for(const item of metadata.nearDuplicates){assert(item.pixels.length>0&&item.pixels.length<=4);assert.deepEqual(pixelDiff(...item.glyphIds.map(id=>byId.get(id).rows)),item.pixels);}
});
await test('Repeat construction reproduces every output and retains evidence hashes',async()=>{
  const again=await constructUnifont();delete again.hex;assert.deepEqual(again,metadata);
  const review=JSON.parse(await readFile(new URL('../resources/unifont/review.json',import.meta.url),'utf8'));
  for(const glyph of metadata.glyphs){
    if(glyph.reviewStatus==='inspected'){const record=review.records[glyph.glyphId];assert.equal(record.bitmapSha256,glyph.bitmapSha256);assert.equal(record.proofSha256,glyph.proofSha256);assert(record.notes.length>0);}
  }
});
await test('Current inspections include coordinate flags and near-duplicate comparisons',async()=>{
  const review=JSON.parse(await readFile(new URL('../resources/unifont/review.json',import.meta.url),'utf8'));
  for(const glyph of metadata.glyphs.filter(g=>g.reviewStatus==='inspected')){
    const record=review.records[glyph.glyphId];
    assert.deepEqual(record.flags.map(({status,finding,...flag})=>flag),glyph.assessment.flags);
    assert(record.flags.every(flag=>flag.status==='inspected'&&flag.finding.length>0));
    assert.match(record.evidence.sha256,/^[0-9a-f]{64}$/);
    assert.equal(record.userAcceptance,null);
  }
  for(const pair of metadata.nearDuplicates){
    const glyphs=pair.glyphIds.map(id=>byId.get(id));
    if(glyphs.some(g=>g.reviewStatus!=='inspected'))continue;
    const reviewed=review.nearDuplicateReviews.find(item=>JSON.stringify(item.glyphIds)===JSON.stringify(pair.glyphIds));
    assert(reviewed);assert.deepEqual(reviewed.pixels,pair.pixels);
    assert.deepEqual(reviewed.bitmapSha256,glyphs.map(g=>g.bitmapSha256));
    assert.deepEqual(reviewed.proofSha256,glyphs.map(g=>g.proofSha256));
    assert.equal(reviewed.status,'inspected');
  }
});
if(process.argv.includes('--reviewed'))await test('Final repertoire has complete current visual and independent review evidence',async()=>{
  assert.equal(metadata.inspected,1216);
  const review=JSON.parse(await readFile(new URL('../resources/unifont/review.json',import.meta.url),'utf8'));
  assert.equal(Object.keys(review.records).length,1216);
  assert.equal(review.nearDuplicateReviews.length,metadata.nearDuplicates.length);
  assert.equal(review.pendingDesignDecisions.length,0);
  assert(review.independentReviews.length>=3);
  for(const report of review.independentReviews)assert.equal(sha256(await readFile(new URL('../'+report.path,import.meta.url))),report.sha256,report.path);
  const evidence=new Map();
  for(const record of Object.values(review.records))evidence.set(record.evidence.path,record.evidence.sha256);
  for(const [file,hash] of evidence)assert.equal(sha256(await readFile(new URL('../'+file,import.meta.url))),hash,file);
});
