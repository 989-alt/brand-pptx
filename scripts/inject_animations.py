#!/usr/bin/env python3
"""inject_animations.py — brand-pptx Phase F
정적 PPTX에 OOXML 애니메이션(<p:timing>)·전환(<p:transition>)·배경 트릭을 주입.
Usage: python3 inject_animations.py <in.pptx> <manifest.json> <out.pptx>
"""
import sys, json, zipfile, shutil, copy
from pathlib import Path
from lxml import etree

NS = {
    'a':   'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p':   'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r':   'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'ct':  'http://schemas.openxmlformats.org/package/2006/content-types',
    'mc':  'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'p14': 'http://schemas.microsoft.com/office/powerpoint/2010/main',
    'p159':'http://schemas.microsoft.com/office/powerpoint/2015/09/main',
}
def q(tag):
    pfx, local = tag.split(':')
    return f'{{{NS[pfx]}}}{local}'

EMU = 9525  # per px @96dpi
SLIDE_H_PX = 720

def E(tag, attrib=None, nsmap=None, **kw):
    el = etree.Element(q(tag), nsmap=nsmap)
    for k, v in (attrib or {}).items():
        if ':' in k:
            el.set(q(k), str(v))
        else:
            el.set(k, str(v))
    for k, v in kw.items():
        el.set(k, str(v))
    return el

# ---------------- package helpers ----------------

class Slide:
    def __init__(self, work, n):
        self.n = n
        self.path = work / 'ppt' / 'slides' / f'slide{n}.xml'
        self.rels_path = work / 'ppt' / 'slides' / '_rels' / f'slide{n}.xml.rels'
        self.tree = etree.parse(str(self.path))
        self.root = self.tree.getroot()
        if self.rels_path.exists():
            self.rels = etree.parse(str(self.rels_path))
        else:
            self.rels_path.parent.mkdir(parents=True, exist_ok=True)
            r = etree.Element(q('rel:Relationships'), nsmap={None: NS['rel']})
            self.rels = etree.ElementTree(r)
        self._next_sp_id = None
        self._tn_id = 0

    # ---- ids ----
    def max_sp_id(self):
        ids = [int(c.get('id')) for c in self.root.iter(q('p:cNvPr'))]
        return max(ids) if ids else 1

    def next_sp_id(self):
        if self._next_sp_id is None:
            self._next_sp_id = self.max_sp_id()
        self._next_sp_id += 1
        return self._next_sp_id

    def next_tn(self):
        self._tn_id += 1
        return self._tn_id

    def next_rid(self):
        nums = [int(r.get('Id')[3:]) for r in self.rels.getroot()
                if r.get('Id', '').startswith('rId')]
        return f'rId{max(nums) + 1 if nums else 1}'

    def add_rel(self, rtype, target, external=False):
        rid = self.next_rid()
        rel = etree.SubElement(self.rels.getroot(), q('rel:Relationship'))
        rel.set('Id', rid); rel.set('Type', rtype); rel.set('Target', target)
        if external:
            rel.set('TargetMode', 'External')
        return rid

    def sp_tree(self):
        return self.root.find(q('p:cSld') + '/' + q('p:spTree'))

    def save(self):
        self.tree.write(str(self.path), xml_declaration=True,
                        encoding='UTF-8', standalone=True)
        self.rels.write(str(self.rels_path), xml_declaration=True,
                        encoding='UTF-8', standalone=True)

# ---------------- media ----------------

def ensure_png_default(work):
    ct_path = work / '[Content_Types].xml'
    tree = etree.parse(str(ct_path))
    root = tree.getroot()
    for d in root.findall(q('ct:Default')):
        if d.get('Extension') == 'png':
            return
    d = etree.SubElement(root, q('ct:Default'))
    d.set('Extension', 'png'); d.set('ContentType', 'image/png')
    tree.write(str(ct_path), xml_declaration=True, encoding='UTF-8', standalone=True)

_media_count = 0
def add_media(work, slide, image_path):
    global _media_count
    _media_count += 1
    media = work / 'ppt' / 'media'
    media.mkdir(exist_ok=True)
    name = f'animimg{_media_count}{Path(image_path).suffix}'
    shutil.copy(image_path, media / name)
    rid = slide.add_rel(
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image',
        f'../media/{name}')
    return rid

# ---------------- background (§1.1a) ----------------

