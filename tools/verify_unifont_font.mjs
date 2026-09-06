import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';

export const UNIFONT_FONT_PATH='resources/fonts/QuintessentialUnifont';
export const UNIFONT_FONT_INPUTS=Object.freeze([
  'tools/build_unifont_font.py','tools/requirements-unifont.txt',
  'resources/unifont/quintessential-latin.hex','resources/unifont/font-companions.hex',
  'resources/unifont/font-companions.json','resources/unifont/OFL.txt',
  'resources/quintessential-latin-allocation.json',
]);
const outputs=['QuintessentialUnifont-Regular.ttf','QuintessentialUnifont-Regular.woff2','OFL.txt'];
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const keys=value=>Object.keys(value||{}).sort().join('|');
export async function verifyUnifontFontBuild(root){
  const fail=message=>{throw new Error(`Unifont font download is missing or stale: ${message}. Run npm run build:unifont:font.`);};
  const read=async file=>{try{return await readFile(path.join(root,file));}catch{fail(file);}};
  const manifest=JSON.parse(await read(UNIFONT_FONT_PATH+'/manifest.json'));
  if(manifest.schemaVersion!==1||manifest.customCharacters!==1216||manifest.nativeCompanions!==214||manifest.family!=='Quintessential Latin Unifont')fail('font identity or coverage');
  if(keys(manifest.sources)!==[...UNIFONT_FONT_INPUTS].sort().join('|')||keys(manifest.outputs)!==[...outputs].sort().join('|'))fail('incomplete source/output manifest');
  for(const file of UNIFONT_FONT_INPUTS)if(hash(await read(file))!==manifest.sources[file])fail(file);
  for(const file of outputs){const data=await read(UNIFONT_FONT_PATH+'/'+file),record=manifest.outputs[file];if(data.length!==record.bytes||hash(data)!==record.sha256)fail(file);}
  return manifest;
}
