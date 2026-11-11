# sprint-9 / agent-b / Impatient power user

Summary: Pairing, per-folder sharing, remote asks, tidy-with-approval, outward-approval blocking and encrypted transport all work, and the paired phone survives a phone close/reopen and a host restart (after Connect is pressed again). Impatient use exposed real problems. The most serious is that a plan already waiting for approval on the phone can still be approved after the owner unticks the folder, and it then changes files in a folder that is no longer shared. A phone-approved change also could not be undone from the host once (Undo said "There is nothing to undo."). Several silent-failure paths (removed phone, restart, refresh mid-pairing) leave the user with no explanation. Verdict: **PASS WITH ISSUES** (leaning FAIL on "remote never exceeds local" because of B1).

Setup: local relay `ws://127.0.0.1:8025`, app `s9-b` on 7925, phones = Playwright persistent contexts on `http://127.0.0.1:8025/`. I unticked "Voice is on" on the host Work tab once. Disk facts were read from `home/artemis.db` (audit_log, undo_journal, remote_devices) read-only, and from `server.log`.

## What I did
1. Added two folders, connected host to the local relay, started pairing.
2. Started two pairings and paired two phones at once; compared safety numbers.
3. Pressed Decline then Confirm on the same entry; pressed Confirm twice fast on the other.
4. Closed and reopened the phone (pairing remembered), refreshed mid-request, asked with no folder ticked, ticked a folder and asked without reloading the phone.
5. Asked for a tidy on the host (card pending), asked the same tidy on the phone, approved on the phone (double-click), then approved the stale host card, then Undo on the host, then Undo again.
6. Unticked the folder while the phone held a pending tidy and pressed Approve on the phone.
7. Phone asked for a web search and an email; Approve was blocked; asked a second thing while a card was pending.
8. Restarted the host (no wipe), reopened the phone, pressed Connect on the host.
9. Removed a device mid-request, then reloaded the phone and tried to ask.
10. Refreshed the phone mid-pairing, re-entered the code, confirmed the stale entry on the host, tried a wrong code and a code with no dash.
11. Two phones plus the host asked the same thing at the same moment.
12. Watched phone WebSocket frames for plaintext; tried Talk with voice off, then on, then switched off while talking.
13. Read the audit table from disk.

## Backlog items checked
- User can pair a remote device with their host machine: PASS. Two phones paired in one go with matching safety numbers (screens 05, 06, 09, 10); phone remembers its pairing after close/reopen (11, 30). Problems around it: B2, B3, U1, U2.
- Relayed traffic is unreadable to the edge: PASS (partial scope). Phone WebSocket frames carried none of the typed text or file names in plaintext. I did not inspect the relay's memory; only the phone-side wire.
- Remote access never grants more than local access: FAIL. Unticked folder still approvable from a pending phone card (B1). Otherwise PASS: unticked or never-ticked folder refused (12, 13), web search and email cannot be approved from the phone (27, 28), voice from a device refused until ticked (41, 42).
- Revoke a device: PARTIAL. Host removal is instant and the phone can no longer talk, but the phone shows no explanation (U3, screen 35).
- Stage gate: deleting the remote plane changes nothing locally: NOT TESTED from the UI (cannot delete code from the UI).
- Session time limit (1 hour in plane.py) and pairing code expiry (5 minutes): NOT TESTED, too long to wait; noted only.
- Audit entries for remote activity: PARTIAL. pairing_started, paired, session started, workspaces, ask (done and refused), approve, revoked, voice_start refused/approved are all written (read from disk). Weak detail: see U8.

## Bugs
### B1 (high): a pending phone plan can still be approved after the folder is unticked
Steps: phone asks "tidy this folder" in docs1 (card shows, Approve visible); on host Settings > Remote access untick docs1 ("Saved."); press Approve on the phone.
Expected: refused, the folder is no longer shared.
Actual: phone shows "Done: 2 folders created, 12 files moved." and the files really moved (disk: docs1 held Documents, Images, budget 2026.xlsx, random.zip). A new ask afterwards was correctly refused. Reproduced 1 time. Evidence: 25-host-unticked.png, 26-phone-approve-after-untick.png, audit approval.decided plan f34e619c3170.

### B2 (medium): Decline then Confirm shows a raw framework error
Steps: pick a waiting device, press Decline, then press Confirm without choosing again.
Expected: "Choose the device first."
Actual: red toast `Value: 5601968dc23ff622 is not in the list of choices: [...]` and "Error" badges on the three dropdowns; the old "Declined" note stays. Reproduced 2 of 2. Evidence: 07a-confirm-after-decline-error.png, server.log traceback (gradio dropdown preprocess).

