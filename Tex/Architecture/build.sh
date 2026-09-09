#!/usr/bin/env bash
# Build the ARTEMIS System Architecture document.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Generating architecture figures =="
python figures/gen_figures.py

echo "== Compiling PDF =="
latexmk -pdf -pdflatex="pdflatex -interaction=nonstopmode -halt-on-error %O %S" -outdir=_latexbuild main.tex

cp _latexbuild/main.pdf "ARTEMIS System Architecture.pdf"
echo "== Done: ARTEMIS System Architecture.pdf =="
