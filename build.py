#!/usr/bin/env python3
"""
The portrait as ONE expression that evaluates to an integer.

One font, one weight (New Computer Modern). Tone comes only from structure:

  white      space between factors
  lightest   long integral signs, far apart
  light      long bracket pairs around a numeral
  mid        runs of numerals (1 and 7 are light, 6 and 9 are dark)
  dark       numerals wrapped in ever deeper nests of brackets

Where the picture is vertically even, the strokes run the full height of the
region (a "leaf"); elsewhere the expression is set in fine rows. Stacked rows
are a column vector inside || . ||_1 (its value is the sum of the rows); things
side by side are multiplied.

Needs a photograph as source.png (not included in the repository).
Writes body.tex (LaTeX), value.tex, expression.txt (linear form) and value.txt.
"""
import sys, json, math, random
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label
from skimage import exposure

args = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
W, RP = 1080, 7                       # page width (bp), row pitch (bp)
ROWS = 139; H = ROWS * RP
CWc = 5; COLS = W // CWc              # coarse cells used only to slice the picture
FS = 9.4; ADV = FS / 2                # type size and numeral advance
TH = 0.5                              # stroke thickness of every delimiter
DL = 1.0                              # pitch of nested delimiters
FH = 6.4                              # height of a delimiter in a fine row
GL, GR = 2.0, 5.5                     # gutters of a stack: || on the left, ||_1 on the right
HI = float(args.get('hi', 0.43))      # darkest ink the structures can reach
GAMMA = float(args.get('gamma', 0.92))
PHI = float(args.get('phi', 97.0)); PLO = float(args.get('plo', 1.0))
MIX = float(args.get('mix', 0.15)); USM = float(args.get('usm', 0.8))
TOL = float(args.get('tol', 0.035))   # how even a column must be to become a long stroke
MINH = int(args.get('minh', 5)); MINW = int(args.get('minw', 4))
LIGHT = float(args.get('light', 0.11)); DARK = float(args.get('dark', 0.30))   # long strokes only for ground this light or this dark
MINA_L = int(args.get('mina_l', 36)); MINA_D = int(args.get('mina_d', 400))
KMAX = 14; KFINE = int(args.get('kfine', 7))
random.seed(int(args.get('seed', 7)))

cal = json.load(open('calib.json'))
INK = {d: cal[str(d)]['ink'] * (FS / 10) ** 2 for d in range(10)}        # bp^2 per numeral
INK_DOT = cal['\\cdot']['ink'] * (FS / 10) ** 2
INK_PLUS = cal['+']['ink'] * (FS / 10) ** 2
BY_INK = sorted(range(1, 10), key=lambda d: INK[d])


