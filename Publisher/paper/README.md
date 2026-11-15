# ARTEMIS paper: one body, any template

The paper text lives once, in `content/`, written in plain LaTeX that every
major publisher class accepts. Each venue gets a thin wrapper that sets the
class, the author block and the bibliography style, then inputs the same
content. Changing venue means changing one wrapper, not the paper.

```
Publisher/paper/
  main.tex            generic article, A4, single column   (arXiv, drafts)
  main-acm.tex        acmart sigconf                      (CHI, IUI, CUI, TiiS)
  main-ieee.tex       IEEEtran conference                 (AGENT'27, ICOSST, FIT)
  main-lncs.tex       Springer LNCS
  content/
    macros.tex        shared packages and the \sys / \InstitutionName macros
    abstract.tex      abstract body only (each class wraps it differently)
    sections.tex      inputs 01..08 in order
    01-introduction.tex ... 08-conclusion.tex
  figures/            fig_lifecycle, fig_tiers, fig_workspace_trust (from Tex/Report)
  references.bib      26 reviewed papers (Tex/Literature-Review) + 3 stack refs
  build.ps1           pdflatex -> bibtex -> pdflatex x2
```

## Build

```powershell
.\build.ps1             # main.tex
.\build.ps1 main-acm    # one wrapper
.\build.ps1 all         # every wrapper
```

Needs MiKTeX with pdflatex and bibtex (installed on this machine, with
acmart, IEEEtran, llncs and elsarticle present). BibTeX, not biber: ACM and
IEEE require it, and `references.bib` uses only standard fields.

## Switching venue

| Venue | Wrapper | Class line | Bib style | Notes |
| --- | --- | --- | --- | --- |
| CHI Posters / LBW, IUI, CUI | `main-acm.tex` | `[sigconf,review,anonymous]` for review, `[sigconf]` final | ACM-Reference-Format | Fill `\acmConference`; add CCS XML from dl.acm.org/ccs |
| ACM TiiS | `main-acm.tex` | `[acmsmall]` | ACM-Reference-Format | Journal length; keep all sections |
| ICSE workshop, ICOSST, FIT | `main-ieee.tex` | `[conference]` | IEEEtran | Workshop pages often 5 (short) or 8 (full) excl. refs |
| IEEE Access | new wrapper on `ieeeaccess.cls` | from IEEE | ieeeaccess | Download the class from IEEE; content drops in unchanged |
| Springer | `main-lncs.tex` | `[runningheads]` | splncs04 | Abstract 150 to 250 words |
| IJHCS (Elsevier) | new wrapper on `elsarticle` | `[preprint,12pt]` | elsarticle-num | Installed; copy `main.tex` and swap the class |
| arXiv | `main.tex` | as is | plainnat | Upload the .tex, .bib, .bbl and figures |

## Rules that keep the content portable

- Only `\section`, `\subsection`, `\paragraph`. No `\chapter`, no custom headings.
- Only `\cite{}`. No `\citep`, `\citet`, `\textcite`.
- Figures use `width=\linewidth` (or `figure*` with `\textwidth` to span both
  columns); they resize correctly in one- and two-column classes.
- Tables use `booktabs`; caption above the table, as ACM, IEEE and Springer want.
- No packages with options in `content/`; options belong in the wrapper so they
  cannot clash with what the class already loaded (hyperref in particular).
- Every wrapper defines `\ifanon` before inputting `macros.tex`. Set `\anontrue`
  for double-blind review: it blanks the author block and replaces the
  institution name inside the body.

## Fitting a page limit

Full version: about 8 to 9 pages in ACM sigconf, 7 to 8 in IEEE, 14 in LNCS.

For a 4-page CHI poster or a 5-page workshop short paper, cut in this order:

1. `06-evaluation.tex`: the persona-simulation subsection (marked `CUT-FOR-SHORT`)
   and the hands-on-rounds subsection.
2. `02-related-work.tex`: collapse the seven theme paragraphs into one
   paragraph plus the "Closest systems" paragraph.
3. `03-design.tex`: keep lifecycle, broker, policy tiers and undo; drop
   disclosure, voice parity and the egress subsection, mentioning each in one
   sentence under lifecycle.
4. `05-formative-study.tex`: keep the four headline numbers (65 percent trust,
   192 to 182 split, 65 percent forgive one mistake, 40 percent local-first)
   and the figure; drop the rest.
5. `04-implementation.tex`: cut to one paragraph.

## Before any submission

- [ ] Author list and order confirmed with the supervisor (emails are filled in
      in all four wrappers).
- [ ] Ethics / consent statement for the questionnaire and interviews added
      to `05-formative-study.tex` (marked `TODO`).
- [ ] Data and code availability statement and acknowledgements added to
      `08-conclusion.tex` (marked `TODO`), wrapped in `\ifanon`.
- [ ] Numbers re-checked against the latest report. Every figure in the text
      comes from `Tex/Report/F26-008.tex` as of 9 November 2026 and from
      `Future-work/benchmark_results.json`; after FYP-II, the controlled
      study replaces Section 7.4 and extends Section 6.
- [ ] Plagiarism check: the text overlaps with the FYP report by design.
      Rewrite any passage the venue's checker flags.
- [ ] Page limit, anonymisation and template version checked against the
      call for papers (see `../ARTEMIS Paper Target Venues, Deadlines and
      Templates.pdf`).
