#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== Generating figures, macros, and tables =="
python figures/gen_figures.py

echo "== Compiling PDF =="
latexmk -pdf -pdflatex="pdflatex -interaction=nonstopmode -halt-on-error %O %S" \
        -outdir=_latexbuild main.tex

cp _latexbuild/main.pdf "Data Collection Findings and Synthesis.pdf"
echo "== Done: Data Collection Findings and Synthesis.pdf =="
