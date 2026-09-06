#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const {nameParts}=require("./canonical_glyph_names.js");
const root=path.resolve(__dirname,"..");
const allocation=JSON.parse(fs.readFileSync(path.join(root,"resources/quintessential-latin-allocation.json"),"utf8"));
const coverage=JSON.parse(fs.readFileSync(path.join(root,"resources/font-coverage.json"),"utf8"));
const check=process.argv.includes("--check");
for(const [filename,digest] of Object.entries(coverage.fontHashes)) {
  if(crypto.createHash("sha256").update(fs.readFileSync(path.join(root,"resources/fonts/QuintessentialSerif",filename))).digest("hex")!==digest)
    throw new Error("Compiled font changed; refresh coverage: "+filename);
}
const names=new Set(),ids=new Set(),codes=new Set();
const entries=allocation.entries.map(entry=>{
  if(["language","model","role"].some(key=>key in entry)) throw new Error("Allocation must describe neutral construction only.");
  const canonicalName=nameParts(entry.parts);
  const name="QUINTESSENTIAL LATIN LETTER "+canonicalName.toUpperCase();
  if(entry.canonicalName!==canonicalName || entry.name!==name) throw new Error("Stale name: "+entry.glyphId);
  if(names.has(name)||ids.has(entry.glyphId)||codes.has(entry.codePoint))throw new Error("Duplicate catalogue identity.");
  names.add(name);ids.add(entry.glyphId);codes.add(entry.codePoint);
  const metrics=coverage.entries[entry.glyphId];
  if(!metrics)throw new Error("Missing compiled coverage: "+entry.glyphId);
  const postures=["Roman","Italic"].filter(posture=>metrics[posture]);
  if(JSON.stringify(postures)!==JSON.stringify(entry.postures))throw new Error("Posture mismatch: "+entry.glyphId);
  return {glyphId:entry.glyphId,codePoint:entry.codePoint,name,canonicalName,familyId:entry.familyId,blockId:entry.blockId,parts:entry.parts,stemless:entry.stemless,postures,...(entry.baseGlyphId?{baseGlyphId:entry.baseGlyphId}:{}),...(entry.middleLegs?{middleLegs:true}:{}),metrics};
});
if(entries.length!==832||entries.filter(e=>e.postures.includes("Italic")).length!==232)throw new Error("Unexpected repertoire.");
if(allocation.displayOrder.length!==entries.length||new Set(allocation.displayOrder).size!==entries.length||allocation.displayOrder.some(id=>!ids.has(id)))throw new Error("Invalid display order.");
const catalogue={schemaVersion:1,version:allocation.version,namingVersion:allocation.namingVersion,axis:{min:400,max:700,default:400},blocks:allocation.blocks,families:allocation.families.map(f=>({id:f.id,title:f.title,...(f.baseFamilyId?{baseFamilyId:f.baseFamilyId}:{})})),displayOrder:allocation.displayOrder,entries};
const json=JSON.stringify(catalogue,null,2)+"\n";
const browser="/* Generated neutral Quintessential Latin catalogue. Project-local PUA assignments. */\n"+
"(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.QuintessentialLatinCatalogue=factory();})(typeof globalThis==='object'?globalThis:this,function(){\n"+
"const catalogue="+JSON.stringify(catalogue)+";\n"+
"const byId=new Map(catalogue.entries.map(e=>[e.glyphId,e]));const rank=new Map(catalogue.displayOrder.map((id,i)=>[id,i]));const compareDisplay=(a,b)=>rank.get(a.glyphId)-rank.get(b.glyphId);\n"+
"function freeze(v){if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;}return freeze({...catalogue,displayEntries:catalogue.displayOrder.map(id=>byId.get(id)),displayFamilies:catalogue.families,compareDisplay,sortForDisplay:items=>[...items].sort(compareDisplay)});});\n";
const byId=new Map(entries.map(e=>[e.glyphId,e]));
const namesList="; Quintessential Latin 0.220; proposed private-use allocation, not a registration.\n"+[...entries].sort((a,b)=>a.codePoint-b.codePoint).map(e=>e.codePoint.toString(16).toUpperCase()+"\t"+e.name).join("\n")+"\n";
const namesMd="# Quintessential Latin character names\n\nGenerated from the neutral structural allocation with canonical naming version "+allocation.namingVersion+".\nThese are project-local private-use names and assignments, not registered UCSUR names.\n\n| Code point | Character name | Native font postures |\n| --- | --- | --- |\n"+allocation.displayOrder.map(id=>byId.get(id)).map(e=>"| U+"+e.codePoint.toString(16).toUpperCase()+" | "+e.name+" | "+e.postures.join(", ")+" |").join("\n")+"\n";
for(const [filename,text] of Object.entries({"resources/catalogue.json":json,"glyph-catalogue.js":browser,"resources/NamesList.txt":namesList,"resources/quintessential-latin-name-catalogue.md":namesMd})){
  const output=path.join(root,filename);
  if(check){if(!fs.existsSync(output)||fs.readFileSync(output,"utf8")!==text)throw new Error("Stale generated file: "+filename);}
  else fs.writeFileSync(output,text);
}
console.log((check?"Verified":"Exported")+" 832 neutral names and compiled availability: 832 Roman, 232 Italic.");
