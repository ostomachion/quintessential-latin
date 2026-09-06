#!/usr/bin/env python3
"""Build the five publication PDFs from the standalone catalogue and proposal.

Run: python tools/build_pdfs.py
Requires the packages in tools/requirements-pdfs.txt. Intermediate static fonts
and geometry evidence stay in .tmp; the original variable fonts are never edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import __version__ as FONTTOOLS_VERSION
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont as SourceFont
from fontTools.varLib.instancer import instantiateVariableFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
PAGE_W, PAGE_H = 612, 792
MARGIN, FOOTER = 42, 44
INK = colors.HexColor('#171717')
MUTED = colors.HexColor('#535353')
RULE = colors.HexColor('#7d7d7d')
VACANT = colors.HexColor('#e5e5e5')
SLUGS = ['quintessential-latin', 'quintessential-latin-extended-a', 'quintessential-latin-extended-b']

# ReportLab 4.4 encodes supplementary scalars as five hexadecimal digits in
# ToUnicode maps. PDF requires UTF-16BE surrogate pairs. Correct the generated
# mapping locally so selecting/copying a Plane 15 glyph preserves its identity.
_reportlab_cmap = ttfonts.makeToUnicodeCMap

def scalar_safe_cmap(fontname, subset):
    cmap = _reportlab_cmap(fontname, subset)
    return re.sub(r'(<[0-9A-Fa-f]{2}> )<([0-9A-Fa-f]{5,6})>',
                  lambda m: m[1] + '<' + chr(int(m[2], 16)).encode('utf-16-be').hex().upper() + '>', cmap)

ttfonts.makeToUnicodeCMap = scalar_safe_cmap


def clean(text):
    return str(text).replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u00a0', ' ')


def paragraph(text, size=10, leading=14, bold=False, color=INK):
    return Paragraph(escape(clean(text)), ParagraphStyle('body', fontName='STIXBold' if bold else 'STIX',
        fontSize=size, leading=leading, textColor=color, alignment=TA_LEFT, splitLongWords=True))


def draw_paragraph(canvas, text, x, top, width, **kwargs):
    p = paragraph(text, **kwargs)
    _, height = p.wrap(width, PAGE_H)
    p.drawOn(canvas, x, top - height)
    return top - height


def static_font(source, weight, destination):
    key = hashlib.sha256(source.read_bytes() + str(weight).encode() + FONTTOOLS_VERSION.encode()).hexdigest()
    cache = destination / f'{source.stem}-{weight}-{key[:12]}.ttf'
    if not cache.exists():
        font = SourceFont(source, recalcTimestamp=False)
        instance = instantiateVariableFont(font, {'wght': weight}, inplace=False)
        instance.save(cache, reorderTables=False)
        instance.close()
        font.close()
    return cache


class Publication:
    def __init__(self, root, catalogue, output):
        self.root, self.data, self.output = root, catalogue, output
        self.entries = {e['codePoint']: e for e in catalogue['entries']}
        self.audit = {'version': catalogue['version'], 'posture': 'Roman', 'weight': 400,
                      'files': {}, 'glyphPlacements': []}
        cache = root / '.tmp' / 'pdf-fonts'
        cache.mkdir(parents=True, exist_ok=True)
        font_root = root / 'resources' / 'fonts'
        script_source = font_root / 'QuintessentialSerif' / 'QuintessentialSerif-Variable.ttf'
        script_path = static_font(script_source, 400, cache)
        ui_source = font_root / 'STIXTwoText' / 'STIXTwoText-VariableFont_wght.ttf'
        for label, path in [('Script', script_path), ('STIX', static_font(ui_source, 400, cache)),
                            ('STIXBold', static_font(ui_source, 700, cache))]:
            pdfmetrics.registerFont(ttfonts.TTFont(label, str(path)))
        self.font = SourceFont(script_path)
        self.units = self.font['head'].unitsPerEm
        self.cmap = self.font.getBestCmap()
        glyph_set = self.font.getGlyphSet()
        self.bounds = {}
        for cp in self.entries:
            if cp not in self.cmap:
                raise ValueError(f'Reference font has no U+{cp:05X}')
            pen = BoundsPen(glyph_set)
            glyph_set[self.cmap[cp]].draw(pen)
            self.bounds[cp] = pen.bounds
        self.audit['sourceFontSha256'] = hashlib.sha256(script_source.read_bytes()).hexdigest()

    def new_document(self, slug, title):
        self.slug, self.page, self.page_records = slug, 0, []
        c = Canvas(str(self.output / f'{slug}.pdf'), pagesize=(PAGE_W, PAGE_H), pageCompression=1, invariant=1)
        c.setTitle(title)
        c.setAuthor('Josh Hufford')
        c.setSubject('Quintessential Latin private-use character charts and draft UCSUR proposal')
        c.setCreator('Quintessential Latin publication builder')
        self.canvas = c
        return c

    def frame(self, title, low=None, high=None, kind='chart', codes=None):
        self.page += 1
        c = self.canvas
        c.setFillColor(INK)
        c.setFont('STIXBold', 10)
        c.drawCentredString(PAGE_W / 2, 753, clean(title))
        c.setFont('STIX', 9)
        if low is not None:
            c.drawString(MARGIN, 753, f'{low:05X}')
            c.drawRightString(PAGE_W - MARGIN, 753, f'{high:05X}')
        c.setStrokeColor(RULE)
        c.setLineWidth(.5)
        c.line(MARGIN, 743, PAGE_W - MARGIN, 743)
        c.line(MARGIN, FOOTER + 14, PAGE_W - MARGIN, FOOTER + 14)
        c.setFillColor(MUTED)
        c.setFont('STIX', 8)
        c.drawString(MARGIN, FOOTER, f'Quintessential Latin 0.220 | Reference font: Roman 400 | Private use')
        c.drawRightString(PAGE_W - MARGIN, FOOTER, str(self.page))
        self.page_records.append({'page': self.page, 'kind': kind, 'title': title,
                                  'start': low, 'end': high, 'codes': codes or []})

    def glyph(self, cp, x, y, width, height, size=25):
        x0, y0, x1, y1 = self.bounds[cp]
        scale = min(size / self.units, width / max(x1-x0, 1), height / max(y1-y0, 1))
        left, bottom = x + (width - (x1-x0)*scale)/2, y + (height-(y1-y0)*scale)/2
        self.canvas.setFillColor(INK)
        self.canvas.setFont('Script', scale*self.units)
        self.canvas.drawString(left - x0*scale, bottom - y0*scale, chr(cp))
        self.audit['glyphPlacements'].append({'file': self.slug, 'page': self.page, 'codePoint': cp,
            'box': [x, y, x+width, y+height],
            'ink': [left, bottom, left+(x1-x0)*scale, bottom+(y1-y0)*scale]})

    def cover(self, block):
        c = self.canvas
        self.frame(block['title'], block['start'], block['end'], 'cover')
        top = 688
        top = draw_paragraph(c, block['title'], MARGIN, top, PAGE_W-2*MARGIN, size=27, leading=32, bold=True)
        top = draw_paragraph(c, f"Range: U+{block['start']:05X}-U+{block['end']:05X}", MARGIN, top-15,
                             PAGE_W-2*MARGIN, size=17, leading=22)
        count = sum(block['start'] <= cp <= block['end'] for cp in self.entries)
        italic = sum(block['start'] <= cp <= block['end'] and 'Italic' in e['postures'] for cp,e in self.entries.items())
        topics = [
            ('Character code tables and names', f'{count} assigned characters. This file presents the Quintessential Latin 0.220 private-use allocation, followed by a numeric list of character names. Charts contain eight hexadecimal columns and sixteen rows per sheet.'),
            ('Status', 'Draft private-use allocation for the Under-ConScript Unicode Registry (UCSUR). These characters are not part of the Unicode Standard. Publication of this document does not indicate registry submission or acceptance.'),
            ('Reading the charts', 'Combine a column heading with a row digit to find a character. The full hexadecimal code appears below each reference glyph. Shaded cells are unallocated. Names list entries are ordered by ascending code point and read down the left column, then the right.'),
            ('Reference font', f'Quintessential Serif 0.220, Roman, weight 400. All {count} assignments in this block are available in Roman; {italic} also have native Italic outlines. Italic is a font posture, not a separate character. The website shows current posture availability and provides weight controls.'),
            ('Authorship and terms', 'Script and original publication: Josh Hufford. Original code and documentation are licensed under MIT. Quintessential Serif and the STIX Two Text interface font are distributed under the SIL Open Font License 1.1. Font notices accompany the downloads.'),
        ]
        for heading, body in topics:
            top = draw_paragraph(c, heading, MARGIN, top-25, PAGE_W-2*MARGIN, size=11, leading=14, bold=True)
            top = draw_paragraph(c, body, MARGIN, top-5, PAGE_W-2*MARGIN, size=10, leading=14)
        top = draw_paragraph(c, 'Project: https://ostomachion.github.io/quintessential-latin/', MARGIN, top-21,
                             PAGE_W-2*MARGIN, size=9, leading=12)
        c.linkURL('https://ostomachion.github.io/quintessential-latin/', (MARGIN, top-2, PAGE_W-MARGIN, top+12), relative=0)
        if top < 72:
            raise ValueError(f'Cover overflow for {block["title"]}')
        c.showPage()

    def chart(self, block, start):
        self.frame(block['title'], start, start+127, 'chart', [cp for cp in range(start,start+128) if cp in self.entries])
        c = self.canvas
        left, top, row_head, cell_w, cell_h = MARGIN+26, 714, 26, (PAGE_W-2*MARGIN-26)/8, 38
        c.setFont('STIXBold', 10)
        c.setFillColor(INK)
        for col in range(8):
            c.drawCentredString(left+(col+.5)*cell_w, top+9, f'{(start>>4)+col:04X}')
        for row in range(16):
            y = top-(row+1)*cell_h
            c.setFont('STIXBold', 10)
            c.setFillColor(INK)
            c.drawCentredString(left-row_head/2, y+cell_h/2-3, f'{row:X}')
            for col in range(8):
                cp = start+16*col+row
                x = left+col*cell_w
                if cp not in self.entries:
                    c.setFillColor(VACANT)
                    c.rect(x,y,cell_w,cell_h,stroke=0,fill=1)
                else:
                    self.glyph(cp,x+4,y+13,cell_w-8,cell_h-17,27)
                    c.setFillColor(INK)
                    c.setFont('STIX',7.2)
                    c.drawCentredString(x+cell_w/2,y+4,f'{cp:05X}')
        c.setStrokeColor(RULE)
        c.setLineWidth(.45)
        for col in range(9):
            c.line(left+col*cell_w,top,left+col*cell_w,top-16*cell_h)
        for row in range(17):
            c.line(left,top-row*cell_h,left+8*cell_w,top-row*cell_h)
        c.setFillColor(MUTED)
        c.setFont('STIX',8)
        c.drawString(MARGIN,82,'Shaded positions are unallocated. Glyphs are reference forms.')
        c.showPage()

    def names(self, block):
        entries = [e for cp,e in sorted(self.entries.items()) if block['start'] <= cp <= block['end']]
        col_width, gap, available = (PAGE_W-2*MARGIN-20)/2, 20, 637
        pages, columns, column, used = [], [], [], 0
        for entry in entries:
            p = paragraph(entry['name'],size=8.1,leading=9.5)
            _,height = p.wrap(col_width-76, PAGE_H)
            row_height = max(22,height+6)
            if used+row_height > available:
                columns.append(column)
                column,used = [],0
                if len(columns)==2:
                    pages.append(columns)
                    columns=[]
            column.append((entry,p,row_height))
            used+=row_height
        if column:
            columns.append(column)
        if columns:
            pages.append(columns)
        for columns in pages:
            codes = [entry['codePoint'] for col in columns for entry,_,_ in col]
            self.frame(block['title'],codes[0],codes[-1],'names',codes)
            c = self.canvas
            c.setFont('STIXBold',10)
            c.setFillColor(INK)
            c.drawString(MARGIN,722,'Names list')
            for col_index,rows in enumerate(columns):
                x,top = MARGIN+col_index*(col_width+gap),705
                for entry,p,row_height in rows:
                    c.setFont('STIXBold',8.2)
                    c.setFillColor(INK)
                    c.drawString(x,top-8.1,f'{entry["codePoint"]:05X}')
                    self.glyph(entry['codePoint'],x+32,top-min(row_height-3,27),38,min(row_height-6,24),18)
                    _,height = p.wrap(col_width-76,PAGE_H)
                    p.drawOn(c,x+76,top-height)
                    top-=row_height
            c.showPage()

    def block(self, block):
        self.cover(block)
        for start in range(block['start'],block['end']+1,128):
            self.chart(block,start)
        self.names(block)

    def finish(self):
        self.canvas.save()
        path = self.output / f'{self.slug}.pdf'
        self.audit['files'][path.name] = {'pages': self.page_records,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes':path.stat().st_size}

    def proposal(self, document):
        self.new_document('quintessential-latin-proposal',document['title'])
        self.frame('Quintessential Latin | UCSUR proposal',kind='proposal')
        c = self.canvas
        top = draw_paragraph(c,document['title'],MARGIN,708,PAGE_W-2*MARGIN,size=26,leading=31,bold=True)-14
        for text in [document.get('subtitle'),document.get('status','Draft private-use proposal'),
                     document.get('author','Josh Hufford')]:
            if text:
                top=draw_paragraph(c,text,MARGIN,top,PAGE_W-2*MARGIN,size=11,leading=15)-5
        top-=12
        for section in document['sections']:
            heading=paragraph(section['title'],size=14,leading=18,bold=True)
            body=[paragraph(value,size=10.3,leading=14.2) for value in section.get('paragraphs',[])]
            body.extend(paragraph('- '+value,size=10.3,leading=14.2) for value in section.get('bullets',[]))
            first_height=body[0].wrap(PAGE_W-2*MARGIN,PAGE_H)[1] if body else 0
            if top-18-first_height-16<75:
                c.showPage(); self.frame('Quintessential Latin | UCSUR proposal',kind='proposal'); top=713
            _,h=heading.wrap(PAGE_W-2*MARGIN,PAGE_H)
            heading.drawOn(c,MARGIN,top-h); top-=h+9
            for p in body:
                _,h=p.wrap(PAGE_W-2*MARGIN,PAGE_H)
                if top-h<75:
                    c.showPage(); self.frame('Quintessential Latin | UCSUR proposal',kind='proposal'); top=713
                if h>638:
                    raise ValueError('Proposal paragraph is too long for one page')
                p.drawOn(c,MARGIN,top-h); top-=h+9
            top-=13
        refs=document.get('references',[])
        if refs:
            if top<200:
                c.showPage(); self.frame('Quintessential Latin | UCSUR proposal',kind='proposal'); top=713
            top=draw_paragraph(c,'References',MARGIN,top,PAGE_W-2*MARGIN,size=14,leading=18,bold=True)-10
            for index,ref in enumerate(refs,1):
                p=paragraph(f'{index}. {ref["title"]}: {ref["url"]}',size=9,leading=12.5)
                _,h=p.wrap(PAGE_W-2*MARGIN,PAGE_H)
                if top-h<75:
                    c.showPage(); self.frame('Quintessential Latin | UCSUR proposal',kind='proposal'); top=713
                p.drawOn(c,MARGIN,top-h)
                c.linkURL(ref['url'],(MARGIN,top-h,PAGE_W-MARGIN,top),relative=0)
                top-=h+9
        c.showPage()
        self.finish()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    root=args.root.resolve(); output=(args.output or root/'output'/'pdf').resolve()
    data=json.loads((root/'resources'/'catalogue.json').read_text(encoding='utf-8'))
    proposal=json.loads((root/'docs'/'proposal.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True,exist_ok=True)
    publication=Publication(root,data,output)
    for slug,block in zip(SLUGS,data['blocks'],strict=True):
        publication.new_document(slug,block['title']); publication.block(block); publication.finish()
    publication.new_document('quintessential-latin-catalogue','Quintessential Latin: complete character catalogue')
    for block in data['blocks']:
        publication.block(block)
    publication.finish()
    publication.proposal(proposal)
    audit=root/'.tmp'/'pdf-layout-audit.json'
    audit.write_text(json.dumps(publication.audit,indent=2)+'\n',encoding='utf-8')
    manifest_sources = [
        'resources/catalogue.json',
        'docs/proposal.json',
        'resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf',
        'resources/fonts/STIXTwoText/STIXTwoText-VariableFont_wght.ttf',
        'tools/build_pdfs.py',
        'tools/requirements-pdfs.txt',
    ]
    manifest = {
        'schemaVersion': 1,
        'repertoireVersion': data['version'],
        'namingVersion': data['namingVersion'],
        'reference': {'font': 'Quintessential Serif', 'posture': 'Roman', 'weight': 400},
        'sources': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                    for name in manifest_sources},
        'outputs': {name: {'sha256': item['sha256'], 'bytes': item['bytes'], 'pages': len(item['pages'])}
                    for name, item in publication.audit['files'].items()},
    }
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    for filename,item in publication.audit['files'].items():
        print(f'{filename}: {len(item["pages"])} pages, {item["bytes"]:,} bytes')
    print('Wrote PDF source/output build-manifest.json.')


if __name__=='__main__':
    main()


