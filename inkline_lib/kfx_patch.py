"""KFX 行内图修复：将 boko 的块级 image 改为官方式行内。

逆向依据：Send-to-Kindle 官方 KFX。
改动（只改 storyline + style entity 内容，不增删 entity）：
1. content_list 内 [text, image]* 交错合并为单个 text（含内联 content_list）
2. image 加 render(601)=inline(283)
3. image 的 style 改为官方结构（width/height/baseline_shift，em 值从 EPUB 源 CSS 取）
"""
import re
import struct
import sys
import zipfile

try:
    from .kfx_symbols import SYMBOLS as YJ
    from .kfx_ion import decode, encode, IonSymbol
except ImportError:
    from kfx_symbols import SYMBOLS as YJ
    from kfx_ion import decode, encode, IonSymbol
F = {n: i for i, n in enumerate(YJ)}
F_TYPE, F_STYLE, F_ID = F['type'], F['style'], F['id']
F_CONTENT, F_CL = F['content'], F['content_list']
F_TEXT, F_IMAGE = F['text'], F['image']
F_RENDER, F_INLINE = F['render'], F['inline']
F_RESNAME = F['resource_name']

# 实测基线偏移（Scribe 真机调定）：middle 等效公式 +0.2em
BS_ADJ = 0.2


def type_of(f):
    tv = f.get(F_TYPE)
    return int(tv) if isinstance(tv, IonSymbol) else tv