def set_bg_image(work, slide, image_path):
    rid = add_media(work, slide, image_path)
    csld = slide.root.find(q('p:cSld'))
    old = csld.find(q('p:bg'))
    if old is not None:
        csld.remove(old)
    bg = E('p:bg'); bgpr = etree.SubElement(bg, q('p:bgPr'))
    blipfill = etree.SubElement(bgpr, q('a:blipFill'))
    blip = etree.SubElement(blipfill, q('a:blip')); blip.set(q('r:embed'), rid)
    stretch = etree.SubElement(blipfill, q('a:stretch'))
    etree.SubElement(stretch, q('a:fillRect'))
    etree.SubElement(bgpr, q('a:effectLst'))
    csld.insert(0, bg)

# ---------------- shapes ----------------

def make_xfrm(x, y, w, h, rot_deg=0, flipV=False):
    xfrm = E('a:xfrm')
    if rot_deg:
        xfrm.set('rot', str(int(rot_deg * 60000)))
    if flipV:
        xfrm.set('flipV', '1')
    off = etree.SubElement(xfrm, q('a:off'))
    ext = etree.SubElement(xfrm, q('a:ext'))
    off.set('x', str(int(x * EMU))); off.set('y', str(int(y * EMU)))
    ext.set('cx', str(int(w * EMU))); ext.set('cy', str(int(h * EMU)))
    return xfrm

def make_line_el(spec):
    ln = E('a:ln', {'w': str(int(spec.get('w_pt', 1) * 12700))})
    if spec.get('cap'):
        ln.set('cap', spec['cap'])
    fill = etree.SubElement(ln, q('a:solidFill'))
    clr = etree.SubElement(fill, q('a:srgbClr')); clr.set('val', spec.get('color', 'FFFFFF'))
    if spec.get('alpha'):
        a = etree.SubElement(clr, q('a:alpha')); a.set('val', str(int(spec['alpha'] * 1000)))
    if spec.get('dash'):
        d = etree.SubElement(ln, q('a:prstDash')); d.set('val', spec['dash'])
    etree.SubElement(ln, q('a:round'))
    return ln

GEOM = {'ellipse': 'ellipse', 'roundRect': 'roundRect', 'rect': 'rect',
        'gear6': 'gear6', 'gear9': 'gear9', 'line': 'line'}

def add_shape(work, slide, spec, slide_count):
    sp = E('p:sp')
    if spec.get('use_bg_fill'):
        sp.set('useBgFill', '1')
    sid = slide.next_sp_id()
    nv = etree.SubElement(sp, q('p:nvSpPr'))
    cnv = etree.SubElement(nv, q('p:cNvPr'))
    cnv.set('id', str(sid)); cnv.set('name', spec['name'])
    if spec.get('link_to_slide'):
        tgt = int(spec['link_to_slide'])
        assert 1 <= tgt <= slide_count, f'link target slide{tgt} out of range'
        rid = slide.add_rel(
            'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide',
            f'slide{tgt}.xml')
        hl = etree.SubElement(cnv, q('a:hlinkClick'))
        hl.set(q('r:id'), rid); hl.set('action', 'ppaction://hlinksldjump')
    etree.SubElement(nv, q('p:cNvSpPr'))
    etree.SubElement(nv, q('p:nvPr'))

    sppr = etree.SubElement(sp, q('p:spPr'))
    x, y, w, h = spec['x'], spec['y'], spec['w'], spec['h']
    flipV = False
    if h < 0:                       # upward line: flipV
        y, h, flipV = y + h, -h, True
    sppr.append(make_xfrm(x, y, w, h, spec.get('rot_deg', 0), flipV))
    geom = etree.SubElement(sppr, q('a:prstGeom'))
    geom.set('prst', GEOM[spec['kind']])
    av = etree.SubElement(geom, q('a:avLst'))
    if spec['kind'] == 'roundRect':
        gd = etree.SubElement(av, q('a:gd'))
        gd.set('name', 'adj'); gd.set('fmla', f"val {spec.get('adj', 50000)}")
    if not spec.get('use_bg_fill') and spec['kind'] != 'line' and not spec.get('fill'):
        sppr.append(E('a:noFill'))
    if spec.get('fill'):
        sf = E('a:solidFill'); c = etree.SubElement(sf, q('a:srgbClr'))
        c.set('val', spec['fill']); sppr.append(sf)
    if spec.get('line'):
        sppr.append(make_line_el(spec['line']))

    tx = etree.SubElement(sp, q('p:txBody'))
    etree.SubElement(tx, q('a:bodyPr')); etree.SubElement(tx, q('a:lstStyle'))
    etree.SubElement(tx, q('a:p'))
    slide.sp_tree().append(sp)
    return sid

