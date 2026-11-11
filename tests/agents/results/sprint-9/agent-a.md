# sprint-9 / agent-a / Curious newcomer

Summary: I paired a simulated phone (second browser context at the local relay http://127.0.0.1:8024) with my private app s9-a (port 7924). Pairing, the safety number match, folder ticking, asking from the phone, outward-action refusal, remote voice (with tick) and device removal all work. Email and web search cannot be approved from the phone (the Approve button is disabled). The main problems are for a non-technical person: the host never shows the email/search that the phone proposed (so "approve it on the computer itself" leads nowhere), nothing updates by itself (host waiting list, phone folder list), a removed phone is left on a normal-looking screen with no message, and voice ignores the chosen folder. Verdict: PASS WITH ISSUES. Evidence: screenshots in agent-a/, Playwright output, disk listing (folder unchanged), host UI.

## What I did
1. Opened Settings > Remote access (collapsed by default). Pressed "Start pairing a device" before connecting: "Connect to a relay first." (clear).
2. Typed ws://127.0.0.1:8024, Connect: "Connected. ARTEMIS dials out to the relay; this computer opens no port."
3. Start pairing: a code like 4ffb51534bb927d6-N5TZGXBLDK appeared with "works once, expires in 5 minutes".
4. Opened the phone page in a second context (400px wide), typed the code, Pair. Phone showed a safety number; the host showed the device only after I pressed "Check again" (first I pressed Confirm without choosing: "Choose the device first.").
5. Compared safety numbers (they matched, e.g. 490339 on both), picked the device in "Waiting for you to confirm", Confirm: "My phone is paired. Tick the folders it may use."
6. On the phone, before any folder was ticked, asked "What files are in my folder?": "That folder is not available remotely." and the folder list was empty. Ticked "docs" on the host; the phone stayed unchanged until reload.
7. After reload the phone listed the 14 files. Asked for an email "to my boss" (it asked for an address), then "sort my stuf" (swallowed by the email dialogue), then an email to sam@example.com (draft shown, Approve disabled), then "search the web for cat videos" (card shown, Approve disabled). Pressed No, leave it: "Left alone. Nothing was changed."
8. On another phone: a code that was already used, a wrong code, a code without a dash. Tried voice before ticking on the host (switched-off message), then unticked host "Voice is on" (permitted) and ticked "Allow talking from a paired device", pressed Start talking with a fake mic WAV ("tell me about my files").
9. Removed the device on the host ("Removed. That device can no longer connect."), asked from the phone, reloaded the phone.

## Backlog items checked
- User can pair a remote device with their host machine: PASS. Code, matching safety numbers, confirm on host, phone became ready (needs a manual Check again, see U1).
- Relayed traffic is unreadable to the edge: PARTIAL. Not verifiable from the UI; the page says messages are scrambled and the relay only handled opaque frames. I did not inspect traffic.
- Remote access never grants more than local access: PASS. Unticked folder refused, only the ticked folder usable; email and web search cannot be approved from the phone (Approve disabled); remote voice needs the tick ("Voice from devices is switched off on the computer."). Disk listing of the folder unchanged afterwards.
- Revoke a device: PASS. After Remove device the phone's ask returned nothing (but see U5).
- Stage gate "deleting the remote plane changes nothing locally": NOT TESTED from the UI (as instructed).
- Optional by construction (off until Connect): PASS. "Not connected. Nothing is sent anywhere until you connect."

## Bugs
B1 (medium). Proposed outward actions are invisible on the host. Steps: pair, tick docs, from phone ask "search the web for cat videos" or "send an email to sam@example.com ...". Phone says "This would leave your computer, so it must be approved on the computer itself." Host Work tab shows only the greeting; no approval card and no phone turns (34-host-work.png). Expected: a card on the host to approve or reject, or a plain message to ask again on the computer. Actual: dead end. Reproduced twice (email and search).

B2 (low). Phone approval card is a run-on block ("Folder docs What it does Send 1 email Risk sends something off this computer Nothing is deleted Every step, in order 1 Send an email ...") and says "decide with the buttons above" while the buttons are below; Approve is greyed with no reason next to it (32-phone-email1.png). Reproduced 3 times.

B3 (low). Voice from the phone ignores the selected folder: dropdown showed docs, I said "tell me about my files" and the reply asked which folder / a directory path (44-voice-after.png). Typed asks on the same phone use the folder. Reproduced twice.

## Not desired behavior
U1 (medium). The host does not notice a joined device until "Check again" is pressed. Two "Check again" buttons exist in Settings (the local model one comes first, the remote one later), easy to press the wrong one (I did). "Choose the device first." is confusing when the list is empty (11-host-check-again.png).
U2 (medium). The phone does not learn that a folder was ticked: it keeps "No folder is shared with this device yet" and an empty list until reloaded. Asking with no folder gives "That folder is not available remotely.", which a newcomer will not understand (16-phone-ask-nofolder.png).
U3 (low). After pairing, "Tick the folders it may use" is far from the checkboxes; ticking gives only a small "Saved." (17-host-ticked.png).
U4 (low). With host "Allow talking" unticked, Start talking shows "Voice from devices is switched off on the computer." but the button reads "Stop talking" (42-voice-notick.png).
U5 (medium). After Remove device the phone keeps its normal screen (Ask, Start talking, old chat log). An ask returns nothing; a reload shows an empty folder list; no "this device was removed, pair again" message (47-phone-after-remove.png, 48-phone-reload-removed.png).
U6 (low). The phone's relay field is prefilled as http://127.0.0.1:8024 while the host uses ws://; the code is long and case/dash sensitive with no copy button (06-phone-initial.png).
U7 (low). "sort my stuf" typed while an email was half-drafted was swallowed by the email dialogue (it does offer "Say cancel"). "tidy this folder by type" from the phone returned a file list rather than a tidy plan.
U8 (low). Known: host voice starts automatically (I unticked it for the voice test); a greeting and a "Hello? Is there anything I can help you with?" nudge appear in the phone's voice log after about 4 seconds.

## Worked well
- Guidance messages: "Connect to a relay first.", "Type the whole code, with the dash.", "The relay refused that." for a wrong code.
- Safety numbers identical on phone and host.
- Folder boundary held: unticked folder refused; folder on disk unchanged after all attempts.
- Email and web search cannot be approved from the phone; reject gives "Left alone. Nothing was changed."
- Voice from the phone works with the tick: speech transcribed ("Tell me about my files.") and answered.
- Remove device stops answers immediately.

## Not tested / blocked
- Stage gate "deleting the remote plane changes nothing locally": not possible from the UI.
- "Unreadable to the relay": not inspected on the wire.
- Confirming a pairing writes the device key to the system keyring (required by the flow); I did not use Save key / Forget key.
- Actual email sending (no account) and real web search results.
- Reused-code result: at 5 s the Pair button was still busy (screenshot 40); I did not wait for the final message.
- Audit / What changed visibility of remote actions (known issue, not re-tested).
