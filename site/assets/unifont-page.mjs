import {inspectorMarkup} from './unifont-model.mjs';
import './unifont-pixels.mjs';
const inspector=document.querySelector('#unifont-inspector');
const status=document.querySelector('#unifont-selection-status');
try{
  const response=await fetch(new URL('../unifont/inspector.json',import.meta.url));
  if(!response.ok)throw new Error('Bitmap metadata unavailable');
  const metadata=await response.json(),byCode=new Map(metadata.glyphs.map(glyph=>[glyph.codePoint,glyph]));
  const links=[...document.querySelectorAll('.bitmap-cell')];
  function select(point,historyChange=false){
    const glyph=byCode.get(point);
    if(!glyph){status.textContent='This character has not been drawn yet.';return;}
    inspector.innerHTML=inspectorMarkup(glyph);
    links.forEach(link=>{if(parseInt(link.closest('td').dataset.unifontCode,16)===point){link.setAttribute('aria-current','true');link.closest('details').open=true;}else link.removeAttribute('aria-current');});
    status.textContent=`Selected U+${point.toString(16).toUpperCase()} ${glyph.canonicalName}`;
    if(historyChange)history.pushState(null,'',`#bitmap-${point.toString(16)}`);
  }
  function fromHash(){
    const match=location.hash.match(/^#bitmap-([0-9a-f]+)$/i);
    if(!match)return;
    const point=parseInt(match[1],16);select(point);
    if(byCode.has(point))inspector.scrollIntoView({block:'start'});
  }
  document.addEventListener('click',event=>{
    const link=event.target.closest('.bitmap-cell');
    if(!link||event.button!==0||event.ctrlKey||event.metaKey||event.altKey||event.shiftKey)return;
    event.preventDefault();select(parseInt(link.closest('td').dataset.unifontCode,16),true);
    if(innerWidth<=1000)inspector.scrollIntoView({block:'start'});
  });
  document.addEventListener('keydown',event=>{
    const current=event.target.closest('.bitmap-cell');
    if(!current||event.ctrlKey||event.metaKey||event.altKey)return;
    const deltas={ArrowLeft:-16,ArrowRight:16,ArrowUp:-1,ArrowDown:1};
    if(!(event.key in deltas))return;
    event.preventDefault();
    const point=parseInt(current.closest('td').dataset.unifontCode,16),grid=current.closest('table'),start=Number(grid.dataset.start),delta=deltas[event.key];
    const min=Math.abs(delta)===1?point-point%16:start,max=Math.abs(delta)===1?point-point%16+15:start+255;
    for(let candidate=point+delta;candidate>=min&&candidate<=max;candidate+=delta){
      const next=grid.querySelector(`[data-unifont-code="${candidate.toString(16).toUpperCase()}"] .bitmap-cell`);
      if(next){next.focus();select(candidate,true);break;}
    }
  });
  window.addEventListener('hashchange',fromHash);
  select(metadata.glyphs[0].codePoint);fromHash();
  document.body.dataset.unifont='ready';
}catch{
  status.textContent='Interactive selection could not load. Each chart link still opens its static proof.';
  document.body.dataset.unifont='error';
}
