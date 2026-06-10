#!/usr/bin/env python3
"""validate_pptx.py — Phase F-Verify (animation-effects.md §3)
1) python-pptx 패키지 무결성  2) 스키마 계약 검사  3) soffice PDF 변환은 호출측에서.
"""
import sys, zipfile, subprocess
from pathlib import Path
from lxml import etree

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MC = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'

errors, warnings = [], []

def check_slide(name, data, rels_data):
    root = etree.fromstring(data)
    # 1. p:sld child order
    order = {f'{{{P}}}cSld': 0, f'{{{P}}}clrMapOvr': 1,
             f'{{{MC}}}AlternateContent': 2, f'{{{P}}}transition': 2,
             f'{{{P}}}timing': 3, f'{{{P}}}extLst': 4}
    seq = [order.get(c.tag, -1) for c in root if c.tag in order]
    if seq != sorted(seq):
        errors.append(f'{name}: p:sld child order violated: {seq}')
    # 2. cTn id uniqueness
    ids = [c.get('id') for c in root.iter(f'{{{P}}}cTn')]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        errors.append(f'{name}: duplicate cTn ids {dup}')
    # 3. spTgt spid must exist
    sp_ids = {c.get('id') for c in root.iter(f'{{{A}}}cNvPr')}
    sp_ids |= {c.get('id') for c in root.iter(f'{{{P}}}cNvPr')}
    for t in root.iter(f'{{{P}}}spTgt'):
        if t.get('spid') not in sp_ids:
            errors.append(f'{name}: spTgt spid={t.get("spid")} not in spTree')
    # 4. useBgFill shapes must not also carry a fill in spPr
    for sp in root.iter(f'{{{P}}}sp'):
        if sp.get('useBgFill') == '1':
            sppr = sp.find(f'{{{P}}}spPr')
            for f in ('solidFill', 'noFill', 'gradFill', 'blipFill', 'pattFill'):
                if sppr is not None and sppr.find(f'{{{A}}}{f}') is not None:
                    errors.append(f'{name}: useBgFill shape also has a:{f}')
    # 5. r:embed / r:id references resolve in rels
    rel_ids = set()
    if rels_data:
        rroot = etree.fromstring(rels_data)
        rel_ids = {rel.get('Id') for rel in rroot}
    for el in root.iter():
        for attr in (f'{{{R}}}embed', f'{{{R}}}id'):
            v = el.get(attr)
            if v and v not in rel_ids:
                errors.append(f'{name}: dangling relationship ref {v}')
    # 6. timing structural sanity: mainSeq exists if timing exists
    if root.find(f'{{{P}}}timing') is not None:
        node_types = [c.get('nodeType') for c in root.iter(f'{{{P}}}cTn')]
        if 'tmRoot' not in node_types or 'mainSeq' not in node_types:
            errors.append(f'{name}: timing tree missing tmRoot/mainSeq')

def main(path):
    # Stage 1: python-pptx
    try:
        from pptx import Presentation
        prs = Presentation(path)
        print(f'[1] python-pptx OK — slides={len(prs.slides)}')
    except Exception as e:
        errors.append(f'python-pptx failed: {e}')
    # Stage 2: XML contracts
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        for n in sorted(names):
            if n.startswith('ppt/slides/slide') and n.endswith('.xml'):
                rels = f'ppt/slides/_rels/{Path(n).name}.rels'
                check_slide(n, z.read(n), z.read(rels) if rels in names else None)
        # hyperlink targets exist
        for n in [x for x in names if x.startswith('ppt/slides/_rels/')]:
            rroot = etree.fromstring(z.read(n))
            for rel in rroot:
                if rel.get('Type', '').endswith('/slide'):
                    tgt = 'ppt/slides/' + rel.get('Target')
                    if tgt not in names:
                        errors.append(f'{n}: hlink target {tgt} missing')
    print(f'[2] XML contract — errors={len(errors)}')
    for e in errors:
        print('   ✗', e)
    sys.exit(1 if errors else 0)

if __name__ == '__main__':
    main(sys.argv[1])
