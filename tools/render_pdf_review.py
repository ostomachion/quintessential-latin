#!/usr/bin/env python3
"""Render publication PDFs and contact sheets for manual visual review.

This prepares inspection images. It does not certify visual acceptance or modify
PDF files or the archived review record. Paths in manifest.json are relative to
this repository when possible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def poppler_program(value):
    if value:
        candidate = Path(value).expanduser()
        if candidate.is_dir():
            candidate = next((candidate / name for name in ('pdftoppm', 'pdftoppm.exe', 'pdftoppm.cmd')
                              if (candidate / name).is_file()), candidate / 'pdftoppm')
        if not candidate.is_file():
            raise ValueError(f'pdftoppm was not found at {candidate}. Pass its executable or containing directory with --poppler-bin.')
        return str(candidate.resolve())
    found = shutil.which('pdftoppm')
    if not found:
        raise ValueError('Poppler pdftoppm is not installed or is not on PATH. Install Poppler, or pass --poppler-bin with its executable or containing directory.')
    return found


def portable_path(path):
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(pdf, output, program, dpi, renderer_version):
    from PIL import Image, ImageDraw
    from pypdf import PdfReader

    page_count = len(PdfReader(pdf).pages)
    folder = output / pdf.stem
    folder.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([program, '-r', str(dpi), '-png', str(pdf), str(folder / 'page')],
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f'Poppler failed for {pdf.name}: {result.stderr.strip() or result.stdout.strip()}')
    digits = len(str(page_count))
    pages = [folder / f'page-{index:0{digits}d}.png' for index in range(1, page_count + 1)]
    missing = [page.name for page in pages if not page.is_file()]
    if missing:
        raise RuntimeError(f'Poppler did not produce expected pages for {pdf.name}: {missing}')
    # Enumerate exactly the current PDF's pages. A previous larger render may
    # leave other scratch files; they never enter the manifest or contact sets.
    contacts = []
    for start in range(0, page_count, 4):
        group = pages[start:start + 4]
        tile_width, tile_height = 459, 622
        sheet = Image.new('RGB', (tile_width * 2, tile_height * ((len(group) + 1) // 2)), '#dddddd')
        draw = ImageDraw.Draw(sheet)
        for index, page in enumerate(group):
            with Image.open(page) as source:
                image = source.convert('RGB')
            image.thumbnail((449, 582))
            x, y = (index % 2) * tile_width + 5, (index // 2) * tile_height + 26
            sheet.paste(image, (x, y))
            draw.text((x, y - 20), f'{pdf.stem} - page {start + index + 1}', fill='black')
        contact = folder / f'contact-{start // 4 + 1}.png'
        sheet.save(contact)
        contacts.append(contact)
    return {'pdf': pdf.name, 'pageCount': page_count,
            'pages': [portable_path(page) for page in pages],
            'contacts': [portable_path(contact) for contact in contacts],
            'pdfSha256': digest(pdf), 'dpi': dpi, 'renderer': renderer_version,
            'renderedPageSha256': {page.name: digest(page) for page in pages}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdfs', nargs='*', type=Path, help='PDF files to render; defaults to all output/pdf/*.pdf')
    parser.add_argument('--poppler-bin', help='pdftoppm executable or its directory; defaults to PATH')
    parser.add_argument('--output', type=Path, default=ROOT / '.tmp' / 'pdf-review', help='Scratch image directory')
    parser.add_argument('--dpi', type=int, default=110, help='Raster resolution, default 110 dpi')
    args = parser.parse_args()
    if args.dpi < 36 or args.dpi > 600:
        parser.error('--dpi must be between 36 and 600')
    try:
        program = poppler_program(args.poppler_bin)
        import PIL
        import pypdf
    except ImportError as error:
        parser.error(f'Missing PDF review dependency: {error.name}. Install tools/requirements-pdfs.txt.')
    except ValueError as error:
        parser.error(str(error))
    files = [pdf.resolve() for pdf in args.pdfs] if args.pdfs else sorted((ROOT / 'output' / 'pdf').glob('*.pdf'))
    if not files:
        parser.error('No PDFs found. Run python tools/build_pdfs.py first.')
    if len({pdf.stem for pdf in files}) != len(files):
        parser.error('Selected PDFs must have unique basenames so review directories cannot collide.')
    for pdf in files:
        if not pdf.is_file() or pdf.suffix.lower() != '.pdf':
            parser.error(f'PDF file not found: {pdf}')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    try:
        version = subprocess.run([program, '-v'], capture_output=True, text=True, check=False)
        renderer_version = (version.stderr or version.stdout).strip().splitlines()[0]
        manifest = [render(pdf, output, program, args.dpi, renderer_version) for pdf in files]
    except (OSError, RuntimeError, IndexError) as error:
        parser.exit(1, f'PDF rendering failed: {error}\n')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {sum(item["pageCount"] for item in manifest)} pages from {len(manifest)} PDFs.')
    print(f'Contact sheets and invocation manifest: {portable_path(output)}')
    print('Rendering prepares review material; it does not record visual acceptance.')


if __name__ == '__main__':
    main()
