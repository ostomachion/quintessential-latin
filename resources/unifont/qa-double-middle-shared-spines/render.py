import json
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'resources/unifont/double-middle-shared-spines.json'
data = json.loads(SOURCE.read_text())
allocation = {g['glyphId']: g for g in json.loads((ROOT / 'resources/quintessential-latin-allocation.json').read_text())['entries']}
regular = str(ROOT / 'resources/fonts/SourceSans3/SourceSans3-Regular.ttf')
font = ImageFont.truetype(regular, 16)
small = ImageFont.truetype(regular, 13)
title = ImageFont.truetype(regular, 24)
stix = ImageFont.truetype(str(ROOT / 'resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf'), 78)
ink = '#203b2f'
glyphs = {g['glyphId']: g for g in data['glyphs']}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def draw_glyph(image, glyph, x, y):
    draw = ImageDraw.Draw(image)
    entry = allocation[glyph['glyphId']]
    draw.text((x, y), f"U+{entry['codePoint']:05X}  {''.join('1' if s else '0' for s in glyph['extensionState'])}", font=font, fill=ink)
    draw.text((x, y+19), f"{glyph['expected']['counters']} counters" + (' / hook contact' if glyph['structuralChecks']['terminalContact'] else ''), font=small, fill='#934812' if glyph['structuralChecks']['terminalContact'] else '#667369')
    gx, gy = x, y+42
    for row in range(17): draw.line((gx, gy+row*8, gx+64, gy+row*8), fill='#e4e3dc')
    for col in range(9): draw.line((gx+col*8, gy, gx+col*8, gy+128), fill='#e4e3dc')
    for yy, row in enumerate(glyph['rows']):
        for xx, bit in enumerate(row):
            if bit == '#': draw.rectangle((gx+xx*8, gy+yy*8, gx+xx*8+7, gy+yy*8+7), fill=ink)
    draw.text((x+80,y+70), chr(entry['codePoint']),font=stix,fill=ink)
    draw.text((x+80,y+144),'Current STIX',font=small,fill='#778176')
    for yy, row in enumerate(glyph['rows']):
        for xx, bit in enumerate(row):
            if bit == '#':
                for repeat in range(5): draw.point((x+xx+repeat*8,y+182+yy),fill=ink)
                draw.rectangle((x+64+xx*2,y+176+yy*2,x+65+xx*2,y+177+yy*2),fill=ink)
    draw.text((x+94,y+178),'1x repeats / 2x',font=small,fill='#778176')

manifest = {'sourceSha256':sha(SOURCE),'reviewer':'foundation_stress','reviewStatus':'pending-visual-inspection','glyphs':[],'proofs':[]}
for start in range(0,len(data['groups']),6):
    groups = data['groups'][start:start+6]
    image = Image.new('RGB',(1160,1370),'#fafaf6')
    draw = ImageDraw.Draw(image)
    side = 'Left' if groups[0]['id'].startswith('left-') else 'Right'
    draw.text((16,8),f'{side} double-arched shared spines / quartets {start%36+1}-{start%36+6}',font=title,fill=ink)
    draw.text((16,37),'Four states: neither, left only, right only, both. Literal 8x16 pixels; each gridded cell is 8x.',font=small,fill='#647062')
    page = OUT / f'page-{start//6+1:02}.png'
    for group_index,group in enumerate(groups):
        for column,glyph_id in enumerate(group['glyphIds']): draw_glyph(image,glyphs[glyph_id],16+column*290,65+group_index*216)
    image.save(page)
    manifest['proofs'].append({'path':str(page.relative_to(ROOT)),'sha256':sha(page),'glyphIds':[gid for group in groups for gid in group['glyphIds']]})
    for group in groups:
        for gid in group['glyphIds']:
            g=glyphs[gid]
            pixels=''.join(f'{int(row.replace(".","0").replace("#","1"),2):02X}' for row in g['rows'])
            manifest['glyphs'].append({'glyphId':gid,'bitmapSha256':hashlib.sha256(bytes.fromhex(pixels)).hexdigest(),'proofPath':str(page.relative_to(ROOT)),'proofSha256':sha(page),'status':'pending-visual-inspection'})

contacts=[]
for side in ['left-','right-']:
    contacts.append(next(group for group in data['groups'] if group['id'].startswith(side) and any(glyphs[gid]['structuralChecks']['terminalContact'] for gid in group['glyphIds'])))
image=Image.new('RGB',(1160,520),'#fafaf6')
draw=ImageDraw.Draw(image)
draw.text((16,8),'8-pixel compact hook contact: independent-extension quartets',font=title,fill=ink)
for row,group in enumerate(contacts):
    for col,gid in enumerate(group['glyphIds']): draw_glyph(image,glyphs[gid],16+col*290,55+row*216)
image.save(OUT/'compact-hook-contacts.png')
(OUT/'review.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Rendered {len(manifest["glyphs"])} glyphs in {len(manifest["proofs"])} sheets')
