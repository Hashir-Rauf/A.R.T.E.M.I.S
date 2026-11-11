# ARTEMIS Simulated User Feedback Study: Exploratory Synthetic Evidence

> This study uses AI-based simulated user agents to explore potential user perceptions and behavioural patterns. The participants are simulated personas, not recruited human subjects. Consequently, the findings represent exploratory synthetic evidence and must not be presented as empirical human-subject results or statistically representative population findings.

## 1. Executive summary

Fifteen simulated participants (AI agents playing assigned personas) were shown a prototype of ARTEMIS, a bounded, opt-in desktop assistant, and each wrote a 12-section report. The support/partial/reject rules were fixed before the agents ran. All counts below are counted from the 15 reports (x of 15) and, for ratings, are means and medians of the 1-5 ratings actually given. There are no significance tests.

What the simulation shows:

- **Problem relevance** was rated 3.27 on average (median 3; range 2 to 4; no 1s or 5s). Seven of 15 rated it 4, five rated it 3, three rated it 2.
- **Value of the solution** was rated 2.8 on average (median 3; range 2 to 3.5). Ten of 15 gave exactly 3.
- **Adoption**: 14 of 15 chose "might try", 1 chose "would not use", none chose "would use" or "would recommend".
- **Central claim, part (a) trust**: 6 agree, 9 partly, 0 disagree. **Part (b) willingness**: 1 agree, 14 partly, 0 disagree. **Part (c) usefulness cost**: 6 said the limitation does not cost too much, 3 partly, 6 cannot say, none said it costs too much.
- The most consistent positive observation was **the plan-approve-undo mechanism**: 10 of 15 approved a tidy-up and used Undo, and in all 10 the reports say the files were restored. Several (Agents 01, 02, 07, 13) said Undo, not the folder limit, did most for their trust.
- The most consistent negative observations were **answer quality in the prototype** (13 of 15 describe a failed, wrong, partial or fabricated answer), **the cloud key shown as "Key saved" on a clean copy** (12 of 15 mention it), and **setup friction** (the Folders box failed on the first try for at least 8).
- No participant would commit to use it (0 "would use"), and 4 participants (Agents 01, 04, 06, 14) said in their own words that the folder boundary was not their reason to try it or not.

Classification under the pre-set rules:

| Claim | Classification |
|---|---|
| H-C (central), classification capped at weakest part | **Partially Supported** |
| H-C part 1: trust increased | Partially Supported |
| H-C part 2: adoption interest increased | Partially Supported (weakest part; see caveat in 10.1) |
| H-C part 3: usefulness not meaningfully reduced | Partially Supported (low confidence) |
| S1 Problem relevance | Partially Supported |
| S2 Access bargain | Supported (with a selection caveat) |
| S3 Trust in bounded scope | Partially Supported |
| S4 Forgiveness with undo | Partially Supported |
| S5 Approval preference is split | Partially Supported (conservative coding) |
| S6 Retention risks | Partially Supported (low confidence, inferred) |
| S7 Feature demand | Partially Supported |
| S8 Onboarding | Supported (with a leading-question caveat) |

These are descriptive conventions applied to synthetic data. They say nothing about how real people would respond.

## 2. Research objectives

1. Explore, before any human study, whether people with different backgrounds react to ARTEMIS's central idea (an assistant limited to folders the user grants, that always asks first and offers undo) the way the project's documents assume.
2. Observe how simulated users actually interact with the working prototype: what they try, ignore, abandon, repeat and hesitate over.
3. Identify concerns, objections and design requirements that should be checked in a real-world study.
4. Apply the fixed rules in `test/agents/RESEARCH_CONTEXT.md` to the central hypothesis (H-C) and the eight supporting claims (S1 to S8), and say plainly where the evidence is weak or negative.
5. Separate what the idea contributes from what the prototype's defects contributed, so the defects do not get read as verdicts on the concept.

This is exploratory. It cannot confirm or refute the hypotheses for real people.

## 3. Original research hypotheses

Quoted as stated in `test/agents/RESEARCH_CONTEXT.md`, which cites the project report.

**Research question (explicit, Report 1.1):** can an assistant restricted to explicitly granted workspaces deliver effective multi-step task automation while measurably improving user trust, and without meaningfully reducing usefulness?

**Explicit central hypothesis**

- **H-C (central, explicitly stated):** restricting an assistant's scope to explicitly granted folders increases user trust and adoption without meaningfully reducing usefulness (Report abstract, 1, 1.1).

**Supporting claims and assumptions.** RESEARCH_CONTEXT.md labels these as "stated in the documents (labelled as such; not all are formally numbered hypotheses)". They are supporting claims, not explicit hypotheses:

- **S1 Problem relevance:** people lose substantial time re-establishing context after interruptions and on routine file work (2.3).
- **S2 Access bargain:** distrust of broad-access assistants is a real barrier to adoption (2.3, 2.9.2).
- **S3 Trust in bounded scope:** a workspace-only assistant is rated more trustworthy than a full-access one (A.3, F5).
- **S4 Forgiveness with undo:** users tolerate a single mistake if recovery is easy, so visible undo matters more than perfection (F6).
- **S5 Approval preference is split:** users are divided between approve-first and act-then-undo, so approval granularity must be configurable (2.9.2).
- **S6 Retention risks:** habit fit and an untrusted mistake are the main reasons to stop; approval fatigue is smaller (F7).
- **S7 Feature demand:** session resume, notes synthesis and folder tidy are wanted most; speech least (F8).
- **S8 Onboarding:** effortless onboarding is a condition for continued use (F9).

H-C has three parts, scored separately: (1) trust increased; (2) adoption interest; (3) usefulness not meaningfully reduced.

Prior evidence in the project documents (a questionnaire and interviews) was not shown to the participants. Where this document mentions it, that is context only and is never combined with the simulation.

## 4. Simulation methodology

