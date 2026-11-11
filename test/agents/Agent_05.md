# Agent_05 report

## 1. Agent ID and persona
Agent_05 (app ua-05, port 7945). Simulated persona: Imran, 38, senior backend developer at a software company.

## 2. Background and relevant characteristics
15 years of experience. Lives in git, the terminal and an IDE. Has Copilot but turns off suggestions he does not trust. Sceptical of AI hype and of agents that edit files. Likes tools that show a diff and let him decide. Compares everything with grep, fzf, git and shell scripts. Would adopt only if it saves real time on work he actually does. (Persona written as plausible reactions, not facts about a real person.)

## 3. Initial expectations (before using it)
- The "bounded folders + always ask first" part is the only bit that interests me. Most assistants are a solution looking for a problem.
- For code I already have grep, ripgrep, fzf, git diff and my IDE. "Suggest fixes to code" I get from Copilot. "Remind you where you left off" is git log, git status and my shell history.
- "Tidy a messy folder" is a real but minor chore, and a ten-line shell script does it. "Answer questions about your notes" depends on retrieval quality; I expect a small local model to be weak.
- I like that it shows a diff and waits. I do not believe "it can undo" until I see it. I expect wrong answers from a local model and I will test that.

## 4. Interaction and exploration summary (in order)
Opened the app, unticked "Voice is on". Read the Folders, What it knows and Settings tabs without changing anything (did not touch key/email buttons). Added an invented project folder (README that states a bug, app/main.py with `a - b` in add(), app/util.py). Asked vague questions first (retry logic of a "payment client", find TODOs, fix the obvious bug) with no folder selected in the "In this folder" box. Then selected the folder and asked where the bug is, then asked to fix it in app/main.py. Then added an invented messy folder (14 files), pressed Suggest a tidy-up, approved, checked the disk, pressed Undo last change, checked the disk again, and looked at What it knows. Evidence: `test/agents/work05/actions.log` (plus the s*.out files).

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app; read the Work tab | Counters (folders visible 0, files known 0, actions recorded), a voice greeting, buttons Approve / Approve, don't ask again / No, leave it | hesitation: busy screen |
| 2 | Unticked "Voice is on" | Worked | - |
| 3 | Read Folders tab | "ARTEMIS cannot see anything on this computer" until a folder is added; per-folder "Allow cloud models here / Keep it on this computer" | interest |
| 4 | Read What it knows | Per-folder file list, Forget this folder / file, Erase everything; "the activity log is kept" | interest |
| 5 | Read Settings | Local model gemma4:e4b; cloud keys (Gemini showed "Key saved" in my copy); email; Remote access section. Did not click any key/email buttons | interest; mild hesitation at the cloud and remote-access options |
| 6 | Added the project folder | "Added 'stuff'. ARTEMIS now knows about 3 files in it." | interest |
| 7 | Asked "Where did the retry logic for the payment client live, and is there anything in the code that looks like a bug?" (no folder selected) | "I don't have any files open right now to check through. If you point me toward the folder..." | hesitation: it already had the folder, I had to pick it in a box |
| 8 | Asked "Find every TODO or FIXME in this folder" | "Just let me know which folder you want me to check" (no search done) | annoyed; repeated once with the same result |
| 9 | Asked "Suggest a fix for the most obvious bug, show me as a diff" | Asked me which file. No diff | annoyed |
| 10 | Selected the folder in the "In this folder" dropdown, asked "Where is the bug in this project? Show me the line." | Answered only from the README: "A tiny demo project with a bug in add()", citing README.md:1. Did not point at main.py | disappointed: grep -n BUG would have found the line instantly |
| 11 | Asked "Fix the bug in app/main.py" | Showed a unified diff (`- return a - b` / `+ return a + b`) with "This is a proposal only. ARTEMIS has not changed your file, and it never edits code itself." File on disk unchanged (I checked) | strong interest: this is the behaviour I want |
| 12 | Added invented messy folder (14 files), pressed Suggest a tidy-up | One summary line: "Would move 12 files and create 2 folders, leaving budget 2026.xlsx, random.zip where they are. Nothing is deleted." No per-file list in the page text I captured | hesitation: I want to see each move |
| 13 | Pressed Approve | "Done: 2 folders created, 12 files moved." Disk showed Documents/ and Images/ plus the 2 left files | interest |
| 14 | Pressed Undo last change | "Undone. 14 steps reversed, and your files are back as they were." Disk listing matched the original 14 files again | strong interest: undo worked as claimed |
| 15 | Looked at What it knows for the messy folder | List of 14 files with sizes | mild interest |

