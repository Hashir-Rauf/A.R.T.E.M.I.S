# sprint-7 / agent-b / Impatient power user

Outward actions are well gated: web search and email always show an approval card first, a double-click on Approve ran exactly one search, "Approve, don't ask again" is disabled on outward cards, nothing left the computer while idle (90 s watch of page requests and the audit table), and drafts never overwrite (a repeated name becomes "(2)"). The weak spot is visibility: after a real search left the machine, the header still says "Nothing has been sent anywhere", "What changed" says "Nothing has changed outside ARTEMIS", and no screen lists what left and when (only the raw audit table has it). Verdict: **PASS WITH ISSUES** (the story "see exactly what left the machine and when" is FAIL in the UI). Real mail sending was not testable (no account may be connected).

## What I did
1. Started a private app (s7-b, port 7919), added two folders, unticked "Voice is on" (voice otherwise greets and arms itself; after a page refresh voice re-armed and the box was ticked again).
2. Asked for a web search; read the card; double-clicked Approve; results appeared. Verified in the audit table (disk) that exactly one search ran.
3. Opened What changed, Settings and What it knows looking for a record of what left the computer.
4. Asked for an email to someone@example.com; read the card; double-clicked Approve (fails cleanly: no mail account).
5. Approved a search and immediately force-clicked "No, leave it".
6. Tried "Approve, don't ask again" on a search card.
7. Refreshed the page with a search card pending; restarted the app with one pending.
8. Queued a search and an email back to back; changed the folder dropdown while an email card was pending, then approved.
9. Drafted a document whose requested name (notes.txt) already exists; drafted "write a summary of my notes" twice; Undo.
10. Two emails in a row; email to an invalid address; email to three addresses; 90 s idle watch.

## Backlog items checked
- Web search on demand, never in the background: PASS. Card first (04-card.png); no outside requests from the page and no web.search or audit rows during a 90 s idle; search only runs after Approve.
- Mail only after approving the draft: PARTIAL. The gate works (card shows To/Subject/Body first; Approve with no account gives "Nothing was changed. 1 step did not run: no mail account is set up yet."; an invalid address is caught). Real sending NOT TESTED.
- Draft document without losing an existing one: PASS. notes.txt unchanged (byte compare); same name twice gave "summary-notes.md" then "summary-notes (2).md"; Undo removed the last file (20-undo.png).
- See exactly what left the machine and when: FAIL in the UI. The audit table has `web.search sent {query, provider, results}` with a timestamp, but What changed says nothing left (06-whatchanged.png), the header says nothing was sent, and the result turn does not say what was sent or to whom.
- Stage gate, no outward action escapes its gate: PASS. Double-click, approve-then-reject, refresh, queued requests: every web.search / send_mail row in the audit follows an approval.decided row; "Approve, don't ask again" is disabled (11-dontask.png) and `remembered` is always false.

## Bugs
### B1 (medium): "Nothing has been sent anywhere" banner is false after a search leaves the computer
Steps: ask for a web search, Approve, look at the top-left green banner and press What changed (also after reload).
Expected: the claim updates or the screen shows a search was sent. Actual: banner stays "Everything is stored on this computer. Nothing has been sent anywhere." and What changed says "Nothing has changed outside ARTEMIS since N minutes ago." while audit row `web.search sent {"provider":"duckduckgo","query":"python dataclasses"}` exists. Evidence: 05-after-dblclick.png, 06-whatchanged.png, audit rows 18 and 33. Reproduced 4 times.

### B2 (medium): No place in the UI shows what left the machine and when
Steps: after a search or mail attempt check Work, What changed, What it knows, Settings. Expected: a list of outward actions with time, destination and content. Actual: none (the audit data exists only in the database; related to the known "audit cannot be read" item, but this is the Sprint 7 story itself). Evidence: 09-What-it-knows.png, 09-Settings.png.

### B3 (low): An outward card replaced by a newer request is dropped silently and stays "pending" in the audit
Steps: ask for a search, 0.3 s later ask for an email, wait. Expected: both handled, or the user is told the first was cancelled. Actual: only the email card shows; search plan 0f5d78a6ce9e has approval.requested and never a decision (audit rows 41/43), with no message. Same for a search card pending when the app restarted (plan afaaac646735). Nothing ran, so not an escape, but the record never resolves. Evidence: 14-queued.png.

## Not desired behavior
- U1 (medium): About 30 s after asking (first run, voice unticked right after load) the conversation was replaced by just the greeting; my request and its message vanished while the card stayed (03-full.png). Related to the known voice greeting item. Seen once.
- U2 (medium): Draft names ignore what the user asked for: "a new document called notes.txt" saved "document-called-notes-txt.md"; "a file called plan.md" gave "file-called-plan-md.md" (17-draft-card.png, 18-draft-approved.png). Safe but not what a person wants.
- U3 (low): Approve/Reject buttons sit above the card, far from the content on long pages; the "no mail account" warning shows only in the chat turn, not on the card, so the card looks sendable (07-email-card.png).
- U4 (low): Approve then immediate "No, leave it": the search still ran and the reject click gave no feedback (10-approve-then-reject.png).
- U5 (low): Changing the folder dropdown while a card is pending leaves the card on the old folder; approval used the card's folder, no warning (15-foldchange.png).
- U6 (low): Emails are written with an invented body and signed "ARTEMIS", and the subject I typed ("test0") was not used.
- U7 (low): Every page load/refresh adds another "Chat - today" entry (six empty entries in 17-draft-card.png); stale banners (e.g. "already granted ...") stay at the top.
- U8 (low): Voice re-arms and the "Voice is on" box ticks itself again after a refresh even if unticked.

## Worked well
- Approval card before every outward action with the risk line "sends something off this computer".
- Double-click Approve ran once (one audit row each).
- "Approve, don't ask again" greyed out for outward actions; a pending search card survives a page refresh and still approves.
- Zero outbound requests and no audit growth while idle.
- Draft collisions become "(2)", the original is untouched, Undo works; friendly message for an invalid address.

## Not tested / blocked
- Real SMTP sending and a "mail sent" success message (no account may be connected).
- Settings email form validation with fake text (only read, not filled).
- Server-side network activity: the server log stayed empty, so I relied on the audit table and browser requests.
- Two browser pages approving the same card at once (only one page used).
