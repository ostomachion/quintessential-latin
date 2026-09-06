import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import test from 'node:test';
import {escapeHtml,code,anchor} from '../site/assets/model.mjs';
import {renderIntroduction} from './site_introduction.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=relative=>readFile(path.join(root,relative),'utf8');
const json=async relative=>JSON.parse(await read(relative));
const [allocation,catalogue,proposal,coverage,serif,unifont,pdf]=await Promise.all([
  'resources/quintessential-latin-allocation.json','resources/catalogue.json',
  'docs/proposal.json','resources/font-coverage.json',
  'resources/fonts/QuintessentialSerif/build-manifest.json',
  'resources/fonts/QuintessentialUnifont/manifest.json','output/pdf/build-manifest.json'
].map(json));
const byId=new Map(catalogue.entries.map(entry=>[entry.glyphId,entry]));
const authority=await read('docs/source-authority.md');
const pages=['index.html','construction.html','charts.html','unifont.html','proposal.html','downloads.html'];
const html=new Map(await Promise.all(pages.map(async page=>[page,await read('dist/'+page)])));
const attribute=(tag,name)=>tag.match(new RegExp(`\\b${name}="([^"]*)"`))?.[1];

test('Publication versions and coverage counts keep repertoire and companion glyphs separate',()=>{
  const count=allocation.entries.length;
  for(const record of [catalogue,proposal,coverage,serif,unifont])assert.equal(record.version,allocation.version);
  assert.equal(pdf.repertoireVersion,allocation.version);
  assert.equal(pdf.namingVersion,allocation.namingVersion);
  assert.equal(catalogue.namingVersion,allocation.namingVersion);
  assert.equal(catalogue.entries.length,count);
  assert.equal(Object.keys(coverage.entries).length,count);
  for(const posture of ['Roman','Italic']){
    const expected=new Set(['U+0020',...allocation.entries.filter(entry=>entry.postures.includes(posture)).map(entry=>code(entry.codePoint))]);
    assert.deepEqual(new Set(serif.charactersByPosture[posture]),expected,posture);
    for(const entry of catalogue.entries)assert.equal(Boolean(coverage.entries[entry.glyphId][posture]),entry.postures.includes(posture),entry.glyphId);
  }
  assert.equal(unifont.customCharacters,count);
  assert.equal(unifont.encodedCharacters,count+unifont.nativeCompanions);
  assert.equal(unifont.glyphs,unifont.encodedCharacters+1);
  const slots=allocation.blocks.reduce((sum,block)=>sum+block.end-block.start+1,0);
  assert.equal(slots,count);
  const prose=JSON.stringify(proposal);
  assert(prose.includes(count.toLocaleString('en-US')),'Proposal must state the actual repertoire count');
  assert(authority.includes(`version **${allocation.version}**`),'Maintainer source map has a stale allocation version');
  assert(authority.includes(`naming version **${allocation.namingVersion}**`),'Maintainer source map has a stale naming version');
  assert(authority.includes(count.toLocaleString('en-US')),'Maintainer source map has a stale inventory count');
  assert(authority.includes(`**${allocation.families.length} families**`),'Maintainer source map has a stale family count');
  for(const block of allocation.blocks){
    assert(prose.includes(code(block.start)),`Proposal missing ${code(block.start)}`);
    assert(prose.includes(code(block.end)),`Proposal missing ${code(block.end)}`);
  }
});

test('Every explanatory character link derives its code and accessible name from the current catalogue',()=>{
  for(const [page,source] of html){
    for(const match of source.matchAll(/<a\b[^>]*\bdata-glyph="[^"]+"[^>]*>/g)){
      const tag=match[0],id=attribute(tag,'data-glyph'),entry=byId.get(id);
      assert(entry,`${page}: unknown example ${id}`);
      assert.equal(attribute(tag,'href')?.split('#')[1],anchor(entry.codePoint),`${page}: stale code for ${id}`);
      const label=attribute(tag,'aria-label');
      assert(label?.includes(escapeHtml(entry.canonicalName))||label?.includes(escapeHtml(entry.name)),`${page}: missing canonical accessible name for ${id}`);
      assert(label?.includes(code(entry.codePoint)),`${page}: missing accessible code for ${id}`);
    }
    for(const match of source.matchAll(/<span\b[^>]*\bdata-form="([^"]+)"[^>]*>\s*<span\b[^>]*class="glyph"[^>]*>([^<]*)<\/span>/gu)){
      const entry=byId.get(match[1]);
      assert(entry,`${page}: unknown rendered form ${match[1]}`);
      assert.equal(match[2],String.fromCodePoint(entry.codePoint),`${page}: wrong scalar for ${entry.glyphId}`);
      assert.equal([...match[2]].length,1,`${page}: supplementary scalar was split`);
    }
  }
});

