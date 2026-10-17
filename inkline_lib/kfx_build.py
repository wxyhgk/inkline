"""md -> EPUB -> 白底 -> boko KFX -> 官方式行内修复，一键链。"""
import os
import shutil
import subprocess
import tempfile
import zipfile

from PIL import Image


def _white_bg(epub_in, epub_out):
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(epub_in) as z:
        z.extractall(tmp)
    n = 0
    for root, _, files in os.walk(tmp):
        for f in files:
            if not f.endswith('.png'):
                continue
            p = os.path.join(root, f)
            im = Image.open(p)
            if im.mode in ('RGBA', 'LA'):
                bg = Image.new('RGB', im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                bg.save(p)
                n += 1
    # 重打包（mimetype 首个不压缩）
    if os.path.exists(epub_out):
        os.remove(epub_out)
    cwd = os.getcwd()
    os.chdir(tmp)
    subprocess.run(['zip', '-q', '-0', '-X', epub_out, 'mimetype'], check=True)
    subprocess.run(['zip', '-q', '-rDX9', epub_out, '.', '-x', 'mimetype'], check=True)
    os.chdir(cwd)
    shutil.rmtree(tmp, ignore_errors=True)
    return n


def epub_to_kfx(epub_path, kfx_path):
    """EPUB -> KFX（boko + 行内修复）。返回 kfx 路径。"""
    from .kfx_patch import patch as kfx_inline_fix
    tmp = tempfile.mkdtemp()
    try:
        w = os.path.join(tmp, 'w.epub')
        n = _white_bg(epub_path, w)
        print(f'white-bg: {n} png')
        raw = os.path.join(tmp, 'raw.kfx')
        r = subprocess.run(['boko', 'convert', w, raw],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f'boko failed: {r.stderr[-500:]}')
        print('boko kfx ok')
        patched = kfx_inline_fix(raw, w)
        shutil.move(patched, kfx_path)
        print(f'kfx: {kfx_path}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return kfx_path
