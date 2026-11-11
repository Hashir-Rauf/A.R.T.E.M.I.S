# sprint-8 / agent-a / Curious newcomer

Summary: Voice behaves as promised on the main paths. A spoken "put a.pdf in the docs folder" produced the same approval card as typing, and nothing moved until Approve (disk checked before and after). Unticking "Voice is on" normally hides the microphone ("Voice is off. Nothing is recorded."), and "Read answers aloud" off silences voice turns. One real gap: if Voice is unticked in the first second or so after the page opens, the microphone recorder stays on screen, and a manual Record still records and transcribes (the "never recorded unless armed" story). Several awkward greeting behaviours too. I cannot hear audio; sound was judged only by the player/clip state (`window.__afState()`) and the UI. **Verdict: PASS WITH ISSUES.**

## What I did
1. Opened the app with a fake microphone (looping WAV). Watched the load: greeting "Good afternoon! I'm ARTEMIS. I'm listening.", then a second greeting "Hi again. Let's pick up where we left off." about 2-4 s later, then listening, then "Hello? Is there anything I can help you with?" after about 4 s of silence.
2. Said "tell me about my files" with no folder added: ARTEMIS asked which folder (reasonable). "Heard: Tell me about my files." note appeared.
3. Unticked Voice quickly, added a folder (mystuff with a.pdf and a docs subfolder) on the Folders tab, re-ticked Voice.
4. Spoke "put a.pdf in the docs folder": heard as "Put A, PDF in the Docs folder."; card "Approve these changes?" (Make folder "Docs", Move a.pdf into "Docs"). Disk before Approve: a.pdf still at root, no change (checked twice, including 20 s later). After Approve: "Done: 1 folder created, 1 file moved", a.pdf in docs/.
5. Silent microphone, new chat: timing of greeting and nudge; untick/re-tick Voice; untick Read answers aloud and spoke/typed.
6. Unticked Voice about 1.2 s after opening and clicked the visible Record button manually.
7. Long run (115 s) after a voice reply watching for the conversation being replaced by only the greeting.

Used: Playwright UI only, disk checks of the sample folder, the page state `window.__afState()`.

## Backlog items checked
- User can speak a request and reach the same gates as typing: PASS. Same Approve card, nothing changed before Approve (approval_card_full.png, after_approve.png; disk checked).
- User is never recorded unless they armed the session: PARTIAL. Normal untick hides the mic (voice_off_widget.png; nothing transcribed over 20 s idle). But unticking during the opening second leaves the recorder usable and a manual recording is transcribed (B1).
- User can hear a spoken result for a voice turn: PARTIAL. Player state showed "speaking" true after voice replies and greetings, and no clip with Read answers aloud off. I cannot hear audio, so I cannot confirm content or that the model name is not spoken. The model name appears only as a faint caption under replies, not in the reply text.
- Stage gate, no new approval gates for speech: PASS. Voice request produced the existing card and buttons only; no extra prompt.

## Bugs
### B1. Recorder stays usable (and transcribes) when Voice is unticked early after page load
Severity: high (violates "never recorded unless armed" in a narrow case).
Steps: open page; about 1.2 s later untick "Voice is on" (greeting still in flight); wait. Click the visible Record button in the Microphone widget, wait 6 s, click Stop.
Expected: with Voice off the mic widget is hidden ("Voice is off. Nothing is recorded.") and cannot record.
Actual: widget shows Clear/Record, `__afState` shows `on:false, record:true`; manual recording was transcribed ("Heard: Tell me about my files.") and answered. Reproduced 3 times (t3, t5, t10). Untick after about 3 s or later (or after New chat + reload) hides it correctly (2 runs).
Evidence: manual_record_while_voice_off.png, manual_record_result.png, voice_off_early_untick.png (this one is the correct, hidden case for comparison).

### B2. Second greeting "Hi again. Let's pick up where we left off. What's next?" appears in a brand-new chat
Severity: low-medium. In a fresh chat after "+ New chat" and reload, two greetings appear within 4 s; the second claims there is something to resume. Every re-tick of Voice adds another "Hi again" turn. Reproduced about 6 times. Evidence: silence_50s.png, load_*.png. (Related to the known greeting-turn clutter, but the "pick up where we left off" wording in an empty chat is new.)

## Not desired behavior
- U1 (medium). A voice request right after refresh gets "tell me which folder" because the folder dropdown is still empty; it fills in a moment later. A newcomer would be confused.
- U2 (low). Reply tone is very casual ("You gotta tell me which folder ... for ya") and does not say how to pick one.
- U3 (medium). The approval card and Approve buttons sit far below the voice widgets (scrolling needed); a hands-free person may not notice a card is waiting (approval_card_full.png).
- U4 (medium). Voice keeps listening while an approval is pending; more spoken requests kept being heard while the first card was open.
- U5 (low). After the first reply, the looping "tell me about my files" was not heard again in 100 s. May be a harness artefact.
- U6 (low). After one "Hello?" nudge, nothing further and no indication whether listening is still on.
- U7 (low, known). Identical "Chat · today" entries pile up (6 after a few refreshes).
- U8 (low). Plan says Make a folder "Docs" though a docs folder already existed (case-insensitive); the disk ended with a single docs folder holding a.pdf, so no harm.

## Worked well
- "Heard:" note; same approval card and wording for voice and typing; nothing changes before Approve.
- Normal untick of Voice stops recording and hides the mic with a clear message.
- Read answers aloud off: no clip/speaking in a voice turn or greeting.
- Silence handling: nudge about 4 s after listening begins.
- Conversation replaced by only the greeting: NOT reproduced in a 115 s voice run or a typed run.

## Not tested / blocked
- Actual sound, and whether the model name is spoken (no speaker).
- The conversation-replaced-by-greeting issue 10-30 s after a reply: watched twice, did not occur.
- Spoken approvals ("yes"), "No, leave it" by voice, a real microphone, Settings/email/web search by voice.
