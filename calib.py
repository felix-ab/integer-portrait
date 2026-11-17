#!/usr/bin/env python3
"""Measure, from LaTeX's own output, the ink of each numeral and operator in the one
font used (New Computer Modern Book, 10bp), and the stem of a tall integral sign."""
import subprocess, json, os, numpy as np
os.makedirs('work', exist_ok=True)
from PIL import Image
PX = 10
GL = list('0123456789') + ['+', r'\cdot', '-', '(', ')', '!']
cells = ''.join(r'\hbox to 8bp{\hss$%s$\hss}' % g for g in GL)
open('work/calib2.tex', 'w').write(r'''\documentclass{article}
\usepackage[paperwidth=%dbp,paperheight=60bp,margin=0pt]{geometry}
\usepackage{amsmath}\usepackage{unicode-math}
\setmainfont{NewCM10-Book.otf}\setmathfont{NewCMMath-Book.otf}[StylisticSet=2]
\pagestyle{empty}\parindent=0pt\topskip=0pt
\newbox\TIa \newbox\TIb \newbox\TIc
\begin{document}\fontsize{10bp}{10bp}\selectfont
\setbox\TIa\hbox{$\inttop$}\setbox\TIb\hbox{$\intbottom$}\setbox\TIc\hbox{$\intextender$}%%
\typeout{INT top \the\wd\TIa/\the\ht\TIa/\the\dp\TIa; bot \the\wd\TIb/\the\ht\TIb/\the\dp\TIb; ext \the\wd\TIc/\the\ht\TIc/\the\dp\TIc}%%
\vbox to 60bp{\offinterlineskip
\hbox to %dbp{\vrule width0pt height9bp depth1bp %s\hss}%%  row 1: glyphs, baseline 1bp above the row floor (10bp row)
\hbox to %dbp{\vrule width0pt height50bp depth0pt \kern10bp\raise 5bp\vbox{\offinterlineskip\hbox{\copy\TIa}\hbox{\copy\TIc}\hbox{\copy\TIc}\hbox{\copy\TIb}}\hss}%%
\vss}
\end{document}
''' % (8 * len(GL), 8 * len(GL), cells, 8 * len(GL)))
out = subprocess.run(['tectonic', '--print', 'calib2.tex'], cwd='work', capture_output=True, text=True)
info = [l for l in (out.stdout + out.stderr).splitlines() if 'INT top' in l]
print(info[0] if info else 'no metrics line')
subprocess.run(['pdftoppm', '-png', '-r', str(72 * PX), '-singlefile', 'calib2.pdf', 'calib2'], cwd='work', check=True)
im = 1 - np.asarray(Image.open('work/calib2.png').convert('L'), dtype=np.float64) / 255
res = {}
for i, g in enumerate(GL):
    cell = im[0:100, i * 80:(i + 1) * 80]                    # 8bp x 10bp cell
    ys, xs = np.nonzero(cell > 0.2)
    res[g] = dict(ink=float(cell.sum() / 100), x0=float(xs.min() / 10), x1=float((xs.max() + 1) / 10),
                  top=float(10 - ys.min() / 10 - 1), bot=float(10 - (ys.max() + 1) / 10 - 1))
    np.save('work/g_%d.npy' % i, cell)
print('glyph: ink area (bp^2), ink x-extent in an 8bp box, height above / below baseline')
for g in GL:
    r = res[g]; print('  %-6s ink %.2f   x %.1f..%.1f   y %.1f..%.1f' % (g, r['ink'], r['x0'], r['x1'], r['bot'], r['top']))
row = im[100:600]
mid = row[200:300]                                           # middle of the stacked integral: the stem
cols = np.nonzero(mid.mean(axis=0) > 0.5)[0]
print('integral stem: x %.2f..%.2f bp from box left (thickness %.2f bp)' % (cols.min() / 10 - 10, (cols.max() + 1) / 10 - 10, (cols.max() + 1 - cols.min()) / 10))
ys, xs = np.nonzero(row > 0.3)
print('integral ink extent: x %.2f..%.2f, height %.1f bp' % (xs.min() / 10 - 10, (xs.max() + 1) / 10 - 10, (ys.max() + 1 - ys.min()) / 10))
json.dump(res, open('calib.json', 'w'))
