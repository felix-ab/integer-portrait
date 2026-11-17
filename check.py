#!/usr/bin/env python3
"""Evaluate the expression in portrait.tex directly from its LaTeX source.

    python3 check.py portrait.tex        (or:  python3 check.py expression.tex)

It takes the expression (the text between the two marker lines, or the whole file if
there are none), discards what only positions things (\\kern, the zero-width \\vrule
struts, \\, , & , \\left, \\right) and
evaluates what remains with exact integer arithmetic. The grammar is the whole
of the notation used:

    sum      :  \\begin{aligned} & line  \\\\ & + line  \\\\ & + line ...  \\end{aligned}
    line     :  product + product + ...
    product  :  factor factor ...            adjacent factors, sometimes with \\cdot
    factor   :  an integer
             |  [ line-or-sum ]                grouping
             |  \\lfloor line-or-sum \\rfloor    floor
             |  \\lceil  line-or-sum \\rceil     ceiling
             |  \\int_{a}^{b} c x^{n} \\mathrm{d}x     definite integral of a monomial

Standard library only. It then compares the result with the value printed in
the file, and evaluates the one-line form of the expression as a second check.
"""
import re
import sys
from fractions import Fraction
from math import ceil, floor

TOKEN = re.compile(
    r'(?P<int>\d+)|(?P<plus>\+)|(?P<dot>\\cdot)'
    r'|(?P<open>\[|\\lfloor|\\lceil)|(?P<close>\]|\\rfloor|\\rceil)|(?P<gap>\s+)'
    r'|(?P<beg>\\begin\{aligned\})|(?P<end>\\end\{aligned\})|(?P<nl>\\\\)'
    r'|(?P<integral>\\int_\{(?P<a>\d+)\}\^\{(?P<b>\d+)\}\s*(?P<c>\d*)(?:(?P<v>[a-z])(?:\^\{(?P<n>\d+)\})?)?\s*\\mathrm\{d\}(?P<w>[a-z]))')


def tokens(path):
    src = open(path).read()
    if '% >>> THE EXPRESSION BEGINS' in src:
        src = src.split('% >>> THE EXPRESSION BEGINS')[1].split('% <<< THE EXPRESSION ENDS')[0]
    src = re.sub(r'%[^\n]*\n', '', src)                                            # comments, if any
    assert '-' not in src, 'a minus sign in the expression'
    src = re.sub(r'\\vrule height[\d.]+bp depth[\d.]+bp width0pt', ' ', src)       # struts           } replaced by a
    src = re.sub(r'\\kern[\d.]+bp', ' ', src)                                      # horizontal space } blank, so that
    src = re.sub(r'\\left|\\right|\\,|&', ' ', src)                               # sizes, thin spaces, &  } digits never join
    out, i = [], 0
    while i < len(src):
        m = TOKEN.match(src, i)
        if not m:
            raise SystemExit('unexpected text in the expression: %r' % src[i:i + 40])
        kind = m.lastgroup if m.lastgroup in ('int', 'plus', 'dot', 'open', 'close', 'beg', 'end', 'nl', 'gap') else 'integral'
        if kind == 'gap':
            pass
        elif kind == 'int':
            assert len(m.group()) == 1 or m.group()[0] != '0', 'an integer with a leading zero'
            out.append(('int', int(m.group())))
        elif kind == 'integral':
            a, b = int(m['a']), int(m['b'])
            c = int(m['c']) if m['c'] else 1
            n = (int(m['n']) if m['n'] else 1) if m['v'] else 0
            assert not m['v'] or m['v'] == m['w'], 'integrand and differential use different variables'
            val = Fraction(c * (b ** (n + 1) - a ** (n + 1)), n + 1)               # int_a^b c x^n dx
            assert val.denominator == 1
            out.append(('integral', int(val)))
        else:
            out.append((kind, m.group()))
        i = m.end()
    return out


class Parser:
    def __init__(self, toks):
        self.t, self.i, self.depth, self.lines = toks, 0, 0, 0

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self, kind=None):
        tok = self.t[self.i]
        assert kind is None or tok[0] == kind, 'expected %s, found %s' % (kind, tok[0])
        self.i += 1
        return tok

    def line(self):                                   # product + product + ...
        total = self.product()
        while self.peek() == 'plus':
            self.take()
            total += self.product()
        return total

    def product(self):                                # factor factor ...
        last = self.peek()
        value = self.factor()
        while self.peek() in ('int', 'integral', 'open', 'dot'):
            if self.peek() == 'dot':
                self.take()
            else:                                     # juxtaposition: never two bare integers side by side
                assert not (last == 'int' and self.peek() == 'int'), 'two integers side by side'
            last = self.peek()
            value *= self.factor()
        return value

    def factor(self):
        kind, x = self.take()
        if kind in ('int', 'integral'):
            return x
        assert kind == 'open', 'a factor cannot start with %s' % kind
        if self.peek() == 'beg':                      # a sum written on several lines
            self.take(); self.lines += 1
            value = self.line()
            while self.peek() == 'nl':
                self.take(); self.take('plus'); self.lines += 1      # every later line begins with +
                value += self.line()
            self.take('end')
        else:
            value = self.line()
        close = self.take('close')[1]
        assert (x, close) in (('[', ']'), ('\\lfloor', '\\rfloor'), ('\\lceil', '\\rceil')), 'mismatched %s ... %s' % (x, close)
        return {'[': value, '\\lfloor': floor(value), '\\lceil': ceil(value)}[x]


class Mono:                                           # c * x**n, for the one-line form
    def __init__(self, c=1, n=1): self.c, self.n = c, n
    def __rmul__(self, k): return Mono(k * self.c, self.n)
    def __pow__(self, k): return Mono(self.c ** k, self.n * k)


def integrate(f, lim):
    _, a, b = lim
    f = f if isinstance(f, Mono) else Mono(f, 0)
    v = Fraction(f.c * (b ** (f.n + 1) - a ** (f.n + 1)), f.n + 1)
    assert v.denominator == 1
    return int(v)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'portrait.tex'
    p = Parser(tokens(path))
    value = p.factor()
    assert p.i == len(p.t), 'text left over after the expression'
    print('lines of sums read from the LaTeX   :', p.lines)
    print('value computed from the LaTeX source: %d digits' % len(str(value)))
    text, ok = open(path).read(), True
    m = re.search(r'\nVALUE\n(\d+)\n', text)
    if m:                                             # portrait.tex restates the result after \end{document}
        stated = int(m.group(1))
        linear = re.search(r'\nTHE SAME EXPRESSION ON ONE LINE\n(.+)\n', text).group(1)
        x = Mono()
        second = eval(linear, dict(floor=floor, ceiling=ceil, integrate=integrate, x=x, t=x, u=x, y=x, s=x))
        ok = value == stated == second
        print('value computed from the one-line form: %d digits' % len(str(second)))
        print('value stated in the file            : %d digits' % len(str(stated)))
        print('all three agree                     :', ok)
    print(value)
    sys.exit(0 if ok else 1)
