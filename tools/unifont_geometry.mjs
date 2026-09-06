export function rowsFromDrawing(drawing, width = 8) {
  if (drawing.length !== 16 || drawing.some(row => row.length !== width || /[^.#]/.test(row))) throw new Error('Expected 16 rows of explicit dot/hash pixels');
  return drawing.map(row => parseInt(row.replaceAll('.', '0').replaceAll('#', '1'), 2));
}
export const rowHex = (rows, width) => rows.map(row => row.toString(16).toUpperCase().padStart(width / 4, '0')).join('');
export const hasPixel = (rows, width, x, y) => x >= 0 && x < width && y >= 0 && y < 16 && Boolean(rows[y] & 1 << (width - x - 1));
export function pixelDiff(a, b, width = 8) {
  const pixels=[];
  for(let y=0;y<16;y++)for(let x=0;x<width;x++)if(hasPixel(a,width,x,y)!==hasPixel(b,width,x,y))pixels.push([x,y]);
  return pixels;
}
export function assessBitmap(rows, width) {
  const regions = ink => {
    const visited=new Set(),result=[];
    const steps=ink?[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]]:[[1,0],[-1,0],[0,1],[0,-1]];
    for(let y=0;y<16;y++)for(let x=0;x<width;x++){
      const key=y*width+x;
      if(visited.has(key)||hasPixel(rows,width,x,y)!==ink)continue;
      const cells=[[x,y]];visited.add(key);
      for(let i=0;i<cells.length;i++)for(const [dx,dy] of steps){
        const [cx,cy]=cells[i],nx=cx+dx,ny=cy+dy,nk=ny*width+nx;
        if(nx<0||nx>=width||ny<0||ny>=16||visited.has(nk)||hasPixel(rows,width,nx,ny)!==ink)continue;
        visited.add(nk);cells.push([nx,ny]);
      }
      result.push(cells);
    }
    return result;
  };
  const ink=regions(true),counters=regions(false).filter(region=>region.every(([x,y])=>x>0&&x<width-1&&y>0&&y<15)),flags=[];
  ink.filter(region=>region.length===1).forEach(region=>flags.push({kind:'isolated-pixel',pixels:region}));
  for(let y=0;y<15;y++)for(let x=0;x<width-1;x++){
    if([[x,y],[x+1,y],[x,y+1],[x+1,y+1]].every(([px,py])=>hasPixel(rows,width,px,py)))flags.push({kind:'solid-2x2',pixels:[[x,y],[x+1,y],[x,y+1],[x+1,y+1]]});
    if(hasPixel(rows,width,x,y)&&hasPixel(rows,width,x+1,y+1)&&!hasPixel(rows,width,x+1,y)&&!hasPixel(rows,width,x,y+1))flags.push({kind:'diagonal-contact',pixels:[[x,y],[x+1,y+1]]});
    if(hasPixel(rows,width,x+1,y)&&hasPixel(rows,width,x,y+1)&&!hasPixel(rows,width,x,y)&&!hasPixel(rows,width,x+1,y+1))flags.push({kind:'diagonal-contact',pixels:[[x+1,y],[x,y+1]]});
  }
  counters.filter(region=>region.length<=2).forEach(region=>flags.push({kind:'small-counter',pixels:region}));
  for(let y=1;y<15;y++)for(let x=1;x<width-1;x++){
    if(hasPixel(rows,width,x,y))continue;
    if(hasPixel(rows,width,x-1,y)&&hasPixel(rows,width,x+1,y))flags.push({kind:'one-pixel-channel',axis:'horizontal',pixels:[[x,y]]});
    if(hasPixel(rows,width,x,y-1)&&hasPixel(rows,width,x,y+1))flags.push({kind:'one-pixel-channel',axis:'vertical',pixels:[[x,y]]});
  }
  return {components:ink.length,counters:counters.length,counterPixels:counters,inkPixels:ink.flat().length,flags};
}
