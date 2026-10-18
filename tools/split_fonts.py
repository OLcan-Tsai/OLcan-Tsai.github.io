"""Split LXGW WenKai into unicode-range woff2 chunks and convert Maple Mono to woff2.
Usage: python3 split_fonts.py <site_root>   (writes <site_root>/fonts/ and prints the @font-face CSS)"""
import glob, html, os, re, sys
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options

root = sys.argv[1]
src = os.path.join(root, 'fonts/LXGWWenKai-Regular.ttf')
out_dir = os.path.join(root, 'fonts/lxgw')
os.makedirs(out_dir, exist_ok=True)

cmap = TTFont(src).getBestCmap()
all_cps = set(cmap)

def gb2312(lo, hi):
    s = set()
    for b1 in range(lo, hi + 1):
        for b2 in range(0xA1, 0xFF):
            try: s.add(ord(bytes([b1, b2]).decode('gb2312')))
            except UnicodeDecodeError: pass
    return s

def is_cjk(cp):
    return cp >= 0x2E80

# Characters actually used on the site go in the common chunk too
site = set()
for f in glob.glob(os.path.join(root, '**/*.html'), recursive=True):
    text = re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', open(f, encoding='utf-8').read(), flags=re.S)
    site |= {ord(c) for c in html.unescape(text)}

latin = {cp for cp in all_cps if not is_cjk(cp)}
common = (gb2312(0xB0, 0xD7) | site | set(range(0x3000, 0x3040)) | set(range(0xFF00, 0xFFF0))) & all_cps - latin
rest = sorted(all_cps - latin - common)

chunks = [('latin', latin), ('common', common)]
size = 1500
for i in range(0, len(rest), size):
    chunks.append((f'ext{i // size:02d}', set(rest[i:i + size])))

def ranges(cps):
    cps = sorted(cps); out = []; start = prev = cps[0]
    for cp in cps[1:] + [None]:
        if cp is not None and cp == prev + 1:
            prev = cp; continue
        out.append(f'U+{start:X}' if start == prev else f'U+{start:X}-{prev:X}')
        if cp is not None: start = prev = cp
    return ', '.join(out)

def subset(path, cps, dest):
    opts = Options(); opts.flavor = 'woff2'; opts.layout_features = ['*']; opts.name_IDs = ['*']
    font = TTFont(path)
    s = Subsetter(opts); s.populate(unicodes=cps); s.subset(font)
    font.flavor = 'woff2'; font.save(dest)

css = []
for name, cps in chunks:
    dest = os.path.join(out_dir, f'{name}.woff2')
    subset(src, cps, dest)
    print(f'{name}: {len(cps)} chars, {os.path.getsize(dest) // 1024} KB', file=sys.stderr)
    css.append("@font-face {\n  font-family: 'LXGW WenKai';\n"
               f"  src: url('/fonts/lxgw/{name}.woff2') format('woff2');\n"
               "  font-display: swap;\n  font-weight: 400;\n  font-style: normal;\n"
               f"  unicode-range: {ranges(cps)};\n}}")

maple = os.path.join(root, 'fonts/MapleMono-Medium.ttf')
mdest = os.path.join(root, 'fonts/MapleMono-Medium.woff2')
subset(maple, set(TTFont(maple).getBestCmap()), mdest)
print(f'MapleMono: {os.path.getsize(mdest) // 1024} KB', file=sys.stderr)
print('\n\n'.join(css))
