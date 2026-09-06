import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {parseHex} from '../site/assets/unifont-model.mjs';
import {rowsFromDrawing,rowHex,assessBitmap,pixelDiff} from './unifont_geometry.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export const sha256=value=>createHash('sha256').update(value).digest('hex');
export async function constructUnifont(root=ROOT){
  const sources={};
  async function read(name){const value=await readFile(path.join(root,name));sources[name]=sha256(value);return value;}
  const json=async name=>JSON.parse((await read(name)).toString('utf8'));
  const allocation=await json('resources/quintessential-latin-allocation.json');
  const design=await json('resources/unifont/design.json');
  const donorInfo=await json('resources/unifont/donors.json');
  const donorBytes=await read('resources/unifont/donors.hex');
  if(sha256(donorBytes)!==donorInfo.subsetSha256)throw new Error('Pinned Unifont donor subset changed');
  const donorMap=parseHex(donorBytes.toString('utf8'));
  for(const donor of donorInfo.donors){
    const glyph=donorMap.get(parseInt(donor.codePoint,16));
    if(!glyph||rowHex(glyph.rows,glyph.width)!==donor.hex||sha256(donor.hex)!==donor.sha256)throw new Error(`Donor ${donor.codePoint} checksum mismatch`);
  }
  const referencePath='resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.woff2';
  const referenceSha256=sha256(await read(referencePath));
  // Review binds renderer and sheet appearance too, not just the HEX output.
  for(const name of ['site/assets/model.mjs','site/assets/style.css','site/assets/unifont-model.mjs','site/assets/unifont.css','tools/unifont_proofs.mjs','tools/unifont_geometry.mjs'])await read(name);
  const bundles=await Promise.all(design.sourceFiles.map(name=>json('resources/unifont/'+name)));
  const byId=new Map(allocation.entries.map(entry=>[entry.glyphId,entry]));
  const stressIds=bundles.flatMap(bundle=>(bundle.groups||[]).flatMap(group=>group.glyphIds));
  const foundationIds=[...allocation.entries.filter(entry=>entry.parts.length===1).map(entry=>entry.glyphId),...design.pairGlyphIds,...stressIds];
  const withoutMiddle=allocation.entries.filter(entry=>!entry.parts.some(part=>part.middle));
  const expectedIds=new Set([...withoutMiddle.map(entry=>entry.glyphId),...stressIds]);
  if(design.stage!=='unextended'||withoutMiddle.length!==design.completeWithoutMiddle||expectedIds.size!==design.expectedDrawn)throw new Error('Unexpected scope for the complete group without middle components');
  const seen=new Set(),bitmaps=new Map();
  const glyphs=bundles.flatMap(bundle=>bundle.glyphs).map(source=>{
    const entry=byId.get(source.glyphId);
    if(!entry||!expectedIds.has(source.glyphId)||seen.has(source.glyphId))throw new Error(`Unexpected or duplicate bitmap identity: ${source.glyphId}`);
    seen.add(source.glyphId);
    if(source.width!==8)throw new Error(`A wider bitmap requires an individually reviewed exception: ${source.glyphId}`);
    const rows=rowsFromDrawing(source.rows,source.width),hex=rowHex(rows,source.width);
    if(rows.some(row=>row&128)||!rows.some(Boolean))throw new Error(`Blank glyph or occupied separation column: ${source.glyphId}`);
    if(bitmaps.has(hex))throw new Error(`Duplicate bitmap: ${source.glyphId} and ${bitmaps.get(hex)}`);
    bitmaps.set(hex,source.glyphId);
    const exact=design.exactDonors[source.glyphId];
    if(exact&&hex!==rowHex(donorMap.get(parseInt(exact,16)).rows,8))throw new Error(`Exact donor changed: ${source.glyphId}`);
    for(const donor of source.donors)if(!donorMap.has(parseInt(donor,16)))throw new Error(`Unknown donor ${donor}: ${source.glyphId}`);
    const assessment=assessBitmap(rows,8);
    for(const field of ['components','counters'])if(source.expected?.[field]!==undefined&&source.expected[field]!==assessment[field])throw new Error(`${source.glyphId}: expected ${source.expected[field]} ${field}, got ${assessment[field]}`);
    const line=entry.codePoint.toString(16).toUpperCase().padStart(6,'0')+':'+hex;
    return {...source,rows,line,hex,codePoint:entry.codePoint,name:entry.name,canonicalName:entry.canonicalName,familyId:entry.familyId,parts:entry.parts,bitmapSha256:sha256(line+'\n'),assessment};
  }).sort((a,b)=>a.codePoint-b.codePoint);
  if(seen.size!==expectedIds.size)throw new Error('Incomplete drawing source set');
  const byGlyph=new Map(glyphs.map(glyph=>[glyph.glyphId,glyph]));
  for(const glyph of glyphs){
    if(!glyph.recipe)continue;
    const {baseGlyphId,addPixels,removePixels,joinPixels}=glyph.recipe;
    const base=byGlyph.get(baseGlyphId);
    if(!base||base===glyph)throw new Error(`Invalid recipe base: ${glyph.glyphId}`);
    const rows=[...base.rows],joins=new Set((joinPixels||[]).map(pixel=>pixel.join(',')));
    for(const [pixels,on] of [[removePixels,false],[addPixels,true]])for(const [x,y] of pixels){
      if(x<1||x>7||y<0||y>15||!Number.isInteger(x)||!Number.isInteger(y))throw new Error(`Invalid recipe coordinate: ${glyph.glyphId}`);
      if(y>=6&&y<=13&&!joins.has(`${x},${y}`))throw new Error(`Undocumented body change: ${glyph.glyphId} at ${x},${y}`);
      if(on)rows[y]|=1<<(7-x);else rows[y]&=~(1<<(7-x));
    }
    if(rowHex(rows,8)!==glyph.hex)throw new Error(`Recipe and editable drawing differ: ${glyph.glyphId}`);
  }
  const groups=bundles.flatMap(bundle=>bundle.groups||[]).map(group=>{
    const base=byGlyph.get(group.glyphIds[0]);
    return {...group,differences:group.glyphIds.map(id=>({glyphId:id,pixels:pixelDiff(base.rows,byGlyph.get(id).rows)}))};
  });
  const nearDuplicates=[];
  for(let i=0;i<glyphs.length;i++)for(let j=i+1;j<glyphs.length;j++){
    const pixels=pixelDiff(glyphs[i].rows,glyphs[j].rows);
    if(pixels.length<=4)nearDuplicates.push({glyphIds:[glyphs[i].glyphId,glyphs[j].glyphId],pixels});
  }
  const sortedSources=Object.fromEntries(Object.entries(sources).sort(([a],[b])=>a.localeCompare(b)));
  const visualSourceSha256=sha256(JSON.stringify(sortedSources));
  const review=JSON.parse(await readFile(path.join(root,'resources/unifont/review.json'),'utf8'));
  for(const glyph of glyphs){
    glyph.proofSha256=sha256(JSON.stringify({bitmap:glyph.bitmapSha256,source:visualSourceSha256,reference:referenceSha256,donors:glyph.donors,notes:glyph.notes}));
    const record=review.records[glyph.glyphId];
    glyph.reviewStatus=record?.bitmapSha256===glyph.bitmapSha256&&record?.proofSha256===glyph.proofSha256&&record?.status==='inspected'?'inspected':'pending';
  }
  return {schemaVersion:1,stage:design.stage,foundationIds,withoutMiddle:withoutMiddle.length,expansionAuthorization:design.expansionAuthorization,userApproval:review.userApproval,sources:sortedSources,reference:{path:referencePath,sha256:referenceSha256},upstreamVersion:donorInfo.version,total:allocation.entries.length,drawn:glyphs.length,inspected:glyphs.filter(glyph=>glyph.reviewStatus==='inspected').length,glyphs,groups,nearDuplicates,hex:glyphs.map(glyph=>glyph.line).join('\n')+'\n'};
}
export async function buildUnifont({root=ROOT,check=false}={}){
  const result=await constructUnifont(root),hex=result.hex;
  delete result.hex;
  const outputs={'quintessential-latin.hex':hex,'glyphs.json':JSON.stringify(result,null,2)+'\n'};
  await mkdir(path.join(root,'resources/unifont'),{recursive:true});
  for(const [file,content] of Object.entries(outputs)){
    const target=path.join(root,'resources/unifont',file);
    if(check){if(await readFile(target,'utf8')!==content)throw new Error(`Stale Unifont output ${file}; run npm run build:unifont`);}
    else await writeFile(target,content);
  }
  return result;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  const result=await buildUnifont({check:process.argv.includes('--check')});
  console.log(`Unifont: ${result.drawn}/${result.total} drawn, all 8 x 16; ${result.inspected} inspected; complete ${result.withoutMiddle}-character group without middle components.`);
}
