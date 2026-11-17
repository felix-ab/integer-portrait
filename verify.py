#!/usr/bin/env python3
"""Four evaluations of the same expression, none of them using the generator:

 1. expression.tex, the LaTeX itself, read by the small parser in check.py (standard library only);
 2. expression.tex again, with no parser of ours: its symbols are replaced one for one by SymPy
    syntax (a text substitution) and SymPy, a general computer-algebra system, evaluates the result;
 3. expression.txt, the expression on one line, with the small exact evaluator in this file;
 4. expression.txt again, with SymPy.

All four must equal value.txt. If the tone target is present (it is derived from the source
photograph, which is not in the repository), the typeset page is also compared with it."""
import json, os, re, subprocess
from fractions import Fraction

src = open('expression.txt').read()
stored = int(open('value.txt').read())
st = json.load(open('stats.json'))
print('expression.txt: %d characters, %d lines of sums, %d delimiter strokes, %d numerals, %d integrals' % (
    len(src), st['lines'], st['strokes'], st['numerals'], st['ints']))
used = sorted(set(re.findall(r'[A-Za-z_]+', src)))
print('names used in the expression:', ', '.join(used))


# ---- 1. the LaTeX source itself
import check
p = check.Parser(check.tokens('expression.tex'))
v0 = p.factor()
assert p.i == len(p.t)
print('1. LaTeX (expression.tex) parsed by check.py       : integer of %d digits; equals value.txt: %s' % (len(str(v0)), v0 == stored))
p = check.Parser(check.tokens('portrait.tex'))
assert p.factor() == stored, 'portrait.tex and expression.tex differ'

# ---- 2. the LaTeX again, by substitution; SymPy does the reading and the arithmetic
import sympy
tex = open('expression.tex').read()
assert '-' not in tex and '%' not in tex and '/' not in tex
tex = re.sub(r'\\vrule height[\d.]+bp depth[\d.]+bp width0pt|\\kern[\d.]+bp|\\left|\\right|\\,', ' ', tex)   # layout
breaks = re.findall(r'\\\\\s*&\s*(\S)', tex)
assert breaks and set(breaks) == {'+'}                                   # every line after the first begins with +
tex = re.sub(r'&|\\\\|\\(?:begin|end)\{aligned\}', ' ', tex)             # so a broken sum is simply  a + b + c
integrals = []
def integral(m):
    f = re.sub(r'(\d)([a-z])', r'\1*\2', m[3].strip() or '1')            # 2x means 2*x; no integrand means 1
    integrals.append(sympy.integrate(sympy.sympify(f), (sympy.Symbol(m[4]), int(m[1]), int(m[2]))))
    return ' I%d ' % (len(integrals) - 1)
tex = re.sub(r'\\int_\{(\d+)\}\^\{(\d+)\}([^\\]*)\\mathrm\{d\}([a-z])', integral, tex)
for a, b in ((r'\lfloor', ' floor( '), (r'\rfloor', ' ) '), (r'\lceil', ' ceiling( '), (r'\rceil', ' ) '),
             ('[', ' ( '), (']', ' ) '), (r'\cdot', ' * ')):
    tex = tex.replace(a, b)
assert '\\' not in tex, 'a command that was not accounted for'
out = []
for t in tex.split():                                                    # adjacent factors are multiplied
    begins = t[0].isdigit() or t[0] == 'I' or t.endswith('(')
    if out and begins and (out[-1][0].isdigit() or out[-1][0] == 'I' or out[-1] == ')'):
        assert not (t[0].isdigit() and out[-1][0].isdigit()), 'two integers side by side'
        out.append('*')
    out.append(t)
ns = dict(floor=sympy.floor, ceiling=sympy.ceiling, __builtins__={})
ns.update({'I%d' % i: val for i, val in enumerate(integrals)})
v00 = eval(' '.join(out), ns)
assert sympy.Integer(v00).is_Integer and len(integrals) == st['ints']
v00 = int(v00)
print('2. LaTeX (expression.tex) by substitution, SymPy %s: integer of %d digits; equals value.txt: %s' % (
    sympy.__version__, len(str(v00)), v00 == stored))

# ---- 3. a self-contained exact evaluator of the one-line form
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
print('3. one-line form, own exact evaluator       : integer of %d digits; equals value.txt: %s' % (len(str(v1)), v1 == stored))

# ---- 4. SymPy on the one-line form
ns = dict(floor=sympy.floor, ceiling=sympy.ceiling, integrate=sympy.integrate)
ns.update({n: sympy.Symbol(n) for n in 'xtuys'})
v2 = eval(src, ns)
assert sympy.Integer(v2).is_Integer
v2 = int(v2)
print('4. one-line form, SymPy %-20s: integer of %d digits; equals value.txt: %s' % (sympy.__version__, len(str(v2)), v2 == stored))
assert v0 == v00 == v1 == v2 == stored and isinstance(v0, int)

# ---- 5. the page against the tone that was asked for (only with the source photograph's tone map)
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
        print('5. page vs requested tone, blurred over %d bp: correlation %.3f, rms ink error %.3f' % (
            sg, np.corrcoef(a.ravel(), b.ravel())[0, 1], np.sqrt(((a - b) ** 2).mean())))
else:
    print('5. tone comparison skipped (needs target.npy, written by build.py from the source photograph)')
