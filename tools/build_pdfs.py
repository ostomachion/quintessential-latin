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


def paragraph(text, size=10, leading=14, bold=False, color=INK, font=None):
    return Paragraph(escape(clean(text)), ParagraphStyle('body', fontName=font or ('STIXBold' if bold else 'STIX'),
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
        self.presentation = json.loads((root / 'resources' / 'chart-presentation.json').read_text(encoding='utf-8'))
        self.families = {f['id']: f for f in catalogue['families']}
        self.audit = {'version': catalogue['version'], 'posture': 'Roman', 'weight': 400,
                      'presentation': self.presentation, 'files': {}, 'glyphPlacements': [],
                      'familyHeadings': [], 'nameEntries': []}
        cache = root / '.tmp' / 'pdf-fonts'
        cache.mkdir(parents=True, exist_ok=True)
        font_root = root / 'resources' / 'fonts'
        script_source = font_root / 'QuintessentialSerif' / 'QuintessentialSerif-Variable.ttf'
        script_path = static_font(script_source, 400, cache)
        ui_source = font_root / 'STIXTwoText' / 'STIXTwoText-VariableFont_wght.ttf'
        for label, path in [('Script', script_path), ('STIX', static_font(ui_source, 400, cache)),
                            ('STIXBold', static_font(ui_source, 700, cache))]:
            pdfmetrics.registerFont(ttfonts.TTFont(label, str(path)))
        for label, style in [('ChartLight', 'Light'), ('Chart', 'Regular'),
                             ('ChartBold', 'Bold'), ('ChartItalic', 'It')]:
            pdfmetrics.registerFont(ttfonts.TTFont(label, str(font_root / 'SourceSans3' / f'SourceSans3-{style}.ttf')))
        self.font = SourceFont(script_path)
        self.font_version = self.font['name'].getDebugName(5).removeprefix('Version ')
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
        if kind != 'proposal':
            return self.chart_frame(title, low, high, kind, codes)
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
        c.drawString(MARGIN, FOOTER, f'Quintessential Latin {self.data["version"]} | Reference font: Roman 400 | Private use')
        c.drawRightString(PAGE_W - MARGIN, FOOTER, str(self.page))
        self.page_records.append({'page': self.page, 'kind': kind, 'title': title,
                                  'start': low, 'end': high, 'codes': codes or []})

    def chart_frame(self, title, low=None, high=None, kind='chart', codes=None):
        self.page += 1
        c, page = self.canvas, self.presentation['page']
        c.setFillColor(colors.black)
        if kind != 'cover':
            c.setFont('ChartBold', 11)
            c.drawCentredString(PAGE_W / 2, page['headerBaseline'], title)
            c.drawString(page['textLeft'], page['headerBaseline'], f'{low:05X}')
            c.drawRightString(page['textRight'], page['headerBaseline'], f'{high:05X}')
        c.setFont('ChartItalic', 9)
        c.drawString(page['textLeft'], page['footerBaseline'],
                     f'Quintessential Latin, Version {self.data["version"]}. Private-use character charts.')
        c.drawRightString(page['textRight'], page['footerBaseline'], str(self.page))
        self.page_records.append({'page': self.page, 'kind': kind, 'title': title,
                                  'start': low, 'end': high, 'codes': codes or []})

    def glyph(self, cp, x, y, width, height, size=25, fixed=False):
        x0, y0, x1, y1 = self.bounds[cp]
        scale = size / self.units
        if fixed and ((x1-x0)*scale > width or (y1-y0)*scale > height):
            raise ValueError(f'U+{cp:05X} does not fit its {size} pt reference box')
        if not fixed:
            scale = min(scale, width / max(x1-x0, 1), height / max(y1-y0, 1))
        left, bottom = x + (width - (x1-x0)*scale)/2, y + (height-(y1-y0)*scale)/2
        self.canvas.setFillColor(colors.black)
        self.canvas.setFont('Script', scale*self.units)
        self.canvas.drawString(left - x0*scale, bottom - y0*scale, chr(cp))
        self.audit['glyphPlacements'].append({'file': self.slug, 'page': self.page, 'codePoint': cp,
            'fontSize': scale*self.units, 'kind': self.page_records[-1]['kind'],
            'box': [x, y, x+width, y+height],
            'ink': [left, bottom, left+(x1-x0)*scale, bottom+(y1-y0)*scale]})

    def cover(self, block):
        c, page = self.canvas, self.presentation['page']
        self.frame(block['title'], block['start'], block['end'], 'cover')
        left, width, top = page['textLeft'], page['textRight']-page['textLeft'], 714
        top = draw_paragraph(c, block['title'], left, top, width, size=11, leading=14.4, font='ChartBold')
        top = draw_paragraph(c, f"Range: {block['start']:05X}-{block['end']:05X}", left, top, width,
                             size=9, leading=10.6, font='Chart')
        count = sum(block['start'] <= cp <= block['end'] for cp in self.entries)
        italic = sum(block['start'] <= cp <= block['end'] and 'Italic' in e['postures'] for cp,e in self.entries.items())
        topics = [
            (None, f'This file contains the character code tables and list of character names for Quintessential Latin, Version {self.data["version"]}. The block contains {count} assigned characters.'),
            ('Status', 'Draft private-use allocation for the Under-ConScript Unicode Registry (UCSUR). These characters are not part of the Unicode Standard. Publication of this document does not indicate registry submission or acceptance.'),
            ('Character code tables', 'The tables contain up to sixteen hexadecimal columns and sixteen rows per page. Each chart stops at its block boundary. Combine a column heading with a row digit to find a character; its full hexadecimal code also appears below the reference glyph. A thin outside edge indicates that the table continues on another page.'),
            ('Character names', 'The names list follows the tables in ascending code point order, reading down the left column and then the right. Family subheadings organize related characters. Names and code points identify characters independently of their representative glyphs.'),
            ('Fonts and representative glyphs', f'The reference font is Quintessential Serif {self.font_version}, Roman, weight 400. All {count} assignments in this block have Roman outlines; {italic} also have native Italic outlines. Italic is a font posture, not a separate character. Glyphs are representative forms; their appearance may vary with font posture and weight.'),
            ('Authorship and terms', 'Script and original publication: Josh Hufford. Original code and documentation are licensed under MIT. Quintessential Serif and the STIX Two Text interface font are distributed under the SIL Open Font License 1.1. Font notices accompany the downloads.'),
        ]
        for heading, body in topics:
            top -= 12
            if heading:
                top = draw_paragraph(c, heading, left, top, width, size=9, leading=10.6, font='ChartBold')
            top = draw_paragraph(c, body, left, top, width, size=9, leading=10.6, font='ChartLight')
        top = draw_paragraph(c, 'Chart text is set in Source Sans 3, distributed under the SIL Open Font License 1.1.',
                             left, top-12, width, size=9, leading=10.6, font='ChartLight')
        top = draw_paragraph(c, 'Project: https://ostomachion.github.io/quintessential-latin/', left, top-12,
                             width, size=9, leading=10.6, font='ChartLight')
        c.linkURL('https://ostomachion.github.io/quintessential-latin/', (left, top-2, left+width, top+12), relative=0)
        if top < 72:
            raise ValueError(f'Cover overflow for {block["title"]}')
        c.showPage()

    def chart(self, block, start):
        c, grid = self.canvas, self.presentation['grid']
        rows = grid['rows']
        remaining = block['end'] - start + 1
        if start % rows or remaining % rows:
            raise ValueError('Code charts require complete hexadecimal columns')
        columns = min(grid['columns'], remaining // rows)
        end = start + columns*rows - 1
        self.frame(block['title'], start, end, 'chart', [cp for cp in range(start,end+1) if cp in self.entries])
        cell_w, cell_h, top = grid['cellWidth'], grid['cellHeight'], grid['top']
        left = (PAGE_W-columns*cell_w)/2
        bottom, right = top-rows*cell_h, left+columns*cell_w
        self.page_records[-1]['grid'] = {'bounds': [left,bottom,right,top], 'columns': columns, 'rows': rows,
            'vacancies': [cp for cp in range(start,end+1) if cp not in self.entries],
            'continuesBefore': start > block['start'], 'continuesAfter': end < block['end']}
        c.setFillColor(colors.black)
        for col in range(columns):
            self.chart_text(f'{(start>>4)+col:04X}', left+(col+.5)*cell_w, grid['labelBaseline'],
                            'Chart', grid['coordinateSize'], cell_w-2, centered=True)
        for row in range(rows):
            y = top-(row+1)*cell_h
            c.setFont('Chart', grid['coordinateSize'])
            c.setFillColor(colors.black)
            c.drawRightString(left-5, y+cell_h/2-3.5, f'{row:X}')
            for col in range(columns):
                cp = start+rows*col+row
                x = left+col*cell_w
                if cp not in self.entries:
                    self.hatch(x,y,cell_w,cell_h)
                else:
                    self.glyph(cp,x+1.25,y+8.5,cell_w-2.5,cell_h-11.5,grid['glyphSize'],fixed=True)
                    c.setFillColor(colors.black)
                    self.chart_text(f'{cp:05X}',x+cell_w/2,y+1.3,'Chart',grid['codeSize'],cell_w-2,centered=True,scale=85)
        c.setStrokeColor(colors.black)
        c.setLineWidth(grid['innerRule'])
        for col in range(columns+1):
            c.line(left+col*cell_w,top,left+col*cell_w,bottom)
        for row in range(rows+1):
            c.line(left,top-row*cell_h,right,top-row*cell_h)
        c.setLineWidth(grid['outerRule'])
        c.line(left,top,right,top)
        c.line(left,bottom,right,bottom)
        for edge, at_boundary in [(left,start==block['start']), (right,end==block['end'])]:
            c.setLineWidth(grid['outerRule'] if at_boundary else grid['innerRule'])
            c.line(edge,grid['railTop'],edge,bottom)
        c.showPage()

    def chart_text(self, text, x, y, font, size, width, centered=False, scale=100):
        measured = pdfmetrics.stringWidth(text,font,size)
        scale = min(scale,100*width/measured)
        # PDF text state, including Tz, survives ET. Keep condensed coordinates
        # local so subsequent script glyphs and names retain their native width.
        self.canvas.saveState()
        t = self.canvas.beginText(x-measured*scale/200 if centered else x,y)
        t.setFont(font,size)
        t.setHorizScale(scale)
        t.textOut(text)
        self.canvas.drawText(t)
        self.canvas.restoreState()

    def hatch(self, x, y, width, height):
        c, grid = self.canvas, self.presentation['grid']
        c.saveState()
        clip = c.beginPath(); clip.rect(x,y,width,height)
        c.clipPath(clip,stroke=0,fill=0)
        c.setStrokeColor(colors.black)
        c.setLineWidth(grid['hatchRule'])
        offset = -height
        while offset <= width:
            c.line(x+offset,y+height,x+offset+height,y)
            offset += grid['hatchSpacing']
        c.restoreState()

    def names(self, block):
        entries = [e for cp,e in sorted(self.entries.items()) if block['start'] <= cp <= block['end']]
        config = self.presentation['names']
        col_width, gap = config['columnWidth'], config['columnGap']
        available = config['top']-config['bottom']
        pages, columns, column, used = [], [], [], 0
        previous_family = None
        for entry in entries:
            p = paragraph(entry['name'],size=config['fontSize'],leading=config['leading'],font='Chart')
            _,height = p.wrap(col_width-config['textOffset'], PAGE_H)
            row_height = max(config['glyphSize'],height)+config['entryGap']
            heading = None
            if entry['familyId'] != previous_family:
                heading = paragraph(self.families[entry['familyId']]['title'],size=config['headingSize'],
                                    leading=config['headingLeading'],font='ChartBold')
            heading_height = heading.wrap(col_width,PAGE_H)[1]+config['entryGap'] if heading else 0
            before_heading = config['headingGap'] if heading and column else 0
            if used+row_height+heading_height+before_heading > available:
                columns.append(column)
                column,used = [],0
                before_heading = 0
                if len(columns)==2:
                    pages.append(columns)
                    columns=[]
            column.append((entry,p,row_height,heading,heading_height,before_heading))
            used+=row_height+heading_height+before_heading
            previous_family = entry['familyId']
        if column:
            columns.append(column)
        if columns:
            pages.append(columns)
        for columns in pages:
            codes = [row[0]['codePoint'] for col in columns for row in col]
            self.frame(block['title'],codes[0],codes[-1],'names',codes)
            c = self.canvas
            for col_index,rows in enumerate(columns):
                x,top = self.presentation['page']['textLeft']+col_index*(col_width+gap),config['top']
                for entry,p,row_height,heading,heading_height,before_heading in rows:
                    if heading:
                        top -= before_heading
                        heading.drawOn(c,x,top-heading_height+config['entryGap'])
                        self.audit['familyHeadings'].append({'file':self.slug,'page':self.page,'column':col_index,
                            'familyId':entry['familyId'],'codePoint':entry['codePoint'],
                            'box':[x,top-heading_height,x+col_width,top]})
                        top -= heading_height
                    c.setFillColor(colors.black)
                    self.chart_text(f'{entry["codePoint"]:05X}',x,top-8.4,'Chart',config['fontSize'],24,scale=90)
                    self.glyph(entry['codePoint'],x+27,top-10.6,13.2,10.6,config['glyphSize'],fixed=True)
                    _,height = p.wrap(col_width-config['textOffset'],PAGE_H)
                    p.drawOn(c,x+config['textOffset'],top-height)
                    self.audit['nameEntries'].append({'file':self.slug,'page':self.page,'column':col_index,
                        'codePoint':entry['codePoint'],'familyId':entry['familyId'],
                        'box':[x,top-row_height,x+col_width,top]})
                    top-=row_height
            c.showPage()

    def block(self, block):
        self.cover(block)
        for start in range(block['start'],block['end']+1,self.presentation['grid']['columns']*16):
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
    audit.write_text(json.dumps(publication.audit,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest_sources = [
        'resources/catalogue.json',
        'resources/chart-presentation.json',
        'docs/proposal.json',
        'resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf',
        'resources/fonts/STIXTwoText/STIXTwoText-VariableFont_wght.ttf',
        'resources/fonts/SourceSans3/SourceSans3-Light.ttf',
        'resources/fonts/SourceSans3/SourceSans3-Regular.ttf',
        'resources/fonts/SourceSans3/SourceSans3-Bold.ttf',
        'resources/fonts/SourceSans3/SourceSans3-It.ttf',
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
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    for filename,item in publication.audit['files'].items():
        print(f'{filename}: {len(item["pages"])} pages, {item["bytes"]:,} bytes')
    print('Wrote PDF source/output build-manifest.json.')


if __name__=='__main__':
    main()