### B3 (medium): refreshing the phone mid-pairing leaves a confirmable ghost
Steps: phone joins with a code (safety number shown), refresh the phone page, host Check again, pick the entry, Confirm.
Expected: the abandoned join disappears or cannot be confirmed.
Actual: host says "Phone A is paired. Tick the folders it may use." and lists "Phone A" under Paired devices, but no phone holds a key (phone shows the pairing form). The ghost stays until removed. Re-entering the same code on the phone gives "Your computer did not answer. Start pairing there first." Reproduced 2 times. Evidence: 36, 38, 39 png.

### B4 (medium): a change approved from the phone could not be undone from the host
Steps: phone tidy then Approve (B1 flow); on host Work press "Undo last change".
Expected: undo reverses the phone-approved plan (journal has rows for plan f34e619c3170, ids 29 to 42).
Actual: "There is nothing to undo." and the files stay moved. In the first run Undo did work, but it reversed the host's stale copy (plan ab0e7bf84c29, "14 steps reversed") while the phone's plan b0865eeed0ae kept its 14 journal rows. Reproduced 1 clean time. Evidence: 24-second-undo.png, undo_journal rows read from disk.

### B5 (medium): phone shows the old card when a second request arrives while a card is pending
Steps: phone asks for a web search (card shown), then asks "email sara@example.com ..." without answering.
Expected: the new request is handled or refused clearly.
Actual: the phone still displays the web search card; the audit log shows a new "1 send mail" approval request (plan f2241dbb2174), so what the phone shows no longer matches what is pending. Reproduced 1 time. Evidence: 28-phone-email.png, audit_log rows 144 and 147.

## Not desired behavior
- U1 (medium): Abandoned pairings pile up in "Waiting for you to confirm" (6 to 8 entries, several named "Phone A"); only the safety number tells them apart. No expiry, and audit pairing_started "pending" rows never close. Evidence: 06-host-waiting.png.
- U2 (medium): After a host restart (data kept) the paired device and ticked folders survive, but the host does not reconnect to the relay; the status reads "Not connected" (also after every page refresh, even when connected) and the phone says "Your computer is not answering. Is ARTEMIS open?" until Connect is pressed again. The first ask right after Connect still failed once. Evidence: 30, 31, 32 png.
- U3 (high): A removed phone looks normal. Reloading shows the full app with an empty folder list and no message; Ask returns nothing clear (no answer within 40 s). It should say the device was removed and offer Forget. Evidence: 34, 35 png.
- U4 (medium): Phone does not refresh its folder list. After the owner ticks a folder the phone keeps asking in vain ("That folder is not available remotely.") until reloaded. With an empty dropdown the message should be "Choose a folder first."
- U5 (medium): Refreshing the phone mid-request loses the answer completely, with no "still working" state (screen 14).
- U6 (medium): The same plan is approvable in two places. After the phone approved the tidy, the host's identical card still showed Approve; approving it gave "Done: 2 folders created. 12 steps did not run: a file with that name already exists." The "Done" wording is misleading. Evidence: 22-host-stale-approve.png.
- U7 (medium): Phone Talk with voice switched off shows the error but the button still says "Stop talking" and the microphone stays open; switching voice off on the host while talking leaves the phone on "Listening…" with no message. Evidence: 41, 42 png.
- U8 (low): Remote audit rows hold only the device id: no folder, request text or plan id on approve; wrong-code pairing attempts are not audited. (The known "audit cannot be read in What changed" also applies.)
- U9 (low): The relay address box pre-fills the deployed Cloudflare address. A wrong code on the phone gives "The relay refused that." which does not say the code is wrong.
- U10 (low): The relay server log fills with long ConnectionClosedError tracebacks when a phone closes.
- Known items seen again, not new: voice greeting turn on host (I unticked Voice is on), two hidden duplicate "Check again" buttons.

## Worked well
- Two phones paired together with distinct safety numbers; double Confirm and Decline did not crash (apart from B2).
- Phone remembers its pairing across close/reopen; host remembers devices and ticked folders across restart.
- Folders are invisible and refused until ticked; web search and email cannot be approved from the phone (Approve disabled, clear wording).
- Phone and host asking at the same moment each got a correct answer; two phones likewise.
- Phone traffic had no plaintext on the wire; voice from a device is refused until ticked.
- Host Undo returned files to the original state in the run where it applied.

## Not tested / blocked
- Gate "deleting the remote plane changes nothing locally": cannot be done from the UI.
- 1-hour session limit and 5-minute code expiry: not waited for.
- Relay-side unreadability beyond phone-side frames: not inspected.
- Actual spoken conversation (fake mic gave silence): only start, refusal and switch-off paths seen.
- Leftover state (ghost device, stale pending pairings) remains in the private app copy only.
