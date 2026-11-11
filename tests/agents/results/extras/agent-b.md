# extras / agent-b / Impatient power user

Summary: Fast stress of everyday chat use on a private app (sx-b, port 7928). Core chat works: Enter and Ask both send, replies stream, 5 rapid sends were all answered, chats save to SQLite, survive an app restart and a reload, delete works, dark mode persists across reloads, no horizontal overflow at 375, 700 or 1920 px. Main problems: deleting a chat while it answers resurrects it, switching chats mid-stream saves the reply into the wrong chat, a reload mid-answer loses the request and leaves junk chats, the voice greeting is saved as a turn on every reload/re-tick, and context is silently capped at 40 turns. Verdict: PASS WITH ISSUES.
Evidence sources: UI via Playwright; I READ the SQLite file (home/artemis.db) and the server log afterwards to verify. The 7-day retention purge was NOT exercised.

## What I did
1. Opened the app, unticked Voice, sent messages with Enter and with Ask; 5 messages in a row, all answered in order.
2. Typed a second and third message while one was streaming (known behavior: dropped; the text stayed in the box).
3. Pressed Enter twice, clicked + New chat 4 times, reloaded repeatedly, restarted the app without wiping data.
4. Switched chats while a reply was streaming, sent in one chat and switched away at once, deleted a chat while it was answering.
5. Left voice on with a fake mic, toggled voice off/on, reloaded mid-stream.
6. Toggled light/dark 5 times and reloaded; resized to 375, 700, 1920 px; Tab/Escape/Shift+Enter/empty Enter; pasted 11,200 characters.
7. 50 turns in one chat, then asked for a fact from turn 1, before and after reopening the chat.
8. Collected console errors and server log.

## Backlog items checked
- Plain chat without a folder: PASS
- Conversation memory in a chat: PARTIAL, only last 40 turns kept (U4)
- Saved chats new / switch: PARTIAL (B2, U1)
- Saved chat delete: PARTIAL (B1)
- Chats survive app restart: PASS (sidebar and DB; reopened old chat answered with correct context)
- 7-day retention: NOT TESTED (label "kept for 7 days" present; purge code only read)
- Streaming replies: PASS
- Dark/light: PASS (persisted across reload; 5 toggles consistent)
- Model names shown: PASS ("gemma4:e4b · on this computer" under each reply)
- Error / empty messages: PASS ("Type a message first." for empty or spaces)
- Responsive layout: PASS with U6
- Keyboard navigation: PARTIAL (U5)
- Long paste: PASS (11,200 chars accepted and answered)
- Settings page generally: NOT TESTED

## Bugs
### B1 (medium) Deleting a chat while it is answering brings it back
Steps: send "Write a 20 line poem about rivers", after ~1 s click Delete this chat. Expected: chat gone, answer discarded. Actual: the poem kept appearing; ~25 s later a chat "Write a 20 line poem about rivers · today" appeared and DB row id 6 holds the turn. Reproduced 1 time. Evidence: 08-delete-while-answering.png, DB dump.
### B2 (medium) Switching chats mid-stream saves the reply into the wrong chat
Steps: send a long poem request, click a different saved chat while it streams. Actual: the other chat (Say BETA) showed the poem turn on top of its own history; DB confirms the turn was saved into session 3 (BETA). Same with "Say DELTA" asked in BETA then switching away at once: saved into GAMMA's session 5. Reproduced 3 times. Evidence: 06-switch-while-streaming.png, 07-switched-mid-stream.png, DB rows.
### B3 (medium) Reload mid-answer loses the request and leaves two junk chats
Steps: ask for a poem, reload after 1.5 s. Actual: request is in no chat (DB has no turn), two new "Chat" entries. Extends the known issue. Evidence: 11-reload-midstream.png.
### B4 (low) Greeting saved as a real turn on every reload and voice re-tick, stacking
Each reload with voice on adds "Hi again. Let's pick up where we left off..." as a saved turn (two stacked after one reload); unticking then re-ticking Voice adds another. DB has chat_turns rows with said=NULL. Evidence: 10-retick-voice.png.
### B5 (low) Empty "Chat" entries pile up on every reload
After a short session the sidebar held 10 identical "Chat · today" rows (16-phone.png). Four fast + New chat clicks gave only one entry (good); reloads do not.

## Not desired behavior
- U1 (medium): Identical titles "Chat · today" with no time or preview make switching impossible.
- U2 (low): Typing while a reply runs is silently ignored; text stays in the box (known).
- U3 (low): Console noise: "AbortError: BodyStreamBuffer was aborted" and "Unexpected error Connection errored out" on reload mid-stream; "play() failed because the user didn't interact"; "Error accessing the microphone: Not supported" x5. Server log: ConnectionResetError [WinError 10054] traceback after disconnects.
- U4 (medium): Memory silently capped at 40 turns (code keeps `transcript[-40:]`). After 50 turns, asking for the code word from turn 1 gave "You haven't actually given me a secret codeword", twice (also after reopening the chat). No notice to the user.
- U5 (medium): Keyboard: first Tab stops are audio-player widgets (Clear, Record, Download, Share, volume, speed, skip, pause) before the ask box; Escape does nothing; Shift+Enter inserts a newline in a single-line-looking box.
- U6 (low): At 375 px the sidebar and a long chat list sit above the work area, pushing the ask box far down.
- U7 (low): "stored locally" grows from 58 MB to 118 MB after first voice use (116 MB voice models in home/voice counted); looks like chats are huge.
- U8 (low): A very long pasted input is accepted silently, no counter or limit message.

## Worked well
- Enter and Ask both send; 5 rapid messages answered in order; progress shown while streaming.
- Chats persist across app restart; reopened chat answered with correct context.
- Dark theme persists after reload; no horizontal overflow at 375/700/1920 px.
- Empty and space-only send gives "Type a message first." with no stray turn.

## Not tested / blocked
- 7-day retention (not run).
- Settings page contents, real clipboard copy/paste, a delete-all-chats control (none found beyond "Delete this chat"), full Tab order beyond the first 14 stops.