def add_picture_layer(work, slide, spec):
    rid = add_media(work, slide, spec['image'])
    pic = E('p:pic')
    sid = slide.next_sp_id()
    nv = etree.SubElement(pic, q('p:nvPicPr'))
    cnv = etree.SubElement(nv, q('p:cNvPr'))
    cnv.set('id', str(sid)); cnv.set('name', spec.get('name', 'pic-layer'))
    cnvp = etree.SubElement(nv, q('p:cNvPicPr'))
    locks = etree.SubElement(cnvp, q('a:picLocks')); locks.set('noChangeAspect', '1')
    etree.SubElement(nv, q('p:nvPr'))
    bf = etree.SubElement(pic, q('p:blipFill'))
    blip = etree.SubElement(bf, q('a:blip')); blip.set(q('r:embed'), rid)
    st = etree.SubElement(bf, q('a:stretch')); etree.SubElement(st, q('a:fillRect'))
    sppr = etree.SubElement(pic, q('p:spPr'))
    ov = spec.get('overscan', 0.0)
    x, y = -1280 * ov, -720 * ov
    w, h = 1280 * (1 + 2 * ov), 720 * (1 + 2 * ov)
    sppr.append(make_xfrm(x, y, w, h))
    g = etree.SubElement(sppr, q('a:prstGeom')); g.set('prst', 'rect')
    etree.SubElement(g, q('a:avLst'))
    # z-order: bottom-most shape = right after nvGrpSpPr + grpSpPr (index 2).
    # html2pptx sets the canvas via bgPr solidFill (no canvas rect shape),
    # so index 2 puts the picture under every text/shape but over the slide bg.
    slide.sp_tree().insert(2, pic)
    return sid

def rename_for_morph(slide, rules):
    for sp in slide.sp_tree().iter(q('p:sp')):
        texts = [t.text or '' for t in sp.iter(q('a:t'))]
        joined = ''.join(texts).strip()
        for rule in rules:
            if ('exact' in rule and joined == rule['exact']) or \
               ('contains' in rule and rule['contains'] in joined):
                sp.find(q('p:nvSpPr') + '/' + q('p:cNvPr')).set('name', rule['name'])

# ---------------- transitions (§1.8) ----------------

def insert_after_clrmap(slide, el):
    root = slide.root
    # remove previous transition containers
    for old in root.findall(q('p:transition')) + root.findall(q('mc:AlternateContent')):
        root.remove(old)
    anchor = root.find(q('p:clrMapOvr'))
    idx = list(root).index(anchor) + 1 if anchor is not None else 1
    root.insert(idx, el)

def set_transition(slide, spec):
    t = spec['type']
    if t == 'auto':
        tr = E('p:transition', {'advClick': '1', 'advTm': str(spec.get('adv_ms', 0))})
        insert_after_clrmap(slide, tr)
    elif t == 'morph':
        ac = E('mc:AlternateContent', nsmap={'mc': NS['mc']})
        choice = etree.SubElement(ac, q('mc:Choice'), nsmap={'p159': NS['p159']})
        choice.set('Requires', 'p159')
        tr = etree.SubElement(choice, q('p:transition'), nsmap={'p14': NS['p14']})
        tr.set('spd', 'slow'); tr.set(q('p14:dur'), str(spec.get('dur_ms', 1500)))
        morph = etree.SubElement(tr, q('p159:morph')); morph.set('option', 'byObject')
        fb = etree.SubElement(ac, q('mc:Fallback'))
        tr2 = etree.SubElement(fb, q('p:transition')); tr2.set('spd', 'slow')
        etree.SubElement(tr2, q('p:fade'))
        insert_after_clrmap(slide, ac)

# ---------------- timing (§1.2~1.7) ----------------

def cbhvr(slide, spid, dur, attrs=None, fill='hold'):
    b = E('p:cBhvr')
    ctn = etree.SubElement(b, q('p:cTn'))
    ctn.set('id', str(slide.next_tn())); ctn.set('dur', str(dur))
    if fill:
        ctn.set('fill', fill)
    tgt = etree.SubElement(b, q('p:tgtEl'))
    spt = etree.SubElement(tgt, q('p:spTgt')); spt.set('spid', str(spid))
    if attrs:
        al = etree.SubElement(b, q('p:attrNameLst'))
        for a in attrs:
            an = etree.SubElement(al, q('p:attrName')); an.text = a
    return b

