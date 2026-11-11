# sprint-2 / agent-a / Curious newcomer

Summary: I used the Folders and What it knows tabs like a first-time user (typos, wrong paths, copy-pasted quotes, a relative name, asking for things outside my folder). The boundary works through the Work tab (outside and ".." requests are refused in plain words), a junction placed inside a folder was not followed during indexing, and forgetting files never touches the disk. But the folder-adding step lets a user grant a whole drive (`C:\`) with no warning, and adding `C:\Windows` froze the whole UI for more than 9 minutes with no cancel. A relative name such as "docs" is silently resolved against the server's working directory and grants the project's own Docs folder. Refusals I made through the UI did not appear in the activity log or What changed, and the Folders tab has no remove button. **Verdict: PASS WITH ISSUES, close to FAIL on the "cannot reach outside" promise for broad paths.**

## What I did
1. Opened the app: stats bar shows 0 folders; Folders tab says "ARTEMIS cannot see anything on this computer." Clear.
2. Typed a non-existent path, an empty box, a path with quotes and trailing space (as copy-pasted): clear messages (shots 03, 04, 05).
3. Pressed Enter in the path box: nothing happened (shot 10). Clicked Add folder: folder added, 14 files (shot 20).
4. Added the same folder again, a `..` path, and a file path: "cannot grant the ARTEMIS store directory", "not a folder: ..." (shots 12, 13).
5. What it knows: Show files, edited the folder on disk (added one file, deleted one), Check for changes, Forget this file (shots 21-24).
6. Work tab: asked to read `C:\Windows\win.ini` and `..\outside\secret.txt` (shots 30, 31); opened What changed (32).
7. Tried broad/odd paths: `C:\`, home folder, `C:\Windows`, relative name `docs`, UNC path, junction, `Z:\` (shots 40-43, 50-*, 60-*).
8. Tried Forget this folder (confirm prompt); looked at the audit database on disk (read only) and the server log.

## Backlog items checked
- User can opt a folder in as a workspace: PARTIAL. Works for a normal folder (14 files, shot 20) but accepts `C:\` and relative names (B1, B3), and Enter does not submit (U1).
- System cannot resolve any path outside a granted workspace: PARTIAL. Requests for `C:\Windows\win.ini` and `..\outside\secret.txt` were refused: "That reaches outside 'docs'" (shots 30, 31). But a user can grant a drive root, which removes the boundary (B1).
- User can see every file indexed and delete any of it: PARTIAL. Show files lists everything; Forget file/folder work and the disk was untouched (15 files remained). Stale counter (U3), non-sticky forget (U4), no remove on Folders tab (U2). Erase everything and the Forget-folder "Yes" were not clicked.
- Stage gate, traversal and symlink escapes refused and logged: PARTIAL. Refused: `..` containing the store dir, outside reads via Work tab; junction inside a folder was not indexed (secret.txt never listed). Logged: NOT confirmed, no refusal rows in audit_log and nothing in What changed (B4).

## Bugs
**B1. Whole drive can be granted as a workspace** (high). Folders > type `C:\` > Add folder. Expected: refusal or strong warning for drive roots/system folders. Actual: added with a blank name, 2661 files indexed and listed (shot 42-folders-after-forget.png: 2 folders, 2675 files). Reproduced 2 times. A beginner who types `C:\` gives the assistant read and change rights on the whole disk.

**B2. Adding `C:\Windows` freezes the app for many minutes** (high). Type `C:\Windows` > Add folder. Expected: quick refusal, or background indexing with progress and cancel. Actual: every panel showed "processing" (62 s, 125 s, ... 563 s by the end of my run; shots 50-add-0, 50-add-1, 50-add-4), stats stayed at 0, later clicks queued behind it, no cancel. Reproduced 1 time.

**B3. Relative path silently grants an unintended folder** (medium). Type `docs` > Add folder. Actual: "Added 'Docs'. ARTEMIS now knows about 22 files in it", and the granted root in audit_log is the project's own `...\A.R.T.E.M.I.S\Docs` (resolved against the server's working directory; shot 60-add-0). Expected: require a full path. Reproduced 1 time.

**B4. Refusals not visible in the activity log** (medium). After refusals (store directory `..\..`, nonexistent path, duplicate) the audit_log held only grant/scan/session/embed rows (SQLite read only); What changed shows only file added/removed lines (shot 32-what-changed). The gate promises "refused and logged". Reproduced 2 times. Not tested whether a Work-tab outside read is logged elsewhere.

## Not desired behavior
- **U1 (medium)** Enter in the path box does nothing and says nothing (shot 10-added-enter; 2 times).
- **U2 (medium)** No remove on Folders cards; the removal is "Forget this folder" on another tab with different wording (shot 42).
- **U3 (low)** Stats "files known" stayed 14 after Forget this file (shot 24).
- **U4 (medium)** What changed says "removed: Invoice_March.pdf" for a file only forgotten (still on disk); next Check for changes brings it back as new (shot 32).
- **U5 (low)** Jargon: "cannot grant the ARTEMIS store directory" for a `..` path (shot 12).
- **U6 (low)** The `C:\` folder card has a blank title (shot 42).
- **U7 (low)** The red "not a folder" banner stays visible after switching to What it knows (shot 14).
- **U8 (low)** Second Add of the same folder re-shows the earlier success message instead of saying "already added".
- **U9 (low)** Every scan writes `index.embed unavailable (ollama 404)` to the activity log.

## Worked well
- Plain-language refusal: "ARTEMIS can only see inside the folders you have added ... Nothing was read, moved or changed."
- Clear empty state and clear messages for empty / nonexistent input; quotes and trailing space handled.
- Forget never touched the disk; Check for changes found 1 new and 1 gone file correctly.
- Forget folder asks for confirmation with reassuring text. A junction inside a folder was not followed on scan.

## Not tested / blocked
- Erase everything and the Forget-folder "Yes" click (budget; app state was messy after B1/B2).
- Real symlinks (need admin on Windows); only a junction was used.
- Native Browse dialog cannot be driven.
- Whether a Work-tab refusal is logged (the DB I inspected came from a run without Work-tab asks).
- Home folder add result not observed because the queue was frozen by B2.
- Note: my first run left an orphan app on port 7903 (my script crashed on a print encoding error); the later runs were fresh.