# ------------------------------------------------------------------ target
def target():
    g = np.asarray(Image.open('source.png').convert('L'), dtype=np.float64) / 255
    g[0:22, 560:640] = np.minimum(g[0:22, 560:640], np.median(g[0:22, 640:700]))   # the "EDIT" overlay
    v = MIX * exposure.equalize_adapthist(g, kernel_size=g.shape[0] // 8, clip_limit=0.012) + (1 - MIX) * g
    v = v + USM * (v - gaussian_filter(v, 4.0))
    lo, hi = np.percentile(v, [PLO, PHI])
    v = np.clip((v - lo) / (hi - lo), 0, 1)
    ref = np.asarray(Image.fromarray((v * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS), dtype=np.float64) / 255
    return (1 - ref) ** GAMMA * HI


T = target()
Tc = gaussian_filter(T.reshape(ROWS, RP, COLS, CWc).mean(axis=(1, 3)), 0.6)
np.save('target.npy', T)


# ------------------------------------------------------------------ slicing
SAT = np.zeros((ROWS + 1, COLS + 1)); SAT[1:, 1:] = np.cumsum(np.cumsum(Tc, axis=0), axis=1)


def ground(mask):
    """the part of a tone class that reaches the edge of the picture (sky, sea), not islands inside the figure"""
    lab, n = label(mask)
    edge = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    return np.isin(lab, [i for i in edge if i])


GROUND = ground(Tc < LIGHT) | ground(Tc > DARK * 0.95)


def bmean(a, b, c, d):
    return (SAT[b, d] - SAT[a, d] - SAT[b, c] + SAT[a, c]) / ((b - a) * (d - c))


def largest(r0, r1, c0, c1):
    """largest block of cells in which every column is vertically even"""
    best, bs = None, 0
    for a in range(r0, r1 - MINH + 1):
        mn = Tc[a, c0:c1].copy(); mx = mn.copy(); gr = GROUND[a, c0:c1].copy()
        for b in range(a + 1, r1 + 1):
            if b - 1 > a:
                np.minimum(mn, Tc[b - 1, c0:c1], out=mn); np.maximum(mx, Tc[b - 1, c0:c1], out=mx)
                gr &= GROUND[b - 1, c0:c1]
            h = b - a
            if h < MINH:
                continue
            ok = ((mx - mn) <= TOL) & gr
            if not ok.any():
                break
            # longest run of ok
            z = np.concatenate(([0], ok.astype(int), [0])); d = np.diff(z)
            st = np.nonzero(d == 1)[0]; en = np.nonzero(d == -1)[0]
            for k in np.argsort(st - en)[:3]:                      # the widest few runs
                w = int(en[k] - st[k])
                if w < MINW:
                    break
                m = bmean(a, b, c0 + int(st[k]), c0 + int(en[k]))
                if (m < LIGHT and w * h >= MINA_L) or (m > DARK and w * h >= MINA_D):
                    s = w * h * h ** 0.5
                    if s > bs:
                        bs, best = s, (a, b, c0 + int(st[k]), c0 + int(en[k]))
    return best


def carve(r0, r1, c0, c1):
    if r1 - r0 < MINH or c1 - c0 < MINW:
        return dict(t='fine', r=(r0, r1), c=(c0, c1))
    b = largest(r0, r1, c0, c1)
    if b is None:
        return dict(t='fine', r=(r0, r1), c=(c0, c1))
    a0, a1, b0, b1 = b
    mid = []
    if b0 > c0: mid.append(carve(a0, a1, c0, b0))
    mid.append(dict(t='leaf', r=(a0, a1), c=(b0, b1)))
    if b1 < c1: mid.append(carve(a0, a1, b1, c1))
    midn = mid[0] if len(mid) == 1 else dict(t='row', r=(a0, a1), c=(c0, c1), ch=mid)
    parts = []
    if a0 > r0: parts.append(carve(r0, a0, c0, c1))
    parts.append(midn)
    if a1 < r1: parts.append(carve(a1, r1, c0, c1))
    return parts[0] if len(parts) == 1 else dict(t='stack', r=(r0, r1), c=(c0, c1), ch=parts)


def entries(node):
    """a stack's bands: list of (r0, r1, [items left to right])"""
    if node['t'] == 'stack':
        out = []
        for ch in node['ch']:
            out += entries(ch)          # a stack inside a stack of the same width simply continues it
        return out
    if node['t'] == 'fine':
        return [(r, r + 1, [dict(t='seg', r=(r, r + 1), c=node['c'])]) for r in range(*node['r'])]
    if node['t'] == 'leaf':
        return [(node['r'][0], node['r'][1], [node])]
    items = []
    for ch in node['ch']:
        items += as_items(ch)
    return [(node['r'][0], node['r'][1], items)]


def as_items(node):
    """a node used as a factor inside a row"""
    if node['t'] == 'leaf':
        return [node]
    if node['t'] == 'row':
        out = []
        for ch in node['ch']:
            out += as_items(ch)
        return out
    if node['t'] == 'fine' and node['r'][1] - node['r'][0] == 1:
        return [dict(t='seg', r=node['r'], c=node['c'])]
    return [dict(t='stk', r=node['r'], c=node['c'], ent=entries(node))]


root = dict(t='stk', r=(0, ROWS), c=(0, COLS), ent=entries(carve(0, ROWS, 0, COLS)))

# ------------------------------------------------------------------ tone bookkeeping
cum = np.concatenate([np.zeros((ROWS, 1)), np.cumsum(T.reshape(ROWS, RP, W).mean(axis=1), axis=1)], axis=1)


def want(r0, r1, xa, xb):
    """target ink (bp^2) in rows r0..r1 between xa and xb"""
    xs = np.arange(W + 1)
    tot = 0.0
    for r in range(r0, r1):
        tot += np.interp(xb, xs, cum[r]) - np.interp(xa, xs, cum[r])
    return tot * RP


DELIMS = ['bar', 'brk', 'flr', 'cel']


def kinds(k):
    out, prev = [], None
    for _ in range(k):
        c = random.choice([d for d in DELIMS if d != prev]); out.append(c); prev = c
    return out


INTS = {  # width class: (lower, upper, integrand tex, linear form, value)
    1: [(0, 1, '', '1', 1), (0, 2, '', '1', 2), (1, 4, '', '1', 3), (2, 7, '', '1', 5), (3, 9, '', '1', 6), (1, 8, '', '1', 7)],
    2: [(0, 2, 'x', 'x', 2), (1, 3, 'x', 'x', 4), (0, 4, 'x', 'x', 8), (2, 4, 'x', 'x', 6), (1, 5, 'x', 'x', 12)],
    3: [(0, 1, '2x', '2*x', 1), (1, 2, '2x', '2*x', 3), (0, 3, '2x', '2*x', 9), (2, 3, '2x', '2*x', 5), (1, 4, '2x', '2*x', 15)],
    4: [(0, 1, '3x^{2}', '3*x**2', 1), (0, 2, '3x^{2}', '3*x**2', 8), (1, 2, '3x^{2}', '3*x**2', 7), (1, 3, '3x^{2}', '3*x**2', 26)],
}


def fill_leaf(xa, xb, r0, r1):
    """long strokes over the whole height of a leaf; one line of content at mid height"""
    Hl = (r1 - r0) * RP - 1.2
    units, x, debt = [], xa + 0.8, 0.0
    while x < xb - 7.5:
        span = min(12.0, xb - x)
        rho = max(0.0, (want(r0, r1, x, x + span) + debt) / (span * (r1 - r0) * RP))
        x0 = x
        if rho < 0.004:
            x += 6.0
        elif TH / rho >= 12.0 and (TH / rho >= 17.0 or random.random() < 0.75):   # sparse: an integral sign
            p = min(TH / rho, 44.0, xb - x - 0.5)
            if p < 12.0:
                x += 6.0
            else:
                cls = 4 if p >= 31 else 3 if p >= 25 else 2 if p >= 19 else 1
                units.append(dict(u='int', x=x, w=p, spec=random.choice(INTS[cls]), var=random.choice('xxxtuys'), ink=TH * Hl))
                x += p
        elif TH / rho >= 6.3 and x + 2 * 6.3 < xb:           # a pair of strokes around a numeral
            q = min(TH / rho, (xb - x - 1.0) / 1.0)
            q = max(q, 6.3)
            if x + q + 0.6 > xb:
                break
            units.append(dict(u='nest', x=x, k=1, d=random.choice(range(1, 10)), kinds=kinds(1), inner=q - TH, ink=2 * TH * Hl))
            x += 2 * q
        else:                                                # nested strokes
            inner = 5.8
            k = inner * rho / max(2 * TH - 2 * DL * rho, 1e-3)
            k = int(max(1, min(KMAX, round(k))))
            w = inner + 2 * k * DL
            while k > 1 and x + w + 0.3 > xb:
                k -= 1; w = inner + 2 * k * DL
            if x + w + 0.3 > xb:
                break
            units.append(dict(u='nest', x=x, k=k, d=random.choice(range(1, 10)), kinds=kinds(k), inner=inner, ink=2 * k * TH * Hl))
            x += max(w + 0.6, min(2 * k * TH / max(rho, 1e-3), w + 6.0))
        got = units[-1]['ink'] if units and units[-1]['x'] == x0 else 0.0
        debt += want(r0, r1, x0, min(x, xb)) - got
        debt = max(-3 * Hl, min(3 * Hl, debt))
    return units


def fill_seg(xa, xb, r):
    """one fine row: numerals, dots, plus signs, and numerals in nests of brackets"""
    units, x, debt, prev = [], xa + 0.3, 0.0, 'start'
    cell = ADV * RP
    lo_run, hi_run = INK[BY_INK[0]] / cell, INK[BY_INK[-1]] / cell
    while x < xb - ADV - 0.2:
        span = min(10.0, xb - x)
        loc = want(r, r + 1, x, x + span) / (span * RP)      # the local tone picks the kind of structure ...
        rho = max(0.0, loc + debt / (span * RP))             # ... the running error only fine-tunes it
        if loc < lo_run * 0.93: rho = min(rho, lo_run * 0.92)
        elif loc <= hi_run * 1.04: rho = min(max(rho, lo_run * 0.94), hi_run * 1.03)
        else: rho = max(rho, hi_run * 1.05)
        x0 = x
        if rho < lo_run * 0.93:                              # lighter than a run of 1s: spaced small factors
            if prev in ('num', 'nest') and x + 3.0 + ADV < xb - 0.3:
                d = BY_INK[0] if rho < 0.6 * lo_run else random.choice(BY_INK[:2])
                plus = random.random() < 0.08
                op = INK_PLUS if plus else INK_DOT
                w = (INK[d] + op) / (RP * max(rho, 0.012)) - ADV
                w = max(7.4 if plus else 2.6, min(w, 26.0, xb - x - ADV - 0.4))
                units.append(dict(u='op', x=x, w=w, op='+' if plus else '.', ink=op)); x += w; prev = 'op'
            else:
                d = BY_INK[0] if rho < 0.6 * lo_run else random.choice(BY_INK[:2])
                units.append(dict(u='num', x=x, d=d, ink=INK[d], first=prev != 'num')); x += ADV; prev = 'num'
        elif rho <= hi_run * 1.04:                           # a run of numerals chosen by weight
            cand = [d for d in range(10) if not (d == 0 and prev != 'num')]
            near = sorted(cand, key=lambda d: abs(INK[d] / cell - rho))
            pool = [d for d in near if abs(INK[d] / cell - rho) <= abs(INK[near[0]] / cell - rho) + 0.012]
            d = random.choice(pool)
            units.append(dict(u='num', x=x, d=d, ink=INK[d], first=prev != 'num')); x += ADV; prev = 'num'
        else:                                                # darker: numeral inside k nested delimiters
            d = random.choice(BY_INK[-4:])
            k = (rho * RP * (ADV + 0.5) - INK[d]) / max(2 * TH * FH - 2 * DL * RP * rho, 0.05)
            k = int(max(1, min(KFINE, round(k))))
            w = ADV + 0.5 + 2 * k * DL
            while k > 1 and x + w > xb - 0.2:
                k -= 1; w = ADV + 0.5 + 2 * k * DL
            if x + w > xb - 0.2:
                d = BY_INK[-1]
                units.append(dict(u='num', x=x, d=d, ink=INK[d], first=prev != 'num')); x += ADV; prev = 'num'
            else:
                units.append(dict(u='nest', x=x, k=k, d=d, kinds=kinds(k), inner=ADV + 0.5 - TH, ink=2 * k * TH * FH + INK[d]))
                x += w + 0.25; prev = 'nest'
        debt += want(r, r + 1, x0, x) - units[-1]['ink']
        debt = max(-1.5 * cell, min(1.5 * cell, debt))
    while units and units[-1]['u'] == 'op':
        units.pop()
    if not units:
        units.append(dict(u='num', x=(xa + xb) / 2 - ADV / 2, d=1, ink=INK[1], first=True))
    return units


# ------------------------------------------------------------------ layout + fill
stats = dict(leaf=0, seg=0, stk=0, strokes=0, numerals=0, ints=0, longest=0.0)


def lay(stk, xa, xb):
    stk['x'] = (xa, xb); stats['stk'] += 1
    ia, ib = xa + GL, xb - GR
    for (r0, r1, items) in stk['ent']:
        for it in items:
            a, b = max(it['c'][0] * CWc, ia), min(it['c'][1] * CWc, ib)
            if it['t'] == 'stk':
                lay(it, a, b)
            elif it['t'] == 'leaf':
                it['x'] = (a, b); it['units'] = fill_leaf(a, b, r0, r1); stats['leaf'] += 1
                stats['longest'] = max(stats['longest'], (r1 - r0) * RP)
            else:
                it['x'] = (a, b); it['units'] = fill_seg(a, b, r0); stats['seg'] += 1
        for p_, q_ in zip(items, items[1:]):                              # two numerals meeting across a seam: put a dot between
            if p_['t'] == 'seg' and q_['t'] == 'seg' and p_['units'] and q_['units'] \
                    and p_['units'][-1]['u'] == 'num' and q_['units'][0]['u'] == 'num':
                last = p_['units'][-1]
                p_['units'][-1] = dict(u='op', x=last['x'], w=ADV, op='.', ink=INK_DOT)
                if len(p_['units']) > 1 and p_['units'][-2]['u'] == 'op':
                    p_['units'].pop(-2)
        if not any(it['t'] == 'stk' or it['units'] for it in items):      # a band may not be empty
            it = items[len(items) // 2]
            it['units'].append(dict(u='nest', x=(it['x'][0] + it['x'][1]) / 2 - 3.5, k=1, d=1, kinds=['bar'], inner=6.0, ink=0))


lay(root, 0.0, float(W))


# ------------------------------------------------------------------ value and linear form
def band_tokens(items):
    toks = []
    for it in items:
        if it['t'] == 'stk':
            toks.append(('v', value(it), lin(it)))
            continue
        run = ''
        for u in it['units']:
            if u['u'] == 'num':
                run += str(u['d']); continue
            if run:
                toks.append(('v', int(run), run)); run = ''
            if u['u'] == 'op':
                toks.append(('+',) if u['op'] == '+' else ('*',))
            elif u['u'] == 'int':
                lo, up, _, f, v = u['spec']; toks.append(('v', v, 'Int(%d,%d,lambda %s: %s)' % (lo, up, u['var'], f.replace('x', u['var']))))
            else:
                s = str(u['d'])
                for kd in reversed(u['kinds']):
                    s = {'bar': 'abs(%s)', 'brk': '(%s)', 'flr': 'floor(%s)', 'cel': 'ceil(%s)'}[kd] % s
                toks.append(('v', u['d'], s))
        if run:
            toks.append(('v', int(run), run))
    return toks


def band_value(items):
    total, prod = 0, 1
    for tk in band_tokens(items):
        if tk[0] == 'v': prod *= tk[1]
        elif tk[0] == '+': total += prod; prod = 1
    return total + prod


def band_lin(items):
    out, last = '', None
    for tk in band_tokens(items):
        if tk[0] == 'v':
            out += ('*' if last == 'v' else '') + tk[2]; last = 'v'
        elif tk[0] == '+': out += ' + '; last = '+'
        else: out += '*'; last = '*'
    return out


def value(stk):
    return sum(abs(band_value(items)) for (_, _, items) in stk['ent'])


def lin(stk):
    return 'N1([' + ', '.join(band_lin(items) for (_, _, items) in stk['ent']) + '])'


N = value(root)
if 'prime' in args:
    # Make the value prime by swapping ONE numeral for the numeral closest to it in weight
    # (searching from the last row upwards), so the picture does not change.
    import gmpy2
    cands = []

    def collect(stk):
        for (_, _, items) in stk['ent']:
            for it in items:
                if it['t'] == 'stk': collect(it)
                elif it['t'] == 'seg': cands.extend(u for u in it['units'] if u['u'] == 'num')
    collect(root)
    tried, found = 0, False
    for u in reversed(cands):
        old = u['d']
        alts = sorted((d for d in range(0 if not u['first'] else 1, 10) if d != old), key=lambda d: abs(INK[d] - INK[old]))[:2]
        for d in alts:
            u['d'] = d; tried += 1
            M = value(root)
            if M % 2 and gmpy2.is_strong_bpsw_prp(M):
                N, found = M, True; break
        if found:
            print('swapped one numeral %d -> %d' % (old, u['d'])); break
        u['d'] = old
    print('prime search: %d candidates tried, %s' % (tried, 'found' if found else 'none found'))
    assert found and gmpy2.is_prime(N, 40)
else:
    N = value(root)
expr = lin(root)
open('expression.txt', 'w').write(expr + '\n')
open('value.txt', 'w').write(str(N) + '\n')
open('value.tex', 'w').write('\\def\\TheValue{%s}\\def\\TheDigits{%d}\n' % (N, len(str(N))))

# ------------------------------------------------------------------ LaTeX
# Each band of a stack is one running row: \k moves right, strokes are bare rules,
# numerals are plain text. Coordinates are bp from the band's baseline (floor + .3).
BASE = 0.3


def f(x):
    return ('%.2f' % x).rstrip('0').rstrip('.')


class Row:
    def __init__(self):
        self.s, self.cur = [], 0.0

    def go(self, x):
        d = x - self.cur
        if abs(d) > 0.004:
            self.s.append(r'\K{%s}' % f(d))
        self.cur = x

    def stroke(self, kd, side, x, yb, h):
        stats['strokes'] += 1
        self.go(x)
        self.s.append(r'\X%s%s{%s}{%s}' % ({'bar': 'b', 'brk': 'q', 'flr': 'f', 'cel': 'c'}[kd], '' if kd == 'bar' else side,
                                          f(yb - BASE), f(yb - BASE + h)))
        self.cur = x + TH

    def num(self, x, d, lift=0.0):
        stats['numerals'] += 1
        self.go(x)
        self.s.append(str(d) if not lift else r'\Lf{%s}{%d}' % (f(lift), d))
        self.cur = x + ADV


def emit_units(row, units, x0, h, tall):
    for u in units:
        x = u['x'] - x0
        if u['u'] == 'num':
            row.num(x, u['d'])
        elif u['u'] == 'op':
            row.go(x); row.s.append(r'\Op{%s}{%s}' % (f(u['w']), '+' if u['op'] == '+' else r'\cdot')); row.cur = x + u['w']
        elif u['u'] == 'int':
            lo, up, tx, _, _ = u['spec']; stats['ints'] += 1; stats['strokes'] += 1
            row.go(x)
            row.s.append(r'\I{%s}{%s}{%d}{%d}{%s}{%s}{%s}' % (f(0.6 - BASE), f(h - 1.2), lo, up, tx.replace('x', u['var']), f(h / 2 - RP / 2), u['var']))
        else:
            k, hh = u['k'], (h - 1.2 if tall else FH)
            yb = 0.6 if tall else (RP - FH) / 2
            w = u['inner'] + TH + 2 * k * DL
            for i, kd in enumerate(u['kinds']):                    # opening delimiters, outermost first
                row.stroke(kd, 'l', x + i * DL, yb, hh)
            row.num(x + k * DL + (u['inner'] + TH - DL - ADV) / 2 + (DL - TH) / 2 + TH / 2, u['d'], (h / 2 - RP / 2) if tall else 0.0)
            for i in reversed(range(k)):                           # closing delimiters, innermost first
                row.stroke(u['kinds'][i], 'r', x + w - TH - i * DL, yb, hh)


def emit(stk):
    xa, xb = stk['x']; r0, r1 = stk['r']; Hs = (r1 - r0) * RP
    s = [r'\Sb{%s}{%s}' % (f(xb - xa), f(Hs))]
    for (a, b, items) in stk['ent']:
        y0 = (r1 - b) * RP; h = (b - a) * RP
        row = Row()
        for it in items:
            if it['t'] == 'stk':
                row.go(it['x'][0] - xa)
                row.s.append(r'\Ab ' + emit(it) + r'\Ae ')
            else:
                emit_units(row, it['units'], xa, h, it['t'] == 'leaf')
        s.append(r'\Bd{%s}' % f(y0 + BASE) + ''.join(row.s) + '\\Be%\n')
    s.append(r'\Se')
    return ''.join(s)


open('body.tex', 'w').write(emit(root) + '%\n')
digits = len(str(N))
json.dump(dict(stats, value_digits=digits, W=W, H=H), open('stats.json', 'w'))
print('stacks %(stk)d, long-stroke leaves %(leaf)d, fine rows %(seg)d' % stats)
print('strokes %(strokes)d (integral signs %(ints)d), numerals %(numerals)d, longest stroke %(longest).0f bp' % stats)
print('the expression evaluates to an integer of %d digits: %s...%s' % (digits, str(N)[:12], str(N)[-12:]))

if 'debug' in args:
    def walk(stk, depth=0):
        for (a, b, items) in stk['ent']:
            for it in items:
                if it['t'] == 'stk':
                    print('  ' * depth + 'stack rows %s x %s' % (it['r'], it['x'])); walk(it, depth + 1)
                elif it['t'] == 'leaf':
                    ks = [u['k'] for u in it['units'] if u['u'] == 'nest']
                    print('  ' * depth + 'leaf rows %d-%d x %.0f-%.0f: %d units, k max %s, ints %d, mean target %.3f' % (
                        a, b, it['x'][0], it['x'][1], len(it['units']), max(ks) if ks else '-', sum(u['u'] == 'int' for u in it['units']),
                        T[a * RP:b * RP, int(it['x'][0]):int(it['x'][1])].mean()))
    walk(root)
    print('target ink by region:')
    for name, (y0, y1, x0, x1) in dict(sky_left=(40, 280, 20, 200), forehead=(120, 200, 400, 620), cheek=(330, 420, 380, 480),
                                       sea_left=(370, 430, 30, 200), headphone=(250, 330, 250, 300), hoodie=(700, 850, 200, 400)).items():
        print('  %-10s %.3f' % (name, T[y0:y1, x0:x1].mean()))
