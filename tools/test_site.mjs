import assert from 'node:assert/strict';
import {readFile,stat,readdir,mkdir,mkdtemp,cp,writeFile,rm} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {verifyPdfBuild,PDF_MANIFEST_PATH,PDF_SOURCE_PATHS,PDF_OUTPUT_NAMES} from './verify_pdf_build.mjs';
import {normalizeSettings,available,searchEntries,chartCode,printableSheets,chartChunks,glyphSize,code,escapeHtml} from '../site/assets/model.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const catalogue=JSON.parse(await readFile(path.join(root,'resources/catalogue.json'),'utf8'));
const read=relative=>readFile(path.join(root,relative),'utf8');
let groups=0;const test=async(name,fn)=>{await fn();groups++;console.log(`PASS ${name}`);};
await test('Mapped repertoire and native posture coverage',()=>{assert.equal(catalogue.entries.length,1216);assert.equal(catalogue.entries.filter(entry=>available(entry,false)).length,1216);assert.equal(catalogue.entries.filter(entry=>available(entry,true)).length,1216);assert.equal(new Set(catalogue.entries.map(entry=>entry.codePoint)).size,1216);assert.equal(new Set(catalogue.entries.map(entry=>entry.name)).size,1216);});
await test('Safe persisted controls with the complete variable axis',()=>{assert.deepEqual(normalizeSettings(null),{weight:400,italic:false});assert.deepEqual(normalizeSettings({weight:900,italic:true}),{weight:700,italic:true});assert.deepEqual(normalizeSettings({weight:200,italic:'false'}),{weight:400,italic:false});assert.deepEqual(normalizeSettings({weight:553,italic:true}),{weight:553,italic:true});});
await test('Code, name, literal-character, and compound search',()=>{const entry=catalogue.entries[0];assert.equal(searchEntries(catalogue.entries,code(entry.codePoint))[0],entry);assert.equal(searchEntries(catalogue.entries,String.fromCodePoint(entry.codePoint))[0],entry);assert(searchEntries(catalogue.entries,entry.canonicalName).includes(entry));assert.equal(searchEntries(catalogue.entries,'no-such-glyph-name').length,0);assert(searchEntries(catalogue.entries,'bowl').every(entry=>/bowl/i.test(entry.name)));});
await test('Search returns logical code order without changing permuted storage order',()=>{const inputs=[{codePoint:0xf2ac0,name:'double bowl',canonicalName:'double bowl'},{codePoint:0xf2a03,name:'stem',canonicalName:'stem'},{codePoint:0xf2a01,name:'open bowl',canonicalName:'open bowl'},{codePoint:0xf2ac1,name:'double open bowl',canonicalName:'double open bowl'}],before=[...inputs];assert.deepEqual(searchEntries(inputs,'bowl').map(entry=>entry.codePoint),[0xf2a01,0xf2ac0,0xf2ac1]);assert.deepEqual(inputs,before);});
await test('Unicode coordinates and five gapless publication sheets',()=>{assert.equal(chartCode(0xf2a00,3,11),0xf2ab3);const sheets=printableSheets(catalogue.blocks);assert.equal(sheets.length,5);assert.deepEqual(sheets.map(sheet=>(sheet.end-sheet.start+1)/16),[12,16,16,16,16]);const codes=sheets.flatMap(sheet=>Array.from({length:sheet.end-sheet.start+1},(_,index)=>sheet.start+index));assert.deepEqual(codes,Array.from({length:1216},(_,index)=>0xf2a00+index));assert.equal(codes.at(-1),0xf2ebf);});
await test('Partial responsive charts retain every position and stop before the next block',()=>{const block={start:0xf2a00,end:0xf2abf},sheet=printableSheets([block])[0];for(const maximum of [16,8,4]){const chunks=chartChunks(sheet,maximum);assert.deepEqual(chunks.map(chunk=>chunk.columns),maximum===16?[12]:maximum===8?[8,4]:[4,4,4]);const codes=chunks.flatMap(chunk=>Array.from({length:chunk.end-chunk.start+1},(_,index)=>chunk.start+index));assert.deepEqual(codes,Array.from({length:192},(_,index)=>block.start+index));}assert.equal(chartChunks(printableSheets([{start:0xf2ac0,end:0xf2bbf}])[0])[0].start,0xf2ac0);});
await test('Long forms fit their allocated representative widths',()=>{for(const entry of catalogue.entries){const size=glyphSize(entry,47,30);assert(size>0&&size<=30);for(const metric of Object.values(entry.metrics)){const width=Math.max(metric.advance,metric.bounds[2])-Math.min(0,metric.bounds[0]);assert(width*size/1000<=47.01,entry.glyphId);}}});
await test('HTML escaping protects generated text',()=>{assert.equal(escapeHtml('<a "x">&\''),'&lt;a &quot;x&quot;&gt;&amp;&#39;');});
const pages=['index.html','charts.html','proposal.html','downloads.html'];
await test('Four progressive pages share the controls and semantic navigation',async()=>{for(const page of pages){const html=await read(`dist/${page}`);assert(html.startsWith('<!doctype html>'));for(const id of ['main','font-weight','font-weight-value','font-italic','font-status'])assert.equal((html.match(new RegExp(`id="${id}"`,'g'))||[]).length,1,`${page}: ${id}`);assert(html.includes('aria-current="page"'));assert(html.includes('<noscript>'));assert(!/conlang|vowels|consonants|readingPairs|proof-data\.json/i.test(html),page);}});
await test('Project marks use the controlled reference font and removed page is absent',async()=>{
  const html=await read('dist/index.html'),point=String.fromCodePoint(catalogue.entries.find(entry=>entry.glyphId==='opposed-bowls-0-0').codePoint);
  assert(html.includes('<span class="brand-icon" aria-hidden="true"><span class="glyph-wrap"'));
  assert(html.includes('<span class="emblem-glyph"><span class="glyph-wrap"'));
  for(const mark of ['brand-icon','emblem-glyph'])assert(new RegExp(`class="${mark}"[^>]*><span class="glyph-wrap"[^>]*><span class="glyph"[^>]*>${point}</span>`,'u').test(html));
  assert(!html.includes('src="assets/project-icon.svg"'));
  assert((await readdir(path.join(root,'dist'))).filter(file=>file.endsWith('.html')).length===4);
  for(const page of pages)assert(!/specimen/i.test(await read('dist/'+page)),page);
  await assert.rejects(()=>stat(path.join(root,'dist/specimens.html')),error=>error.code==='ENOENT');
});
await test('Responsive static variants, five print grids, and one numeric names list',async()=>{
  const html=await read('dist/charts.html');
  assert.equal((html.match(/data-chart-kind="screen"/g)||[]).length,34);
  assert.equal((html.match(/data-chart-kind="print"/g)||[]).length,5);
  for(const columns of [16,8,4])assert.equal((html.match(new RegExp(`data-chart-columns="${columns}"`,'g'))||[]).length,5);
  const codes=[...html.matchAll(/data-name-codepoint="([A-F\d]+)"/g)].map(match=>parseInt(match[1],16));
  assert.equal(codes.length,1216);assert.deepEqual(codes,[...codes].sort((a,b)=>a-b));assert.equal(new Set(codes).size,1216);
  assert.equal((html.match(/class="vacant"/g)||[]).length,0);
  for(const entry of catalogue.entries)assert.equal((html.match(new RegExp(`id="u-${entry.codePoint.toString(16)}"`,'g'))||[]).length,1);
  for(const family of catalogue.families)assert(html.includes(`<h4>${escapeHtml(family.title)}</h4>`));
  const presentation=JSON.parse(await read('resources/chart-presentation.json')),css=await read('dist/assets/chart-presentation.css');
  assert(css.includes(`--chart-cell-width:${presentation.screen.cellWidth}px`));
  assert(css.includes(`@container chart (min-width:${presentation.screen.mediumWidth}px)`));
  assert(css.includes(`@container chart (min-width:${presentation.screen.wideWidth}px)`));
});
await test('Every local link and asset resolves beneath the Pages repository prefix',async()=>{for(const page of pages){const html=await read(`dist/${page}`);for(const match of html.matchAll(/(?:href|src)="([^"#]+)(?:#[^"]*)?"/g)){const url=match[1].split('#')[0];if(/^(?:https?:|data:|mailto:)/.test(url))continue;assert(!url.startsWith('/'),`${page}: absolute link ${url}`);const resolved=path.resolve(root,'dist',url);assert(resolved.startsWith(path.join(root,'dist')+path.sep));assert((await stat(resolved)).isFile(),`${page}: ${url}`);}}});
await test('Curated deployment excludes proof data and source trees',async()=>{const files=[];async function walk(directory){for(const entry of await readdir(directory,{withFileTypes:true})){const file=path.join(directory,entry.name);if(entry.isDirectory())await walk(file);else files.push(file);}}await walk(path.join(root,'dist'));assert(files.every(file=>!file.includes('proof-data')&&!file.endsWith('.ufo')&&!file.includes('build-manifest')));assert.equal(files.filter(file=>file.endsWith('.pdf')).length,5);assert.equal(await read('resources/NamesList.txt'),await read('dist/data/names-list.txt'));});
await test('PDF freshness binds current inputs and detects stale or altered publication artifacts',async()=>{
  await verifyPdfBuild(root);
  const temporaryRoot=path.resolve(root,'.tmp');await mkdir(temporaryRoot,{recursive:true});
  const fixture=await mkdtemp(path.join(temporaryRoot,'pdf-site-check-'));
  try{
    for(const relative of [...PDF_SOURCE_PATHS,PDF_MANIFEST_PATH,...PDF_OUTPUT_NAMES.map(name=>'output/pdf/'+name)]){
      const destination=path.join(fixture,relative);await mkdir(path.dirname(destination),{recursive:true});await cp(path.join(root,relative),destination);
    }
    await verifyPdfBuild(fixture);
    const proposalPath=path.join(fixture,'docs/proposal.json'),originalProposal=await readFile(proposalPath);
    await writeFile(proposalPath,Buffer.concat([originalProposal,Buffer.from('\n')]));
    await assert.rejects(()=>verifyPdfBuild(fixture),/docs\/proposal\.json changed.*python tools\/build_pdfs\.py/);
    await writeFile(proposalPath,originalProposal);
    const pdfPath=path.join(fixture,'output/pdf',PDF_OUTPUT_NAMES[0]),originalPdf=await readFile(pdfPath);
    await writeFile(pdfPath,Buffer.concat([originalPdf,Buffer.from('altered')]));
    await assert.rejects(()=>verifyPdfBuild(fixture),/does not match.*python tools\/build_pdfs\.py/);
    await writeFile(pdfPath,originalPdf);
    const manifestPath=path.join(fixture,PDF_MANIFEST_PATH),originalManifest=await readFile(manifestPath),manifest=JSON.parse(originalManifest.toString('utf8'));
    delete manifest.sources['docs/proposal.json'];await writeFile(manifestPath,JSON.stringify(manifest));
    await assert.rejects(()=>verifyPdfBuild(fixture),/complete required source set.*python tools\/build_pdfs\.py/);
    await writeFile(manifestPath,originalManifest);await rm(manifestPath);
    await assert.rejects(()=>verifyPdfBuild(fixture),/cannot read output\/pdf\/build-manifest\.json.*python tools\/build_pdfs\.py/);
  }finally{
    assert(path.resolve(fixture).startsWith(temporaryRoot+path.sep),'Temporary fixture must stay inside its intended workspace directory');
    await rm(fixture,{recursive:true,force:true});
  }
});
console.log(`${groups} site acceptance groups passed.`);
