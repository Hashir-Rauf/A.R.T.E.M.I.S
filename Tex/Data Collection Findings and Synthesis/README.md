# Data Collection Findings and Synthesis

LaTeX source for the ARTEMIS foundational-research findings report (FYP F26-008).

## Output

`Data Collection Findings and Synthesis.pdf` at this directory's root is the compiled report:
a 12-page body (Executive Summary through Recommendations), plus a title page, table of
contents, list of figures, and an appendix with the full response distributions.

## Layout

```
main.tex            The report.
preamble.sty        Packages, Times Roman fonts, heading styles, the "Finding" callout box.
references.bib      Citations for the two internal datasets.
data/
  questionnaire.csv Copy of the questionnaire responses (374 rows).
  interviews.xlsx   Copy of the coded in-person interviews.
  interviews.csv    Cleaned interview coding, written by gen_figures.py.
figures/
  gen_figures.py    Reads data/, writes every figure PDF plus stats.tex, tables.tex, segments.tex.
  *.pdf             Generated charts (committed).
  stats.tex         \newcommand macros for every headline number used in the prose.
  tables.tex        Appendix response-distribution tables.
  segments.tex      The segment cross-tab table.
build.sh / build.ps1  Regenerate figures, then compile.
```

Every number in the prose comes from a macro in `figures/stats.tex`, so the text cannot drift
from the data. Regenerate the figures and macros whenever `data/` changes.

## Build

Dependencies:

- Python 3 with `matplotlib` and `openpyxl`
- A TeX distribution with `pdflatex` and `latexmk` (MiKTeX or TeX Live). The `newtx` package is
  auto-installed by MiKTeX on first run.

From this directory:

```
# One command:
./build.sh              # or:  pwsh ./build.ps1

# Or by hand:
python figures/gen_figures.py
latexmk -pdf -outdir=_latexbuild main.tex
cp _latexbuild/main.pdf "Data Collection Findings and Synthesis.pdf"
```

`gen_figures.py` prints a summary of every statistic it computes so the prose can be
cross-checked against the data.

The `_latexbuild/` directory holds LaTeX auxiliary files and is not committed.