- **Participants.** 15 simulated participants, Agent_01 to Agent_15. Each played one persona (a named person with an age, occupation, habits and attitude toward AI). The agents were run in two batches (7 and 8 agents), as given by the study's orchestrator.
- **Information given.** Each agent was given only the neutral participant brief (`test/agents/PARTICIPANT_BRIEF.md`) plus its persona. The brief describes ARTEMIS in lay terms, states the makers' idea ("an assistant that is deliberately limited to folders you chose, and that always asks first, can be more trustworthy and more likely to be used, without being much less useful than an assistant that has full access"), and says agreement, partial agreement and disagreement are all acceptable ("Nobody wants a flattering answer").
- **No cross-agent access.** Agents were told not to read other agents' reports, the test results, `Docs/` or `Tex/`. Each had its own private copy of the app and its own data.
- **Task.** Write first impressions, explore the prototype as the persona would (about 30 tool calls), compare with current tools, and then write a report with 12 fixed sections: persona, background, initial expectations, exploration summary, an observed-behaviour table, feedback, problem relevance (1-5), value (1-5), adoption (one of: would not use / might try / would use / would recommend), concerns, a three-part assessment of the central claim plus short questions, and implementation limitations.
- **Evidence.** Each report cites an action log (a timestamped script log of what the agent did and saw). Logs are in `tests/agents/work/ua-NN/actions.log` and in per-agent folders under `test/agents/` (`w04`, `work05`, `w06`, `work08`, `w09`, `w11`, `w13`, `work14`, `scratch15`, `Agent_12_actions.log`). I spot-checked 15 reports' behavioural claims against their logs (Appendix B).
- **Honesty rules given to agents.** Report only what was actually done; keep Observed behaviour, Expressed feedback and Interpretation apart; judge the idea, not the prototype's polish, and list prototype problems separately.
- **Classification rules** (fixed before any agent ran; from RESEARCH_CONTEXT.md, counted over 15 participants using each participant's final statements plus observed behaviour):

| Classification | Rule |
|---|---|
| Supported | at least 10 of 15 hold the claim, positive evidence appears across at least 3 of the 4 persona clusters, and no strong, well-reasoned contradicting pattern |
| Partially supported | 6 to 9 of 15 hold it, or 10 or more hold it but only in some persona clusters, or it holds with a significant condition that many participants attach |
| Not supported | 5 or fewer hold it, or a majority give a reasoned contradiction |
| Inconclusive | evidence thin (fewer than 8 participants engaged with the point), or contradictory in a way the data cannot resolve |

For H-C the three parts are scored separately and the classification cannot exceed the weakest part.

- **How I applied "hold".** The rules do not say what "hold" means for a three-way answer scale. I used this convention for every claim: *agree* is a strong hold; *partly* is a hold that carries a condition; *disagree* and *cannot say* do not hold. "Supported" needs at least 10 holders with most of them unconditional. Where at least 10 hold but most with conditions, the rule's "holds with a significant condition that many participants attach" clause makes it Partially Supported. Where this choice changes the outcome I give the alternative reading.
- **Coding of ambiguous answers.** Where an agent gave two answers (for example "Partly / disagree for me") I coded the first stated answer and record the ambiguity in Appendix A and in `Future-work/user_feedback_tally.json`. Half-point ratings (3.5, 2.5) are kept as given. If an agent gave two ratings (for their own work and for the concept) I coded the one for their own use and noted the other.
- **Not computed.** No percentages other than counts as "x of 15", no significance tests, no weighting.

## 5. Participant persona overview

**Cluster mapping.** The research context names four clusters (student, developer, freelancer or employee, sceptic or non-adopter) but does not publish which persona belongs to which. I assigned each persona to one cluster from its description, before looking at its ratings: students by occupation; developers by technical work or building software; freelancers and employees by working role; sceptic or non-adopter by the persona's stated stance toward AI or toward new software (compliance analyst, lecturer sceptical of AI summaries, manager who calls AI "a fad"). Three assignments are judgement calls and flagged: Agent_03 (a privacy-conscious sceptic but an engineering student; coded student), Agent_07 (a business student who builds apps with AI; coded developer), Agent_14 (a postgraduate student who ended as the only non-adopter; coded student by occupation, so the sceptic cluster does not contain her). Cluster sizes are 5, 4, 3 and 3, so cluster-level comparisons rest on very few cases.

"Tech level" and "AI attitude" are as the reports describe the persona; where a report does not give a tech level I wrote "not stated".

| Agent | Persona | Cluster | Tech level | AI attitude |
|---|---|---|---|---|
| 01 | Danish, 20, third-year CS undergraduate | student | technical (CS student); impatient with setup | daily ChatGPT and Copilot user; little thought about privacy |
| 02 | Ayesha, 21, second-year English literature and mass-communication student | student | low confidence | never used an AI assistant; nervous, has heard it "copies your data" |
| 03 | Bilal, 22, final-year electrical engineering student | student | high (dual-boots Linux) | privacy-conscious, sceptical of marketing; uses no AI on personal files |
| 04 | Mariam, 26, master's student writing a thesis | student | moderate | occasional ChatGPT; distrusts its citations |
| 05 | Imran, 38, senior backend developer | developer | high | sceptical of AI hype; likes diffs and control |
| 06 | Sana, 24, junior full-stack developer | developer | high | uses AI coding agents; dislikes approval prompts |
| 07 | Hamza, 19, first-year business student, "vibe coder" | developer | low to moderate (cannot read code) | trusts AI output too easily; excited by tools that "just handle it" |
| 08 | Zara, 29, freelance graphic designer and copywriter | freelancer-or-employee | moderate | uses some AI tools but never uploads client documents |
| 09 | Tariq, 45, freelance bookkeeper and tax consultant | freelancer-or-employee | low to moderate | has never used AI on work files; cautious, legal-risk minded |
| 10 | Farah, 33, operations coordinator at a logistics company | freelancer-or-employee | moderate | IT warned against pasting data into chatbots; open if approved |
| 11 | Naveed, 41, compliance analyst at a bank | sceptic-or-non-adopter | not stated | low enthusiasm; judges everything by approvability and auditability |
| 12 | Dr. Kamran, 48, university lecturer and researcher | sceptic-or-non-adopter | moderate | sceptical of AI summaries (hallucinated citations); protects student privacy |
| 13 | Mr. Aslam, 58, manager at a family-run manufacturing firm | sceptic-or-non-adopter | low | distrusts new software; calls AI "a fad" |
| 14 | Hira, 23, postgraduate student, strictly organised | student | moderate | finds ChatGPT "fine"; says she feels no need |
| 15 | Omar, 31, data analyst and productivity tinkerer | developer | high | moderately sceptical; runs full-access agents only in sandboxes |

## 6. Behavioural observations

All three layers are kept apart. **OBSERVED** is what the report's behaviour table and the action logs show the agent did and saw. **EXPRESSED** is what the persona said it thinks or feels. **INTERPRETATION** is my reading, and is marked as such.

### 6.1 OBSERVED: what participants did

Counts are from the reports' own tables and summaries; "did not try" means the report says so or does not mention it.

| Behaviour | Count | Agents |
|---|---|---|
| Opened Settings | 15 of 15 | all (Agent_06 later could not describe What it knows because its text was not captured) |
| Opened "What it knows" | 15 of 15 | all; 14 read the content (Agent_06's text did not come through) |
| Added a folder successfully | 14 of 15 | all except 09 (could never add one) |
| Hit "Type or browse to a folder first" or "Choose a folder first" at least once | at least 8 of 15 | 02, 03, 04, 07, 09, 10, 14, 15 (several say it was their own script typing in the wrong box; 09 repeated about 6 times and never got past it) |
| Viewed a tidy-up plan | 14 of 15 | all except 09 (09 pressed it with no folder and got "Choose a folder first") |
| Approved a tidy-up | 10 of 15 | 01, 02, 03, 05, 06, 07, 08, 11, 13, 15 |
| Used Undo after approving | 10 of 15 | the same ten; each report says the files came back |
| Viewed the plan and declined or did not approve | 4 of 15 | 04 (would move thesis files), 10, 12, 14 (would override her own structure); 08 declined once then approved |
| Asked at least one question about their file contents | 14 of 15 | all except 09 (09 asked but had no folder) |
| Received "NOT FOUND IN YOUR FILES" for something that was in the folder | 4 of 15 | 02 (resume), 07 (invoices/CV), 12 (summary of a file), 13 (latest invoice) |
| Received an appropriate "not found" for something not in the files | 1 of 15 | 04 (Jones 2020) |
| Typed an email-draft request and was asked for an address first | 5 of 15 | 01, 03, 08, 10, 12 |
| Had a later, different request answered by the pending email prompt | 4 of 15 | 01, 08, 10, 12 (07's delete request also got no visible reply; the report cannot say why) |
| Asked for a code fix | 3 of 15 | 05 and 06 (correct diff shown, file not edited), 15 (wrong fix) |
| Asked for or triggered a web search | 3 of 15 | 01, 03, 11; none approved it |
| Tested the folder boundary by asking for an outside path | 3 of 15 | 01 (reply not captured), 11 (refused), 15 (refused) |
| Asked it to read a secrets file inside the folder | 1 of 15 | 15 (it printed the fake token) |
| Used the per-folder cloud toggle | 1 of 15 | 03 (turned on and back off; sent nothing) |
| Pressed "Erase everything" | 1 of 15 | 03 (stopped at the confirmation, did not confirm) |
| Pressed "Approve, don't ask again" | 0 of 15 | seen by several, never pressed |
| Used or could hear voice | 0 of 15 | no microphone in the test browser; voice greeting started by itself for most |
| Connected email, saved or forgot a key | 0 of 15 | forbidden by the brief |

**Abandoned interactions (OBSERVED).**

- 09 stopped after about 20 tool calls because the folder never added; tidy-up, undo and file questions were never reached.
- 01's "Delete all the screenshots" was swallowed by the pending email prompt and not retried.
- 07's "delete random.zip" got no visible reply after about 35 seconds and was dropped.
- 02 gave up on the resume question after "NOT FOUND IN YOUR FILES".
- 03 abandoned asking about his notes after "I don't have access to your personal files right now".
- 10 abandoned the typed route to a tidy-up when the email prompt absorbed it, then used the button.
- 12 abandoned the grant-draft question when the email prompt answered it.
- 04, 10, 12 and 14 viewed the tidy-up plan and declined it.
- 13 left Settings as "too technical".

**Repeated interactions (OBSERVED).** Add-folder was retried by 02, 03, 04, 07 (about 4 times), 09 (about 6 times), 10, 14, 15. 08 asked about unpaid invoices three ways before a wording worked. 05 repeated the TODO request with the same non-answer. 06, 08 and 11 re-checked the disk after Undo; 02, 03, 05, 13, 15 also checked the disk.

**Points of hesitation (OBSERVED, from the table rows).**

- **Settings page:** 14 of 15 recorded hesitation or worry in the table row (04 "a small worry"; 15 recorded interest and noted the Gemini key).
- **Busy first screen:** hesitation recorded by 01, 02, 05, 06, 13.
- **Tidy-up plan:** hesitation at moving files by 04, 07 (long list), 08, 13, 14.
- **Cloud key shown as "Key saved" on a fresh copy:** 12 of 15 mention it (01, 02, 03, 04, 05, 08, 09, 10, 11, 12, 13, 15).

**Where the prototype held up (OBSERVED).** Where the plan card was shown it listed steps and risk lines for 03, 10, 13 and 15; the disk afterwards matched the plan for 02, 11 and 15; Undo restored the folder for all ten who tried it; 11 and 15 saw an outside path refused.

### 6.2 EXPRESSED: what participants said

- **Valued:** the plan before action (02, 03, 07, 10, 15), Undo (02, 07, 13, 05, 08, 15), "nothing is deleted" (01, 02, 13), the "What it knows" page with erase (02, 14, 09, 15), source file names on answers (04, 12, 08, 11), the per-folder cloud switch (03, 05, 08, 12).
- **Not valued:** tidy-up that groups by file type (02, 07, 08, 14, 15), voice (14 of 15 say no or probably not), email (many), Settings (14 of 15 recorded hesitation).
- **Sceptical of the boundary as a differentiator:** 01, 04, 05, 06, 14, 15.
- **Wanted proof rather than promises:** 03, 08, 09, 11, 15 asked to see or verify the boundary or a log.

### 6.3 INTERPRETATION (mine, not the agents')

- Interpretation: the behavioural evidence supports the *mechanism* (plan, approval, undo) more strongly than the *boundary* claim. What was tested was whether a tidy-up could be reversed, which worked in all 10 attempts. What was not tested was whether a mistake would be tolerated, because no participant experienced a harmful mistake.
- Interpretation: approval was never refused at the approval step. The four tidy-ups that were not approved were declined because the participant did not want the files moved, not because of the approval prompt itself. The data therefore says little about approval fatigue.
- Interpretation: the Settings page is the point where doubt was recorded most often (14 of 15), and it is also where the local-only story is weakest for a first-time user (cloud keys, "Key saved").
- Interpretation: the first-attempt Folders failure may be partly an automation artefact (several agents say their script typed into a hidden second input), so I do not treat 8 of 15 as a real-user failure rate.

## 7. Consolidated feedback

Counts are of agents whose report (any section) raises the theme. Coding is mine; lists are given so each count can be checked.

| # | Theme | Count | Agents |
|---|---|---|---|
| T1 | Undo plus visible plan is the part that builds trust or that they would use | 12 of 15 | 01, 02, 03, 05, 06, 07, 08, 10, 11, 13, 15, 14 (14 liked the plan list and "What it knows", not Undo; she did not test Undo) |
| T2 | Scope limit is reassuring or the reason they could consider it | 9 of 15 | 02, 03, 05, 08, 09, 10, 11, 12, 15 |
| T3 | The scope limit is not their main reason or is not a differentiator (undo, sources, usefulness or existing tools matter more) | 6 of 15 | 01, 04, 05, 06, 14, 15 |
| T4 | Source-cited answers raise trust; they want exact line, page or quote, not `file:1` | 4 of 15 name source citation as the trust driver (04, 08, 11, 12); 04 and 12 ask for exact location | 04, 08, 11, 12 |
| T5 | Boundary and privacy claims must be verifiable (log, network list, OS enforcement), not just text | 6 of 15 | 02, 03, 08, 09, 11, 15 |
| T6 | Cloud options or "Key saved" in Settings undermine the local-only story | 12 of 15 mention the saved key | 01, 02, 03, 04, 05, 08, 09, 10, 11, 12, 13, 15 |
| T7 | Settings and first screen too technical, long, or busy | 6 of 15 for Settings jargon or length; 5 for a busy first screen | Settings: 01, 02, 06, 07, 13, 14. First screen: 01, 02, 05, 06, 13 |
| T8 | Answer reliability: NOT FOUND, no-folder confusion, wrong, invented or partial answers | 13 of 15 | 01, 02, 03, 04, 05, 06, 07, 08, 10, 11, 12, 13, 15 |
| T9 | Tidy-up is crude (file-type buckets), ignores existing structure, or they do not want files moved | 7 of 15 | 02, 04, 07, 08, 13, 14, 15 |
| T10 | Email flow asks for an address before a draft, and the pending prompt swallows later requests | 5 of 15 for address-first; 4 for swallowing | address-first: 01, 03, 08, 10, 12. Swallowing: 01, 08, 10, 12 |
| T11 | Ask-first is too much for small things; want fewer or smarter approvals | 5 of 15 | 01, 06, 07, 08, 10 (09 and 13 fear "Approve, don't ask again" rather than seek it) |
| T12 | Undo cannot fix a sent email, a leaked file or a wrong claim | 9 of 15 | 02, 03, 04, 08, 09, 10, 11, 12, 14 |
| T13 | Does not beat what they use now (ChatGPT, grep, coding agent, Cursor, journal or Notion, own scripts) | 6 of 15 | 01, 05, 06, 07, 14, 15 |
| T14 | Needs organisational approval or policy clearance | 2 of 15 | 10, 11 |
| T15 | Needs a trusted person to vouch or install it | 3 of 15 | 02, 13, 09 (asks who is accountable) |
| T16 | Audit or activity log not visible or not exportable | 5 of 15 | 03, 08, 09, 11, 15 |
| T17 | Slow replies from the shared local model | 11 of 15 report 10 to 50 seconds | 01, 02, 03, 04, 05, 08, 10, 11, 12, 14, 15 |
| T18 | Wanted code diffs to be appliable, or more of a developer tool | 3 of 15 | 05, 06, 15 |
| T19 | Remote-access relay is an extra trust surface | 3 of 15 | 03, 05, 11 |
| T20 | Format and platform compatibility (PDF, Office or Outlook, Linux) | 3 of 15 | 03 (Linux), 04 (PDFs), 10 (Office, Outlook) |
| T21 | Sensitive files in a granted folder are readable on request | 1 of 15 | 15 |
| T22 | Liability and accountability for wrong output | 1 of 15 explicit | 09 (11 raises auditability under T16) |

**Number raising significant concerns.** I count a concern as significant if the participant ties it to a condition for trying, using or avoiding the product in section 9 or 10 of their report. On that definition 15 of 15 raised at least one significant concern. 12 of 15 raised the pre-saved cloud key specifically.

**Concerns, with counts** (section 10 and 12 coded together; the list above is the full table): answer reliability 13; cloud key saved 12; speed 11; tidy-up quality 7; undo limits 9; verification 6; Settings jargon 6; existing tools suffice 6; approval burden 5; address-first email 5; audit log 5; busy first screen 5; policy 2; remote relay 3; compatibility 3; trusted-person 3; sensitive-file guard 1; liability 1.

## 8. Quantitative summaries

All numbers are counted from the reports. Rating means are sums divided by 15. Appendix A holds the per-agent extraction.

### 8.1 Problem relevance (1-5), by agent

| Agent | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Relevance | 4 | 4 | 3 | 4 | 2 | 3 | 4 | 4 | 3 | 4 | 2 | 4 | 3 | 2 | 3 |

| Statistic | Value |
|---|---|
| Sum | 49 |
| Mean | 3.27 (49/15) |
| Median | 3 |
| Distribution (rating: count) | 1: 0; 2: 3 (05, 11, 14); 3: 5 (03, 06, 09, 13, 15); 4: 7 (01, 02, 04, 07, 08, 10, 12); 5: 0 |

Agents 03, 07 and 09 qualified the rating (03 sees it more as a privacy problem than a productivity one; 04 gave 4 for resuming work and 2 for routine tidying; 14 imagines 3 to 4 for classmates but rated her own 2).

### 8.2 Value of the proposed solution (1-5), by agent

| Agent | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Value | 3 | 3 | 3 | 3.5 | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 2.5 | 2 | 3 |

| Statistic | Value |
|---|---|
| Sum | 42 |
| Mean | 2.8 (42/15) |
| Median | 3 |
| Distribution (rating: count) | 2: 3 (05, 09, 14); 2.5: 1 (13); 3: 10 (01, 02, 03, 06, 07, 08, 10, 11, 12, 15); 3.5: 1 (04); 1, 4 and 5: 0 |

Coding notes. Agent_05 gave 2 for his work and 3 for the concept; Agent_09 gave 2 for what he could use and 3 for the concept; Agent_11 gave 3 for home and 1 to 2 for work. I coded 2, 2 and 3. Sensitivity: coding 05, 09 and 11 at their concept or home values (3, 3, 3) gives a mean of 2.93; coding 11 as 1.5 gives 2.7. The median is 3 in all three readings. No participant rated value above 3.5.

### 8.3 Adoption category

| Category | Count | Agents |
|---|---|---|
| Would not use | 1 | 14 |
| Might try | 14 | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 15 |
| Would use | 0 | none |
| Would recommend | 0 | none |

Coding notes: 05 wrote "might try (leaning 'would not use' for daily work)", coded might try. 11 would try at home only and would not use at work, coded might try. 14 said she "might mention it to a friend" but chose would not use. Many "might try" answers are conditional (13 needs his nephew to install it; 10 needs IT approval; 09 would use only an invented test folder).

### 8.4 Central claim, three parts

(a) Would it make you trust it more than a full-access assistant? (b) Would that make you more willing to use it? (c) Does the limitation cost too much usefulness? For (c), "disagree" means "it does not cost too much", which favours H-C.

| Answer | (a) trust | (b) willingness | (c) usefulness cost |
|---|---|---|---|
| Agree | 6 (05, 08, 09, 10, 11, 12) | 1 (08) | 0 |
| Partly | 9 (01, 02, 03, 04, 06, 07, 13, 14, 15) | 14 (all except 08) | 3 (06, 08, 15) |
| Disagree | 0 | 0 | 6 (02, 04, 11, 12, 13, 14) |
| Cannot say | 0 | 0 | 6 (01, 03, 05, 07, 09, 10) |
| No answer | 0 | 0 | 0 |

Ambiguous: Agent_06 (b) "partly / disagree for me", coded partly. Agent_15 (b) "partly agree", coded partly. Agent_01 (c) "Cannot say / probably not", coded cannot say. Agent_14 (c) "disagree for my uses; cannot say for others", coded disagree.

### 8.5 Short questions

| Question | Agree | Partly | Disagree | Cannot say | No answer |
|---|---|---|---|---|---|
| Q1 Are people really losing time to interruptions and routine file work? | 8 (01, 02, 04, 07, 08, 10, 12, 15) | 7 (03, 05, 06, 09, 11, 13, 14) | 0 | 0 | 0 |
| Q2 Is wanting an assistant with broad access a real barrier for you? | 10 (02, 03, 05, 08, 09, 10, 11, 12, 13, 15) | 2 (04, 07) | 3 (01, 06, 14) | 0 | 0 |
| Q3 Would you accept one mistake if undo is easy? | 7 (01, 03, 05, 06, 07, 08, 15) | 8 (02, 04, 09, 10, 11, 12, 13, 14) | 0 | 0 | 0 |

| Q4 Ask before every change, or act and let me undo? | Count | Agents |
|---|---|---|
| Ask first | 8 | 02, 03, 04, 05, 09, 11, 13, 14 |
| Mixed (ask for sending or batches, act-then-undo for small things) | 6 | 01, 07, 08, 10, 12, 15 |
| Act then undo | 1 | 06 |
| No answer | 0 | none |

Coding notes. Q1: Agent_04 wrote "Agree for resuming and re-finding... Partly for routine file work", coded agree. Q3: Agents 03 and 08 wrote agree for file moves and disagree for anything that leaves the computer; coded agree. Q4: Agents 03, 05 and 14 wrote ask first but allow act-then-undo for trivial moves; coded ask first, which is the conservative reading (including them as "granularity wanted" would give 10 of 15 in the non-flat group; see S5).

**Q5, which abilities would you use** (named by the participant; some conditional):

| Ability | Clear yes | Conditional or "maybe" | No or probably not |
|---|---|---|---|
| Questions or finding files over their own notes and files | 12 | 3 (05 if retrieval accurate, 13 only if it is right nearly every time, 14 "maybe") | 0 |
| Tidy-up | 7 (01, 02, 06, 07, 10, 11, 15) | 4 (03, 05, 08, 12) | 4 (04, 09, 13, 14) |
| Voice | 1 (07, who could not test it) | 0 | 14 |
| Email drafts | 4 (08, 09, 10, 12) | 2 (01, 13 a letter, not tried) | 9 |
| Code diff suggestions | 2 (05, 06) | 1 (03) | rest |
| "What it knows" or erase page | 4 (02, 11, 14, 15) | 0 | not named by others |
| "Where did I leave off" | 3 (04, 09, 10) | 0 | not named by others |

**Q6, what would make setup too much effort** (counts of agents naming each; lists given):

| Setup cost named | Count | Agents |
|---|---|---|
| Keys, app passwords or email setup | 13 | 01, 02, 03, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14 |
| Typing or retyping folder paths | 8 | 02, 04, 07, 09, 10, 12, 13, 15 |
| Choosing, tuning or downloading a model, or model jargon | 9 | 01, 03, 05, 08, 09, 10, 13, 14, 15 |
| Something else (re-explaining folders, admin rights, security review, special file format) | 5 | 04, 06, 10, 11, 12 |

All 15 named at least one setup cost.

### 8.6 Counts by persona cluster

| Cluster (n) | Mean relevance | Mean value | Adoption | (a) agree / partly | (b) agree / partly | (c) disagree / partly / cannot say |
|---|---|---|---|---|---|---|
| Student (5: 01, 02, 03, 04, 14) | 3.4 (17/5) | 2.9 (14.5/5) | 4 might try, 1 would not use | 0 / 5 | 0 / 5 | 3 / 0 / 2 |
| Developer (4: 05, 06, 07, 15) | 3.0 (12/4) | 2.75 (11/4) | 4 might try | 1 / 3 | 0 / 4 | 0 / 2 / 2 |
| Freelancer or employee (3: 08, 09, 10) | 3.67 (11/3) | 2.67 (8/3) | 3 might try | 3 / 0 | 1 / 2 | 0 / 1 / 2 |
| Sceptic or non-adopter (3: 11, 12, 13) | 3.0 (9/3) | 2.83 (8.5/3) | 3 might try | 2 / 1 | 0 / 3 | 3 / 0 / 0 |

| Cluster | Q1 agree / partly | Q2 agree / partly / disagree | Q3 agree / partly | Q4 ask / mixed / act |
|---|---|---|---|---|
| Student | 3 / 2 | 2 / 1 / 2 | 2 / 3 | 4 / 1 / 0 |
| Developer | 2 / 2 | 2 / 1 / 1 | 4 / 0 | 1 / 2 / 1 |
| Freelancer or employee | 2 / 1 | 3 / 0 / 0 | 1 / 2 | 1 / 2 / 0 |
| Sceptic or non-adopter | 1 / 2 | 3 / 0 / 0 | 0 / 3 | 2 / 1 / 0 |

Cluster sizes are 3 to 5, so any cluster difference is only a pointer for further research. One pattern worth noting: no student agreed outright on (a), while 5 of the 6 who agreed on (a) were in the freelancer or sceptic clusters (11 and 12 are sceptics; 08, 09 and 10 are freelancers or employees; 05 is a developer).

### 8.7 Concerns, with counts

See table T1 to T22 in section 7. 15 of 15 raised at least one significant concern; the most frequent are answer reliability (13), pre-saved cloud key (12), slow replies (11) and the limits of undo (9).

## 9. Qualitative analysis

### 9.1 Motivations

- **Fear of losing or scrambling files** drove interest in tidy-up plus undo (02 "my biggest fear is losing an essay"; 07 got burned by an AI renaming a directory; 01 lost an assignment once).
- **Confidentiality or contractual obligations** drove interest in the boundary (08 NDAs; 09 client tax data; 12 student submissions; 10 IT policy; 11 bank rules).
- **Traceable answers** drove interest among the research-minded (04, 12).
- **Control and inspectability** drove the developers and the privacy-minded (03, 05, 15).

### 9.2 Objections

- It does not do what they need better than what they have (01, 05, 06, 07, 14, 15).
- The promise is words on a screen, not a verifiable property (03, 08, 09, 11, 15).
- The local model's quality is the bigger limit, not the folder boundary (05, 08, 15, 01).
- Undo does not protect against wrong claims, sent email or leaks (T12, 9 of 15).
- Setup and Settings are too technical for non-technical personas (02, 07, 13).

### 9.3 Differences across personas

- **Students** were the least moved by the boundary: none agreed outright on (a), and 01 and 14 disagreed that broad access is a barrier. They valued tidy-up and undo where they had a messy folder (01, 02, 07) and rejected the tidy-up where they were already organised (14).
- **Developers** treated the approve-first design as a cost (06) or as the right control for their own repos (05), and said the tool was not a developer tool because it would not apply code edits.
- **Freelancers and employees** were the clearest on trust and willingness: 3 of 3 agreed on (a) and the only (b) "agree" is 08. Their condition was contractual or organisational (NDAs, client law, IT approval) rather than personal taste.
- **Sceptics and non-adopters** agreed that broad access is a barrier (3 of 3) and all three said the limit does not cost them much. They also wanted proof, approval or a helper to install it before any use (11, 13).
- Participants with an existing system or tools (14, 05, 15) found little problem to solve; those with no system (01, 02, 07, 08, 13) found the file-finding and tidy-up relevant.

### 9.4 Contradictions between participants

- **Tidy-up:** liked by 01, 02, 06, 07, 10, 11 (as a plan card), 15; disliked or refused by 04, 13, 14, and judged crude by 02, 07, 08.
- **Source of trust:** the boundary (08, 09, 12), Undo (01, 02, 13), sources (04, 12), verification (03, 11, 15).
- **Approval:** ask-first as essential (02, 09, 11, 13) versus a burden (06, 07).
- **Privacy:** a hard barrier (09, 12, 11, 10) versus not a concern (01, 06, 14).
- **Local model:** reassuring to those who want data to stay home (03, 08, 12), a disadvantage to those who expect weaker answers (01, 05, 06).

### 9.5 Contradictions between behaviour and stated opinion

Interpretation throughout.

- **Agent_13** said "I do not want it moving my files" and wanted a "never move, only find" default, yet approved the tidy-up in his second session (he says only because it could be undone, then checked it).
- **Agent_07** said ask-first makes him feel safe, then admitted he clicks yes without reading and approved the plan after reading only a summary line. He names this himself as a gap.
- **Agent_09** reported a "might try" and rated concept value 3, but never got past adding a folder, so the stated openness has no behavioural support.
- **Agent_03** said tidy-up has no value for him and that his notes Q&A is what he wants, then ran the tidy-up and undo (and verified the disk), which he then called the one claim he could verify.
- **Agent_10** rated the problem 4 (daily) but did not approve any change or test Undo.
- **Agent_06** said approval prompts are what he turns off, but accepted the single batch approval without comment and did not test the "ask every time" cost.
- **Agent_14** said she does not lose context, then found the answers correct only because they came from her own journal, which matches her statement.
- **Agent_05** said he would not believe undo until he saw it; the observed behaviour (check the disk after undo) matches.

### 9.6 Areas for further research

- Whether trust gains come from the folder boundary or from the plan, approval and undo mechanism, which this study could not separate.
- Whether people tolerate a real mistake with undo (no participant experienced one).
- Whether approval fatigue builds over repeated sessions (single sessions only).
- Whether the tool must offer exact search, exact citations or other behaviours to be preferred over grep, chatbots and notes systems.
- How a persona with no existing system (no journal, no Notion) compares with one that has one.
- How participants who cannot verify a boundary (02, 13) behave when someone they trust installs it.

## 10. Hypothesis-by-hypothesis assessment

### 10.1 H-C: central hypothesis

**As stated.** "restricting an assistant's scope to explicitly granted folders increases user trust and adoption without meaningfully reducing usefulness" (Report abstract, 1, 1.1).

#### Part 1: trust increased

- **Supporting observations.** (a): 6 agree, 9 partly, 0 disagree, 0 cannot say. Agree came from 05 (developer), 08, 09, 10 (freelancer or employee), 11, 12 (sceptic); no student agreed outright. The boundary refusal was seen by 11 and 15, and the folder switch by 03. 03 diffed the folder after Undo and found it identical.
- **Contradictory observations.** Many "partly" answers attach a condition: the boundary is enforced by the app, not the OS, and the claim cannot be checked (03); the boundary is not what raises trust, Undo or sources are (01, 02, 04, 13, 15); trust needs a person to vouch for it (02, 13); safe-feeling exceeds real safety because the user clicks yes (07); trust needs IT approval (10). 15 saw the model print a secrets file and invent CSV numbers inside the allowed folder.
- **Relevant participant feedback.**
  - Agent_03: "I only trust it as much as I can verify the boundary."
  - Agent_04: "I would accept the limit, but I would not choose the product because of it."
  - Agent_10: "I would trust it because it is local and approved, not just because I picked folders."
  - Agent_12: "A limit on folders does not stop a small model from making things up inside those folders, so the idea only earns my trust if the source check is strict."
- **Evidence limitations.** No participant used a real full-access assistant in the session, so every comparison with "full access" is hypothetical. The persona descriptions of 09, 11, 12 were written with privacy and compliance concerns built in. LLM agreeableness may inflate "partly".
- **Classification: Partially Supported.** Reasoning: 15 of 15 hold it at least partly, 6 outright. The 9 "partly" answers attach conditions (verifiability, other causes of trust), which the rules treat as a significant condition many attach. Positive evidence is spread over all four clusters, but only 6 are unconditional, so Supported is not reached.

#### Part 2: adoption interest

- **Supporting observations.** (b): 1 agree, 14 partly, 0 disagree. All 15 expressed some willingness to try. 14 of 15 chose "might try".
- **Contradictory observations.** No participant chose "would use" or "would recommend". 14 "might try" answers are conditional on answer quality, ease of setup, an installer, or IT approval. Four participants said the boundary is not their reason to try or not (01 "What gets me to use it is that it is quick and has undo, not the boundary itself."; 04; 06 "Constant asking pushes me away; the bounded part is neutral"; 14). 06 disagreed in part. Agent_09 never got past adding a folder.
- **Relevant participant feedback.**
  - Agent_14: "but I am not nervous enough to need it"
  - Agent_06: "Constant asking pushes me away; the bounded part is neutral."
  - Agent_05: "But a safe tool that does not do anything I need is a safe toy."
  - Agent_08: "For me the limit is the selling point."
- **Evidence limitations.** Expressed intent only; there was no real choice between two products. "Might try" is the weakest positive category, and an LLM persona asked to choose a category tends toward the middle.
- **Classification: Partially Supported, and the weakest part.** Reasoning: under my convention 15 of 15 are at least partly willing, with significant conditions attached by 14. If "hold" were read as the explicit "agree" only, the count would be 1 of 15 and the rule would give Not Supported. I use the "partly counts as a conditional hold" reading for consistency across claims, but I flag that this part is the one most sensitive to the reading, and that no one reached "would use".

#### Part 3: usefulness not meaningfully reduced

- **Supporting observations.** (c): 6 said the limitation does not cost too much, 3 said partly, 0 said it costs too much, 6 cannot say. The disagree answers came from students (02, 04, 14) and sceptics (11, 12, 13), who said their work lives in a few folders.
- **Contradictory observations.** 06 (partly): for coding the tool will not edit code and explores files weakly. 15 (partly): work that spans repos, downloads and browser would need many folders, "which starts to resemble broad access". 08 (partly): patchy answers cost more than the folder limit (her interpretation: prototype quality). No developer or freelancer-or-employee said "disagree". 6 of 15 could not say, mostly because they did not reach enough features (01, 03, 05, 07, 09, 10).
- **Relevant participant feedback.**
  - Agent_15: "A scoped assistant is a limitation when my work spans repos, downloads, and the browser; I would need to add a lot of folders, which starts to resemble broad access."
  - Agent_05: "The folder limit did not hurt me (my work lives in a few repos anyway); the model quality hurt more than the boundary."
- **Evidence limitations.** Usefulness cost cannot be separated from model quality and prototype defects (agents 05, 08, 15 say so). Test folders were small, invented and single. Nobody tested a task that needed several folders or a large collection.
- **Classification: Partially Supported (low confidence).** Reasoning: 9 of 15 gave a substantive answer (6 disagree, 3 partly), above the 8-participant minimum, so the rule does not force Inconclusive. 6 to 9 hold, which falls in the Partially Supported band. The 6 "cannot say" answers and the confound with model quality limit confidence.

#### H-C overall

**Partially Supported.** All three parts land at Partially Supported; the cap at the weakest part gives the same result. The weakest is part 2 (adoption), where no participant went beyond "might try" and the boundary was often described as secondary to usefulness and ease. A stricter reading of "hold" would put part 2 at Not Supported and so cap H-C there; I record that sensitivity rather than choose it.

### 10.2 S1: problem relevance

- **As stated.** "people lose substantial time re-establishing context after interruptions and on routine file work (2.3)."
- **Supporting.** Q1: 8 agree, 7 partly, 0 disagree. Relevance mean 3.27, median 3, 7 rated 4. Participants described weekly or daily cost for 01, 02, 04, 07, 08, 10, 12.
- **Contradictory.** 3 rated 2 (05, 11, 14), each with an existing system (git and shell notes, managed shares, journal and Notion). No one rated 5. Many described the problem as real but modest or "not a disaster" (01, 03, 05, 06, 11, 13). The resume-context half was real mainly for 04 and 10; 14 rarely loses context.
- **Feedback.** Agent_14: "But I have to be honest: I do not lose context." Agent_01: "That is exactly what I want for Downloads."
- **Limitations.** Persona descriptions fixed the ratings in part (14 was written as organised). Each persona rated its own situation, not a population.
- **Classification: Partially Supported.** Reasoning: all 15 at least partly agree and none disagree, but "substantial" is not reached: 8 outright agree (6 to 9 band), the rest qualify the size of the problem, the average rating is just above 3, and no one rated 5.

### 10.3 S2: access bargain

- **As stated.** "distrust of broad-access assistants is a real barrier to adoption (2.3, 2.9.2)."
- **Supporting.** Q2: 10 agree, 2 partly, 3 disagree. Agree appears in all four clusters (student 02, 03; developer 05, 15; freelancer or employee 08, 09, 10; sceptic 11, 12, 13). Reasons given are concrete: NDAs (08), client tax data (09), IT policy (10), bank rules (11), student data (12).
- **Contradictory.** 01 ("I use broad cloud tools already"), 06 ("my code is not secret") and 14 disagreed, each with a reason; 04 and 07 said partly. Two of the three dissenters are young heavy chatbot users, so there is a reasoned minority pattern among students, though not a strong one: in the student cluster 2 of 5 agreed.
- **Feedback.** Agent_09: "Right now my choice is 'no AI' or 'AI that sees everything', and I pick 'no AI'." Agent_03: "Broad access is the reason I use none." Agent_01: "It is not a barrier for me" (and "I use broad cloud tools already.")
- **Limitations.** This is expressed opinion; nobody was observed being blocked or refusing something. Several personas (09, 10, 11, 12) were written with a confidentiality role that makes this answer close to given. The brief's wording frames the issue.
- **Classification: Supported (with a selection caveat).** Reasoning: 10 of 15 agree, in all four clusters, and the dissent (3 of 15) is a minority with its own reasons rather than a strong contradicting pattern. The caveat is that the personas were chosen with the barrier partly built in.

### 10.4 S3: trust in bounded scope

- **As stated.** "a workspace-only assistant is rated more trustworthy than a full-access one (A.3, F5)."
- **Supporting.** This is the same evidence as H-C(a): 6 agree, 9 partly, 0 disagree. Each at-least-partly answer says the bounded design is safer than a full-access one (03 "a bigger attack surface", 05 "trust it more than a full-access agent", 11 "easier to reason about and defend").
- **Contradictory.** The trust gain was often credited to other features (Undo, sources, the plan card). The boundary's enforcement could not be verified (03, 11). 15 saw reads allowed inside the folder (a secrets file printed).
- **Feedback.** Agent_13: "the Undo button did more for my trust than the folder limit." Agent_15: "Inside the folder it happily printed my secrets file."
- **Limitations.** No real full-access assistant was compared. 
- **Classification: Partially Supported.** Reasoning: direction is consistent (15 at least partly), but only 6 outright and 9 hold it with a condition, so it falls in the partial band under the rule.

### 10.5 S4: forgiveness with undo

- **As stated.** "users tolerate a single mistake if recovery is easy, so visible undo matters more than perfection (F6)."
- **Supporting.** Q3: 7 agree, 8 partly, 0 disagree. Undo was used by 10 and worked in each. Participants named Undo as the best or trust-making feature (02, 07, 13, 01, 05, 15). 13: "One mistake with a working undo, yes; two, I stop."
- **Contradictory.** The "partly" answers limit the claim to file moves: not for sent email (03, 08, 10), not for wrong claims or citations (04, 09, 12), not for records at work (11). Several want accuracy as well as undo (04, 12, 15). 13: "one success does not remove my fear".
- **Feedback.** Agent_03: "an undo cannot un-send data." Agent_02: "The undo button is the best part, because my biggest fear is losing an essay." Agent_11: "Undo-only is not acceptable to me."
- **Limitations.** No participant experienced a harmful mistake; "tolerate" is hypothetical. The undo covered only a tidy-up. "Matters more than perfection" was not tested; the evidence is that undo mattered a lot and perfection also mattered.
- **Classification: Partially Supported.** Reasoning: 7 outright agree (6 to 9 band); with the 8 who agree only for reversible file moves, the claim holds only with a significant condition. It does not support "more than perfection" for anything beyond reversible file operations.

### 10.6 S5: approval preference is split

- **As stated.** "users are divided between approve-first and act-then-undo, so approval granularity must be configurable (2.9.2)."
- **Supporting.** Q4: 8 ask first, 6 mixed, 1 act then undo. Both poles exist, and the "mixed" answers describe different granularity by action type (ask for sending or batches, act-then-undo for small moves): 01, 07, 08, 10, 12, 15. 06 asked for a per-folder trust level. If 03, 05 and 14 (ask first, with act-then-undo for trivial moves) are counted, 10 of 15 want something other than a flat ask-first.
- **Contradictory.** The headline answer is ask-first for 8 of 15; only 1 chose act-then-undo. 11: "Undo-only is not acceptable to me." The sample is not evenly divided between two poles; it leans to ask-first with exceptions. Nobody used "Approve, don't ask again" and 09 and 13 would avoid it.
- **Feedback.** Agent_01: "Ask once for a batch (like the tidy-up), then let me undo; I would be annoyed asking for every small thing." Agent_08: "Asking for every small change would wear me out." Agent_11: "Undo-only is not acceptable to me."
- **Limitations.** Expressed only; nobody tried different granularity. The prototype offers one granularity switch that nobody used.
- **Classification: Partially Supported.** Reasoning: using each participant's headline answer, 7 of 15 do not choose flat ask-first (the "split" evidence), which is in the 6 to 9 band. Counting the three who add exceptions would reach 10 and meet the numeric threshold, but it requires coding "ask first with exceptions" as a different preference, which I did not do. I chose the conservative coding. The direction (granularity should be configurable) is consistent with the answers; it was never tested.

### 10.7 S6: retention risks

- **As stated.** "habit fit and an untrusted mistake are the main reasons to stop; approval fatigue is smaller (F7)."
- **Supporting.** This claim is about stopping, and no participant used it over repeated sessions. I coded each agent's primary stated "avoid or stop" condition from section 9: trust breach or wrong or fabricated output 9 (02, 03, 04, 08, 09, 11, 12, 13, 15); habit fit or no need 2 (05, 14); approval or friction 2 (06, 07); speed or usefulness 1 (01); organisational approval 1 (10). So approval fatigue is a primary stop reason for 2, fewer than the 9 for trust or mistake.
- **Contradictory.** Of the 9 "trust or mistake" reasons, only 5 are about a mistake as such (04, 12, 13, 15, and 02's unapproved change); 4 are about data leaving or a cloud default (03, 08, 09, 11), which is a privacy event, not an error. Habit fit was primary for only 2, though more mention it (01 ChatGPT is free, 06 coding agent, 15 own scripts). Approval-related annoyance appears in 5 reports overall (01, 06, 07, 08, 10).
- **Feedback.** Agent_12: "What would make me avoid it: one more fabricated reference." Agent_13: "One mistake with a working undo, yes; two, I stop." Agent_06: "Constant asking pushes me away".
- **Limitations.** The report format did not ask about retention directly; I inferred stop reasons from "what would change my mind" statements. No repeated use, so "approval fatigue" was never experienced over time. The claim omits answer quality and policy, which were prominent.
- **Classification: Partially Supported (low confidence).** Reasoning: 11 of 15 give a primary reason that fits one of the two named causes (broadly read), and approval fatigue is primary for only 2, in line with the claim; but the mistake leg is thin when read narrowly, the habit-fit leg is thin, and this is inferred, not observed. The rules do not allow Supported when most holders attach a significant condition, and I did not use Inconclusive because 15 participants addressed stop conditions.

### 10.8 S7: feature demand

- **As stated.** "session resume, notes synthesis and folder tidy are wanted most; speech least (F8)."
- **Supporting.** Questions or finding over notes and files: 12 clear yes and 3 conditional yes. Tidy-up: 7 clear yes, 4 conditional, 4 no. Speech: 14 of 15 say they would not use it (07 would, but could not test). 04 valued resume and synthesis with sources; 09 and 10 named "where did I leave off".
- **Contradictory.** Session resume was named as a wanted ability by only 3 (04, 09, 10). In the observed attempts it produced a generic answer for 01 and 10, a correct answer from the persona's own journal for 14, and a clear value for 04. Tidy-up was rejected by 4 (04, 09, 13, 14) and judged crude by others. Notes synthesis proper (comparing across notes) was tested by 04 only.
- **Feedback.** Agent_13: "If it just answered 'where is that file' reliably, I would use that." Agent_04: "Each claim came with a file name. That is the first time a chatbot has made me feel I could check it."
- **Limitations.** Voice was untestable (no microphone, no audio), so "speech least" is only stated. Test folders were tiny.
- **Classification: Partially Supported.** Reasoning: finding and asking over notes was wanted by all 15 (partly conditional), tidy-up by 7 to 11, speech the least; but session resume was named by only 3, so the claim's three-item ranking is not matched. The speech ranking could not be tested.

### 10.9 S8: onboarding

- **As stated.** "effortless onboarding is a condition for continued use (F9)."
- **Supporting.** Q6: all 15 named a setup cost; 13 named keys, app passwords or email setup; 8 named typing folder paths. Observed: at least 8 hit the Folders failure on the first try, 09 was blocked entirely, 07 nearly abandoned after about 4 repeats. Participants tied adoption to setup: 01 "If it takes more than a minute I will drop it"; 02 "setup that is only 'pick a folder'" as a condition for "would use"; 13 needs his nephew to install it; 07 "if setup is one click".
- **Contradictory.** None said onboarding is unimportant. Several of the observed failures were their automation typing in a hidden second input, so friction for a real user is not established. Continued use (as distinct from trying) was not observed.
- **Feedback.** Agent_01: "If it takes more than a minute I will drop it."
- **Limitations.** Q6 ("what would make setup too much effort") presupposes the answer, so 15 of 15 may be elicited by the question. The Folders failure is an implementation defect that inflates observed friction. Single session, so "continued use" is expressed only.
- **Classification: Supported (with a leading-question caveat).** Reasoning: all 15 name setup limits, positive evidence appears in all four clusters, and there is no contradicting pattern; at least 8 saw real friction. The caveat is that the evidence is partly elicited and not observed over time.

## 11. Implementation limitations that affected the evidence

Kept separate from the idea. These are defects of the prototype or the test set-up that the participants reported and I could confirm in the logs where noted. Each may have lowered or raised the apparent value of the idea.

| Limitation | Agents | Likely effect on the evidence |
|---|---|---|
| **Folders box.** Typing a path and pressing Enter or Add failed with "Type or browse to a folder first" until the right box was used; 09 never got a folder added; 07 retried about 4 times. Several agents say their script typed into a hidden second input. | at least 02, 03, 04, 07, 09, 10, 14, 15 | Inflates S8 friction; removed one participant (09) from all feature tests; may have lowered ratings by irritation. Unclear how much is an automation artefact. |
| **Questions answered as if no folder existed** even though one was added (assistant asked to be pointed to a folder). | 03, 04 (first questions), 05, 06, 08 | Lowers perceived usefulness and may have been read as a cost of the boundary (which it is not). Confounds H-C part 3. |
| **"NOT FOUND IN YOUR FILES"** returned for items present in the folder (resume, invoices and CV, a summary, the latest invoice). Placeholder file contents were tiny. | 02, 07, 12, 13 | Lowers value ratings; may be read as an effect of the small local model or the placeholder content rather than the concept. |
| **Fabricated or wrong answers.** With no folder added it gave invented CSV numbers and said the file was "loaded now" (15); it invented a file name "Ali_Assignment_2.pdf" (12); a wrong code fix (15); a wrong citation (11, random.zip). | 11, 12, 15 | Reduces trust in answers; participants kept it separate from the boundary only partly (12). |
| **Tidy-up behaviour.** Everything sorted into generic "Documents" and "Images" (and moved the participant's own screenshot files); proposed restructuring an already organised folder; one "Documents" folder for all files. | 02, 04, 07, 08, 13, 14, 15 | Depresses value for organised users and may exaggerate the tidy-up objection; also is the main feature everyone tried, so it dominates the evidence. |
| **Pending email question swallowing messages.** A drafted email asked for an address first; later unrelated requests were answered with "I still need an email address" (log confirms for 01, 08, 10, 12). | 01, 08, 10, 12 | Interrupts testing; participants attribute it to the product. Also biases the abandoned-interaction counts. |
| **Cloud key shown as "Key saved"** (Gemini) on a clean private copy. | 12 of 15 | Probably a test-environment artefact (Agent_02's interpretation); cannot be confirmed from the reports. It raised privacy doubts in sceptical personas and weakens the local-only story. May inflate T6 and lower trust (a). |
| **"What changed"** said "Nothing has changed outside ARTEMIS" right after it moved files; no visible, exportable activity log. | 01, 10, 11, 15; log request: 03, 08, 09, 11, 15 | Weakens the audit and verification story; participants interpreted it as missing accountability. |
| **Source references end in `:1`;** no page or line. | 04, 12 | Weakens the traceability value. |
| **Voice** started on its own and "No microphone found"; unticking did not always stick (06). | 13 of 15 list it | Voice features and the S7 "speech least" claim were untestable. |
| **Harness side effects.** Participants' own screenshots were saved in the test folder, changing file counts and being moved by tidy-up; folder list empty after restarts (07, 13). | 02, 03, 07, 11, 13, 14 | Distorts counts and tidy-up plans. |
| **Slow replies** (10 to 50 s), shared model; **duplicate tab bars** in the DOM. | 11 of 15; 01, 02, 03, 05, 07, 09 | Lowers perceived quality; the single shared model also couples participants' timing. |
| **Silent or unobserved replies.** 09's safety questions and 07's delete request showed no reply; 01's outside-folder reply and 06's What it knows text were not captured. | 01, 06, 07, 09 | Missing evidence for those points; claims are limited accordingly. |

How they may bias the results: most defects lower usefulness and value ratings (so the usefulness and adoption parts are more likely understated than overstated), but a few may favour the project by hiding weaknesses that real use would reveal (small invented folders, no mistakes experienced, undo tried only on tidy-up).

## 12. Limitations and potential biases

> This study uses AI-based simulated user agents to explore potential user perceptions and behavioural patterns. The participants are simulated personas, not recruited human subjects. Consequently, the findings represent exploratory synthetic evidence and must not be presented as empirical human-subject results or statistically representative population findings.

- **Synthetic participants.** All 15 are AI agents playing personas. Their "feelings" are plausible reactions, not lived experience.
- **One underlying language model played all personas.** Views are not independent, and personas may share the same reasoning style and the same blind spots. The 15 agree more than 15 separate people would be expected to.
- **Persona prompts were written by the researchers.** The personas include built-in attitudes (privacy, compliance, a "fad" attitude), so some results (notably S2) are partly set by design. The cluster list was chosen by the researchers, not drawn from a population.
- **LLM tendency to agreeableness.** Despite the brief's "nobody wants a flattering answer", the dominant pattern is "partly" and "might try", which is both a hedge and a polite middle. The brief also states the makers' idea in full and then asks participants to assess it, which invites a response to that framing.
- **Small n and no statistics.** 15 participants; clusters of 3 to 5; thresholds are conventions, not tests. No percentages, no significance.
- **Prototype defects** (section 11) shaped what could be observed, and the report format let agents say whether a problem was the idea or the prototype but the split is the agent's own judgement.
- **Shared local model.** All agents used the same local model concurrently, so latency and answer quality are linked across participants.
- **No audio.** Voice and talk features could not be exercised or heard.
- **Simulated actions are not real-world behaviour.** Participants acted through scripts with a roughly 30-call budget, in a single short session, on small invented folders. They never faced real files, real stakes, real interruptions or repeated use, and several errors were caused by the scripting.
- **Report-extraction limits.** Counts depend on my coding of free-text answers (the ambiguous cases are listed in Appendix A and the JSON file).
- **Context only.** The project's documents mention a questionnaire of 374 respondents and 13 interviews. Those are not combined with these counts in any way; any similarity or difference between them and this simulation would be a context observation only and is not claimed.

## 13. Research implications

- The strongest, most consistent result is about the **mechanism**: showing the plan, asking once, and a working Undo. It was used and liked by 10 of 10 who tried it. This supports building the project around the plan-approve-undo loop.
- The **boundary** claim is only partly supported as a driver: it reassures many (9 of 15 name it) and is a requirement for several confidentiality-bound personas, but it is not why most would try the product, and several want it verifiable rather than stated. The research question's "measurably improving trust" will need a measure the participants cannot provide in this format.
- **Usefulness** is currently dominated by answer quality, which participants do not separate cleanly from the boundary. Any real study needs the model to be good enough that the boundary is the variable.
- Setup, Settings jargon and the cloud-key display need attention before user testing, otherwise a real study will measure those defects.
- Evidence on "approval fatigue", "forgiveness for a mistake" and "retention" is absent, because none of those can be observed in one session.
- The hypotheses are less likely to hold for already-organised users (14) and for coders with their own tools (05, 06, 15), and more likely for people with no system and confidentiality constraints (02, 08, 09, 12). This is a hypothesis for real-world testing, not a finding.

## 14. Recommendations for subsequent real-world validation

1. **Fix the defects that contaminate evidence first** (Folders input, no-folder answers, NOT FOUND, tidy-up grouping, cloud key shown as saved, "What changed" wording, email prompt). Run a short usability pass with 3 to 5 real people before the main study.
2. **Recruit about 16 to 24 participants**, four to six per cluster (students, developers, freelancers or employees, sceptics or non-adopters), recruited by their actual occupation and attitude, not assigned. Add a group of people with a strong personal organising system and a group with none, because S1 and S7 depend on it.
3. **Tasks.** A scripted set done on the participant's own non-sensitive files or a realistic provided set: add a folder; ask for a file by meaning; ask a cross-note question with sources; tidy-up with plan; approve; undo; deliberately provoke a mistake and ask for recovery; find "what it knows" and erase an item; try a request outside the folder.
4. **Measures.** Trust questionnaire before and after (including trust in the boundary versus trust in undo, separately); time on task and errors for each task; the NASA-TLX workload scale for the setup and approval steps; SUS or similar for usability; think-aloud with recording of hesitations; willingness to try, keep and pay on a numeric scale; a free-text "why" for each.
5. **A comparison condition**: the same tasks with a full-access assistant or a chatbot, so S3 and H-C can be tested against an actual alternative rather than a hypothetical.
6. **Approval fatigue over repeated sessions.** A diary or multi-session design over at least 2 weeks with logged approvals, declines, "don't ask again" use and drop-out. This is the only way to test S5 and S6.
7. **Mistake tolerance.** A planned, harmless mistake in a controlled task, with measured reaction and trust afterwards (S4).
8. **Boundary verifiability.** Ask participants to try to verify the claim (log, network list) and measure whether visible logs change trust (T5, T16).
9. **Onboarding.** Measure time to first useful answer and drop-offs (S8).
10. **Pre-register** the rules and thresholds, and report real statistics only if the sample supports them. Keep the simulation and the human study separate in every table.

## 15. Final conclusion

This is exploratory synthetic evidence. Within it, the central hypothesis (H-C) is Partially Supported, and so are each of its three parts. Participants almost all said a bounded assistant is at least somewhat more trustworthy (6 agree, 9 partly, none disagree) and at least somewhat more attractive to try (1 agree, 14 partly, none disagree), but none would commit to use it, and most trust came from the plan-and-undo mechanism and from source-cited answers as much as from the boundary. The claim that the limitation does not cost too much usefulness is supported for the participants who could judge it (6 of 15) but cannot be separated from the prototype's weak answers.

Among the supporting claims, S2 (broad access as a barrier) and S8 (onboarding as a condition) reach Supported, both with caveats (persona design for S2; a leading question and prototype defect for S8). S1, S3, S4, S5, S6 and S7 are Partially Supported. In particular, problem relevance is real but modest (mean 3.27), the undo advantage holds for reversible file moves only, approval preference leans to ask-first with exceptions, session resume was rarely named as a wanted feature, and retention could not be observed.

Nothing here is evidence about real users. The most useful outputs are a list of prototype defects to fix, a set of design requirements (verifiable privacy, exact citations, safer and structure-aware tidy-up, simpler first screen and Settings), and a concrete plan for a real study (section 14).

## Appendix A: Raw per-agent extraction

Values are as stated in each report; "no answer" would mean the agent did not answer (none did not). Coding notes are in `Future-work/user_feedback_tally.json`. Cluster is my coding (section 5). Ratings are 1-5. For (c), "disagree" means the limit does not cost too much.

| Agent | Cluster | Relevance | Value | Adoption | (a) trust | (b) willing | (c) cost | Q1 time loss | Q2 broad access barrier | Q3 accept one mistake | Q4 ask or act |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | student | 4 | 3 | might try | partly | partly | cannot say | agree | disagree | agree | mixed |
| 02 | student | 4 | 3 | might try | partly | partly | disagree | agree | agree | partly | ask first |
| 03 | student | 3 | 3 | might try | partly | partly | cannot say | partly | agree | agree | ask first |
| 04 | student | 4 | 3.5 | might try | partly | partly | disagree | agree | partly | partly | ask first |
| 05 | developer | 2 | 2 | might try | agree | partly | cannot say | partly | agree | agree | ask first |
| 06 | developer | 3 | 3 | might try | partly | partly | partly | partly | disagree | agree | act then undo |
| 07 | developer | 4 | 3 | might try | partly | partly | cannot say | agree | partly | agree | mixed |
| 08 | freelancer-or-employee | 4 | 3 | might try | agree | agree | partly | agree | agree | agree | mixed |
| 09 | freelancer-or-employee | 3 | 2 | might try | agree | partly | cannot say | partly | agree | partly | ask first |
| 10 | freelancer-or-employee | 4 | 3 | might try | agree | partly | cannot say | agree | agree | partly | mixed |
| 11 | sceptic-or-non-adopter | 2 | 3 | might try | agree | partly | disagree | partly | agree | partly | ask first |
| 12 | sceptic-or-non-adopter | 4 | 3 | might try | agree | partly | disagree | agree | agree | partly | mixed |
| 13 | sceptic-or-non-adopter | 3 | 2.5 | might try | partly | partly | disagree | partly | agree | partly | ask first |
| 14 | student | 2 | 2 | would not use | partly | partly | disagree | partly | disagree | partly | ask first |
| 15 | developer | 3 | 3 | might try | partly | partly | partly | agree | agree | agree | mixed |

Totals recomputed from the table: relevance 49 (mean 3.27, median 3); value 42 (mean 2.8, median 3); adoption 1 / 14 / 0 / 0; (a) 6 agree, 9 partly; (b) 1 agree, 14 partly; (c) 6 disagree, 3 partly, 6 cannot say; Q1 8 / 7; Q2 10 / 2 / 3; Q3 7 / 8; Q4 8 / 6 / 1.

Free-text answers (Q5 abilities, Q6 setup effort):

| Agent | Q5 abilities they would use | Q6 what makes setup too much effort |
|---|---|---|
| 01 | tidy-up, find and summarise notes and lab files, maybe email drafts; not voice, remote | beyond adding a folder: email app passwords, API keys, picking models, long reading |
| 02 | tidy-up with preview, finding the right file or version, What it knows; not email, voice, settings | typing a folder path, keys, models, app passwords, more than a couple of steps |
| 03 | notes Q&A if it works, code suggestions, perhaps tidy-up; not email, voice, phone remote | cloud account or key, big model download, Windows-only, long setup |
| 04 | resume, ask-the-notes with sources, draft paragraph with sources; not tidying, voice, email | retyping paths, unclear errors, converting files to a special format |
| 05 | diff proposals for code, notes Q&A if accurate, maybe tidy-up; not voice, email, probably not web search | anything beyond adding a path, a browser tab to remember, 9.6 GB model, credentials |
| 06 | tidy-up with undo, questions about notes, maybe diff suggestions; skip email, voice | many Settings steps (keys, app passwords), re-explaining folders |
| 07 | tidy-up, undo, talk to it, ask about files; skip email, settings | typing folder paths, keys or app passwords, pages with many options |
| 08 | find the latest file with sources, email drafts, search contracts, tidy-up if it respects structure; not voice, remote | email app passwords, picking models, re-explaining folders |
| 09 | questions about notes and files, where-did-I-leave-off, reminder email; not voice, not web search with client data | typing folder paths, long email app-password steps, models and keys |
| 10 | where-I-left-off, tidy-up, finding files, email drafts; not code, probably not voice | typing folder paths, Gmail app password, picking models, admin rights |
| 11 | source-cited answers, tidy-up with plan, undo, What it knows; not voice, remote | beyond choosing a folder, email app-password steps, relay server, a security review |
| 12 | question-answering with sources, email drafts for review, maybe tidy-up; probably not voice | Gmail app password and 2-step setup (borderline), retyping paths, fixing the model |
| 13 | finding files and "where is..."; maybe drafting a letter (not tried); not tidy-up, voice, web, email | typing a folder path, keys or passwords, choosing models, anything needing his nephew |
| 14 | questions over notes with sources (maybe), What it knows or erase; not tidy-up, daily recovery, voice, email | 9.6 GB model, keys or app passwords, rebuilding her structure in another tool |
| 15 | tidy-up with plan card, Q&A over notes or CSVs with sources, What it knows erase; probably not voice, drafting | typing many folder paths, tuning models, any unclear first step, over a minute or two |

## Appendix B: Action-log spot checks

I compared 15 reports' behavioural claims with their logs. Result: no claim contradicted by a log; two small points could not be verified.

| Agent | Log | Claims checked | Result |
|---|---|---|---|
| 01 | `tests/agents/work/ua-01/actions.log` | "Delete all the screenshots" answered by "I still need an email address..."; Undo then "There is nothing to undo"; "Key saved"; outside-folder reply not captured | Match. The log ends at the outside-folder ASK with no reply captured, as the report says. |
| 02 | `tests/agents/work/ua-02/actions.log` | Resume question "NOT FOUND IN YOUR FILES"; casual "Oh yeah, you don't need to worry" answer; 17 files; Undo restored (19 steps reversed); "Key saved" | Match. The report's "18 numbered steps" and "Enter did nothing" were not separately verifiable from the log. |
| 03 | `tests/agents/work/ua-03/actions.log` | "27 things"; "I don't have access to your personal files right now"; "Undone. 6 steps reversed"; cloud toggle text; erase confirmation "Forget all 1 folder?" | Match. |
| 04 | `test/agents/w04/actions.log` | `supervisor-meeting-2026-10-28.md:1` and `reading-notes-lee2021.md:1` references; Jones 2020 "NOT FOUND"; tidy-up "Would move 9 files and create 1 folder" | Match. |
| 05 | `test/agents/work05/actions.log` | Bug question answered from README (`README.md:1`); diff `return a + b`; "proposal only... never edits code itself"; "Done: 2 folders created, 12 files moved"; "Undone. 14 steps reversed" | Match. |
| 06 | `test/agents/w06/` (`actions.log`, `out_*.txt`) | Diff `a + b` and "proposal only"; 12 files moved; "Undone. 14 steps reversed" | Match for outcomes. **Weak mismatch:** the report says replies "took about 5 seconds each"; the log shows the script's fixed wait ("done after 5s"), not a measured reply time, so that timing claim cannot be confirmed (other agents on the same model report 10 to 50 seconds). |
| 07 | `tests/agents/work/ua-07/actions.log` | "NOT FOUND" for invoices and CV; 21 files moved; "Undone. 23 steps reversed"; delete request with no visible reply | Match. |
| 08 | `test/agents/work08/actions.log` | Three unpaid-invoice wordings; "I still need an email address..."; "Okay then."; "9 steps reversed"; Invoice 0042 answer with source | Match. |
| 09 | `test/agents/w09/actions.log` | Add-folder failure messages (2 "Type or browse to a folder first", 4 "Choose a folder first"); "That works on a folder, and there is none yet"; safety question with no reply | Match. "Browse showed nothing" was not verifiable. |
| 10 | `tests/agents/work/ua-10/actions.log` | `random.zip:1` source; email prompt after a typed tidy-up request; plan "move 16 files"; "4 minutes ago" | Match. |
| 11 | `test/agents/w11/actions.log` | 19 files moved; "Undone. 21 steps reversed"; refusal for `C:\Windows\System32\drivers\etc\hosts`; web search "Nothing has happened yet" | Match. The wrong-citation claim (random.zip) was not separately re-checked. |
| 12 | `test/agents/Agent_12_actions.log` | "Ali_Assignment_2.pdf" invented file name; "NOT FOUND IN YOUR FILES" labels on content present in the file; "I still need an email address" in answer to the grant question | Match. |
| 13 | `test/agents/w13/actions.log` | "NOT FOUND" for latest invoice; "Done: 2 folders created, 16 files moved"; "Undone. 18 steps reversed" | Match. |
| 14 | `test/agents/work14/actions.log` | `2026-11-08_journal.md:1` answer; "Book viva slot and fix reference list"; "Would move 13 files and create 2 folders" | Match. |
| 15 | `test/agents/scratch15/actions.log` | Invented "North America $1,200,000, Europe $950,000..." with no folder; `FAKE_TOKEN=abc123notreal` printed; outside-folder refusal; "Done: 3 folders created, 13 files moved"; "Undone. 16 steps reversed" | Match. |

Summary: 15 logs checked; 15 matched on the claims listed; one weak mismatch (Agent_06 reply timing); several small details (step counts, "Enter did nothing", "Browse showed nothing") could not be verified from the logs.
