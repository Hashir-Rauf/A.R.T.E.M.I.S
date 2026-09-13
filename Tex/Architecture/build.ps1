# Build the ARTEMIS System Architecture document.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "== Generating architecture figures =="
python figures/gen_figures.py
if ($LASTEXITCODE -ne 0) { throw "figure generation failed" }

Write-Host "== Compiling PDF =="
latexmk -pdf -pdflatex="pdflatex -interaction=nonstopmode -halt-on-error %O %S" -outdir=_latexbuild main.tex
if ($LASTEXITCODE -ne 0) { throw "latexmk failed" }

Copy-Item _latexbuild/main.pdf "ARTEMIS System Architecture.pdf" -Force
Write-Host "== Done: ARTEMIS System Architecture.pdf =="
