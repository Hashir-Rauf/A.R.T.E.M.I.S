# Build one wrapper of the paper: pdflatex -> bibtex -> pdflatex -> pdflatex.
# Usage (from any directory):
#   .\build.ps1            # builds main.tex (generic)
#   .\build.ps1 main-acm   # or main-ieee, main-lncs
#   .\build.ps1 all        # builds every wrapper
param([string]$Target = "main")

Set-Location $PSScriptRoot

function Build-One([string]$name) {
    Write-Host "== $name ==" -ForegroundColor Cyan
    pdflatex -interaction=nonstopmode -halt-on-error "$name.tex" | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Host "pdflatex pass 1 failed; see $name.log" -ForegroundColor Red; return }
    bibtex $name | Out-Null
    pdflatex -interaction=nonstopmode -halt-on-error "$name.tex" | Out-Null
    pdflatex -interaction=nonstopmode -halt-on-error "$name.tex" | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Host "pdflatex final pass failed; see $name.log" -ForegroundColor Red; return }
    $out = Select-String -Path "$name.log" -Pattern "Output written on" | Select-Object -Last 1
    Write-Host $out.Line
    $warn = Select-String -Path "$name.log" -Pattern "Citation .* undefined|Reference .* undefined|LaTeX Warning: There were"
    if ($warn) { $warn | ForEach-Object { Write-Host "  $($_.Line)" -ForegroundColor Yellow } }
}

if ($Target -eq "all") {
    foreach ($t in @("main", "main-acm", "main-ieee", "main-lncs")) { Build-One $t }
} else {
    Build-One $Target
}
