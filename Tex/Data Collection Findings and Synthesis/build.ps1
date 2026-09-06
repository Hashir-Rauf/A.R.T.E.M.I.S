# Build the "Data Collection Findings and Synthesis" report.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "== Generating figures, macros, and tables =="
python figures/gen_figures.py
if ($LASTEXITCODE -ne 0) { throw "figure generation failed" }

Write-Host "== Compiling PDF =="
latexmk -pdf -pdflatex="pdflatex -interaction=nonstopmode -halt-on-error %O %S" -outdir=_latexbuild main.tex
if ($LASTEXITCODE -ne 0) { throw "latexmk failed" }

Copy-Item _latexbuild/main.pdf "Data Collection Findings and Synthesis.pdf" -Force
Write-Host "== Done: Data Collection Findings and Synthesis.pdf =="
