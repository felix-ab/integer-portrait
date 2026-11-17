#!/usr/bin/env python3
"""Evaluate expression.txt, the typeset expression written on one line, twice and
independently of the generator:

 1. with the small exact evaluator in this file (integers, and polynomials with
    rational coefficients for the integrals);
 2. with SymPy, a general computer-algebra system, reading the very same text.

The text uses nothing but: decimal integers, *, +, parentheses, floor(), ceiling(),
and integrate(f, (x, a, b)) for a definite integral. Both results must equal value.txt.

If the tone target is present (it is derived from the source photograph, which is not
in the repository), the typeset page is also compared with the tone that was asked for."""
import json, os, re, subprocess
from fractions import Fraction

src = open('expression.txt').read()
stored = int(open('value.txt').read())
st = json.load(open('stats.json'))
print('expression.txt: %d characters, %d lines of sums, %d delimiter strokes, %d numerals, %d integrals' % (
    len(src), st['lines'], st['strokes'], st['numerals'], st['ints']))
used = sorted(set(re.findall(r'[A-Za-z_]+', src)))
print('names used in the expression:', ', '.join(used))


# ---- 1. a self-contained exact evaluator
class Poly:
    """a polynomial in one variable with rational coefficients"""
    def __init__(self, c): self.c = [Fraction(v) for v in c]
    def __mul__(self, o):
        o = o if isinstance(o, Poly) else Poly([o])
        r = [Fraction(0)] * (len(self.c) + len(o.c) - 1)
        for i, a in enumerate(self.c):
            for j, b in enumerate(o.c):
                r[i + j] += a * b
        return Poly(r)
    __rmul__ = __mul__
    def __pow__(self, n):
        r = Poly([1])
        for _ in range(n): r = r * self
        return r
    def antiderivative_at(self, x):
        return sum(a * Fraction(x) ** (k + 1) / (k + 1) for k, a in enumerate(self.c))


def my_integrate(f, lim):
    _, a, b = lim
    f = f if isinstance(f, Poly) else Poly([f])
    v = f.antiderivative_at(b) - f.antiderivative_at(a)
    assert v.denominator == 1
    return int(v)


def my_round(x):                     # floor and ceiling of an integer are that integer
    assert isinstance(x, int)
    return x


X = Poly([0, 1])
v1 = eval(src, dict(floor=my_round, ceiling=my_round, integrate=my_integrate, x=X, t=X, u=X, y=X, s=X))
print('1. own exact evaluator : integer of %d digits; equals value.txt: %s' % (len(str(v1)), v1 == stored))

# ---- 2. SymPy
import sympy
ns = dict(floor=sympy.floor, ceiling=sympy.ceiling, integrate=sympy.integrate)
ns.update({n: sympy.Symbol(n) for n in 'xtuys'})
v2 = eval(src, ns)
assert sympy.Integer(v2).is_Integer
v2 = int(v2)
print('2. SymPy %-14s: integer of %d digits; equals value.txt: %s' % (sympy.__version__, len(str(v2)), v2 == stored))
assert v1 == stored and v2 == stored and isinstance(v1, int)

# ---- 3. the page against the tone that was asked for (only with the source photograph's tone map)
if os.path.exists('target.npy') and os.path.exists('portrait.pdf'):
    import numpy as np
    from PIL import Image
    from scipy.ndimage import gaussian_filter
    Image.MAX_IMAGE_PIXELS = None
    os.makedirs('work', exist_ok=True)
    subprocess.run(['pdftoppm', '-png', '-r', '432', '-singlefile', 'portrait.pdf', 'work/p432'], check=True)
    page = 1 - np.asarray(Image.open('work/p432.png').convert('L').resize((1080, 973), Image.BOX), dtype=np.float64) / 255
    tgt = np.load('target.npy')
    for sg in (6, 12):
        a, b = gaussian_filter(page, sg), gaussian_filter(tgt, sg)
        print('3. page vs requested tone, blurred over %d bp: correlation %.3f, rms ink error %.3f' % (
            sg, np.corrcoef(a.ravel(), b.ravel())[0, 1], np.sqrt(((a - b) ** 2).mean())))
else:
    print('3. tone comparison skipped (needs target.npy, written by build.py from the source photograph)')
