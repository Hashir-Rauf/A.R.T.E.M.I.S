# ARTEMIS Foundational Research Questionnaire (Trimmed)

**Revision note:** Cut from 22 to 15 questions per supervisor feedback (Mubashar Hussain, 2026-08-25): "reduce by almost half," "make questions more direct and straightforward," "shorter the better." Removed severity/follow-up/secondary-adversarial items, kept one strong question per pain point / tradeoff / adoption signal. Question IDs no longer show technique tags (FORCED CHOICE / ADVERSARIAL / etc.) in the fielded version — kept invisible from respondents, noted here only for the team's own reference.

**Target respondents:** Students, freelancers, developers, researchers/scholars, working professionals who manage multi-file work.

**Estimated time:** 4–5 minutes.

**Anonymous:** Email collection should be turned off in Google Forms — an anonymous survey gets more honest answers to the adoption/distrust questions (B3, B7) than one asking for contact info.

---

## Screening

**Q0.** How often do you work on projects that involve managing multiple files, documents, or folders (e.g. coursework, code projects, client deliverables, research)?
- Daily
- A few times a week
- A few times a month
- Rarely / never *(if selected → thank and exit)*

---

## Part A — Your Current Experience

**A1.** What best describes you?
Student / Freelancer / Developer / Software Engineer / Researcher / Scholar / Other knowledge worker / Other

**A2.** How often do you return to a project after a break of a day or more and struggle to remember what you were doing or what to do next?
Never / Rarely / Sometimes / Often / Every time

**A3.** *"My folders and files tend to become messy or disorganized faster than I can manually clean them up."* *(Likert 1–5)*

**A4.** If you repeat the same manual file-handling task often, why haven't you automated it? Pick the honest reason. *(forced choice)*
- I don't know how / it feels out of reach
- It would take longer to set up than the time it saves
- I don't trust automation to do it correctly without supervision
- Not applicable — I don't have repeated manual tasks

**A5.** Roughly how much total time per week do you think you lose to these issues (reorienting after breaks, tidying files, repeating manual tasks, searching scattered notes)?
Under 30 min / 30–60 min / 1–3 hrs / 3–5 hrs / Over 5 hrs

**A6.** Have you used an AI assistant (e.g. Copilot, ChatGPT, Gemini, a computer-use agent) to help manage files, write code, or handle tasks on your computer?
Yes regularly / Yes occasionally / Tried once or twice / Never

---

## Part B — Reacting to the ARTEMIS Concept

*Show the concept description first:*

> **ARTEMIS** is a desktop assistant you can add to specific folders ("workspaces") on your computer. It only ever knows about files, notes, and tabs you explicitly add — nothing outside that folder. It can resume interrupted work, tidy files, pull together notes, catch repeated tasks and offer automation, explain/fix code, search the web on demand, draft emails, and draft documents. Every file-changing or outbound action is shown for approval first, and can be undone. Nothing is deleted or sent without explicit go-ahead.

**B1.** Which of these two assistants would you actually prefer to use day to day? *(forced choice — the core tradeoff)*
- Assistant A — asks approval before every file change or outbound action, even small ones
- Assistant B — acts automatically on reasonable requests, review/undo afterward

**B2.** *"An assistant that only sees files I explicitly add to a workspace is meaningfully more trustworthy to me than one with full access to my computer."* *(Likert 1–5, neutral phrasing)*

**B3.** Suppose ARTEMIS made a wrong or unwanted suggestion once. Would you keep using it? *(adversarial)*
- Yes, one mistake wouldn't change my usage
- More cautious but keep using it
- Stop trusting that specific feature area
- Likely stop using the tool altogether

**B4.** Which features would you actually use in your first week, if it worked exactly as described? *(select top 3 of the 9 features)*

**B5.** Local-first (private, possibly slower/weaker) vs. cloud-backed (faster/more capable, less private) — which would you actually choose? *(forced choice)*
- Local-first even if slower/weaker
- Cloud-backed even if less private
- Need more specifics before deciding

**B6.** If ARTEMIS worked exactly as described, how likely would you be to actually use it for your own work?
Very likely / Likely / Neutral / Unlikely / Very unlikely

**B7.** What is the single most likely reason you would stop using ARTEMIS after a week, if you had to guess right now? *(adversarial pre-mortem)*
- It asks for approval too often and slows me down
- It makes a mistake I don't trust it to avoid again
- It doesn't do anything I couldn't already do myself easily
- I forget to use it / it doesn't fit into my existing habits
- Privacy or data-control concerns
- I don't think I would stop using it

---

## Closing — Open-Ended

**C1 (open-ended, only free-text field).** *"Is there anything about how you currently manage multi-file work — a frustration, a workaround, or a feature you wish existed — that this questionnaire didn't ask about, but that you think we should know before building a tool like this?"*

---

## What was cut from the previous 22-question version, and why

- **A3, A5 (severity follow-ups)** — asked what a pain point "cost" the respondent last time. Useful detail, but not essential to decide whether to build the feature; the frequency/Likert items already establish the pain point exists.
- **A6, A8 (second Likert + code-specific frequency)** — redundant with A3's messy-folders Likert and A2's resume-struggle question in spirit; A8 also only applied to a subset of respondents, adding friction for the rest.
- **A11 (AI-assistant follow-up reason)** — nice-to-have detail on why people don't rely on AI tools more, but not essential to the core hypothesis.
- **B2 (approval-fatigue adversarial), B5 (false-positive vs. missed-approval tradeoff)** — B1 and B3 already carry the core "does the approval model hold up" signal; these were redundant elaborations.
- **B4 old version / "wrong suggestion" (kept as new B3), B7 old (feature distrust), B8 old (local vs cloud, kept as new B5)** — feature-distrust question (old B7) cut as lowest-signal of the adversarial set; local-vs-cloud (old B8) kept since it directly tests a real architecture decision (see [[project-artemis-open-questions]]).

## Notes for the team

- Tag responses by **A1** segment (student/freelancer/developer/researcher) if you want to check whether the bounded-scope hypothesis generalizes across audiences, as the proposal claims.
- **B3, B7** remain the highest-value questions for finding reasons ARTEMIS could fail — read these first.
- Target N: 30–50 responses per major segment for any segment-level comparison to be meaningful; otherwise treat as pooled/exploratory.
- **C1** is the only free-text field — read every response in full rather than skimming, since it's the sole place an issue outside the fixed answer options can surface.
