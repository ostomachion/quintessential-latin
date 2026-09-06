"""Render the preserved 148-glyph baseline directly from the current HEX export."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[2]
UNIFONT = DIRECTORY.parent
PINNED_BASELINE_SHA256 = '76e0a9f5f073ef4ddec768e82e66c94a38ccac8234254a3a66761ec6d76f3020'

def sha(content):
    return hashlib.sha256(content).hexdigest()

baseline_bytes = (UNIFONT / 'approved-baseline.hex').read_bytes()
if sha(baseline_bytes) != PINNED_BASELINE_SHA256:
    raise ValueError('Approved baseline changed')
baseline = {int(line.split(':')[0], 16): line for line in baseline_bytes.decode().splitlines()}
current_bytes = (UNIFONT / 'quintessential-latin.hex').read_bytes()
current = {int(line.split(':')[0], 16): line for line in current_bytes.decode().splitlines()}
catalogue = {g['codePoint']: g for g in json.loads((UNIFONT / 'glyphs.json').read_text())['glyphs']}
if len(baseline) != 148:
    raise ValueError('Wrong baseline count')
glyphs = []
for code, baseline_line in sorted(baseline.items()):
    if current.get(code) != baseline_line:
        raise ValueError(f'Current HEX differs at U+{code:05X}')
    record = catalogue[code]
    if record['line'] != baseline_line:
        raise ValueError(f'Site bitmap differs at U+{code:05X}')
    raw = bytes.fromhex(baseline_line.split(':')[1])
    if list(raw) != record['rows'] or len(raw) != 16:
        raise ValueError('Bitmap rows do not match the HEX export')
    bitmap_sha = sha((baseline_line + '\n').encode())
    if record['bitmapSha256'] != bitmap_sha:
        raise ValueError('Site bitmap hash differs')
    glyphs.append({**record, 'proofRows': [f'{row:08b}' for row in raw]})

regular = str(ROOT / 'resources/fonts/SourceSans3/SourceSans3-Regular.ttf')
font = ImageFont.truetype(regular, 16)
small = ImageFont.truetype(regular, 13)
heading = ImageFont.truetype(regular, 23)
stix = ImageFont.truetype(str(ROOT / 'resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf'), 67)
ink = '#203b2f'
manifest = {
    'schemaVersion': 1,
    'reviewer': 'foundation_stress',
    'approvedBaselineSha256': PINNED_BASELINE_SHA256,
    'currentHexSha256': sha(current_bytes),
    'preservedGlyphCount': len(glyphs),
    'preservation': 'All 148 approved lines exactly match the current HEX export and current site bitmap data.',
    'userAcceptance': 'unchanged',
    'status': 'pending-visual-inspection',
    'proofs': [],
    'glyphs': [],
}
for start in range(0, len(glyphs), 24):
    page_glyphs = glyphs[start:start+24]
    image = Image.new('RGB', (1380, 1120), '#fafaf6')
    draw = ImageDraw.Draw(image)
    draw.text((12, 7), f'Approved baseline / preserved glyphs {start+1}–{start+len(page_glyphs)} of 148', font=heading, fill=ink)
    draw.text((12, 37), 'Current HEX pixels: gridded 8x, native repetitions, 2x; current STIX structural reference. Exact approved bytes verified.', font=small, fill='#657465')
    for index, g in enumerate(page_glyphs):
        x, y = 12+(index%6)*230, 65+(index//6)*260
        draw.text((x,y), f"U+{g['codePoint']:05X}", font=font, fill=ink)
        label = g['canonicalName']
        while len(label) > 31:
            cut = label.rfind(' ',0,32)
            draw.text((x,y+22), label[:cut], font=small, fill=ink)
            label = label[cut+1:]
            break
        draw.text((x,y+38 if len(g['canonicalName'])>31 else y+22), label[:33], font=small, fill=ink)
        gx, gy = x, y+57
        for row in range(17): draw.line((gx,gy+row*8,gx+64,gy+row*8),fill='#e3e3db')
        for column in range(9): draw.line((gx+column*8,gy,gx+column*8,gy+128),fill='#e3e3db')
        for yy,row in enumerate(g['proofRows']):
            for xx,bit in enumerate(row):
                if bit == '1':
                    draw.rectangle((gx+xx*8,gy+yy*8,gx+xx*8+7,gy+yy*8+7),fill=ink)
                    for repeat in range(5): draw.point((x+xx+repeat*8,y+212+yy),fill=ink)
                    draw.rectangle((x+64+xx*2,y+204+yy*2,x+65+xx*2,y+205+yy*2),fill=ink)
        draw.text((x+76,y+87),chr(g['codePoint']),font=stix,fill=ink)
        draw.text((x+78,y+164),'Current STIX',font=small,fill='#718070')
        draw.text((x+97,y+212),'1x / 2x',font=small,fill='#718070')
        draw.text((x,y+239),f"{g['assessment']['components']} component / {g['assessment']['counters']} counters",font=small,fill='#718070')
    file = DIRECTORY / f'baseline-{start//24+1:02}.png'
    image.save(file)
    proof_hash = sha(file.read_bytes())
    path = str(file.relative_to(ROOT)).replace('\\','/')
    manifest['proofs'].append({'path':path,'sha256':proof_hash,'glyphIds':[g['glyphId'] for g in page_glyphs]})
    for g in page_glyphs:
        manifest['glyphs'].append({
            'glyphId':g['glyphId'], 'codePoint':g['codePoint'], 'line':g['line'],
            'bitmapSha256':g['bitmapSha256'], 'proofPath':path, 'proofSha256':proof_hash,
            'status':'pending-visual-inspection', 'preservedApprovedBitmap':True,
        })
(DIRECTORY / 'review-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Preserved and rendered all {len(glyphs)} approved glyphs on {len(manifest["proofs"])} sheets.')
