#!/usr/bin/env python3
"""Independent checks on the structured portrait.
 1. expression.txt (the linear form of what is typeset) is evaluated from scratch with
    exact integer arithmetic and must equal value.txt.
 2. If the tone target is present (it is derived from the source photograph, which is not
    in the repository), the typeset page is compared with the tone that was asked for."""
import subprocess, json, os, numpy as np
from fractions import Fraction
from math import floor, ceil
from PIL import Image
from scipy.ndimage import gaussian_filter
Image.MAX_IMAGE_PIXELS = None


def N1(rows):                       # || column ||_1 : the sum of the absolute values of the rows
    return sum(abs(r) for r in rows)


def Int(a, b, f):                   # exact integral of a polynomial of degree <= 3 (Simpson's rule is exact)
    a, b = Fraction(a), Fraction(b)
    v = (b - a) / 6 * (f(a) + 4 * f((a + b) / 2) + f(b))
    assert v.denominator == 1
    return int(v)


src = open('expression.txt').read()
val = eval(src, dict(N1=N1, Int=Int, abs=abs, floor=floor, ceil=ceil))
stored = int(open('value.txt').read())
st = json.load(open('stats.json'))
print('1. expression.txt: %d characters; %d stacks, %d integral signs, %d strokes, %d numerals' % (
    len(src), src.count('N1('), src.count('Int('), st['strokes'], st['numerals']))
print('   evaluated independently: an integer of %d digits; equal to value.txt: %s' % (len(str(val)), val == stored))
print('   type %s, exact (no floating point anywhere)' % type(val).__name__)
assert val == stored and isinstance(val, int)

if os.path.exists('target.npy') and os.path.exists('portrait.pdf'):
    os.makedirs('work', exist_ok=True)
    subprocess.run(['pdftoppm', '-png', '-r', '432', '-singlefile', 'portrait.pdf', 'work/p432'], check=True)
    page = 1 - np.asarray(Image.open('work/p432.png').convert('L').resize((1080, 973), Image.BOX), dtype=np.float64) / 255
    tgt = np.load('target.npy')
    for sg in (6, 12):
        a, b = gaussian_filter(page, sg), gaussian_filter(tgt, sg)
        print('2. page vs requested tone, blurred over %d bp: correlation %.3f, rms ink error %.3f' % (
            sg, np.corrcoef(a.ravel(), b.ravel())[0, 1], np.sqrt(((a - b) ** 2).mean())))
    print('   mean ink requested %.3f, printed %.3f; lightest region %.3f, darkest %.3f' % (
        tgt.mean(), page.mean(), gaussian_filter(page, 12).min(), gaussian_filter(page, 12).max()))
else:
    print('2. tone comparison skipped (needs target.npy, written by build.py from the source photograph)')
txt = subprocess.run(['pdftotext', 'portrait.pdf', '-'], capture_output=True, text=True).stdout
print('3. glyphs in the PDF text layer: %d digits (numerals %d + limits, indices and integrands)' % (sum(c.isdigit() for c in txt), st['numerals']))
