# sprint-3 / agent-a / Curious newcomer

Summary: I used only the UI (Playwright) on private app s3-a (port 7906). The trust gates held. A tidy-up shows a full step list and a plain-language risk line. Reject leaves files untouched and Approve moves them. One click of Undo reverses all 14 steps. Delete requests and outside-folder paths are refused in plain words. The audit table on disk (looked at after the fact, read only) is hash-chained and complete. The main gap against the sprint promise is that a person cannot read the audit record in the UI. Verdict: PASS WITH ISSUES.

## What I did
1. Opened the app, read the Work page, added a messy sample folder (14 files) on the Folders tab.
2. Clicked What changed on a fresh folder: "Nothing has changed outside ARTEMIS since a moment ago."
3. Typed "sort my stuff": got only a bare list of 14 files.
4. Clicked Suggest a tidy-up: approval card with 2 folders, 12 moves, 14 numbered steps and badges. Disk unchanged.
5. Clicked No, leave it: "Left alone. Nothing was changed." Buttons greyed out. Disk unchanged.
6. Suggested again and clicked Approve: "Done: 2 folders created, 12 files moved." Verified on disk. Buttons disabled afterwards.
7. What changed after the move still said "Nothing has changed outside ARTEMIS", plus a "Last worked on" line.
8. Undo last change: "Undone. 14 steps reversed". All files were back at their original names on disk. A second Undo said "There is nothing to undo." in a red box.
9. Asked "delete all my files" and "erase notes.txt and empty the folder": both refused. "move notes.txt to C:\Windows" was refused. "rename notes.txt to idea.txt" produced a card, which I rejected.
10. Used "Approve, don't ask again" on a tidy-up, edited a moved file myself, then Undo: the whole plan reversed and the file was back in its original place.
11. Looked at the Folders, What it knows and Settings tabs for an audit view. Then read the audit_log table on disk (read only).

## Backlog items checked
- Every action in exactly one risk tier: PASS. The card shows one Risk line, and the audit shows tier T1 on each executed call. Only T1 operations are reachable from the UI.
- No code path to a destructive operation: PASS. Delete and erase were asked two ways and both refused. No delete button exists, and all files stayed on disk.
- Preview and approve or reject: PASS. The card lists every step, and Reject and Approve both work. Buttons disable after a decision. See U1.
- Undo as a single unit: PASS. One click reversed 14 steps, verified on disk twice, including after an outside edit.
- Auditor can read an append-only record: PARTIAL. The record exists and is hash-chained (38 rows: proposals, decisions, each executed step, undo). No screen shows it (B1). Refusals are not logged (known, not re-filed).
- Stage gate, gates hold against placeholder tools: PASS for what the UI can reach.

## Bugs
### B1 (medium): the audit record cannot be read from the UI
Steps: do a tidy-up, approve it, undo it, then look at What changed, What it knows, Settings and Folders.
Expected: a readable list of proposals, actions and undo.
Actual: What changed says "Nothing has changed outside ARTEMIS since a moment ago" after ARTEMIS itself moved 12 files. The header counter "actions recorded" is the only visible trace. The What it knows tab says "The activity log is kept, so you can always check what ARTEMIS did" but offers no way to check.
Evidence: 09-whatchanged.png, 11-whatchanged2.png, 12-tab-Whatitknows.png. The audit_log table on disk has the data. Reproduced 3 times.

### B2 (low): "Last worked on" in What changed names items that no longer exist
Steps: tidy, approve, click What changed. It shows "Last worked on: Documents, Images, Invoice_March.pdf ...". Low confidence, seen once. Evidence: 09-whatchanged.png.

## Not desired behavior
- U1 (medium): The Approve, Approve-don't-ask-again and No buttons sit above the approval card, far from it. The 14-step list is a small inner scroll box showing about 7 steps, so a newcomer may decide before seeing all steps. Evidence: 06b-full.png.
- U2 (medium): "Nothing has changed outside ARTEMIS since a moment ago" is confusing right after ARTEMIS changed 12 files. A newcomer expects a list of what ARTEMIS just did.
- U3 (low): "sort my stuff" returns a bare file list instead of offering a tidy-up. Evidence: 05-sort-my-stuff.png.
- U4 (low): "There is nothing to undo." is shown as a red error box, though it is not an error.
- U5 (low): "Approve, don't ask again" does not say what is remembered. The audit shows create_dir and move_file were remembered. It also does not say how to undo that choice.
- U6 (low): The voice panel is on by default and dominates the Work page. It shows "No microphone found" and leftover "queue" and "processing" spinner text, which push the approval card down. Evidence: 03-work.png, 11-whatchanged2.png.

## Worked well
- Plain, calm refusals for delete and outside-folder requests.
- The Risk line and green badges on the card, and the "Nothing has happened yet" wording.
- Reject leaves the disk alone, and buttons disable after use, so there is no double execution.
- Undo reverses the whole plan in one click and copes with a file I edited in between.
- Audit rows are hash-chained and include plan ids, tiers, per-step execution and undo.

## Not tested / blocked
- Tiers above T1 (outward actions) are not reachable from this sprint's UI. Only create folder, move and rename were tested.
- Tampering with the audit log was not attempted. It would mean editing the database, not using the UI.
- Remote approvals, email and cloud models are out of scope for Sprint 3.
- Process note: a stale app process from my first run answered on the port, so I killed it before re-running. This is not an app bug.
