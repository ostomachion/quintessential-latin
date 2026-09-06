"""Render source-bound before/after proofs for the native terminal revision."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]
BASE = DIR.parent
data = json.loads((BASE / 'glyphs.json').read_text(encoding='utf8'))
revisions = json.loads((BASE / 'tail-revisions.json').read_text(encoding='utf8'))
current = {g['glyphId']: g for g in data['glyphs']}
old = {r['glyphId']: list(bytes.fromhex(r['before'].split(':')[1])) for r in revisions['glyphs']}
donors = {d['codePoint']: list(bytes.fromhex(d['hex'])) for d in json.loads((BASE / 'donors.json').read_text())['donors']}
fontpath = ROOT / 'resources/fonts/SourceSans3/SourceSans3-Regular.ttf'
font = ImageFont.truetype(str(fontpath), 17)
small = ImageFont.truetype(str(fontpath), 14)
heading = ImageFont.truetype(str(fontpath), 27)

def glyph(draw, rows, x, y, scale, color='#193d30', grid=False):
    if grid:
        for k in range(9): draw.line((x+k*scale,y,x+k*scale,y+16*scale), fill='#d8ded5')
        for k in range(17): draw.line((x,y+k*scale,x+8*scale,y+k*scale), fill='#d8ded5')
    for row, bits in enumerate(rows):
        for col in range(8):
            if bits & (128 >> col): draw.rectangle((x+col*scale,y+row*scale,x+(col+1)*scale-1,y+(row+1)*scale-1), fill=color)

hero = Image.new('RGB',(1040,470),'#fafaf6')
d = ImageDraw.Draw(hero)
d.text((24,14),'Native Unifont precedents / corrected Quintessential forms',font=heading,fill='#193d30')
for i,(gid,cp,label) in enumerate([('tail','0237','TAIL / dotless j'),('turned-bowl-tail','0261','BOWL WITH TAIL / script g'),('turned-arch-tail','0079','ARM WITH TAIL / y')]):
    x=24+i*344
    d.text((x,66),label,font=font,fill='#193d30')
    for j,(rows,title) in enumerate([(old[gid],'Before'),(current[gid]['rows'],'After'),(donors[cp],'Native')]):
        px=x+j*106
        d.text((px,100),title,font=small,fill='#647367')
        glyph(d,rows,px,128,10,grid=True)
        glyph(d,rows,px+12,316,2)
        for repeat in range(8): glyph(d,rows,px+repeat*8,374,1)
    d.text((x,419),'After = native, all 128 pixels',font=font,fill='#193d30')
hero.save(DIR/'native-comparison.png')

manifest={'currentHexSha256':hashlib.sha256((BASE/'quintessential-latin.hex').read_bytes()).hexdigest(),'changed':len(old),'preserved':1216-len(old),'userAcceptance':None,'pages':[]}
for start in range(0,len(revisions['glyphs']),24):
    records=revisions['glyphs'][start:start+24]
    im=Image.new('RGB',(1380,1080),'#fafaf6');d=ImageDraw.Draw(im)
    d.text((14,10),f'Native terminal revision / {start+1}–{start+len(records)} of {len(old)}',font=heading,fill='#193d30')
    d.text((14,46),'Before (gray) / after (green), 6x grid and 1x runs. Every changed cell is included; unchanged cells match the baseline exactly.',font=small,fill='#647367')
    for index,record in enumerate(records):
        g=current[record['glyphId']];x=14+(index%6)*228;y=82+(index//6)*247
        d.text((x,y),f"U+{g['codePoint']:05X}",font=font,fill='#193d30')
        name=g['canonicalName']
        lines=[]
        while len(name)>28:
            k=name.rfind(' ',0,29);k=k if k>0 else 28
            lines.append(name[:k]);name=name[k:].lstrip()
        lines.append(name)
        for line,text in enumerate(lines[:2]): d.text((x,y+22+line*17),text,font=small,fill='#647367')
        glyph(d,old[g['glyphId']],x,y+62,6,'#859087',True)
        glyph(d,g['rows'],x+72,y+62,6,grid=True)
        for repeat in range(10): glyph(d,g['rows'],x+repeat*8,y+169,1)
        d.text((x,y+198),f"{len(record['pixels'])} pixel changes / {g['assessment']['counters']} counters",font=small,fill='#647367')
    name=f'changes-{start//24+1:02}.png';im.save(DIR/name)
    manifest['pages'].append({'path':name,'sha256':hashlib.sha256((DIR/name).read_bytes()).hexdigest(),'glyphIds':[r['glyphId'] for r in records]})
(DIR/'proof-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print(f"Rendered native comparison and {len(manifest['pages'])} contact sheets for {len(old)} changed glyphs.")
