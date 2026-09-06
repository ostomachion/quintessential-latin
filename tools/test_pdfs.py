#!/usr/bin/env python3
"""Verify publication PDF coverage, vector fonts, text bounds and layout evidence."""
from __future__ import annotations
import hashlib
import json
import re
import unittest
from collections import Counter
from pathlib import Path

import pdfplumber
from fontTools.ttLib import TTFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


class PublicationPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/'resources'/'catalogue.json').read_text(encoding='utf-8'))
        cls.audit = json.loads((ROOT/'.tmp'/'pdf-layout-audit.json').read_text(encoding='utf-8'))
        cls.presentation = json.loads((ROOT/'resources'/'chart-presentation.json').read_text(encoding='utf-8'))
        cls.entries = {e['codePoint']:e for e in cls.data['entries']}
        cls.pdfs = {name:PdfReader(ROOT/'output'/'pdf'/name) for name in cls.audit['files']}
        cls.texts = {name:[p.extract_text() for p in pdf.pages] for name,pdf in cls.pdfs.items()}

    def test_five_final_outputs_and_bound_layout_evidence(self):
        self.assertEqual(set(self.pdfs),{'quintessential-latin.pdf','quintessential-latin-extended-a.pdf',
            'quintessential-latin-extended-b.pdf','quintessential-latin-catalogue.pdf','quintessential-latin-proposal.pdf'})
        for name,item in self.audit['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/'output'/'pdf'/name).read_bytes()).hexdigest(),item['sha256'],name)
            self.assertEqual(len(self.pdfs[name].pages),len(item['pages']),name)
        font=ROOT/'resources'/'fonts'/'QuintessentialSerif'/'QuintessentialSerif-Variable.ttf'
        self.assertEqual(hashlib.sha256(font.read_bytes()).hexdigest(),self.audit['sourceFontSha256'])

    def test_complete_numeric_chart_and_names_coverage(self):
        total_charts=0
        for name,item in self.audit['files'].items():
            if 'proposal' in name:
                continue
            charts=[p for p in item['pages'] if p['kind']=='chart']
            names=[p for p in item['pages'] if p['kind']=='names']
            expected=sorted(cp for p in charts for cp in range(p['start'],p['end']+1) if cp in self.entries)
            self.assertEqual([cp for p in names for cp in p['codes']],expected,name)
            self.assertEqual(sorted(cp for p in charts for cp in p['codes']),expected,name)
            self.assertEqual(len(expected),len(set(expected)),name)
            # Independently inspect actual PDF text, including correct Plane 15
            # copy/extraction through each embedded font's ToUnicode mapping.
            extracted=Counter(ord(ch) for text in self.texts[name] for ch in text if 0xF2A00<=ord(ch)<=0xF2FFF)
            self.assertEqual(extracted,Counter({cp:2 for cp in expected}),name)
            name_text=' '.join(self.texts[name][p['page']-1] for p in names)
            normalized=re.sub(r'\s+',' ',name_text)
            for cp in expected:
                self.assertIn(self.entries[cp]['name'],normalized,f'{name}: U+{cp:05X}')
            # The reference layout places one 256-position chart on each sheet.
            for p in charts:
                self.assertEqual(p['start']%256,0)
                self.assertEqual(p['end']-p['start'],255)
            self.assertEqual(len(charts),6 if 'catalogue' in name else (4 if 'extended-b' in name else 1))
            if 'catalogue' not in name:
                total_charts+=len(charts)
        self.assertEqual(total_charts,6)
        combined=self.audit['files']['quintessential-latin-catalogue.pdf']['pages']
        self.assertEqual(sum(p['kind']=='cover' for p in combined),3)

    def test_glyph_ink_is_inside_cell_and_page(self):
        for placement in self.audit['glyphPlacements']:
            x0,y0,x1,y1=placement['box']; left,bottom,right,top=placement['ink']
            label=f'{placement["file"]}, page {placement["page"]}, U+{placement["codePoint"]:05X}'
            self.assertGreaterEqual(left,x0-0.001,label); self.assertLessEqual(right,x1+0.001,label)
            self.assertGreaterEqual(bottom,y0-0.001,label); self.assertLessEqual(top,y1+0.001,label)
            self.assertGreaterEqual(left,42,label); self.assertLessEqual(right,570,label)
            self.assertGreaterEqual(bottom,62,label); self.assertLessEqual(top,735,label)
            self.assertEqual(placement['fontSize'],22 if placement['kind']=='chart' else 10,label)

    def test_reference_grid_geometry_rules_and_hatched_vacancies(self):
        self.assertEqual(self.audit['presentation'],self.presentation)
        grid=self.presentation['grid']
        left=(612-16*grid['cellWidth'])/2
        right=612-left
        bottom=grid['top']-16*grid['cellHeight']
        for name,item in self.audit['files'].items():
            if 'proposal' in name:
                continue
            with pdfplumber.open(ROOT/'output'/'pdf'/name) as document:
                for record in item['pages']:
                    if record['kind']!='chart':
                        continue
                    label=(name,record['page'])
                    evidence=record['grid']
                    self.assertEqual((evidence['columns'],evidence['rows']),(16,16),label)
                    self.assertEqual(evidence['bounds'],[left,bottom,right,grid['top']],label)
                    expected_vacancies=[cp for cp in range(record['start'],record['end']+1) if cp not in self.entries]
                    self.assertEqual(evidence['vacancies'],expected_vacancies,label)
                    page=document.pages[record['page']-1]
                    # Check the actual vector operators independently of the audit.
                    lines=page.lines
                    def has_line(x0,y0,x1,y1,width):
                        return any(all(abs(actual-expected)<.02 for actual,expected in zip(
                            [line['x0'],line['y0'],line['x1'],line['y1'],line['linewidth']],
                            [min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1),width])) for line in lines)
                    for column in range(1,16):
                        self.assertTrue(has_line(left+column*grid['cellWidth'],bottom,
                                                 left+column*grid['cellWidth'],grid['top'],grid['innerRule']),label)
                    for row in range(1,16):
                        y=grid['top']-row*grid['cellHeight']
                        self.assertTrue(has_line(left,y,right,y,grid['innerRule']),label)
                    for y in [bottom,grid['top']]:
                        self.assertTrue(has_line(left,y,right,y,grid['outerRule']),label)
                    for x,continued in [(left,evidence['continuesBefore']),(right,evidence['continuesAfter'])]:
                        self.assertTrue(has_line(x,bottom,x,grid['railTop'],
                                                 grid['innerRule'] if continued else grid['outerRule']),label)
                    content=self.pdfs[name].pages[record['page']-1].get_contents().get_data()
                    self.assertEqual(content.count(b'W*'),len(expected_vacancies),label)
                    if expected_vacancies:
                        self.assertTrue(any(abs(line['linewidth']-grid['hatchRule'])<.001 and
                                            line['x0']!=line['x1'] and line['y0']!=line['y1'] for line in lines),label)
                    self.assertFalse(any(line['y0']==line['y1'] and
                                         (line['y0']>grid['railTop'] or line['y0']<bottom) for line in lines),label)
                    glyphs=[c for c in page.chars if len(c['text'])==1 and ord(c['text']) in self.entries]
                    self.assertEqual(len(glyphs),len(record['codes']),label)
                    self.assertTrue(all(abs(c['size']-grid['glyphSize'])<.001 for c in glyphs),label)

    def test_names_family_headings_stay_with_complete_entries(self):
        config=self.presentation['names']
        for name,item in self.audit['files'].items():
            if 'proposal' in name:
                continue
            slug=name[:-4]
            entries=[row for row in self.audit['nameEntries'] if row['file']==slug]
            headings=[row for row in self.audit['familyHeadings'] if row['file']==slug]
            expected_families=[]
            for entry in entries:
                if not expected_families or expected_families[-1]!=entry['familyId']:
                    expected_families.append(entry['familyId'])
            self.assertEqual([h['familyId'] for h in headings],expected_families,name)
            if 'catalogue' in name:
                self.assertEqual(len(headings),58)
            names_text=re.sub(r'\s+',' ',' '.join(self.texts[name][p['page']-1]
                                                  for p in item['pages'] if p['kind']=='names'))
            families={f['id']:f for f in self.data['families']}
            for heading in headings:
                following=next(e for e in entries if e['codePoint']==heading['codePoint'])
                self.assertEqual((heading['page'],heading['column']),(following['page'],following['column']))
                self.assertAlmostEqual(heading['box'][1],following['box'][3])
                self.assertIn(families[heading['familyId']]['title'],names_text)
            previous={}
            for entry in entries:
                x0,y0,x1,y1=entry['box']
                self.assertGreaterEqual(y0,config['bottom']-.001)
                self.assertLessEqual(y1,config['top']+.001)
                self.assertAlmostEqual(x1-x0,config['columnWidth'])
                key=(entry['page'],entry['column'])
                self.assertLessEqual(y1,previous.get(key,config['top'])+.001)
                previous[key]=y0

    def test_actual_pdf_glyphs_and_names_keep_native_horizontal_proportions(self):
        def advances(path):
            with TTFont(path) as font:
                units=font['head'].unitsPerEm
                return {cp:font['hmtx'][name][0]/units for cp,name in font.getBestCmap().items()}
        script=advances(ROOT/'resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf')
        sans=advances(ROOT/'resources/fonts/SourceSans3/SourceSans3-Regular.ttf')
        config=self.presentation['names']
        names_ranges=[(self.presentation['page']['textLeft']+column*(config['columnWidth']+config['columnGap'])+
                       config['textOffset'],self.presentation['page']['textLeft']+
                       column*(config['columnWidth']+config['columnGap'])+config['columnWidth'])
                      for column in range(2)]
        for name,item in self.audit['files'].items():
            if 'proposal' in name:
                continue
            checked_glyphs=checked_names=0
            with pdfplumber.open(ROOT/'output'/'pdf'/name) as document:
                for record,page in zip(item['pages'],document.pages):
                    for char in page.chars:
                        if len(char['text'])!=1:
                            continue
                        cp=ord(char['text'])
                        if cp in self.entries:
                            # Font size alone misses leaked PDF Tz horizontal
                            # scaling. The real extracted advance must match hmtx.
                            self.assertAlmostEqual(char['adv'],script[cp]*char['size'],places=3,
                                                   msg=f'{name} page {record["page"]} U+{cp:05X}')
                            checked_glyphs+=1
                        elif record['kind']=='names' and 'SourceSans3-Regular' in char['fontname'] and \
                                792-config['top']-3 <= char['top'] <= 792-config['bottom'] and \
                                any(left-.01<=char['x0'] and char['x1']<=right+.01 for left,right in names_ranges):
                            self.assertAlmostEqual(char['adv'],sans[cp]*char['size'],places=3,
                                                   msg=f'{name} page {record["page"]} name character {char["text"]!r}')
                            checked_names+=1
            expected=sum(len(page['codes']) for page in item['pages'] if page['kind'] in ['chart','names'])
            self.assertEqual(checked_glyphs,expected,name)
            self.assertGreater(checked_names,1000,name)

    def test_native_font_embedding_and_vector_glyphs(self):
        for name,pdf in self.pdfs.items():
            embedded=set()
            for page in pdf.pages:
                resources=page['/Resources'].get_object()
                for reference in resources.get('/Font',{}).values():
                    font=reference.get_object(); base=str(font.get('/BaseFont',''))
                    if not any(family in base for family in ['Quintessential','STIX','SourceSans3']):
                        continue
                    self.assertEqual(font['/Subtype'],'/TrueType',(name,base))
                    descriptor=font['/FontDescriptor'].get_object()
                    self.assertIn('/FontFile2',descriptor,(name,base))
                    self.assertGreater(len(descriptor['/FontFile2'].get_object().get_data()),1000)
                    self.assertIn('/ToUnicode',font,(name,base))
                    embedded.add('Script' if 'Quintessential' in base else ('Chart' if 'SourceSans3' in base else 'STIX'))
                for reference in resources.get('/XObject',{}).values():
                    self.assertNotEqual(reference.get_object().get('/Subtype'),'/Image',name)
            if 'proposal' in name:
                self.assertIn('STIX',embedded,name)
                self.assertNotIn('Chart',embedded,name)
            else:
                self.assertIn('Chart',embedded,name)
                self.assertIn('Script',embedded,name)

    def test_text_stays_on_page_and_headers_are_present(self):
        for name,pdf in self.pdfs.items():
            with pdfplumber.open(ROOT/'output'/'pdf'/name) as document:
                for index,page in enumerate(document.pages):
                    self.assertEqual((round(page.width),round(page.height)),(612,792))
                    self.assertIn('Reference font: Roman 400' if 'proposal' in name else
                                  'Private-use character charts.',self.texts[name][index])
                    self.assertTrue(self.texts[name][index].strip().endswith(str(index+1)) or
                                    re.search(rf'\b{index+1}\b',self.texts[name][index]))
                    for char in page.chars:
                        if len(char['text'])==1 and 0xF2A00<=ord(char['text'])<=0xF2FFF:
                            continue # true script ink bounds are independently recorded above
                        self.assertGreaterEqual(char['x0'],40,(name,index+1,char['text']))
                        self.assertLessEqual(char['x1'],572,(name,index+1,char['text']))
                        self.assertGreaterEqual(char['top'],25,(name,index+1,char['text']))
                        self.assertLessEqual(char['bottom'],755,(name,index+1,char['text']))

    def test_proposal_contains_every_section_and_reference(self):
        proposal=json.loads((ROOT/'docs'/'proposal.json').read_text(encoding='utf-8'))
        text=re.sub(r'\s+',' ',' '.join(self.texts['quintessential-latin-proposal.pdf']))
        for section in proposal['sections']:
            self.assertIn(section['title'],text)
        for reference in proposal['references']:
            self.assertIn(reference['url'],text)
        self.assertIn('1,216',text)
        self.assertIn('native Italic',text)
        self.assertIn('each can extend independently',text)
        self.assertIn('U+F2E00',text)
        self.assertIn('not an announcement of registration',text)


if __name__=='__main__':
    unittest.main(verbosity=2)
