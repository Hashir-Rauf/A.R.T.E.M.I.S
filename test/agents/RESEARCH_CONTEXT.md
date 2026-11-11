# Research context (orchestrator only; participant agents must NOT read this file)

Sources read: `Tex/Report/F26-008.pdf` (project report, 83 pp.), `Tex/Data Collection Findings and Synthesis/`, `Docs/Architecture/ARTEMIS-Architecture.md`, `Tex/Supervisor-Review/What ARTEMIS Does Differently.pdf`, `Docs/Research Docs/*`, `Docs/Data Collection/*`, and `tests/agents/FINAL-REPORT.md` (implementation test report, used only for limitations).

## Problem
Users of multi-file knowledge work lose time re-establishing context after interruptions and doing routine file and correspondence tasks. AI assistants that could relieve this ask for broad, unbounded access to the machine, which creates privacy exposure, risk of unintended change and loss of control that many users will not accept (Report 2.2).

## Proposed solution
ARTEMIS: a bounded, opt-in desktop assistant. It works only inside folders the user explicitly grants, deletes nothing (no code path), routes every file change or outward action through preview, approval and one-click undo, discloses everything it holds ("What ARTEMIS knows", every entry deletable), is local-first, supports voice under the same gates, and optionally remote access.

## Target population (Report 2.1, 2.9)
Students (81 % of the 374-respondent questionnaire), developers (13 %), freelancers and employed knowledge workers; single-user personal desktop; interrupted multi-file work.

## Research question and hypotheses
- **Research question (Report 1.1):** can an assistant restricted to explicitly granted workspaces deliver effective multi-step task automation while measurably improving user trust, and without meaningfully reducing usefulness?
- **H-C (central, explicitly stated):** restricting an assistant's scope to explicitly granted folders increases user trust and adoption without meaningfully reducing usefulness (Report abstract, 1, 1.1).
- Supporting claims and assumptions stated in the documents (labelled as such; not all are formally numbered hypotheses):
  - **S1 Problem relevance:** people lose substantial time re-establishing context after interruptions and on routine file work (2.3).
  - **S2 Access bargain:** distrust of broad-access assistants is a real barrier to adoption (2.3, 2.9.2).
  - **S3 Trust in bounded scope:** a workspace-only assistant is rated more trustworthy than a full-access one (A.3, F5).
  - **S4 Forgiveness with undo:** users tolerate a single mistake if recovery is easy, so visible undo matters more than perfection (F6).
  - **S5 Approval preference is split:** users are divided between approve-first and act-then-undo, so approval granularity must be configurable (2.9.2).
  - **S6 Retention risks:** habit fit and an untrusted mistake are the main reasons to stop; approval fatigue is smaller (F7).
  - **S7 Feature demand:** session resume, notes synthesis and folder tidy are wanted most; speech least (F8).
  - **S8 Onboarding:** effortless onboarding is a condition for continued use (F9).

Prior evidence in the documents (questionnaire n=374, 13 interviews) is NOT shown to the participant agents, so that their reactions are independent of it. It may be compared with the simulation only in the synthesis, as context, never merged with it.

## What would support, partially support or reject each claim (fixed before any agent ran)
Counted over the 15 simulated participants, using each participant's own final statements plus behaviour observed in their log.

| Classification | Rule |
|---|---|
| Supported | at least 10 of 15 hold the claim, positive evidence appears across at least 3 of the 4 persona clusters (student, developer, freelancer or employee, sceptic or non-adopter), and no strong, well-reasoned contradicting pattern |
| Partially supported | 6 to 9 of 15 hold it, or 10 or more hold it but only in some persona clusters, or it holds with a significant condition that many participants attach |
| Not supported | 5 or fewer hold it, or a majority give a reasoned contradiction |
| Inconclusive | evidence thin (fewer than 8 participants engaged with the point), or contradictory in a way the data cannot resolve |

For H-C the three parts (trust increased; adoption interest; usefulness not meaningfully reduced) are scored separately, and the classification cannot exceed the weakest part. These thresholds are descriptive conventions for synthetic data, not statistical tests.
