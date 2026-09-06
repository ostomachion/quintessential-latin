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
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


class PublicationPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/'resources'/'catalogue.json').read_text(encoding='utf-8'))
        cls.audit = json.loads((ROOT/'.tmp'/'pdf-layout-audit.json').read_text(encoding='utf-8'))
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
            extracted=Counter(ord(ch) for text in self.texts[name] for ch in text if 0xF2A00<=ord(ch)<=0xF2DFF)
            self.assertEqual(extracted,Counter({cp:2 for cp in expected}),name)
            name_text=' '.join(self.texts[name][p['page']-1] for p in names)
            normalized=re.sub(r'\s+',' ',name_text)
            for cp in expected:
                self.assertIn(self.entries[cp]['name'],normalized,f'{name}: U+{cp:05X}')
            # Numeric ranges must form consecutive 128-position sheets.
            for p in charts:
                self.assertEqual(p['start']%128,0)
                self.assertEqual(p['end']-p['start'],127)
            self.assertEqual(len(charts),8 if 'catalogue' in name else (4 if 'extended-b' in name else 2))
            if 'catalogue' not in name:
                total_charts+=len(charts)
        self.assertEqual(total_charts,8)
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

    def test_native_font_embedding_and_vector_glyphs(self):
        for name,pdf in self.pdfs.items():
            embedded=set()
            for page in pdf.pages:
                resources=page['/Resources'].get_object()
                for reference in resources.get('/Font',{}).values():
                    font=reference.get_object(); base=str(font.get('/BaseFont',''))
                    if 'Quintessential' not in base and 'STIX' not in base:
                        continue
                    self.assertEqual(font['/Subtype'],'/TrueType',(name,base))
                    descriptor=font['/FontDescriptor'].get_object()
                    self.assertIn('/FontFile2',descriptor,(name,base))
                    self.assertGreater(len(descriptor['/FontFile2'].get_object().get_data()),1000)
                    self.assertIn('/ToUnicode',font,(name,base))
                    embedded.add('Script' if 'Quintessential' in base else 'STIX')
                for reference in resources.get('/XObject',{}).values():
                    self.assertNotEqual(reference.get_object().get('/Subtype'),'/Image',name)
            self.assertIn('STIX',embedded,name)
            if 'proposal' not in name:
                self.assertIn('Script',embedded,name)

    def test_text_stays_on_page_and_headers_are_present(self):
        for name,pdf in self.pdfs.items():
            with pdfplumber.open(ROOT/'output'/'pdf'/name) as document:
                for index,page in enumerate(document.pages):
                    self.assertEqual((round(page.width),round(page.height)),(612,792))
                    self.assertIn('Reference font: Roman 400',self.texts[name][index])
                    self.assertTrue(self.texts[name][index].strip().endswith(str(index+1)) or
                                    re.search(rf'\b{index+1}\b',self.texts[name][index]))
                    for char in page.chars:
                        if len(char['text'])==1 and 0xF2A00<=ord(char['text'])<=0xF2DFF:
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
        self.assertIn('232',text)
        self.assertIn('600',text)
        self.assertIn('832',text)
        self.assertIn('not an announcement of registration',text)


if __name__=='__main__':
    unittest.main(verbosity=2)
