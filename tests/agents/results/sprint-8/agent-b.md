# sprint-8 / agent-b / Impatient power user

Summary: Voice is wired to the same gates as typing: a spoken "tidy up this folder" produced the normal approval card and nothing on disk changed until Approve (disk listing compared). "Read answers aloud" off gave silent replies. But the "never recorded unless armed" promise has a real hole: turning "Voice is on" off while the mic is recording leaves a browser microphone track live (and the page still says "Voice is off. Nothing is recorded."). Turning voice back on then produced a duplicated spoken request. Also, with "Read answers aloud" off, hands-free listening stops for about 60 s after each turn. I cannot hear audio; I judged by the UI, `window.__afState()`, an injected getUserMedia wrapper (live track count) and `<audio>` state. The fake mic (a looping WAV) only reliably delivered the first spoken phrase per page load, so repeated spoken turns are only partly tested. Verdict: **FAIL** (one high-severity privacy bug against a Critical story).

## What I did
1. Started private app s8-b (port 7922), added a messy folder, watched the greeting, silence nudge ("Hello? Is there anything I can help you with?") and a spoken "tell me about my files" turn.
2. Toggled "Voice is on" off/on 8 times rapidly, ended off, watched 16 s: widget idle, no live tracks.
3. Typed a request with voice off (answered, no speech, mic idle).
4. Unticked "Read answers aloud" while the mic was armed; spoke a request; watched 3 minutes.
5. While listening: typed a message + Enter, filled the box and clicked Ask, switched to Folders tab and back, clicked the mic widget's Stop myself.
6. Typed while ARTEMIS was speaking; clicked + New chat mid speech; reloaded mid-turn; watched 2 minutes.
7. Spoken "tidy up this folder": card appeared, mic kept listening, checked disk, pressed Approve, checked disk.
8. Unticked Voice while recording (live track count), re-ticked.

## Backlog items checked
- User can speak a request and reach the same gates as typing: PASS. Spoken tidy gave "Would move 12 files and create 2 folders" with Approve; disk unchanged for 30 s on screen, changed only after Approve (shots 12-14).
- User is never recorded unless they armed the session: FAIL. Voice off while recording leaves 1 live mic track for 10+ s (B1). Voice off when idle: 0 live tracks, PASS. Rapid toggles ending off: 0 tracks (shot 02).
- User can hear a spoken result for a voice turn: PARTIAL. Player reaches "speaking" state with a clip for greeting and replies; I cannot hear it. "Read answers aloud" off: reply produced no clip and no speaking state (PASS) but see B2.
- Stage gate: speech required no new approval gates: PASS. Spoken request showed the same card and "Done: 2 folders created, 12 files moved." only after Approve. Not tested: pressing Approve at the exact moment of speech (script poll missed the window).

## Bugs
### B1 (high): Mic stays live after "Voice is on" is unticked mid-recording
Steps: let the mic arm (widget shows Clear/Stop, rec=true, 2 live tracks); untick "Voice is on". Expected: all tracks stopped, nothing recorded. Actual: note says "Voice is off. Nothing is recorded." but 1 MediaStream track stays live for the whole 10 s I watched (injected `window.__live()`); the visible mic buttons are hidden so the user cannot see or stop it. Re-ticking Voice then raised live tracks to 3 (leak accumulates). Reproduced 1 time with direct evidence. Likely cause from the code: only the page's own stream is stopped, not the Gradio widget's. Evidence: 16-off-while-rec.png, work/s8-b/t6.log.

### B2 (medium): With "Read answers aloud" off, listening pauses about 55-60 s after each turn
Steps: untick Read answers aloud, speak a request. Reply arrives in about 5 s, but the mic did not re-arm until 82 s (reply at 27 s). Expected: listen again right after the reply. Actual: the page waits for a spoken reply that never comes (60 s timeout). Reproduced 1 time (work/s8-b/t3.log, shots 05, 06).

### B3 (medium): Duplicate spoken request after toggling voice off then on
After B1's off/on, the same spoken "tidy up this folder" produced two identical proposal turns (t6.log final turns list). Audio captured while the session was "off" appears to be processed once voice is back on. One reproduction; cause not proven.

### B4 (low): Ask clicked right after typing says "Type a message first." and drops the text
Filled the box with "and also say hi" and clicked Ask during a running turn: a turn "Type a message first." appeared and the text was lost. May be a Gradio sync race with very fast fill (could be a script artefact); 1 reproduction (t4.log, shot 07).

## Not desired behavior
- U1 (medium): Conversation view temporarily drops the in-flight turn. After reload, at +10 s the view had 3 turns including "Working on it"; at +15 s only the 2 older turns (greeting, "Hello?"); at +20 s the reply turn returned. Earlier turns did not vanish permanently in my run, and I did not observe the 10-30 s greeting-only replacement.
- U2 (medium): The spoken reply of the previous chat keeps playing after + New chat (speaking=true with an empty conversation, shot 09).
- U3 (low): Reload mid-turn restarts the greeting and a new silence-nudge turn ("Hello? ...") before the old request is handled (t4.log).
- U4 (low): Greeting audio took 15 to 48 s to become ready (cold TTS) with only "processing | Ns"; unticking Read answers aloud 6 s in did not stop that greeting from playing.
- U5 (low): Mic keeps recording while a typed turn runs (live=2), so it may capture the answer or room noise.
- Known items seen again: greeting turn on top; each reload adds "Chat · today"; voice re-arms after refresh.

## Worked well
- Rapid toggling off/on did not crash or leave tracks when idle.
- Voice off when idle: mic widget hidden, note says "Voice is off", 0 live tracks, typed requests still work silently.
- Spoken requests become the same approval card; Approve applied it; nothing moved before.
- Read answers aloud off: replies without sound.
- Typing while ARTEMIS speaks works.

## Not tested / blocked
- Hearing audio (no speaker). Approve at the exact moment ARTEMIS is speaking (timing missed). Repeated spoken turns in one page load (the fake mic WAV did not deliver the phrase again after the first listen; likely a harness limit). Switching folders mid spoken turn. The exact "greeting-only replacement 10-30 s after a reply" (not reproduced). Refusals and audit of spoken requests.
