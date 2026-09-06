import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp,cp,appendFile,rm} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {test} from 'node:test';
import {buildUnifont,constructUnifont,sha256} from './build_unifont_glyphs.mjs';
import {parseHex,bitmapSvg,bitmapSequenceSvg} from '../site/assets/unifont-model.mjs';
import {assessBitmap,hasPixel,pixelDiff,rowsFromDrawing} from './unifont_geometry.mjs';

const metadata=await buildUnifont({check:true}),byId=new Map(metadata.glyphs.map(glyph=>[glyph.glyphId,glyph]));
const allocation=JSON.parse(await readFile(new URL('../resources/quintessential-latin-allocation.json',import.meta.url),'utf8'));
const byAllocation=new Map(allocation.entries.map(entry=>[entry.glyphId,entry]));
const donorInfo=JSON.parse(await readFile(new URL('../resources/unifont/donors.json',import.meta.url),'utf8'));
const before=parseHex(await readFile(new URL('../resources/unifont/qa-tail-precedents/before.hex',import.meta.url),'utf8'));
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
await test('Shared CSS and screen alignment changes invalidate proofs without changing donor pixels',async()=>{
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
    for(const dependency of ['site/assets/style.css','site/assets/unifont-pixels.mjs']){
      const target=path.join(fixture,dependency),original=await readFile(target);
      await appendFile(target,'\n/* proof dependency mutation */\n');
      const changed=await constructUnifont(fixture);assert.equal(changed.inspected,0);
      assert.deepEqual(changed.glyphs.map(g=>g.bitmapSha256),metadata.glyphs.map(g=>g.bitmapSha256));
      assert(changed.glyphs.every((g,i)=>g.proofSha256!==metadata.glyphs[i].proofSha256));
      await writeFile(target,original);
    }
  }finally{
    assert.equal(path.dirname(path.resolve(fixture)),path.resolve(temporary));
    assert(path.basename(fixture).startsWith('unifont-invalidation-'));
    await rm(fixture,{recursive:true,force:true});
  }
});
await test('Native donor bits including dotless j, script g, and y are exact and independently pinned',()=>{
  assert.equal(donorInfo.sourceCompressedSha256,'2ae5311c8e123e9e85f5331cd012aa99757071df23243f1487fdbf8f3acd86be');
  assert.equal(donorInfo.donors.length,42);
  assert.equal(byId.get('stem').line,'0F2A03:000000000000180808080808083E0000');
  assert.equal(byId.get('tail').hex,'0000000000000C040404040404044830');
  assert.equal(byId.get('turned-bowl-tail').hex,'0000000000003A46424242463A02423C');
  assert.equal(byId.get('turned-arch-tail').hex,'0000000000004242424242261A02023C');
  assert.equal(byId.get('special-ring').line,'0F2A00:0000000000003C4242424242423C0000');
  assert.equal(byId.get('arch').hex,donorInfo.donors.find(d=>d.codePoint==='006E').hex);
  assert.equal(byId.get('turned-arch').hex,donorInfo.donors.find(d=>d.codePoint==='0075').hex);
  for(const [id,point] of [['special-turned-open-bowl','0254'],['special-turned-double-open-bowl','025C'],['special-spine','0073'],['turned-bowled-spine','0061'],['bowled-spine','0250'],['tail','0237'],['turned-bowl-tail','0261'],['turned-arch-tail','0079']])assert.equal(byId.get(id).hex,donorInfo.donors.find(d=>d.codePoint===point).hex);
  assert.equal(byId.get('opposed-bowls-0-0').recipe.baseGlyphId,'turned-bowled-spine');
});
await test('Tail and native-f revision preserves every unrelated bitmap and long-bowl contact mask',()=>{
  assert.equal(before.size,1216);
  let changed=0;
  for(const glyph of metadata.glyphs){
    const original=before.get(glyph.codePoint);assert(original,glyph.glyphId);
    const differences=pixelDiff(original.rows,glyph.rows);
    if(differences.length){
      changed++;
      const tail=glyph.parts.some(part=>part.lower==='curved');
      const hook=glyph.parts.some(part=>part.kind==='stem'&&part.upper==='curved');
      assert(tail||hook,`Unrelated bitmap changed: ${glyph.glyphId}`);
      if(!tail)assert.deepEqual(differences,[[3,3],[3,4]],`Native-f-only correction: ${glyph.glyphId}`);
    }
    for(const bowl of glyph.parts.filter(part=>part.long)){
      const rows=bowl.closingEnd==='lower'?[14,15]:[0,1,2,3,4,5];
      for(const y of rows)assert.equal(glyph.rows[y],original.rows[y],`Long-bowl mask ${glyph.glyphId}, row ${y}`);
    }
  }
  assert(changed>0);
});
await test('Revision records bind every changed bitmap and preserve the complete prior repertoire',async()=>{
  const revision=JSON.parse(await readFile(new URL('../resources/unifont/tail-revisions.json',import.meta.url),'utf8'));
  assert.equal(revision.beforeSha256,sha256(await readFile(new URL('../resources/unifont/qa-tail-precedents/before.hex',import.meta.url))));
  assert.equal(revision.userAcceptance,null);
  const records=new Map(revision.glyphs.map(record=>[record.glyphId,record]));
  assert.equal(records.size,revision.glyphs.length);
  let changed=0;
  for(const glyph of metadata.glyphs){
    const original=before.get(glyph.codePoint),record=records.get(glyph.glyphId);
    if(record){
      changed++;assert.equal(record.before,original.line,glyph.glyphId);assert.equal(record.after,glyph.line,glyph.glyphId);
      assert.deepEqual(record.pixels,pixelDiff(original.rows,glyph.rows),glyph.glyphId);
      assert(record.pixels.length>0&&record.reason.length>0,glyph.glyphId);
    }else assert.equal(glyph.line,original.line,`Unlisted bitmap changed: ${glyph.glyphId}`);
  }
  assert.equal(changed,records.size);assert.equal(revision.changed,changed);assert.equal(revision.preserved,1216-changed);
});
await test('Uncompacted tails consistently retain their native dotless-j, y, or script-g lower shape',()=>{
  const donorRows=point=>parseHex(`${point}:${donorInfo.donors.find(d=>d.codePoint===point).hex}`).get(parseInt(point,16)).rows;
  for(const glyph of metadata.glyphs.filter(g=>g.parts.length===1&&g.parts[0].lower==='curved'))assert.deepEqual(glyph.rows.slice(7),donorRows('0237').slice(7),glyph.glyphId);
  for(const glyph of metadata.glyphs.filter(g=>g.parts.length===2&&!g.parts.some(p=>p.middle)&&g.parts[1].lower==='curved')){
    const part=glyph.parts[0],bowl=part.kind==='spine'||part.kind==='double bowl'||part.kind==='bowl'&&!part.long;
    assert.deepEqual(glyph.rows.slice(11),donorRows(bowl?'0261':'0079').slice(11),glyph.glyphId);
  }
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
await test('Continuous bitmap runs preserve all cells beyond the 32-bit mask width',()=>{
  const run=['stem','special-ring','special-spine','stem','special-ring','special-spine','stem','special-ring'].map(id=>byId.get(id));
  const svg=bitmapSequenceSvg(run);
  assert(svg.includes('data-bitmap-width="64"'));
  assert(svg.includes('viewBox="0 0 64 16"'));
  const pixels=Array.from({length:16},()=>Array(64).fill(false));
  for(const match of svg.matchAll(/M(\d+) (\d+)h1v1h-1z/g))pixels[Number(match[2])][Number(match[1])]=true;
  for(let y=0;y<16;y++)for(let x=0;x<64;x++){
    assert.equal(pixels[y][x],Boolean(run[Math.floor(x/8)].rows[y]&(128>>(x%8))),`Run pixel (${x},${y})`);
  }
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
    const hasTail=glyph.parts.some(part=>part.lower==='curved');
    const closesTail=hasTail&&glyph.parts[0].lower==='straight';
    assert.equal(glyph.assessment.counters,closesTail?3:2,glyph.glyphId);
    assert.deepEqual(glyph.rows.slice(7,hasTail?11:13),shared.rows.slice(7,hasTail?11:13));
    if(hasTail){
      const lower=[0x46,0x3A,0x02,0x42,0x3C];
      if(glyph.parts[0].lower==='straight')for(const index of [1,2,3,4])lower[index]|=0x40;
      assert.deepEqual(glyph.rows.slice(11),lower,glyph.glyphId);
      assert.deepEqual(glyph.assessment.counterPixels.map(region=>region.length),closesTail?[9,5,9]:[9,5],glyph.glyphId);
    }
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
    const expected=[],joins=[];
    for(const position of positions){
      const part=glyph.parts[position.partIndex];assert(part.middle);assert.equal(part.kind,position.kind);
      if(part.upper==='straight')for(const y of [3,4,5])expected.push([position.column,y]);
      if(part.lower==='straight')for(const y of [14,15])expected.push([position.column,y]);
      for(const pixel of position.joinPixels||[]){
        assert.equal(part.kind,'leg',glyph.glyphId);
        assert.deepEqual(pixel,[position.column,13],glyph.glyphId);
        assert(glyph.parts.some(part=>part.kind==='stem'&&part.lower==='curved'),glyph.glyphId);
        if(part.lower!=='straight'){
          assert.equal(part.lower,'none',glyph.glyphId);
          assert(!hasPixel(glyph.rows,8,position.column,13),glyph.glyphId);
          continue;
        }
        assert([-1,0,1].some(dx=>hasPixel(glyph.rows,8,position.column+dx,12)),glyph.glyphId);
        assert(!hasPixel(byId.get(glyph.recipe.baseGlyphId).rows,8,position.column,13),glyph.glyphId);
        expected.push(pixel);joins.push(pixel);
      }
    }
    const sort=pixels=>pixels.map(p=>p.join(',')).sort();
    assert.deepEqual(sort(glyph.extensionPixels),sort(expected),glyph.glyphId);
    assert.deepEqual(sort(glyph.extensionJoinPixels||[]),sort(joins),glyph.glyphId);
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
        if(part.lower==='curved'){
          assert.equal(x,6);
          for(const [px,py] of [[6,14],[2,15],[3,15],[4,15],[5,15]])add(px,py);
          if(glyph.parts.some(part=>part.kind==='spine'||part.kind==='double bowl'||part.kind==='bowl'&&!part.long))add(1,14);
        }
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
