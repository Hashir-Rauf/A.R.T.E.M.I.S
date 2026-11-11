# sprint-5 / agent-a / Curious newcomer
Summary: The core promises of Sprint 5 mostly hold. Tidy previews every move and nothing moves before Approve; undo (same session) restores files; outside-folder and delete requests are refused; the pattern notice appears only after the 3rd approved tidy; a saved note survives a restart. But the experience is rough for a newcomer: natural phrasings ("please tidy up", "organise my files", "sort files by type") only list files; new files on disk are invisible until "Check for changes" and tidy then says the folder is "tidy enough"; accepting a habit does nothing (the app itself says automatic offers are not built); undo is lost after a restart; "What changed" shows the old note. I unticked "Voice is on" in Talk to avoid the voice greeting. Actions were UI only; I read the disk and the habit source afterwards to verify. Verdict: PASS WITH ISSUES.

## What I did
1. Started a private app (s5-a, port 7912), added a messy 14-file folder, unticked "Voice is on".
2. Clicked "Suggest a tidy-up", read the preview card, reloaded the page (card vanished, another "Hi again" greeting appeared).
3. Typed 7 vague and varied tidy requests, declined a plan, then approved tidy three times (adding new files on disk and using What it knows > Check for changes), pressing Repeated tasks after each.
4. Opened Habits and choices, accepted one habit, declined another.
5. Saved an empty note and a note with HTML, clicked What changed, killed and restarted the app without wiping data, looked at the resume card, tried Undo.
6. Did a fresh tidy, approve, undo and checked the disk; tried outside-folder, traversal, delete and rename requests.

## Backlog items checked
- Pick up where you left off: PARTIAL. Note saved and shown after restart (20-after-restart.png). But resume card shows only the note, What changed echoes the note, undo history is gone after restart, and a "Hi again, pick up where we left off" greeting appears even with no note.
- Tidy a folder after previewing every move: PASS. Every step listed, nothing moved before Approve (disk checked), decline leaves files alone, undo restored files (22-undo-ok.png). Typed phrasing coverage is poor (B1).
- Automation offered only after 3 repeats: PARTIAL. Rounds 1 and 2: "Nothing repeated often enough"; round 3: "Noticed 3 things" (10-round3-repeated.png). Threshold correct. Accept and decline are recorded but accepting changes nothing (B3).
- Capabilities reach files only via the broker: PARTIAL. Outside-folder paths and `..` refused, delete refused, rename goes through an approval card. Internals not visible from the UI.
- Stage gate (three features end to end through gates): PARTIAL, as above.

## Bugs
B1 (medium) Natural requests to tidy do not produce a tidy plan. Steps: Work, type "please tidy up this folder" / "tidy up this folder please" / "can you organise my files" / "sort files by type", Enter. Expected: the tidy preview. Actual: a bare list of the 14 files; "orgnize my docs into folders" gets a chatty offer with no card. Only "tidy", "Tidy up this folder", "clean up this folder" work. Reproduced twice. Evidence: 11-phrasings.png, 05-vague.png.
B2 (medium) Tidy says "Only 2 loose files here, which is tidy enough" while 4 to 6 new files sit in the folder; it uses a stale index. New files are seen only after What it knows > Check for changes (found only by exploring). Reproduced 2 times. Evidence: 12-folders.png, 14-knows.png, disk listing.
B3 (medium) Accepting a habit ("Yes, that is a habit") does nothing: message says "Automatic offers are not built yet, so it will not act on it." The story "offered automation" ends with a notice and no offer. Evidence: 17-accepted.png.
B4 (low) Plan says "Create 2 folders" and result "Done: 2 folders created" in rounds 2 and 3 although Documents and Images already existed (disk). Evidence: 08-round3-preview.png.
B5 (medium) "What changed" returns the saved note ("You noted: ...") instead of a list of changes, twice, including after restart. (Related to the known audit-unreadable issue, but different symptom.) Evidence: 20-after-restart.png.
B6 (medium) After restarting the app, Undo says "There is nothing to undo" though tidies were done and the card had said "You can undo it". Each restart also adds another "Chat · today" entry. Evidence: t13 run output.
B7 (low) After a habit was accepted/declined, Repeated tasks says "Nothing repeated often enough" while the panel still lists "moving JPG files". Contradictory. Evidence: 18-declined-habit.png.

## Not desired behavior
U1 (medium) "Hi again. Let's pick up where we left off. What's next?" shows on a brand-new data folder with no note, and one more is added on every reload. Misleading.
U2 (medium) Habit wording vague ("creating a folder for files", "moving PDF files", no folder or example); three "habits" come from one tidy. Habit dropdowns are empty with no explanation until Repeated tasks is pressed (06-habits-open.png). Nothing is offered proactively.
U3 (low) Saving an empty note gives no feedback.
U4 (low) Approve buttons sit above the preview, which scrolls inside a small box (7 of 14 steps visible); the card shows "docs" only, not a path.
U5 (low) After reload, Approve buttons are greyed with no explanation; the newest user chat bubble is clipped (06-habits-open.png).
U6 (low) A vague "sort my stuf out pls" gives only a file list, no hint about Suggest a tidy-up.

## Worked well
- Preview lists every step with reassurance chips; declining says "Left alone. Nothing was changed."
- Moves matched the preview on disk; undo restored files in the same session.
- Outside-folder and delete requests refused in plain wording; rename shown as a card.
- Three-repeat threshold respected; declined habit not raised again.
- Note persists across restart.

## Not tested / blocked
- "Ask me again before doing this" (revoking a remembered choice) not tested.
- Broker internals cannot be observed from the UI.
- Voice not tested (unticked). Habits across multiple folders not tested.
