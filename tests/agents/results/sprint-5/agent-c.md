# sprint-5 / agent-c / Chaos monkey

Adversarial testing of Sprint 5 (resume notes, tidy with preview, habits, broker confinement) through the UI only (Playwright, private app `s5-c` on port 7914). Boundary confinement held up well: every attempt to reach outside the folder, delete, or escape with `..`, other drives or absolute paths was refused with a plain message and nothing changed on disk. HTML/script notes are escaped. The three-repeat threshold behaves exactly (offered after 3, not after 2). But the tidy feature has a real data-loss path: when two loose files would land on the same destination name, the preview shows no problem, the run half-fails, and **Undo then overwrites an original file and reports "your files are back as they were"**. Also a saved note is silently lost after the next approved change. Verdict: **FAIL** (one reproducible data-loss bug in a feature whose promise is that nothing is lost).

Disk and server log were read only to verify what the UI claimed. Voice was unticked ("Voice is on") at the start of every session to keep the voice greeting out of the way.

## What I did
1. Started a private app, unticked voice, added a "messy" folder.
2. Saved notes: empty, whitespace, `<script>`/`<img onerror>` HTML, unicode/emoji/RTL-override, 100,000 characters, multi-line with SQL-like text, template syntax. Checked each via "What changed" and after a reload.
3. Built a hostile folder (29 entries: dotfiles, no-extension files, 200-char names, emoji, brackets, `&%;'`, double extensions, a loose file named `Images`, `a.txt` plus `a (2).txt` with an existing `Documents/a.txt`, nested `sub/deep`). Ran Suggest a tidy-up, approved, then Undo. Compared disk before and after.
4. Reproduced the collision with a minimal 5-file folder with unique file contents.
5. Ran four tidy cycles (4 new files each), pressing "Repeated tasks" after each, then accepted one habit and inspected the others.
6. Typed hostile requests in the ask box (`../../outside/secret.txt`, absolute path to another folder, "delete everything", `D:\` target, `..\escaped.txt`, prompt injection to overwrite, a script tag).
7. Saved a note, did a tidy, then looked at "What changed" to see if the note survived.

## Backlog items checked
- Resume / pick up where you left off: PARTIAL. Notes stored and replayed, HTML escaped, unicode fine, empty note refused. Note lost after the next approved change (B2); long note overflows layout (U2); cut to 500 chars silently (U3).
- Tidy a folder after previewing every move: FAIL. Preview lists every move, nothing happens before Approve, nothing deleted, nested folders left alone. But colliding names in one plan are not caught in the preview (B1), and a file named like a target folder breaks the plan (B3). Dotfiles get moved (U1).
- Automation offered only after 3 repeats: PASS. After tidy 2: "Nothing repeated often enough"; after tidy 3: "Noticed 3 things you do repeatedly" (20-habit-after-*.png). Accepting does nothing ("not built yet"), so no outside-folder automation could be accepted or run. Wording odd (U5, U6).
- Capability services reach files only through the broker: PASS. 8 hostile requests refused; `outside/secret.txt` untouched, nothing created next to the folder (31-q*.png).
- Stage gate (three features end to end through real gates): PARTIAL. Notes, tidy and habits all run through the cards, but tidy Undo is not reliable (B1).

## Bugs

### B1. Tidy with colliding names half-fails, and Undo destroys an original file while saying files are back as they were (high, data loss)
Steps (reproduced 2 times): folder with `a.txt` ("ORIGINAL-a"), `a (2).txt` ("ORIGINAL-a2"), `Documents/a.txt` ("EXISTING"), `p.pdf`, `q.pdf`. Suggest a tidy-up, Approve, then Undo last change.
Expected: preview warns about the clash or picks unique names; Undo restores both originals.
Actual: the preview (40-preview-collide.png) lists "Move a.txt" and "Move a (2).txt" into Documents as normal. After Approve: "Done: 1 folder created, 3 files moved. 1 step did not run: a file with that name already exists." After Undo ("5 steps reversed, and your files are back as they were."): root `a.txt` contains "ORIGINAL-a2"; the real original "ORIGINAL-a" is gone and `a (2).txt` exists nowhere (42-undo.png). In the bigger chaos run (29-step plan, 7 failed) the same loss happened and it said "29 steps reversed". The journal seems to reverse the failed step too, and that move overwrites.
Evidence: 40/41/42 screenshots, disk dump before and after.

### B2. Saved note is dropped after the next approved change or undo (medium)
Steps: Save note "remember to finish report"; Suggest a tidy-up; Approve; What changed.
Expected: the note is still shown until the user returns.
Actual: only "Nothing has changed ... Last worked on: ..." The note is gone. Cause read in code, not from UI: the checkpoint after a change or undo is written with an empty note. Seen once.

### B3. A loose file named like a target group (e.g. `Images`) breaks the plan; preview does not warn (medium)
Steps: loose extension-less file `Images` plus 5 images; tidy; approve.
Actual: the plan moves file `Images` into `Other/` and also creates folder `Images`; that step failed, so all 5 images stayed ("7 steps did not run: a file with that name already exists"), with no message about which. Evidence: 11-tidy-approved.png.

## Not desired behavior
- U1 (medium) Dotfiles are tidied: `.gitignore` into `Other/`, `.hidden.txt` and `..hid.txt` into `Documents/`; `.env` was skipped, so it is inconsistent. Moving config dotfiles is unwanted. (10-tidy-preview.png)
- U2 (low) A long unbroken note overflows the card horizontally (02-note4.png).
- U3 (low) Notes over 500 characters are cut silently; newlines flattened to spaces although the note is described as verbatim; an RTL-override character garbles the display.
- U4 (low) Empty or whitespace-only note: no visible message on screen (02-note0.png).
- U5 (low) Habit label "creating a folder for files" is vague; one repeated tidy yields three offers.
- U6 (low) The habit dropdown is empty after a restart or reload until a button such as Repeated tasks is pressed.
- U7 (low) Files added on disk are invisible to tidy ("Only 0 loose files") until "Check for changes", which lives on the What it knows tab; nothing on Work hints at it. Summary says "create 1 folder" when the folder already exists.
- U8 (low) The echoed user message drops backslashes (`C:\Windows\Temp` shows as `C:WindowsTemp`).
- U9 (low) A partial tidy does not say which step failed.

## Worked well
- Confinement: `..`, absolute paths elsewhere, another drive, "delete everything" and a prompt-injection overwrite were all refused clearly; no disk change.
- Script/HTML in notes shown as text.
- Three-repeat threshold exact; accepting a habit executes nothing.
- Preview shows every step in order; nested folders and groups of one are left alone; 200-char and emoji names handled.

## Not tested / blocked
- Habits from model-driven typed actions (write/rename) were not driven; only tidy-based patterns.
- Case-colliding names (`A.TXT` vs `a.txt`) cannot coexist on this filesystem.
- Audit log content not re-checked beyond the known gaps.
