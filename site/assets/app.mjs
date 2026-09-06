import {available,normalizeSettings,searchEntries,code,anchor,glyphSize} from './model.mjs';
import {typeGuidesMarkup} from './type-guides.mjs';
const storageKey='quintessential-latin-font';
let saved={};try{saved=JSON.parse(localStorage.getItem(storageKey)||'{}');}catch{}
let settings=normalizeSettings(saved),catalogue,byId,byCode,activeEntry,announcementTimer,fontRequest=0;
const $=selector=>document.querySelector(selector);
const $$=selector=>[...document.querySelectorAll(selector)];
const weight=$('#font-weight'),italic=$('#font-italic'),fontStatus=$('#font-status');
const dialog=$('#character-dialog');
let dialogChartOrigin;
document.documentElement.classList.add('enhanced');
function announce(message){$('#announcement').textContent=message;clearTimeout(announcementTimer);announcementTimer=setTimeout(()=>{$('#announcement').textContent='';},3500);}
function applyPosture(root=document){root.querySelectorAll('[data-form]').forEach(element=>{const pending=settings.italic&&element.dataset.italic!=='true';element.classList.toggle('is-pending',pending);const link=element.closest('[data-glyph]');if(link){link.classList.toggle('is-pending',pending);const label=link.getAttribute('aria-label');if(label){link.setAttribute('aria-label',label.replace(/ — Italic pending$/,'')+(pending?' — Italic pending':''));}}});}
function saveSettings(){try{localStorage.setItem(storageKey,JSON.stringify(settings));}catch{}}
async function loadFont(){const request=++fontRequest;document.body.dataset.fonts='loading';fontStatus.classList.remove('error');fontStatus.textContent='Loading reference font…';try{const sample=$('[data-italic="true"] .glyph')?.textContent||String.fromCodePoint(0xf2a07);const faces=await document.fonts.load(`${settings.italic?'italic':'normal'} ${settings.weight} 30px "Quintessential Serif"`,sample);if(!faces.length)throw new Error('Reference font was not loaded');if(request!==fontRequest)return;document.body.dataset.fonts='ready';document.documentElement.classList.remove('font-failed');fontStatus.textContent='';}catch{if(request!==fontRequest)return;document.body.dataset.fonts='error';document.documentElement.classList.add('font-failed');fontStatus.classList.add('error');fontStatus.textContent='Reference font could not load. Reload this page to retry.';}}
function applySettings(persist=true){if(weight)weight.value=settings.weight;if(italic)italic.checked=settings.italic;if($('#font-weight-value'))$('#font-weight-value').value=String(settings.weight);document.documentElement.style.setProperty('--script-weight',settings.weight);document.documentElement.style.setProperty('--script-style',settings.italic?'italic':'normal');document.documentElement.dataset.posture=settings.italic?'Italic':'Roman';$$('[data-print-posture]').forEach(item=>{item.textContent=settings.italic?'Italic':'Roman';});$$('[data-print-weight]').forEach(item=>{item.textContent=settings.weight;});applyPosture();if(catalogue)updateDialog();if(persist)saveSettings();loadFont();}
weight?.addEventListener('input',()=>{settings=normalizeSettings({...settings,weight:Number(weight.value)});applySettings();});
italic?.addEventListener('change',()=>{settings={...settings,italic:italic.checked};applySettings();});
window.addEventListener('storage',event=>{if(event.key!==storageKey)return;try{settings=normalizeSettings(JSON.parse(event.newValue||'{}'));applySettings(false);}catch{}});
applySettings(false);
function makeGlyph(entry,width=48,maximum=32){const wrap=document.createElement('span');wrap.className='glyph-wrap';wrap.dataset.form=entry.glyphId;wrap.dataset.italic=String(entry.postures.includes('Italic'));const character=document.createElement('span');character.className='glyph';character.textContent=String.fromCodePoint(entry.codePoint);character.setAttribute('aria-hidden','true');character.style.setProperty('--glyph-size',`${glyphSize(entry,width,maximum).toFixed(2)}px`);const pending=document.createElement('span');pending.className='pending-label';pending.textContent='Italic pending';wrap.append(character,pending);wrap.classList.toggle('is-pending',!available(entry,settings.italic));return wrap;}
async function copy(text,success){try{await navigator.clipboard.writeText(text);announce(success);}catch{const helper=document.createElement('textarea');helper.value=text;helper.style.position='fixed';helper.style.opacity='0';document.body.append(helper);helper.select();let copied=false;try{copied=document.execCommand('copy');}catch{}helper.remove();announce(copied?success:'Copy is unavailable. Select and copy the character code.');}}
function sizeDialogStudy(){
  const study=$('#dialog-glyph .type-study');
  if(!study||!activeEntry||!dialog.open)return;
  // Reserve the left gutter for metric labels, including on a narrow phone.
  study.style.setProperty('--study-size',`${glyphSize(activeEntry,Math.max(40,study.clientWidth-92),145).toFixed(2)}px`);
}
function updateDialog(){if(!activeEntry)return;const entry=activeEntry;$('#dialog-code').textContent=code(entry.codePoint);$('#dialog-name').textContent=entry.name;const study=document.createElement('div');study.className='type-study';study.innerHTML=typeGuidesMarkup(true);study.append(makeGlyph(entry));$('#dialog-glyph').replaceChildren(study);sizeDialogStudy();const family=catalogue.families.find(item=>item.id===entry.familyId),block=catalogue.blocks.find(item=>item.id===entry.blockId);$('#dialog-meta').textContent=`${block?.title||''} · ${family?.title||''}. ${entry.postures.includes('Italic')?'Roman and native Italic available.':'Roman available; native Italic pending.'}`;$('#character-permalink').href=`charts.html#${anchor(entry.codePoint)}`;}
function openCharacter(entry,updateHistory=true,origin){if(!entry)return;dialogChartOrigin=origin?{code:origin.dataset.code,block:origin.closest(".chart-block")}:undefined;activeEntry=entry;updateDialog();if(!dialog.open)dialog.showModal();sizeDialogStudy();if(updateHistory)history.replaceState(null,'',`#${anchor(entry.codePoint)}`);}
window.addEventListener('resize',sizeDialogStudy);
$('#close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('close',()=>{
  const origin=dialogChartOrigin;dialogChartOrigin=undefined;
  if(!origin)return;
  const target=[...origin.block.querySelectorAll(`.chart-variant .chart-cell[data-code="${origin.code}"]`)].find(cell=>cell.getClientRects().length);
  if(target){target.focus({preventScroll:true});target.scrollIntoView({block:'nearest',inline:'nearest'});}
});
dialog.addEventListener('click',event=>{if(event.target===dialog){const bounds=dialog.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)dialog.close();}});
$('#copy-character').addEventListener('click',()=>{if(activeEntry)copy(String.fromCodePoint(activeEntry.codePoint),'Character copied');});
$('#copy-code').addEventListener('click',()=>{if(activeEntry)copy(code(activeEntry.codePoint),'Code point copied');});
document.addEventListener('click',event=>{const link=event.target.closest('a[data-glyph]');if(!link||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||event.button!==0||!byId)return;event.preventDefault();openCharacter(byId.get(link.dataset.glyph),true,link.closest(".chart-variant")?link:undefined);});
function openHash(){const match=location.hash.match(/^#u-([\da-f]+)$/i);if(match&&byCode)openCharacter(byCode.get(parseInt(match[1],16)),false);}
window.addEventListener('hashchange',openHash);
function renderSearch(){const search=$('#character-search');if(!search||!catalogue)return;const query=search.value.trim(),section=$('#search-results');section.hidden=!query;if(!query){$('#result-count').textContent=`${catalogue.entries.length.toLocaleString('en-US')} mapped characters${catalogue.blocks.reduce((count,block)=>count+block.end-block.start+1,0)>catalogue.entries.length?' · '+(catalogue.blocks.reduce((count,block)=>count+block.end-block.start+1,0)-catalogue.entries.length)+' unallocated positions':''}`;section.querySelector('ul').replaceChildren();return;}const results=searchEntries(catalogue.entries,query);$('#result-count').textContent=`${results.length} ${results.length===1?'character':'characters'} found`;const fragment=document.createDocumentFragment();for(const entry of results){const item=document.createElement('li'),link=document.createElement('a');link.href=`#${anchor(entry.codePoint)}`;link.dataset.glyph=entry.glyphId;link.setAttribute('aria-label',`${code(entry.codePoint)} ${entry.name}`);const point=document.createElement('span');point.className='code';point.textContent=code(entry.codePoint);const name=document.createElement('span');name.className='entry-name';name.textContent=entry.name;link.append(point,makeGlyph(entry,64,34),name);item.append(link);fragment.append(item);}section.querySelector('ul').replaceChildren(fragment);applyPosture(section);}
$('#character-search')?.addEventListener('input',renderSearch);

// Static variants work without JavaScript. Preserve the focused character when
// a container breakpoint changes which chart is visible.
let focusedChart;
document.addEventListener('focusin',event=>{
  const cell=event.target.closest('.chart-variant .chart-cell');
  if(cell)focusedChart={cell,code:cell.dataset.code,block:cell.closest('.chart-block')};
  else if(event.target!==document.body)focusedChart=undefined;
});
document.addEventListener('pointerdown',event=>{if(!event.target.closest('.chart-cell'))focusedChart=undefined;});
if(typeof ResizeObserver!=='undefined'){
  const chartResize=new ResizeObserver(()=>{
    if(!focusedChart||focusedChart.cell.getClientRects().length)return;
    const replacement=[...focusedChart.block.querySelectorAll(`.chart-variant .chart-cell[data-code="${focusedChart.code}"]`)].find(cell=>cell.getClientRects().length);
    if(replacement){replacement.focus({preventScroll:true});replacement.scrollIntoView({block:'nearest',inline:'nearest'});}
  });
  $$('.chart-block').forEach(block=>chartResize.observe(block));
}
document.addEventListener('keydown',event=>{const current=event.target.closest('.chart-cell');if(!current||event.altKey||event.ctrlKey||event.metaKey)return;const deltas={ArrowLeft:-16,ArrowRight:16,ArrowUp:-1,ArrowDown:1};const grid=current.closest('table'),links=[...grid.querySelectorAll('.chart-cell')];let destination;if(event.key==='Home')destination=links.find(link=>Number(link.dataset.code)%16===Number(current.dataset.code)%16);else if(event.key==='End')destination=links.filter(link=>Number(link.dataset.code)%16===Number(current.dataset.code)%16).at(-1);else if(event.key in deltas){const delta=deltas[event.key],currentCode=Number(current.dataset.code),vertical=Math.abs(delta)===1,columnStart=currentCode-currentCode%16,minimum=vertical?columnStart:Number(grid.dataset.start),maximum=vertical?columnStart+15:Number(grid.dataset.end);let candidate=currentCode+delta;while(candidate>=minimum&&candidate<=maximum){destination=grid.querySelector(`[data-code="${candidate}"]`);if(destination)break;candidate+=delta;}}else return;event.preventDefault();destination?.focus();});
try{const response=await fetch(new URL('../data/catalogue.json',import.meta.url));if(!response.ok)throw new Error('Catalogue response failed');catalogue=await response.json();byId=new Map(catalogue.entries.map(entry=>[entry.glyphId,entry]));byCode=new Map(catalogue.entries.map(entry=>[entry.codePoint,entry]));document.body.dataset.catalogue='ready';renderSearch();openHash();}catch{document.body.dataset.catalogue='error';fontStatus.textContent='Character data could not load. Static charts remain available; reload to retry.';fontStatus.classList.add('error');}