def effect_par(slide, eff, spid):
    """One effect <p:par> per §1.3–1.7."""
    t = eff['type']
    par = E('p:par')
    ctn = etree.SubElement(par, q('p:cTn'))
    ctn.set('id', str(slide.next_tn()))
    preset = {'motion_line': ('0', 'path'), 'grow_shrink': ('6', 'emph'),
              'spin': ('8', 'emph'), 'fade_out': ('10', 'exit')}[t]
    ctn.set('presetID', preset[0]); ctn.set('presetClass', preset[1])
    ctn.set('presetSubtype', '0')
    if eff.get('repeat') == 'indefinite':
        ctn.set('repeatCount', 'indefinite')
    if eff.get('auto_rev'):
        ctn.set('autoRev', '1')
    if eff.get('smooth'):
        ctn.set('accel', '50000'); ctn.set('decel', '50000')
    ctn.set('fill', 'hold'); ctn.set('nodeType', 'withEffect')
    st = etree.SubElement(ctn, q('p:stCondLst'))
    cond = etree.SubElement(st, q('p:cond'))
    cond.set('delay', str(eff.get('delay_ms', 0)))
    child = etree.SubElement(ctn, q('p:childTnLst'))
    dur = eff.get('dur', 2000)

    if t == 'motion_line':
        m = etree.SubElement(child, q('p:animMotion'))
        m.set('origin', 'layout')
        m.set('path', f"M 0 0 L {eff.get('dx', 0)} {eff.get('dy', 0)} E")
        m.set('pathEditMode', 'relative'); m.set('ptsTypes', '')
        m.append(cbhvr(slide, spid, dur, ['ppt_x', 'ppt_y']))
        # cBhvr must be the FIRST child of animMotion
        m.insert(0, m[-1])
    elif t == 'grow_shrink':
        s = etree.SubElement(child, q('p:animScale'))
        s.append(cbhvr(slide, spid, dur))
        # CT_TLPoint: <p:by x=".." y=".."/> — 빈 요소 + 속성 (a:pt 자식 아님!)
        by = etree.SubElement(s, q('p:by'))
        by.set('x', str(int(eff.get('sx', 1.0) * 100000)))
        by.set('y', str(int(eff.get('sy', 1.0) * 100000)))
    elif t == 'spin':
        rdir = -1 if eff.get('ccw') else 1
        rot = etree.SubElement(child, q('p:animRot'))
        rot.set('by', str(rdir * int(eff.get('deg', 360) * 60000)))
        rot.append(cbhvr(slide, spid, dur, ['r']))
    elif t == 'fade_out':
        fx = etree.SubElement(child, q('p:animEffect'))
        fx.set('transition', 'out'); fx.set('filter', 'fade')
        fx.append(cbhvr(slide, spid, dur, fill=None))
    return par