def load_kfx(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'CONT'
    hl = struct.unpack('<I', d[6:10])[0]
    co = struct.unpack('<I', d[10:14])[0]
    cl = struct.unpack('<I', d[14:18])[0]
    ci, _ = decode(d[co:co + cl])
    info = dict(ci)
    io = info[F['bcIndexTabOffset']]
    il = info[F['bcIndexTabLength']]
    idx = d[io:io + il]
    ents = []
    for i in range(len(idx) // 24):
        ents.append(struct.unpack('<IIQQ', idx[i * 24:(i + 1) * 24]))
    return d, hl, co, cl, ci, ents


def get_body(d, hl, off, ln):
    seg = d[hl + off:hl + off + ln]
    if seg[:4] == b'ENTY':
        hlen = struct.unpack('<I', seg[6:10])[0]
        return seg[:hlen], seg[hlen:]
    return b'', seg


def patch(path, epub_path=None):
    d, hl, co, cl, ci, ents = load_kfx(path)
    info = dict(ci)

    chunks = {}
    for eid, tid, off, ln in ents:
        if YJ[tid] != 'content':
            continue
        _, body = get_body(d, hl, off, ln)
        v, _ = decode(body)
        for fid, val in v:
            if fid == F_CL:
                chunks[eid] = val

    def text_of(el):
        for fid, val in el:
            if fid == F_CONTENT and isinstance(val, list):
                idx2 = dict(val).get(403)
                for arr in chunks.values():
                    if idx2 is not None and idx2 < len(arr):
                        return arr[idx2]
        return ''

    DOC = []
    def sym_name(i):
        if isinstance(i, IonSymbol):
            i = int(i)
        if isinstance(i, int):
            return YJ[i] if i < len(YJ) else (DOC[i - len(YJ)] if i - len(YJ) < len(DOC) else None)
        return i
    img_ems = []  # image 的 em（按遇到顺序）
    def fix_list(items):
        """递归修复含 image 的 content_list。返回 (新list, 是否改动)。"""
        has_img = False
        for it in items:
            if isinstance(it, list) and type_of(dict(it)) == F_IMAGE:
                has_img = True
                break
        if not has_img:
            # 递归进子 text
            changed = False
            out = []
            for it in items:
                if isinstance(it, list):
                    f = dict(it)
                    if F_CL in f:
                        nl, c = fix_list(f[F_CL])
                        if c:
                            it = [(k, nl if k == F_CL else v) for k, v in it]
                            changed = True
                out.append(it)
            return out, changed
        # 无文本基（独立显示公式块）：保持块级，不合并
        bases = [it for it in items if isinstance(it, list) and type_of(dict(it)) == F_TEXT]
        if not bases:
            return items, False
        base = bases[0]
        nl = []
        for it in items:
            if not isinstance(it, list):
                nl.append(it)
                continue
            f = dict(it)
            if type_of(f) == F_IMAGE:
                el = list(it) + [(F_RENDER, IonSymbol(F_INLINE))]
                r = f.get(F_RESNAME)
                rn = sym_name(r)
                em = res_em(rn) if rn else None
                img_ems.append(em)
                nl.append(el)
            elif type_of(f) == F_TEXT:
                t = text_of(it)
                if t:
                    nl.append(t)
            else:
                nl.append(it)
        new_el = [(k, v) for k, v in base if k != F_CONTENT] + [(F_CL, nl)]
        return [new_el], True

    # EPUB: png字节 -> em
    ep = epub_path or (sys.argv[2] if len(sys.argv) > 2 else None)
    bem = {}
    if ep:
        z = zipfile.ZipFile(ep)
        xt = ''
        for n in z.namelist():
            if n.endswith('.xhtml'):
                xt += z.read(n).decode('utf-8')
        src_em = {}
        for m in re.finditer(r'<img[^>]*src="([^"]+)"[^>]*style="([^"]*)"', xt):
            src, st = m.group(1), m.group(2)
            w = re.search(r'width:([\d.]+)em', st)
            h = re.search(r'height:([\d.]+)em', st)
            if w and h:
                src_em[src.split('/')[-1]] = (float(w.group(1)), float(h.group(1)))
        for n in z.namelist():
            if n.endswith('.png') and n.split('/')[-1] in src_em:
                raw = z.read(n)
                w0, h0 = src_em[n.split('/')[-1]]
                try:
                    from PIL import Image as _Im
                    import io as _io
                    pw, ph = _Im.open(_io.BytesIO(raw)).size
                except Exception:
                    pw, ph = None, None
                bem[raw] = (w0, h0, pw, ph)
    print(f'EPUB png-em: {len(bem)}个')
    # KFX: resource/raw 顺序提字节；doc symbols
    ds_off, ds_len = info[F['bcDocSymbolOffset']], info[F['bcDocSymbolLength']]
    dsv, _ = decode(d[ds_off:ds_off + ds_len])
    DOC = list(dict(dsv[1])[7])
    raw_bytes = []
    res_names = []
    F_LOC = F.get('location', 165)
    for eid, tid, off, ln in ents:
        if YJ[tid] == 'bcRawMedia':
            _, body = get_body(d, hl, off, ln)
            raw_bytes.append(body)
        elif YJ[tid] == 'external_resource':
            _, body = get_body(d, hl, off, ln)
            v, _ = decode(body)
            loc = dict(v).get(F_LOC)
            res_names.append(loc.split('/')[-1] if isinstance(loc, str) and '/' in loc else None)
    res_order = {n: k for k, n in enumerate(res_names) if n}
    print(f'resource数: {len(res_names)} raw数: {len(raw_bytes)}')
    def res_em(rname):
        k = res_order.get(str(rname or ''))
        if k is None or k >= len(raw_bytes):
            return None
        return bem.get(raw_bytes[k])
    F_W, F_H, F_MW = F['width'], F['height'], F['max_width']
    F_BS = F['baseline_shift']
    F_VAL, F_UNIT = F['value'], F['unit']
    F_EM, F_PCT = F['em'], F['percent']
    F_YJVA = F.get('yj.vertical_align', 633)
    new_payloads = {}
    for eid, tid, off, ln in ents:
        if YJ[tid] != 'storyline':
            continue
        head, body = get_body(d, hl, off, ln)
        v, _ = decode(body)
        nv, changed = [], False
        for fid, val in v:
            if fid == F_CL:
                val, c = fix_list(val)
                changed = changed or c
            nv.append((fid, val))
        if changed:
            new_payloads[eid] = (head, encode(nv))
            print(f'storyline {eid}: 已合并')
        else:
            print(f'storyline {eid}: 无改动')
    # 按 em 分组建 style
    groups = {}
    for em in img_ems:
        if em:
            groups.setdefault(em, 0)
            groups[em] += 1
    print(f'em分组: {len(groups)}种，共{len(img_ems)}图')
    # 零新增方案：改 boko 已生成的 image styles（每图独立），image 引用不动
    # 收集 style符号 -> em（按 img_ems 顺序配对 storyline 里的 image）
    style_em = {}
    em_iter2 = iter(img_ems)
    for eid, tid, off, ln in ents:
        if YJ[tid] != 'storyline' or eid not in new_payloads:
            continue
        head, nb = new_payloads[eid]
        v, _ = decode(nb)
        def collect(x):
            if isinstance(x, list):
                if x and all(isinstance(i, tuple) and len(i) == 2 and isinstance(i[0], int) for i in x):
                    f = dict(x)
                    tv = f.get(F_TYPE)
                    tv = int(tv) if isinstance(tv, IonSymbol) else tv
                    if tv == F_IMAGE and any(k == F_RENDER for k, _ in x):
                        em = next(em_iter2, None)
                        st = f.get(F_STYLE)
                        st = int(st) if isinstance(st, IonSymbol) else st
                        if em and st not in style_em:
                            style_em[st] = em
                for i in x:
                    collect(i)
            elif isinstance(x, tuple):
                collect(x[1])
        collect(v)
    print(f'style-em配对: {len(style_em)}个')
    for eid, tid, off, ln in ents:
        if YJ[tid] != 'style':
            continue
        head, body = get_body(d, hl, off, ln)
        v, _ = decode(body)
        sn = dict(v).get(173)
        sn = int(sn) if isinstance(sn, IonSymbol) else sn
        target = None
        for st, em in style_em.items():
            if st == sn:
                target = em
                break
        if target is None:
            continue
        t = target
        w0, h0 = t[0], t[1]
        hd = (w0 * t[3] / t[2]) if len(t) > 3 and t[2] and t[3] else h0
        bs = round(-(hd / 2 - 0.25) + BS_ADJ, 4)
        nv = [(k, x) for k, x in v if k not in (F_YJVA, F_H, F_W, F_MW)]
        nv.append((F_W, [(F_VAL, w0), (F_UNIT, IonSymbol(F_EM))]))
        nv.append((F_MW, [(F_VAL, 100.0), (F_UNIT, IonSymbol(F_PCT))]))
        nv.append((F_BS, [(F_VAL, bs), (F_UNIT, IonSymbol(F_EM))]))
        new_payloads[eid] = (head, encode(nv))
    return repack(d, hl, info, ci, ents, new_payloads, path)


def repack(d, hl, info, ci, ents, new_payloads, path, extra_ents=None, new_symtab=None):
    """全重建 container。extra_ents=[(eid,tid,payload)] 追加；new_symtab 替换符号表。"""
    import hashlib
    out_ents = []
    for eid, tid, off, ln in ents:
        _, body = get_body(d, hl, off, ln)
        seg = d[hl + off:hl + off + ln]
        head = seg[:len(seg) - len(body)] if body else seg
        if eid in new_payloads:
            head, nb = new_payloads[eid]
            out_ents.append((eid, tid, head + nb))
        else:
            out_ents.append((eid, tid, seg))
    if extra_ents:
        out_ents.extend(extra_ents)
    # 索引
    new_idx = bytearray()
    cur = 0
    for eid, tid, payload in out_ents:
        new_idx += struct.pack('<IIQQ', eid, tid, cur, len(payload))
        cur += len(payload)
    # 符号表
    sym_off = info[F['bcDocSymbolOffset']]
    sym_len = info[F['bcDocSymbolLength']]
    symtab_raw = new_symtab if new_symtab is not None else d[sym_off:sym_off + sym_len]
    # caps
    cap_off = info[F['bcFCapabilitiesOffset']]
    cap_len = info[F['bcFCapabilitiesLength']]
    caps_raw = d[cap_off:cap_off + cap_len]
    # payload sha
    sha = hashlib.sha1()
    for _, _, p in out_ents:
        sha.update(p)
    # kfxgen 区（ci 之后到 hl）：更新 sha
    ci_off = struct.unpack('<I', d[10:14])[0]
    ci_len = struct.unpack('<I', d[14:18])[0]
    gen_raw = d[ci_off + ci_len:hl]
    try:
        gs = gen_raw.decode('utf-8')
        gs = re.sub(r'\{key:"kfxgen_payload_sha1",value:"[0-9a-f]*"\}',
                    f'{{key:"kfxgen_payload_sha1",value:"{sha.hexdigest()}"}}', gs)
        gen_raw = gs.encode('utf-8')
    except Exception:
        pass
    # 新 ci
    idx_off_new = 18
    sym_off_new = idx_off_new + len(new_idx)
    cap_off_new = sym_off_new + len(symtab_raw)
    ci_off_new = cap_off_new + len(caps_raw)
    gen_off_new = None  # ci 后
    ci_nv = []
    for fid, val in dict(ci).items():
        n = YJ[fid] if fid < len(YJ) else fid
        if n == 'bcIndexTabOffset':
            val = idx_off_new
        elif n == 'bcIndexTabLength':
            val = len(new_idx)
        elif n == 'bcDocSymbolOffset':
            val = sym_off_new
        elif n == 'bcDocSymbolLength':
            val = len(symtab_raw)
        elif n == 'bcFCapabilitiesOffset':
            val = cap_off_new
        elif n == 'bcFCapabilitiesLength':
            val = len(caps_raw)
        ci_nv.append((fid, val))
    ci_raw = encode(ci_nv)
    gen_off_new = ci_off_new + len(ci_raw)
    hl_new = gen_off_new + len(gen_raw)
    head = (b'CONT' + d[4:6] + struct.pack('<III', hl_new, ci_off_new, len(ci_raw)))
    out = bytearray(head) + new_idx + symtab_raw + caps_raw + ci_raw + gen_raw
    for _, _, payload in out_ents:
        out += payload
    op = path + '.patched'
    open(op, 'wb').write(bytes(out))
    print(f'写出: {op} (hl {hl}->{hl_new})')
    return op


if __name__ == '__main__':
    patch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
