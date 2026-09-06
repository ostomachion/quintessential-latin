import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {parseHex} from '../site/assets/unifont-model.mjs';
import {rowsFromDrawing,rowHex,assessBitmap,pixelDiff} from './unifont_geometry.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export const sha256=value=>createHash('sha256').update(value).digest('hex');
// Keep generated per-glyph and per-comparison records on separate lines.
// Coordinates remain readable in the editable drawing sources and proofs.
export function serializeUnifontRecords(value,compactFields){
  return '{\n'+Object.entries(value).map(([key,item])=>{
    const data=compactFields.includes(key)?'[\n'+item.map(record=>'    '+JSON.stringify(record)).join(',\n')+'\n  ]':JSON.stringify(item,null,2).replaceAll('\n','\n  ');
    return '  '+JSON.stringify(key)+': '+data;
  }).join(',\n')+'\n}\n';
}
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
  for(const name of ['site/assets/model.mjs','site/assets/style.css','site/assets/type-guides.mjs','site/assets/unifont-model.mjs','site/assets/unifont-pixels.mjs','site/assets/unifont.css','tools/unifont_proofs.mjs','tools/unifont_geometry.mjs'])await read(name);
  const bundles=await Promise.all(design.sourceFiles.map(name=>json('resources/unifont/'+name)));
  const byId=new Map(allocation.entries.map(entry=>[entry.glyphId,entry]));
  if(byId.size!==1216||new Set(allocation.entries.map(entry=>entry.codePoint)).size!==1216||allocation.entries.some(entry=>entry.codePoint<0xf2a00||entry.codePoint>0xf2ebf))throw new Error('Allocation is not the unique complete 1216-character range');
  for(const bundle of bundles)for(const name of bundle.sourceReferences||[])await read('resources/unifont/'+name);
  const stressIds=bundles[design.sourceFiles.indexOf('stress.json')].groups.flatMap(group=>group.glyphIds);
  const foundationIds=[...allocation.entries.filter(entry=>entry.parts.length===1).map(entry=>entry.glyphId),...design.pairGlyphIds,...stressIds];
  const withoutMiddle=allocation.entries.filter(entry=>!entry.parts.some(part=>part.middle));
  const expectedIds=new Set(allocation.entries.map(entry=>entry.glyphId));
  if(design.stage!=='complete-repertoire'||withoutMiddle.length!==design.completeWithoutMiddle||expectedIds.size!==1216||design.expectedDrawn!==1216)throw new Error('Unexpected scope for the complete repertoire');
  const baselineBytes=await read('resources/unifont/approved-baseline.hex');
  if(sha256(baselineBytes)!=='76e0a9f5f073ef4ddec768e82e66c94a38ccac8234254a3a66761ec6d76f3020')throw new Error('Approved 148-character baseline changed');
  const baseline=parseHex(baselineBytes.toString('utf8'));
  if(baseline.size!==148)throw new Error('Incomplete approved baseline');
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
    if(baseline.has(entry.codePoint)&&baseline.get(entry.codePoint).line!==line)throw new Error(`Approved bitmap changed: ${source.glyphId}`);
    return {...source,rows,line,hex,codePoint:entry.codePoint,name:entry.name,canonicalName:entry.canonicalName,familyId:entry.familyId,parts:entry.parts,bitmapSha256:sha256(line+'\n'),assessment};
  }).sort((a,b)=>a.codePoint-b.codePoint);
  if(seen.size!==expectedIds.size)throw new Error('Incomplete drawing source set');
  const byGlyph=new Map(glyphs.map(glyph=>[glyph.glyphId,glyph]));
  for(const bundle of bundles)for(const source of bundle.glyphs){
    const template=bundle.layoutTemplates?.[source.layout?.templateId];
    if(!template)continue;
    const rows=rowsFromDrawing(template.bodyRows,8);
    for(const [x,y] of [...source.layout.outerMasks.flatMap(mask=>mask.pixels),...source.extensionPixels])rows[y]|=1<<(7-x);
    if(rowHex(rows,8)!==byGlyph.get(source.glyphId).hex)throw new Error(`Component layout and drawing differ: ${source.glyphId}`);
  }
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
  const groupKeys=new Set();
  const groups=bundles.flatMap(bundle=>bundle.groups||[]).filter(group=>{
    const key=[...group.glyphIds].sort().join('|');
    if(groupKeys.has(key))return false;
    groupKeys.add(key);return true;
  }).map(group=>{
    const base=byGlyph.get(group.glyphIds[0]);
    return {...group,differences:group.glyphIds.map(id=>({glyphId:id,pixels:pixelDiff(base.rows,byGlyph.get(id).rows)}))};
  });
  const nearDuplicates=[];
  const popcount=Array.from({length:256},(_,n)=>n.toString(2).replaceAll('0','').length);
  for(let i=0;i<glyphs.length;i++)for(let j=i+1;j<glyphs.length;j++){
    let distance=0;
    for(let y=0;y<16&&distance<=4;y++)distance+=popcount[glyphs[i].rows[y]^glyphs[j].rows[y]];
    if(distance>4)continue;
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
  const inspector={glyphs:result.glyphs.map(({glyphId,codePoint,canonicalName,familyId,width,rows,line,notes,reviewStatus,assessment})=>({glyphId,codePoint,canonicalName,familyId,width,rows,line,notes,reviewStatus,assessment:{components:assessment.components,counters:assessment.counters,flagCount:assessment.flags.length}}))};
  const outputs={'quintessential-latin.hex':hex,'glyphs.json':serializeUnifontRecords(result,['glyphs','groups','nearDuplicates']),'inspector.json':JSON.stringify(inspector)+'\n'};
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
  console.log(`Unifont: ${result.drawn}/${result.total} drawn, all 8 x 16; ${result.inspected} inspected; ${result.groups.filter(g=>g.glyphIds.length===2).length} pairs and ${result.groups.filter(g=>g.glyphIds.length===4).length} quartets.`);
}