def build_timing(slide, effect_pairs):
    """effect_pairs: list of (effect_spec, spid)."""
    timing = E('p:timing')
    tnlst = etree.SubElement(timing, q('p:tnLst'))
    par0 = etree.SubElement(tnlst, q('p:par'))
    root_ctn = etree.SubElement(par0, q('p:cTn'))
    root_ctn.set('id', str(slide.next_tn()))  # 1
    root_ctn.set('dur', 'indefinite'); root_ctn.set('restart', 'never')
    root_ctn.set('nodeType', 'tmRoot')
    c0 = etree.SubElement(root_ctn, q('p:childTnLst'))
    seq = etree.SubElement(c0, q('p:seq'))
    seq.set('concurrent', '1'); seq.set('nextAc', 'seek')
    main = etree.SubElement(seq, q('p:cTn'))
    main_id = slide.next_tn()                 # 2
    main.set('id', str(main_id)); main.set('dur', 'indefinite')
    main.set('nodeType', 'mainSeq')
    c1 = etree.SubElement(main, q('p:childTnLst'))
    parA = etree.SubElement(c1, q('p:par'))
    ctnA = etree.SubElement(parA, q('p:cTn'))
    ctnA.set('id', str(slide.next_tn())); ctnA.set('fill', 'hold')
    stA = etree.SubElement(ctnA, q('p:stCondLst'))
    etree.SubElement(stA, q('p:cond')).set('delay', 'indefinite')
    onb = etree.SubElement(stA, q('p:cond'))
    onb.set('evt', 'onBegin'); onb.set('delay', '0')
    tn = etree.SubElement(onb, q('p:tn')); tn.set('val', str(main_id))
    cA = etree.SubElement(ctnA, q('p:childTnLst'))
    parB = etree.SubElement(cA, q('p:par'))
    ctnB = etree.SubElement(parB, q('p:cTn'))
    ctnB.set('id', str(slide.next_tn())); ctnB.set('fill', 'hold')
    stB = etree.SubElement(ctnB, q('p:stCondLst'))
    etree.SubElement(stB, q('p:cond')).set('delay', '0')
    cB = etree.SubElement(ctnB, q('p:childTnLst'))
    for eff, spid in effect_pairs:
        cB.append(effect_par(slide, eff, spid))
    # seq conds AFTER the cTn
    prev = etree.SubElement(seq, q('p:prevCondLst'))
    pc = etree.SubElement(prev, q('p:cond')); pc.set('evt', 'onPrev'); pc.set('delay', '0')
    pt = etree.SubElement(pc, q('p:tgtEl')); etree.SubElement(pt, q('p:sldTgt'))
    nxt = etree.SubElement(seq, q('p:nextCondLst'))
    nc = etree.SubElement(nxt, q('p:cond')); nc.set('evt', 'onNext'); nc.set('delay', '0')
    nt = etree.SubElement(nc, q('p:tgtEl')); etree.SubElement(nt, q('p:sldTgt'))
    # insert: after transition/AlternateContent, else after clrMapOvr
    root = slide.root
    for old in root.findall(q('p:timing')):
        root.remove(old)
    anchor = None
    for tag in ('mc:AlternateContent', 'p:transition', 'p:clrMapOvr'):
        anchor = root.find(q(tag))
        if anchor is not None:
            break
    root.insert(list(root).index(anchor) + 1, timing)

def make_dark_image(image_path, brightness=0.45):
    """§1.1(b') — 영상의 '어두운 사진 덮기' 단계. 밝기를 낮춘 사본 생성."""
    from PIL import Image, ImageEnhance
    src = Path(image_path)
    out = src.with_name(src.stem + f'_dark{int(brightness*100)}' + src.suffix)
    if not out.exists():
        img = Image.open(src)
        ImageEnhance.Brightness(img).enhance(brightness).save(out)
    return str(out)

# ---------------- main ----------------

def main(in_pptx, manifest_path, out_pptx):
    manifest = json.loads(Path(manifest_path).read_text())
    work = Path('_inject_work')
    if work.exists():
        shutil.rmtree(work)
    with zipfile.ZipFile(in_pptx) as z:
        z.extractall(work)
    ensure_png_default(work)
    slide_count = len(list((work / 'ppt' / 'slides').glob('slide*.xml')))

    for n_str, cfg in manifest['slides'].items():
        slide = Slide(work, int(n_str))
        if cfg.get('background_image'):
            set_bg_image(work, slide, cfg['background_image'])
        if cfg.get('dark_cover'):
            dc = cfg['dark_cover']
            dark_path = make_dark_image(dc['image'], dc.get('brightness', 0.45))
            add_picture_layer(work, slide,
                              {'image': dark_path, 'name': 'dark-cover',
                               'overscan': dc.get('overscan', 0.0)})
        effect_pairs = []
        if cfg.get('picture_layer'):
            sid = add_picture_layer(work, slide, cfg['picture_layer'])
            for eff in cfg['picture_layer'].get('effects', []):
                effect_pairs.append((eff, sid))
        for spec in cfg.get('shapes', []):
            sid = add_shape(work, slide, spec, slide_count)
            for eff in spec.get('effects', []):
                effect_pairs.append((eff, sid))
        if cfg.get('rename_for_morph'):
            rename_for_morph(slide, cfg['rename_for_morph'])
        if cfg.get('transition'):
            set_transition(slide, cfg['transition'])
        if effect_pairs:
            build_timing(slide, effect_pairs)
        slide.save()
        print(f'slide{n_str}: shapes+{len(cfg.get("shapes", []))} effects+{len(effect_pairs)}')

    # rezip
    out = Path(out_pptx)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(work.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(work).as_posix())
    print('OK ', out)

if __name__ == '__main__':
    main(*sys.argv[1:4])