test('Writing diagrams are static accessible continuous paths tied to actual constructions',()=>{
  const diagrams=[...html.get('index.html').matchAll(/<svg\b[^>]*data-writing-example="([^"]+)"[^>]*>([\s\S]*?)<\/svg>/g)];
  assert(diagrams.length>=2&&diagrams.length<=4,'Keep a small set of concrete writing examples');
  for(const [whole,id,body] of diagrams){
    assert(byId.has(id),`Unknown writing construction ${id}`);
    assert(/role="img"/.test(whole)&&/aria-labelledby="[^"]+"/.test(whole));
    assert(/<title\b[^>]*>[^<]+<\/title>/.test(body)&&/<desc\b[^>]*>[^<]+<\/desc>/.test(body));
    const paths=[...body.matchAll(/<path\b[^>]*class="intro-writing-path"[^>]*\bd="([^"]+)"/g)];
    assert.equal(paths.length,1,`${id}: a handwriting example needs one illustrated path`);
    assert.equal((paths[0][1].match(/[Mm]/g)||[]).length,1,`${id}: a second moveto would lift the pen`);
    assert(body.includes('x-height')&&body.includes('baseline'),`${id}: missing writing guides`);
  }
  // A structural change must demand diagram review rather than publish an old
  // path under a new construction label. The normal build exercises valid input.
  const changed=structuredClone(catalogue);
  changed.entries.find(entry=>entry.glyphId===diagrams[0][1]).parts=[{kind:'spine'}];
  assert.throws(()=>renderIntroduction({catalogue:changed,glyph:()=>'',scriptLink:()=>'',code,anchor,esc:escapeHtml}),/diagram no longer matches catalogue parts/);
});

test('Proposal examples and nearby citations are complete and share the standalone source',()=>{
  const references=new Set(proposal.references.map(reference=>reference.url));
  assert.equal(references.size,proposal.references.length,'Bibliography URLs must be unique');
  const required=[
    'https://www.kreativekorp.com/ucsur/',
    'https://www.evertype.com/standards/csur/',
    'https://www.evertype.com/standards/csur/naming.html',
    'https://www.unicode.org/faq/private_use.html',
    'https://www.evertype.com/standards/csur/seuss.html',
    'https://www.kreativekorp.com/ucsur/charts/sp-radicals.html'
  ];
  const resource=url=>{const parsed=new URL(url);return parsed.hostname.replace(/^www\./,'')+parsed.pathname.replace(/\/$/,'');};
  const resources=new Set([...references].map(resource));
  for(const url of required)assert(resources.has(resource(url)),`Missing primary reference ${url}`);
  let examples=0,citations=0;
  for(const section of proposal.sections){
    const generated=html.get('proposal.html').match(new RegExp(`<section[^>]* id="${section.id}"[^>]*>([\\s\\S]*?)</section>`))?.[1];
    assert(generated,`Missing proposal section ${section.id}`);
    for(const id of section.examples||[]){
      const entry=byId.get(id);assert(entry,`Unknown proposal example ${id}`);
      assert(generated.includes(`data-glyph="${id}"`),`Example ${id} missing from ${section.id}`);
      assert(generated.includes(escapeHtml(entry.canonicalName)),`Example name missing for ${id}`);
      assert(generated.includes(code(entry.codePoint)),`Example code missing for ${id}`);
      examples++;
    }
    for(const url of section.references||[]){
      assert(references.has(url),`Unlisted citation ${url}`);
      assert(generated.includes(`href="${escapeHtml(url)}"`),`Citation not beside section ${section.id}`);
      citations++;
    }
  }
  assert(examples>=4,'Representative distinctions should be illustrated');
  assert(citations>=4,'Registry facts need citations near their discussion');
});

test('Permanent section links remain valid across the six static pages',()=>{
  const ids=new Map();
  for(const [page,source] of html){
    const found=[...source.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
    assert.equal(new Set(found).size,found.length,`${page}: duplicate HTML IDs`);
    ids.set(page,new Set(found));
  }
  for(const [page,source] of html){
    for(const match of source.matchAll(/\bhref="([^"#]*#([^"]+))"/g)){
      const destination=match[1];
      if(/^[a-z][a-z\d+.-]*:/i.test(destination))continue;
      const [target,fragment]=destination.split('#');
      if(!ids.has(target||page))continue;
      assert(ids.get(target||page).has(decodeURIComponent(fragment)),`${page}: broken fragment ${destination}`);
    }
  }
});
