# ARTEMIS test summary for the project owner

27 testers (9 areas x newcomer / power user / chaos) used the real UI. Full detail: `FINAL-REPORT.md`; machine-readable: `bugs.json`.

**Verdict: PASS WITH ISSUES, not ready to hand to real users yet.** Nobody found a clean pass; 4 of 27 testers said FAIL. Of the 39 backlog stories and gates, 13 pass, 20 partly pass, 5 fail and 1 could not be tested. We found **71 distinct bugs (1 critical, 18 high, 37 medium, 15 low)** and 63 "works but nobody would want this" items.

## What is solid
- ARTEMIS never deleted anything, however it was asked (many phrasings), and refused anything outside the chosen folder, in plain words.
- Nothing left the computer (web search, email) without an approval card; double-clicks and stale clicks did not run things twice; code questions only ever produce a diff, never an edit.
- Voice cannot approve, delete or send. A phone cannot approve emails or searches, only sees folders you tick, and can be removed instantly.
- Tidy previews every step, undo works in normal use, and the "repeat three times" habit rule is exact.

## What is broken
- **Data loss:** if a tidy meets two files with the same destination name, one is silently lost on Undo and the app says "your files are back as they were". Undo can also overwrite a file you made in the meantime.
- **You cannot see what ARTEMIS did.** The activity record exists on disk but no screen shows it; "What changed" says nothing changed right after ARTEMIS moved files; refused attempts are not logged; and a banner keeps saying "Nothing has been sent anywhere" after a web search.
- **Privacy and boundary slips:** the microphone can stay live after "Voice is off"; a phone plan still ran after the folder was un-shared; a chat can carry one folder's content into another; "Allow cloud" can be switched on without choosing a folder; any drive (even C:\) can be added as a folder.
- **Untrustworthy answers:** it sometimes invents answers with no source, says "not found" for things that are in the files, cites the wrong file, claims it searched the web when it did not, and writes emails that say "see attached" with nothing attached.
- **Rough edges everywhere:** the voice greeting and panel crowd the page and sometimes wipe the conversation from view; messages sent while busy, or before a reload, vanish silently; new files are invisible until "Check for changes".

## Fix first (details and the full top 15 in the report)
1. Make tidy/undo collision-safe (never overwrite; report what could not be restored).
2. Add a readable activity view and log every refusal; replace the static "nothing was sent" banner with a live one.
3. Stop the microphone completely when voice is off.
4. Re-check the folder grant when a phone approves a waiting plan.
5. Make answers honest: no source means a visible "not backed by a file" label; fix the missing embedding model and warn when search is degraded.
6. Add guard-rails to "Add folder": refuse drives and system folders, require full paths, index in the background with progress.

## Caveats
Testers could not hear audio, never saw a cloud model answer or a real email go out, and did not test the remote relay's own side, the 7-day chat retention, or the "remove the remote plane" gate. The machine lacked the embedding model, which probably inflates the retrieval misses. Several of the worst findings come from a single tester and are marked as such in the report; they deserve a quick re-check once fixed.
