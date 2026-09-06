import {readFile,writeFile} from 'node:fs/promises';
import {rowsFromDrawing,assessBitmap,pixelDiff,rowHex,hasPixel} from '../../tools/unifont_geometry.mjs';
const root=new URL('../../',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const allocation=await read('resources/quintessential-latin-allocation.json');
const existing=[];for(const p of ['primitives','pairs','stress','unextended-branches','unextended-spines'])existing.push(...(await read('resources/unifont/'+p+'.json')).glyphs);
const existingMap=new Map(existing.map(g=>[g.glyphId,g]));
const entries=allocation.entries.filter(e=>e.parts.some(p=>p.middle)&&!e.familyId.includes('opposed'));
const groupsMap=new Map();
function key(e){return e.familyId+':'+JSON.stringify(e.parts.map(p=>p.middle?{...p,lower:'none',upper:'none'}:p.long?{...p,returnContact:false}:p));}
for(const entry of entries){const k=key(entry);if(!groupsMap.has(k))groupsMap.set(k,[]);groupsMap.get(k).push(entry);}
const rowsToDrawing=rows=>rows.map(r=>Array.from({length:8},(_,x)=>r&(1<<(7-x))?'#':'.').join(''));
const glyphs=[],groups=[],layoutTemplates={};
for(const [,members]of groupsMap){
 const state=e=>e.parts.filter(p=>p.middle).map(p=>p.upper!=='none'||p.lower!=='none');
 const stateIndex=e=>state(e).reduce((n,on,i)=>n+(on?2**i:0),0);
 members.sort((a,b)=>stateIndex(a)-stateIndex(b));
 const first=members[0],middleCount=state(first).length,turned=first.parts[0].kind!=='stem',columns=middleCount===1?[1,4,7]:[1,3,5,7],last=first.parts.length-1;
 const terminal=first.parts[turned?0:last],kind=terminal.kind,long=Boolean(terminal.long),side=turned?'left':'right',templateId=`${middleCount}-middle-${side}-${long?'long-bowl':kind}`;
 const body=Array(16).fill(0),pixel=(rows,x,y,on=true)=>{if(on)rows[y]|=1<<(7-x);else rows[y]&=~(1<<(7-x));};
 const fill=(rows,x,from,to)=>{for(let y=from;y<=to;y++)pixel(rows,x,y);};
 const horizontal=(rows,a,b,y)=>{for(let x=a;x<=b;x++)pixel(rows,x,y);};
 if(!turned){columns.forEach((x,i)=>fill(body,x,i===0?6:7,13));for(let i=0;i<columns.length-1;i++)horizontal(body,columns[i]+1,columns[i+1]-1,6);}
 else {columns.forEach(x=>fill(body,x,6,12));pixel(body,columns.at(-1),13);for(let i=0;i<columns.length-1;i++)horizontal(body,columns[i]+1,columns[i+1]-1,13);}
 const lo=turned?columns[0]:columns.at(-2),hi=turned?columns[1]:columns.at(-1);
 if(!['leg','arm'].includes(kind)&&!long){
   for(let y=6;y<=13;y++)for(let x=lo;x<=hi;x++)pixel(body,x,y,false);
   if(!turned){
     fill(body,lo,7,13);horizontal(body,lo+1,hi-1,6);
     if(kind==='shoulder')fill(body,hi,7,8);
     if(kind==='bowl'){fill(body,hi,7,12);horizontal(body,lo+1,hi-1,13);}
     if(kind==='double bowl'){for(const y of [7,8,10,11,12])pixel(body,hi,y);horizontal(body,lo+1,hi-1,9);horizontal(body,lo+1,hi-1,13);}
     if(kind==='spine'){fill(body,hi,7,9);horizontal(body,lo+1,hi-1,10);pixel(body,hi,12);horizontal(body,lo+1,hi-1,13);}
   }else{
     fill(body,hi,6,12);horizontal(body,lo+1,hi-1,13);
     if(kind==='hip')fill(body,lo,11,12);
     if(kind==='bowl'){fill(body,lo,7,12);horizontal(body,lo+1,hi-1,6);}
     if(kind==='double bowl'){for(const y of [7,8,10,11,12])pixel(body,lo,y);horizontal(body,lo+1,hi-1,6);horizontal(body,lo+1,hi-1,9);}
     if(kind==='spine'){horizontal(body,lo+1,hi-1,6);pixel(body,lo,7);horizontal(body,lo+1,hi-1,9);fill(body,lo,10,12);}
   }
 }
 const baseRows=[...body],outerMasks=[];
 first.parts.forEach((part,index)=>{
   if(part.middle)return;
   const x=columns[index],additions=[];
   if(['stem','leg','arm'].includes(part.kind)){
     if(part.upper==='straight')for(const y of [3,4,5])additions.push([x,y]);
     if(part.upper==='curved')additions.push([x+1,3],[x+2,3],[x,4],[x,5]);
     if(part.lower==='straight')for(const y of [14,15])additions.push([x,y]);
     if(part.lower==='curved')additions.push([x,14],[x-2,15],[x-1,15]);
   }
   if(part.long){
     if(part.closingEnd==='upper'){for(let x=lo+1;x<hi;x++)additions.push([x,3]);additions.push([lo,4],[hi,4],[lo,5]);}
     else {additions.push([hi,14]);for(let x=lo+1;x<hi;x++)additions.push([x,15]);}
   }
   for(const [x,y]of additions)pixel(baseRows,x,y);
   if(additions.length)outerMasks.push({partIndex:index,pixels:additions});
 });
 const groupId='variants-'+first.glyphId;
 const donors=[...(turned?['0068','0064']:['0070','0071']),middleCount===1?(turned?'026F':'006D'):(turned?'026F':'006D'),...(kind==='shoulder'?['0072']:kind==='hip'?['0279']:kind==='bowl'&&!long?(turned?['0251']:['0062','0070']):kind==='double bowl'?(turned?['025B','0064','0071']:['025C','0062','0070']):kind==='spine'?(turned?['0061']:['0250']):['006E','0075']),...((long||first.parts.some(p=>p.upper==='curved'))?['0066']:[]),...((first.parts.some(p=>p.lower==='curved')||long)?['014B','0237']:[])];
 const description=`${middleCount===1?'Three':'Four'} staves use columns ${columns.join(', ')}. ${turned?'Native turned-m/u hips retain body rows 6–13; only the final right stave keeps its baseline pixel.':'Native m/n shoulders retain body rows 6–13; medial staves start beneath the roof at row 7.'} ${!['arm','leg'].includes(kind)&&!long?`The ${side} ${kind} is drawn explicitly within columns ${lo}–${hi}, retaining ${kind==='double bowl'?'two distinct counters':kind==='spine'?'the native '+(turned?'a lower counter and open upper sweep':'turned-a upper counter and open lower sweep'):kind==='bowl'?'one closed counter':'its open terminal'} without extra bulbs or repeated standalone serifs.`:''} ${long?`The long bowl returns only to part ${terminal.closingNeighbor} at column ${columns[terminal.closingNeighbor]}; its neighboring middle extension controls closure.`:''}`.trim();
 layoutTemplates[templateId]={columns,bodyRows:rowsToDrawing(body),terminalInterval:[lo,hi],donors:[...new Set(donors)],notes:description};
 groups.push({id:groupId,title:first.canonicalName+' — independent middle extensions',glyphIds:members.map(e=>e.glyphId),notes:description});
 for(const entry of members){
   const rows=[...baseRows],extensionPixels=[],middleParts=[];
   entry.parts.forEach((part,index)=>{if(!part.middle)return;const x=columns[index],mask=part.kind==='leg'?[[x,14],[x,15]]:[[x,3],[x,4],[x,5]],extended=part.upper!=='none'||part.lower!=='none';middleParts.push({partIndex:index,column:x,kind:part.kind,extended,pixels:mask});if(extended){extensionPixels.push(...mask);for(const [x,y]of mask)pixel(rows,x,y);}});
   const counters=kind==='double bowl'?2:kind==='spine'?1:kind==='bowl'&&!long?1:long&&entry.parts.find(p=>p.long).returnContact?1:0;
   const assessment=assessBitmap(rows,8);
   if(assessment.components!==1||assessment.counters!==counters)throw new Error(entry.glyphId+' topology '+JSON.stringify({components:assessment.components,counters:assessment.counters,expected:counters,rows:rowsToDrawing(rows)}));
   const layout={templateId,staveColumns:columns,partColumns:entry.parts.map((p,i)=>({partIndex:i,kind:p.kind,column:columns[i],middle:Boolean(p.middle)})),middleParts,outerMasks,terminalInterval:[lo,hi]};
   const structuralChecks={staveColumns:columns};
   if(long){const partIndex=turned?0:last,bowl=entry.parts[partIndex],closingNeighbor=bowl.closingNeighbor,closureGap=bowl.closingEnd==='upper'?[columns[closingNeighbor],5]:[columns[closingNeighbor],14],counterSeed=[lo+1,8];structuralChecks.closingNeighbor=closingNeighbor;structuralChecks.closureGap=closureGap;structuralChecks.counterSeed=counterSeed;if(hasPixel(rows,8,...closureGap)!==bowl.returnContact||assessment.counterPixels.some(region=>region.some(([x,y])=>x===counterSeed[0]&&y===counterSeed[1]))!==bowl.returnContact)throw new Error('Closure '+entry.glyphId);}
   const glyph={glyphId:entry.glyphId,width:8,rows:rowsToDrawing(rows),donors:[...new Set(donors)],notes:description+' Middle state: '+state(entry).map(x=>x?'extended':'short').join(', ')+'.',expected:{components:1,counters},reviewNotes:middleCount===2&&kind==='double bowl'?[`The three-column double bowl preserves a two-pixel upper counter at column ${lo+1}, rows 7–8, and a three-pixel lower counter at rows 10–12. The row-9 waist separates them; neither is a filled substitute.`]:[],layout,structuralChecks,extensionState:state(entry),extensionPixels};
   if(entry.glyphId!==first.glyphId){const addPixels=pixelDiff(baseRows,rows);glyph.recipe={baseGlyphId:first.glyphId,addPixels,removePixels:[],joinPixels:[]};}
   if(existingMap.has(entry.glyphId)){if(rowHex(rows,8)!==rowHex(rowsFromDrawing(existingMap.get(entry.glyphId).rows),8))throw new Error('Existing stress mismatch '+entry.glyphId);}
   else glyphs.push(glyph);
 }
}
if(glyphs.length!==496||groups.length!==168)throw new Error('Scope '+glyphs.length+'/'+groups.length);
const bits=new Map();for(const g of [...existing,...glyphs]){const hex=rowHex(rowsFromDrawing(g.rows),8);if(bits.has(hex))throw new Error('Duplicate '+g.glyphId+' = '+bits.get(hex));bits.set(hex,g.glyphId);}
const outputPath=new URL('resources/unifont/middle-branches.json',root);
const output=JSON.stringify({schemaVersion:1,constructionVersion:'compact-native-branches-1',sourceReferences:['construct_middle_branches.mjs'],layoutTemplates,groups,glyphs},null,2)+'\n';
if(process.argv.includes('--check')){
  if(await readFile(outputPath,'utf8')!==output)throw new Error('Stale middle-branches.json; run this constructor without --check');
}else await writeFile(outputPath,output);
console.log(`Generated ${glyphs.length} new drawings in ${groups.length} independent groups, with ${Object.keys(layoutTemplates).length} explicit compact layouts; all148 approved pixels preserved.`);
