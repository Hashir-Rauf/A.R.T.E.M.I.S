# sprint-5 / agent-b / Impatient power user

Core File Features mostly works through the real gates: tidy previews every step, approve/undo is reliable under rapid clicking, notes survive an app restart, and the habit offer appears exactly at the third non-undone repeat. The main weaknesses: ARTEMIS does not notice files changed outside it (tidy and the resume card work from a stale index until the user clicks "Check for changes" in another tab), the "you can undo it" line and Undo are lost after a restart, and a habit the user accepts does nothing yet. Verdict: **PASS WITH ISSUES**.

Method: all actions through the UI (Playwright). I looked at the disk to verify claims, and I moved/edited files on disk myself to simulate outside changes. I unticked "Voice is on" at the start of every session (the greeting turn and a "Voice is on. Just talk" line were in the way). I did not use the server log (nothing useful in it).

## What I did
1. Started private app s5-b, added a messy folder "docs" (14 files), unticked voice.
2. Clicked "Suggest a tidy-up" 4 times fast, then Approve (twice quickly), Undo twice quickly.
3. Suggested a tidy, then on disk deleted a file, edited one, renamed one, added one, then Approved. Undid.
4. Added a second folder (notes2), made a tidy plan, switched the dropdown to docs while the plan was pending, approved.
5. Saved notes (empty, Enter key, double click, 700 chars, HTML characters). Restarted the app (data kept) and reloaded.
6. Ran more tidies (flatten folder on disk, Check for changes, tidy, approve) and watched "Repeated tasks" and the Habits accordion.
7. Accepted a habit, declined a habit, rapid-clicked Yes/No/forget; used "Approve, don't ask again" then "Ask me again before doing this".
8. Rapid Approve then "No, leave it"; 3x Undo.

## Backlog items checked
- Pick up where you left off (note + resume card + restart): PARTIAL. Note saved and shown after restart (15-after-restart.png). But the resume card says "Nothing has changed outside ARTEMIS" while files changed on disk, until "Check for changes" is clicked (B1); "ARTEMIS last did this... You can undo it." and Undo are lost after restart (B3).
- Tidy a folder after previewing every move: PASS. The card lists every step and nothing moves before Approve (02-rapid-tidy.png). Edge cases are weak (B2, B5).
- Automation offered only after a pattern repeats three times: PARTIAL. Not offered after 2 plans, offered after the 3rd; undone plans did not count. Accept saves a habit but says "Automatic offers are not built yet" (U3). Decline hides it; forgetting a rule works. Lists empty on load (U4).
- Capability services reach files only through the broker: PARTIAL. From the UI every file change came through an approval card (or a prior "don't ask again" rule); no direct change seen. Internals not inspected.
- Stage gate (three features end to end through real gates): PASS WITH ISSUES. Resume, tidy and habits all ran with approval and undo.

## Bugs
**B1 medium. Resume card and tidy use a stale index of the folder.** Steps: tidy and approve, then on disk move all files back to the root, click "What changed" or "Suggest a tidy-up". Expected: ARTEMIS sees the 13 loose files. Actual: resume says "Nothing has changed outside ARTEMIS since a moment ago" and tidy says "Only 3 loose files here, which is tidy enough", even after an app restart while the picker shows 13 files. Only What it knows > "Check for changes" fixes it; then What changed shows "10 new, 10 gone". Reproduced 3 times. Evidence: 14-after-flatten.png, 16-tidy-after-restart.png.

**B2 medium. Approving a stale plan runs part of it and shows a raw OS error.** Steps: suggest tidy, delete one file and rename another on disk, Approve. Actual: "Done: 2 folders created, 10 files moved. 2 steps did not run: [WinError 2] The system cannot find the file specified." No file names, raw error text, no re-preview of a plan whose files changed. Reproduced 2 times. Evidence: 11-stale-approve.png.

**B3 low-medium. Undo and the "last did this" line do not survive a restart.** After restart "Undo last change" says "There is nothing to undo." although an approved plan exists. 1 time.

**B4 low. Undo count overstated after a partly-failed plan.** Plan with 12 steps run and 2 failed; Undo said "14 steps reversed". 1 time (06-undo-after-edit.png).

**B5 medium. Changing the folder dropdown while a plan is pending leaves the old folder's plan live.** Made a tidy for notes2, switched the dropdown to docs: card still titled notes2, buttons enabled; Approve moved the notes2 files while the picker showed docs, and "Done" does not name the folder. 1 time. Evidence: 08-after-switch.png, 09-approve-after-switch.png.

## Not desired behavior
**U1 low.** Four fast clicks on "Suggest a tidy-up" add four identical chat turns for one plan; no hint that it is already suggested.
**U2 low.** Notes: no clearly visible save confirmation in my captures; a 700-char note is silently cut to 500; only the latest note is kept; Enter in the box does nothing.
**U3 medium.** Accepting a habit says "Automatic offers are not built yet, so it will not act on it." The story promises automation offered after three repeats; the user can accept but nothing ever happens.
**U4 medium.** "A habit ARTEMIS noticed" and "told not to ask about" lists are empty on page load and after restart; they fill only after clicking "Repeated tasks". After "Approve, don't ask again" the rule list stays empty until then.
**U5 low.** Habit labels are generic ("creating a folder for files", "moving PDF files") and six appear at once from one repeated tidy; "Repeated tasks" says "Nothing repeated" while the list still holds offers.
**U6 low.** The resume card disappears after clicking "Repeated tasks".
**U7 low.** "Voice is on. Just talk" text and a Microphone widget ("No microphone found") remain after unticking voice; greeting turn on top (known).

## Worked well
- Approve and Undo clicked rapidly do not double-apply; extra Undo clicks say "There is nothing to undo."
- Plan preview lists every step; "Nothing is deleted" and risk text are clear.
- HTML in notes is escaped; notes, folders and chats survive restart.
- Habit offered exactly at the third non-undone plan; undone plans ignored.
- "Ask me again before doing this" brings the approval card back.
- Tidy leaves unknown types (xlsx, zip) in place.

## Not tested / blocked
- Broker internals (UI only; source not read).
- Decline message text (not captured), later effect of an accepted habit (none exists).
- Voice, huge folders, page refresh mid-plan (out of budget).
