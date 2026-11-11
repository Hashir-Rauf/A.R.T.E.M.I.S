# sprint-6 / agent-a / Curious newcomer
Verdict: **PASS WITH ISSUES**. Code questions give a diff and never edit (main.py unchanged on disk, 2 requests); unsupported facts are often shown as NOT FOUND; adding a 400-file folder took about 3 s without freezing the page; answers list source files. But retrieval is inconsistent (false NOT FOUND for facts that exist) and an irrelevant file can be cited as source on an answer that says "I could not find it". UI only; I checked the disk for file contents. I unticked "Voice is on" in Talk instead of dealing with the greeting.

## What I did
1. Opened the app, unticked voice, added a notes folder (19 files) in Folders.
2. Asked six questions (Orion budget/owner, January meeting, lecture 3, summary, euro/approval claim).
3. Added a project folder with the bug, asked vaguely, then by file name to fix and save; asked about util.py, README, database.
4. Added a 400-file folder, browsed What it knows, asked three questions.
5. Tried a false claim, a rewrite request, a missing file; added phoenix.txt on disk, asked, used Check for changes, asked again, opened What changed.

## Backlog items checked
- Incremental indexing without blocking UI: PARTIAL. 400 files in about 2.9 s, page responsive, but no real progress indicator (U1); embeddings missing.
- Notes answers with sources: PARTIAL. Files listed, but line always ":1", duplicates (B4), wrong file cited sometimes (B1).
- Unsupported claim shown as unsupported: PARTIAL. "NOT FOUND IN YOUR FILES... not backed by a file" shown for euro/approval and bonus claims; but a bogus source sits beside "could not find it" (B1, U5), and real facts also get NOT FOUND (B2).
- Code question gives diff, never an edit: PASS. Diff a - b to a + b, "This is a proposal only"; file bytes unchanged. Vague phrasing failed (U2).
- Retrieval fast as folder grows: PARTIAL. Big folder replies 4.6 s, 11.6 s, 4.5 s vs 2.5-6.5 s small; quality poor on list/count questions (B2, B3).

## Bugs
- B1 (high): irrelevant file cited. notes_user, "what is the budget for project orion?" gives "I could not find it. budget 2026.xlsx:1 Sources: budget 2026.xlsx:1". "What is the Phoenix budget?" before Check for changes returned "sample content of budget 2026.xlsx" as the answer. Expected: notes.txt answer or clean NOT FOUND. Evidence q0.png, phoenix.png. Reproduced 2x.
- B2 (high): false NOT FOUND. "who is the owner of Orion and when is the deadline?" NOT FOUND, yet "summarise my notes" returns Sara Khan and 14 March. Big: "which files mention subject 5?" NOT FOUND. Works: January meeting, lecture 3, shout, README, document 123, hardware risks. Evidence q1.png, q5.png. Likely missing embedding model.
- B3 (medium): big selected, "how many documents are there about subject 3?" asks which folder to look in.
- B4 (low): citations always ":1" and repeated ("notes.txt:1, notes.txt:1").

## Not desired behavior
- U1 (medium) no visible indexing progress, only generic processing timer.
- U2 (medium) vague "fix the bug in add()" did not find app/main.py (c0.png).
- U3 (medium) "what is in the file called secrets.txt?" gives just "Nothing ran."
- U4 (low) "rewrite notes.txt ... save it" only echoes the file.
- U5 (low) two different unsupported wordings; one hides the unsupported state.
- U6 (low) tall Talk panel hides answers below the fold; fresh install says "pick up where we left off".
- U7 (low) new files unseen until Check for changes (known).

## Worked well
- Diff proposal with clear "proposal only" note, file untouched.
- Fast folder add, page responsive.
- Check for changes then What changed ("added: phoenix.txt").
- Clear NOT FOUND for bonus/euro/approval claims.

## Not tested / blocked
- Visible progress on large indexing (too fast on tiny files), embedding path (model missing), voice, folders over 400 files. Screenshots are in tests/agents/results/sprint-6/agent-a/.