Features skipped (did not try): voice/talk, web search, drafting documents or emails, email connection, Remote access, "Repeated tasks", "What changed", "Approve, don't ask again", "Leave a note", cloud model use, "Erase everything", large folders (tiny invented files only, so retrieval quality on a real repo is untested).

Decisions: stopped after the diff and tidy/undo checks, because those are the two claims I could verify against the disk.

## 6. Feedback about the research idea (persona's words)
"The bit I like is not the AI, it is the contract. A folder allow-list, a diff before anything happens, and a real undo is how I already treat git. It showed me a diff for the code fix and said outright it never edits code itself. That earns more trust from me than Copilot Chat or an agent with a terminal. But a safe tool that does not do anything I need is a safe toy. For code I would never go to a chat box when ripgrep gives me the line in 20 ms, exact. The local model also dodged my first three questions and answered the bug question from the README, not the code. If the assistant is limited AND weaker than grep, I have no reason to open it."

## 7. Perceived problem relevance
Rating 2/5. Interruptions and context loss are real for me, but I already handle them with git log, a todo.md, shell history and tmux. Folder tidying is a once-a-month nuisance. Notes search over my own documents is occasionally useful. (Interpretation: it would rate higher for people who keep many loose documents and do not use version control.)

## 8. Perceived value of the proposed solution
Rating 2/5 for my work, 3/5 for the concept in general. Valuable: the visible boundary, the diff-first and approve-first pattern, the working undo, the "What it knows" page with erase. Not valuable to me: chat for things grep/fzf/IDE already do better, weak retrieval from a small local model, voice, email.

## 9. Adoption likelihood and reasoning
Choice: **might try** (leaning "would not use" for daily work).
Would change my mind: it finds the exact line and file reliably across a real repository with citations, it does things grep cannot (cross-note questions, "what did I change last Tuesday across these folders"), it saves a measurable number of minutes a week, and it has a CLI or editor integration instead of a browser tab. I would not pay unless it beat a shell script on a recurring task.

## 10. Concerns, objections and suggestions
- Without a folder selected, the assistant acts as if it has no files. For a "bounded" tool the scope should be obvious and applied by default.
- Show the full list of file moves in the tidy preview, not just counts.
- Add exact search (literal and regex) as a first-class tool; do not have the language model guess where a TODO is.
- Code answers must cite file and line (the one citation I got was the README).
- Offer the approval as a diff for every change type, with "copy as patch" so I can git apply it.
- Cloud keys and Remote access in Settings sit uneasily next to "everything stays on this computer"; I want them clearly off by default and easy to confirm as off.
- I would turn the voice greeting off permanently.

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: **agree**. Seeing the allow-list, the diff and the undo working made me trust it more than a full-access agent.
(b) More willing to use it: **partly**. It lowers the barrier to trying, but usefulness decides whether I come back.
(c) Does the limitation cost too much usefulness: **cannot say**. The folder limit did not hurt me (my work lives in a few repos anyway); the model quality hurt more than the boundary. (Interpretation: the two are confounded in this prototype.)

Short questions:
- Are people really losing time to interruptions and routine file work? **Partly** in general; **disagree** that it is a big loss for me, since git and shell notes cover it.
- Is wanting broad access a real barrier for me? **Agree** about agents with full access (I would not run one on a work machine with company code); with this tool the question never came up.
- Would I accept one mistake if undo is easy? **Agree**, provided undo is verified as it was here (I saw the files restored on disk).
- Ask before every change, or act and let me undo? **Ask first** for edits; for trivially reversible moves such as a tidy-up I could accept act-and-undo.
- Abilities I would actually use: diff proposals for code, notes/file Q&A if retrieval is accurate, maybe tidy-up. Not voice, not email, probably not web search.
- What makes setup too much effort: anything beyond adding a path; a browser tab I must remember to open; a 9.6 GB local model; anything that needs credentials or app passwords.

## 12. Implementation limitations I ran into
- Questions asked with no folder selected were answered as if no files existed, and the model asked me for the folder even though one had been added.
- "Find every TODO or FIXME" did not search; it only replied conversationally.
- "Where is the bug" cited the README rather than main.py.
- The tidy preview showed only a count, not the planned moves, in the text I captured.
- Chat history from earlier runs reappeared in my session, and "Hi again. Let's pick up where we left off" appeared repeatedly.
- Replies took 30-50 seconds.
- Two tab bars appeared in the page text (duplicated Work / Folders / What it knows / Settings).
- The page tried to start voice automatically and reported "No microphone found".
- My harness screenshots were saved into the test folders and showed up as an extra file (tidy.png), which is a test artefact, not the app.
