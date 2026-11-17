# A portrait that is one integer

![The expression](portrait.png)

This picture is a single mathematical expression, typeset in LaTeX.
It evaluates to a 221-digit integer:

```
10462823909000930371012423280261573066304047387772774161345026568186973468
83249703763694089480003089055105792426671463445778351110087416678821071115
6801330129520006604040466513832218432055052660531225951649290443923312862
```

One font, one weight (New Computer Modern). Nothing is shaded. The tone comes
only from the structure of the expression:

| Tone | What is on the page |
| --- | --- |
| white | space between factors |
| lightest | tall integral signs, far apart, each with its limits and integrand |
| light | long bracket pairs around a single numeral |
| mid | runs of numerals: 1 and 7 are light, 6 and 9 are dark |
| dark | numerals inside deeper and deeper nests of `\| \|`, `[ ]`, `⌊ ⌋`, `⌈ ⌉` |

Long strokes are used for the background that reaches the edge of the picture
(sky, sea). The figure is set in fine rows.

## How to read it

- Things side by side are multiplied.
- A column of rows inside `‖ … ‖₁` is the sum of its rows.
- A numeral inside `| |`, `[ ]`, `⌊ ⌋` or `⌈ ⌉` is itself.
- Each tall `∫` is an ordinary definite integral; its limits sit at the two ends of the stroke.

## Check it yourself

```
tectonic portrait.tex      # typesets the picture from body.tex
python3 verify.py          # evaluates expression.txt exactly and compares with value.txt
```

`body.tex` is the expression as LaTeX (19,848 delimiter strokes, 16,685 numerals,
30 integral signs, 16 stacked blocks). `expression.txt` is the same expression in
linear form, so it can be evaluated without looking at the picture:
`N1([...])` is `‖ … ‖₁`, `Int(a, b, f)` is a definite integral, `abs`, `floor`, `ceil`
and plain parentheses are the four kinds of delimiter.

## Files

| File | What it is |
| --- | --- |
| `portrait.png`, `portrait.pdf` | the expression, nothing else |
| `poster.pdf` | the expression with its value and a reading key |
| `body.tex`, `kit.tex`, `portrait.tex`, `poster.tex` | the LaTeX |
| `expression.txt`, `value.txt` | linear form of the expression and the integer it equals |
| `verify.py`, `verification.txt` | the independent check and its output |
| `build.py`, `calib.py`, `calib.json` | the generator and the font measurements it uses |

## Honest notes

- Brackets around a single numeral do not change its value. They are the shading. The integrals, products and sums are the parts that compute.
- The darkest structure reaches about 42% ink, so the picture is paler than a photograph.
- The source photograph is not in this repository. `build.py` expects one as `source.png`; everything else rebuilds from the files here.
- Built with [Tectonic](https://tectonic-typesetting.github.io) (XeTeX), and Python. The check uses exact integer arithmetic only.
