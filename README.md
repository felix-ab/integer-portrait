# A portrait that is one integer

![The expression](portrait.png)

This picture is a single mathematical expression, typeset in LaTeX.
It evaluates to a 220-digit integer:

```
20933085614569928271348620629319806063957319928223862732707204554184676221
03117633301626583972756499090119088608916735703124752523838466376999206871
199705654051555884435369889596575381861178898181445402799646275283208489
```

## The expression is ordinary LaTeX

[`expression.tex`](expression.tex) is the expression and nothing else. It has no comments, no
definitions and no custom commands. This is its complete vocabulary:

| In the file | Meaning |
| --- | --- |
| `0` … `9` | decimal integers; a run of digits is one integer |
| `+`, `\cdot` | addition, multiplication |
| `[ ]` | grouping |
| `\lfloor \rfloor`, `\lceil \rceil` | floor, ceiling |
| `\left`, `\right` | size prefixes for those three delimiter pairs |
| `\int_{a}^{b} f\,\mathrm{d}x` | a definite integral; `f` is nothing (that is, 1), `x` or `2x` |
| `\begin{aligned} & … \\ & + … \end{aligned}` | one sum broken over several lines inside a bracket (amsmath) |
| `\kern<length>`, `\vrule height<h> depth<d> width0pt`, `\,`, `&` | spacing and alignment; no mathematical content |

Nothing else occurs in the file. In numbers: 223 lines in 15 bracketed sums, 19,928 delimiters,
16,616 numerals, 381 plus signs, 1,816 multiplication dots and 26 integrals.

How it reads:

- The whole expression is one bracketed sum. Each line is a sum of products, and every line
  after the first begins with `+`.
- Adjacent factors are multiplied, as in `2[3]\lfloor 4\rfloor` = 24.
- Two integers never stand side by side without an operator between them. Nothing is ever
  placed between the digits of an integer. No integer has a leading zero.
- There is no subtraction (the character `-` does not occur in the file), no division and no
  free variable.
- Every bracket, floor and ceiling encloses a positive integer, so it leaves that integer
  unchanged. The value does not depend on which of the three a stroke is taken to be.
- Every integrand is a monomial in its own variable and every other factor is a constant, so
  the value does not depend on where an integral's scope is taken to end.

## The picture is the structure

One font, one weight (New Computer Modern). Nothing is shaded:

| Tone | What is on the page |
| --- | --- |
| white | space between factors |
| lightest | tall integral signs, far apart |
| light | tall bracket pairs around a single numeral |
| mid | runs of numerals: 1 and 7 are light, 6 and 9 are dark |
| dark | numerals inside deeper and deeper nests of `[ ]`, `⌊ ⌋`, `⌈ ⌉` |

Where the picture is vertically even and reaches the edge (sky, sea), the strokes run the full
height of the region. The figure is set in fine lines.

## Two ways to typeset it

- [`stock.tex`](stock.tex) is nine lines: `article`, `amsmath`, and `\[ \input{expression.tex} \]`.
  Unmodified LaTeX accepts the expression as it stands. The result is a very wide formula with
  LaTeX's own delimiter shapes. It is the same mathematics, but not the picture, because the
  spacing was computed for thinner strokes.
- [`portrait.tex`](portrait.tex) contains the same expression, character for character, after a
  short drawing layer. The drawing layer redraws the commands in the table above as hairline
  strokes of exact size, with numerals at a fixed advance. It changes how they look, not what
  they denote. The file is self-contained: after `\end{document}` it restates the value, gives
  the expression on one line and includes the checker.

## Check it yourself

```
python3 check.py expression.tex   # reads the LaTeX, evaluates it exactly, prints the integer
python3 verify.py                 # four evaluations, each compared with value.txt
tectonic portrait.tex             # typesets the picture
tectonic stock.tex                # typesets the bare expression with unmodified LaTeX
```

`verify.py` evaluates the expression four ways. None of them uses the generator.

1. `check.py` parses `expression.tex` with a recursive-descent parser of about a hundred lines
   (Python standard library only) and evaluates it with exact integer arithmetic. It rejects
   anything outside the vocabulary above, two integers side by side, a leading zero, a minus
   sign, a mismatched delimiter and a continuation line that does not begin with `+`.
2. `expression.tex` again, with no parser of ours. Each symbol is replaced by its SymPy
   spelling (a text substitution) and SymPy reads and evaluates the result, integrals included.
3. `expression.txt`, the same expression on one line in calculator syntax, with a small exact
   evaluator.
4. `expression.txt` again, with SymPy.

All four give the integer above. The output of the last run is in `verification.txt`.

## Files

| File | What it is |
| --- | --- |
| `expression.tex` | the expression alone, in stock LaTeX |
| `stock.tex` | nine-line wrapper that typesets `expression.tex` with unmodified LaTeX |
| `portrait.tex`, `portrait.pdf`, `portrait.png` | the picture: drawing layer plus the same expression |
| `poster.tex`, `poster.pdf` | the picture with its value printed underneath |
| `expression.txt`, `value.txt` | the expression on one line, and the integer it equals |
| `check.py`, `verify.py`, `verification.txt` | the checks and their output |
| `build.py`, `template.tex`, `calib.py`, `calib.json` | the generator, the template of `portrait.tex`, and the font measurements |

## Honest notes

- The brackets, floors and ceilings are the shading. The products, sums and integrals are what
  compute.
- The darkest structure reaches about 42% ink, so the picture is paler than a photograph.
- The source photograph is not in this repository. `build.py` expects one as `source.png`;
  everything else rebuilds from the files here.
- Typeset with [Tectonic](https://tectonic-typesetting.github.io) (XeTeX). `stock.tex` uses
  only LaTeX and amsmath; it has been run through Tectonic, not through pdfLaTeX.
