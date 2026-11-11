# sprint-6 / agent-b / Impatient power user

Summary: Indexing is fast and never blocked the UI (tab switches 0.07-0.12 s while a 400-file and a 5030-file folder were added). Grounded answers with "Sources: file:line" work for simple single-fact questions, and the code flow gives a diff with the file never changed (md5 on disk checked). Weaknesses: the "NOT FOUND IN YOUR FILES" label is applied to correct, cited answers and is missing where an answer is invented; compound questions fail; a request sent just before a reload is lost; a large folder's index silently stopped at 4543 of 5030 files. Verdict: PASS WITH ISSUES (leaning FAIL on the "unsupported claim must be shown as unsupported" gate).

## What I did
1. Added docs (messy + facts.txt) and proj (code) folders; looked at Folders and What it knows.
2. Asked fact questions in docs, including a compound one and an unanswerable one (CEO salary).
3. Added the 400-file "big" folder, flipped tabs and asked a question while it ran; timed tab switches.
4. Asked about document 123 and a two-attribute question in big.
5. Edited facts.txt on disk and created newfile.txt; asked before and after What it knows > Check for changes.
6. Fired three questions rapid-fire (only the first was answered; known).
7. Asked code questions in proj: "fix the bug", explain, "edit the file directly"; checked md5 of main.py and util.py on disk.
8. Asked summary/verification questions about Project Orion and a salary question not in the files.
9. Switched folder mid-answer; reloaded the page mid-answer.
10. Added a 5000-file folder, created 30 files in it mid-index, reloaded mid-index, watched counts for minutes, asked about it.

## Backlog items checked
- Incremental indexing, does not block UI: PASS. Tab switch 0.07-0.12 s during indexing of 400 and 5030 files; Add folder returned in ~3 s; asking worked meanwhile (07, 20).
- Incremental indexing, completeness: FAIL. huge has 5030 files on disk; header and Folders settled at 4543 (4962 total) across minutes and 3 reloads (B3). Reload mid-index did not crash it.
- Edit on disk / new files / Check for changes: PARTIAL. Edited facts.txt answered with the new value (9000) before any check (good); new newfile.txt invisible until Check (known), then found. Late files in huge were not found even after a check (B3).
- Grounded answers with sources: PARTIAL. Simple facts show "Sources: facts.txt:1" (ZEBRA port, document 123, huge doc 4321). Compound questions return NOT FOUND although facts exist (B4).
- Unsupported claim shown as unsupported (stage gate): FAIL. B1, B2, B5.
- Code question gives diff, never an edit: PASS. "Fix" and "edit directly" both produced a diff with "This is a proposal only. ARTEMIS has not changed your file"; md5 of main.py unchanged, util.py unchanged (14, 16).
- Retrieval fast on big: PASS. 1-5 s per answer on 400- and 4500-file folders including the model call (10, 23). Caveat: some answers fall to NOT FOUND (missing embedding model, known).

## Bugs
B1 (high). Invented answer with no source and no unsupported label.
Steps: folder huge (late_7.txt holds "late file 7 SECRETWORD7", not indexed), ask "what does late file 7 say?". Expected: not found / unsupported warning. Actual: "It says that the project needs to be reviewed by next Friday, according to late file 7." No Sources line, no warning. Reproduced 1x (another attempt gave NOT FOUND). Evidence: 23-huge-q.png.

B2 (high). "NOT FOUND IN YOUR FILES" / "None of this is backed by a file" on correct cited answers.
Steps: docs, ask "Is the Orion deadline 14 March and the owner Sara Khan?". Actual: NOT FOUND heading, body "Yes, ... [notes.txt:1]", warning that nothing is backed by a file, no Sources line. Also proj: "explain app/main.py and show me how to change it" gave a cited first sentence and a NOT FOUND flag on the (correct) second half. Reproduced 2x. Evidence: 17-summary.png, 15-explain.png.

B3 (medium). Large folder index silently stops short.
Steps: add a 5000-file folder, create 30 files in it 1.5 s later, reload ~7 s after. Folders showed 3340, later 4543, and stays there over minutes and reloads (disk has 5030). No message that indexing is unfinished. Check for changes reported only "1 new, 1 changed" for the selected folder. Reproduced 1x. Evidence: 21-huge-after.png, 22-knows.png.

B4 (medium). Compound or two-attribute questions return NOT FOUND though the facts are in one file.
"who maintains zebra and where is the warehouse" -> NOT FOUND (both in facts.txt); "Which file is about subject 5 and document 22?" -> NOT FOUND. Single-fact versions work ("who is the maintainer of ZEBRA?" gave Imran Qureshi). Likely the missing embedding model (known) but specific to compound questions. Evidence: 06-who_maintain.png, 10-big-q.png.

B5 (medium). "Could not find it" answers cite a wrong file as source.
docs, "What is Project Orion budget?" -> "I could not find it. budget 2026.xlsx:1 / Sources: budget 2026.xlsx:1"; the fact is in notes.txt. A not-found answer should not show a source. Also the "Summarise my notes" answer shows "notes.txt:1, notes.txt:1" and presents the deadline as the launch date without flagging it. Reproduced 1x (a later query gave the budget correctly). Evidence: 06-What_is_Proj.png, 17-summary.png.

B6 (medium). A question sent just before a page reload vanishes.
Sent "What port does the ZEBRA protocol use?", reloaded after 0.3 s: afterwards the chat has no trace of the question or any answer. Reproduced 2x (also mid-index run). Evidence: 19-reload.png.

## Not desired behavior
U1 (medium). Per-folder file counts on Folders and in the dropdown stay stale while indexing continues (huge 3340 while header says 4962 and growing); no "still indexing" indicator anywhere.
U2 (low). Out-of-scope questions are handled inconsistently: "CEO's salary" gets a friendly chat reply with no tag, while "Sara Khan's salary and home address" gets the NOT FOUND banner plus "none of this is backed by a file".
U3 (low). The diff reply shows Approve buttons although the text says it is a proposal only; unclear what Approve would do.
U4 (low). Check for changes acts only on the folder selected in What it knows and the result text does not name the folder.
U5 (low). The saved-chats list fills with identical "Chat - today" entries, hard to tell apart.
U6 (low). Rapid-fire: 2nd and 3rd requests silently dropped (known). Voice greeting turn on top (known; I left voice on).

## Worked well
- UI stayed responsive during bulk indexing (under 0.13 s per tab switch).
- Edited file content reflected in answers without a manual re-index.
- Code requests never touched files; diff text is clear and says it is a proposal.
- Answers in 1-5 s, including big folders.
- Check for changes gives a readable summary and finds the new file.

## Not tested / blocked
- I did not isolate which folder Check for changes processed on huge (time budget).
- Dark mode, voice, cloud tiers out of scope.
- Verification used disk only (md5 of main.py/util.py, directory counts) and the server log (only Windows connection-reset noise from browser closes).
