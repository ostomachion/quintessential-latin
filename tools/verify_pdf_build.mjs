import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';

export const PDF_MANIFEST_PATH='output/pdf/build-manifest.json';
export const PDF_SOURCE_PATHS=Object.freeze([
  'resources/catalogue.json',
  'docs/proposal.json',
  'resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf',
  'resources/fonts/STIXTwoText/STIXTwoText-VariableFont_wght.ttf',
  'tools/build_pdfs.py',
  'tools/requirements-pdfs.txt',
]);
export const PDF_OUTPUT_NAMES=Object.freeze([
  'quintessential-latin.pdf',
  'quintessential-latin-extended-a.pdf',
  'quintessential-latin-extended-b.pdf',
  'quintessential-latin-catalogue.pdf',
  'quintessential-latin-proposal.pdf',
]);
const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const fail=reason=>{throw new Error(`PDF reference build is missing or stale: ${reason}. Regenerate with: python tools/build_pdfs.py`);};
const sameKeys=(record,keys)=>record&&typeof record==='object'&&!Array.isArray(record)&&Object.keys(record).sort().join('\n')===[...keys].sort().join('\n');

/** Verify the checked-in PDFs against every content and font input before deployment. */
export async function verifyPdfBuild(root){
  const read=async relative=>{try{return await readFile(path.join(root,relative));}catch{fail(`cannot read ${relative}`);}};
  let manifest;
  try{manifest=JSON.parse((await read(PDF_MANIFEST_PATH)).toString('utf8'));}catch(error){if(error.message.includes('Regenerate with:'))throw error;fail(`invalid JSON in ${PDF_MANIFEST_PATH}`);}
  if(!manifest||typeof manifest!=='object'||Array.isArray(manifest))fail('invalid manifest object');
  if(manifest.schemaVersion!==1)fail('unsupported manifest schema');
  if(!sameKeys(manifest.sources,PDF_SOURCE_PATHS))fail('manifest does not bind the complete required source set');
  if(!sameKeys(manifest.outputs,PDF_OUTPUT_NAMES))fail('manifest does not bind exactly the five reference PDFs');
  if(manifest.reference?.font!=='Quintessential Serif'||manifest.reference?.posture!=='Roman'||manifest.reference?.weight!==400)fail('manifest reference must be Quintessential Serif Roman 400');
  const sources=new Map();
  for(const relative of PDF_SOURCE_PATHS){
    const bytes=await read(relative);sources.set(relative,bytes);
    if(!/^[a-f0-9]{64}$/.test(manifest.sources[relative]||'')||sha256(bytes)!==manifest.sources[relative])fail(`${relative} changed after PDF generation`);
  }
  const catalogue=JSON.parse(sources.get('resources/catalogue.json').toString('utf8'));
  if(manifest.repertoireVersion!==catalogue.version||manifest.namingVersion!==catalogue.namingVersion)fail('manifest repertoire or naming version differs from the catalogue');
  for(const name of PDF_OUTPUT_NAMES){
    const record=manifest.outputs[name],bytes=await read(`output/pdf/${name}`);
    if(!record||!Number.isInteger(record.pages)||record.pages<1||record.bytes!==bytes.length||! /^[a-f0-9]{64}$/.test(record.sha256||'')||sha256(bytes)!==record.sha256)fail(`${name} does not match its generated PDF record`);
  }
  return manifest;
}
