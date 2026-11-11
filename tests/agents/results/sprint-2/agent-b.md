# sprint-2 / agent-b / Impatient power user

Folder opt-in, the "What it knows" list, forget actions and the traversal/symlink refusals mostly work and survive double-clicks, tab switching and reloads. Symlinked entries inside a granted folder are left out of the index, and requests that reach outside the folder are refused (the symlink refusal is logged). But there are real gaps: the typed `..\` refusal is not logged anywhere, a whole drive (`C:\`) can be granted with no warning, and the AI invented file content. Verdict: **PASS WITH ISSUES**.

## What I did
1. Opened the Folders tab on a fresh private app and added a messy folder by double-clicking Add folder (one grant, no duplicates).
2. Pressed Enter in the path box (nothing happened). Retried the same folder with a trailing slash, lowercase and quotes (all "already granted").
3. Tried empty, spaces, missing, file path, `a\..\b`, `C:\`, `..`, a UNC path and a path reached through a symlink.
4. Went to What it knows: Show files, forgot one file with a double click, forgot a folder with Cancel then double-clicking "Yes, forget it", then re-added it.
5. Edited files on disk (new file, deleted file) and double-clicked Check for changes.
6. Reloaded in the middle of adding a 400-file folder and switched tabs mid-action.
7. On the Work tab asked about a symlinked file, `..\secret\private.txt` and a symlinked directory; checked What changed and read the audit database from disk (read-only).
8. Used "Erase everything" with a double-click on confirm. Disk files were intact throughout.

(I looked at the disk and the audit database read-only to verify UI claims; all actions were through the UI.)

## Backlog items checked
- User can opt a folder in as a workspace: PASS. Add folder works, shows counts and a message, duplicates are not created, the grant survives a restart. Enter does not submit (U1) and `C:\` is accepted (B1).
- System cannot resolve any path outside a granted workspace: PARTIAL. `..\secret\private.txt` refused with a clear message, `list_dir(linkdir)` refused (audit rows 39-41). Symlinked dir and file were not indexed (14 files, not 16). The `..\` pre-check refusal is not logged (B2). A symlinked-file read could not be verified because the AI made up an answer (B3).
- User can see every file indexed and delete any of it: PASS. Show files lists all files with sizes. Forget file and Forget folder (with confirmation) never touched the disk. Erase everything asks first. The "files known" stat went stale after forgetting one file (B4).
- Stage gate, traversal and symlink escapes refused and logged: PARTIAL. Symlink escape refused and logged (broker.resolve, policy.classify, dispatch.execute). The typed `..\` traversal was refused but has no audit row (B2), and refusals are not visible in "What changed" (U4).

## Bugs
### B1. A whole drive root (`C:\`) can be granted with no warning (high)
Steps: Folders tab, type `C:\`, click Add folder. Reproduced 1 time (granted; re-adding says "already granted").
Expected: a warning or refusal, since the promise is a narrow boundary the user opts into.
Actual: the grant succeeded and 355 files were indexed. The card has an empty folder name (only "355 files" and `C:\`). Audit row 14 `workspace.grant` with `name:""`, `root:"C:\\"`. Evidence: `c_folders_cards.png`, `b_root.png`.

### B2. Typed `..\` traversal refusal is not written to the audit log (medium)
Steps: Work tab, folder docs, ask `show me ..\secret\private.txt`. UI says "reaches outside docs, so it was not done". Reproduced 1 time.
Expected: refusal recorded (the gate says "refused and logged"). Actual: `audit_log` has no row for that turn (rows 37-41 belong only to the later linkdir turn). The code path `_outside_reference` in `assistant.py` answers before the gateway. Evidence: `l_*.png`, read-only query of artemis.db.

### B3. The AI invents content for a file it cannot see (medium, 1 time)
Steps: with docs selected, ask `read linkfile.txt and tell me what it says` (linkfile.txt is a symlink to an outside file containing "TOP SECRET outside" and is not in the index).
Expected: "I can't see that file". Actual: "It says the meeting is rescheduled to Tuesday afternoon...". A fabricated claim; no audit row for the turn either. Evidence: `l_*.png` (first question's screenshot).

### B4. "files known" stat does not update after forgetting one file (low)
Steps: What it knows, forget one file. The stat stayed 373 (should be 372). Reproduced 1 time. Evidence: `e_forget_file_dbl.png`.

## Not desired behavior
- U1 (medium): Pressing Enter in "Folder to add" does nothing, with no feedback. Power users expect it to add. Reproduced 2 times.
- U2 (low): Errors are terse and raw ("already granted: E:\...", "folder does not exist: ..."). A relative path (`..`) resolves against the server's working directory and gave "cannot grant the ARTEMIS store directory", which is confusing.
- U3 (medium): Reloading while a large folder is being indexed leaves no progress indicator. "files known" climbs 501 -> 773 silently in the background. `n_reload_midadd.png`.
- U4 (medium): Refusals are not visible to the user. What changed says "Nothing has changed outside ARTEMIS" and only lists file changes, so refused attempts cannot be seen in the UI.
- U5 (low): "stored locally" jumps from 527 KB to about 118 MB after granting `C:\`, unexplained.
- U6 (low): Browse gives no feedback when no dialog opens (headless, so uncertain).
- U7 (low): No-selection feedback is inconsistent: Forget file says "choose a file first"; Show files and Forget folder showed no message I could capture.
- U8 (low): Tab labels appear twice in the page text (probably a hidden duplicate).

## Worked well
- Double-clicking Add folder, Check for changes, Forget file and "Yes, forget it" caused no duplicates, errors or crashes.
- Forget never touched files on disk (confirmed: 400 files in big, docs intact).
- Forget folder and Erase ask first, with clear wording ("None of your files are touched").
- Rescan reports "1 new, 1 gone" and matches the disk.
- Symlinked dir/file inside a granted folder were excluded from the index; the symlinked directory refusal was logged on three layers.
- State survives reload and server restart.

## Not tested / blocked
- Browse dialog (native, headless).
- Junctions (real symlinks were created and used).
- Other drives, locked or read-only folders.
- A real file-read through a symlink by an approved plan (the model answered without a plan).
- Cloud-model toggles (outside Sprint 2).
