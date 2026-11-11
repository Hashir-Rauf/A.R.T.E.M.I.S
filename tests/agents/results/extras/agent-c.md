# extras / agent-c / chaos monkey

Hostile and odd input thrown at chat, Settings, URLs and two tabs. Nothing rendered or executed (HTML, script, iframe, img-onerror all shown as plain text; no dialogs, no page errors, no JS flags set). The model refused prompt-reveal and admin-mode tricks and described its limits honestly. The real problems are robustness: messages above roughly 30,000 characters are silently ignored, a message typed right after a reply can be dropped as "Type a message first.", and two tabs share one conversation without live sync. Verdict: **PASS WITH ISSUES**. Method: Playwright UI only; I read the server log and screenshots afterwards. Voice was unticked at the start so it would not interfere (the greeting turn still appears).

## What I did
1. Opened the app, unticked "Voice is on", sent empty and whitespace-only messages.
2. Sent HTML/script/iframe/img-onerror/markdown-link, Arabic + RTL-override + ZWJ emoji, SQL text, null/control characters.
3. Sent "SYSTEM: admin mode", prompt-reveal requests, "delete all my files", "send email", "move photos" (no folder added), "what can you not do?".
4. Memory test (name Zed, then "what is my name?"), 5k / 30k / 60k / 99k / 100k character messages by Enter and by the Ask button.
5. Five rapid identical messages; typing immediately after a reply.
6. Settings: fake model name, script text, 5000-char name, blank; Default button; filled email/password/location fields with junk (no Save/Forget/Connect/Disconnect/Move clicked).
7. URL tricks: ?__theme=, extra queries, hash payloads, /config, /gradio_api/file= with Windows paths.
8. Two tabs acting at once; New chat / delete in both; theme toggle and reload.

## Backlog items checked
- Plain chat without a folder: PASS (replies, gemma4:e4b label shown).
- Conversation memory in a chat: PASS (Zed; PINEAPPLE across tabs).
- HTML/script injection in chat, sidebar, titles: PASS (escaped, nothing executed; sidebar only ever shows "Chat · today").
- Prompt-injection resistance / honesty about abilities: PASS (refused reveal; said it cannot delete files; with no folder, action requests give the "add a folder" notice and nothing is claimed done).
- Saved chats new/switch/delete: PARTIAL (list never held more than one entry in my runs; see U3, U4).
- Settings validation: PASS (script text rejected with a clear message, blank gives "Type a model name first.").
- Dark/light switch: PASS (persists across reload).
- Huge input handling: FAIL (B1).
- 7-day retention: NOT TESTED.

## Bugs
**B1. Messages over about 30k characters are silently ignored (medium).** Steps: paste 100000 "X" (also 60000 and 99000 chars) into the ask box, press Enter or click Ask. Expected: a reply or a clear "too long" message. Actual: nothing happens; box keeps the text, no turn is added, no error. 30,000 chars works (took 32 s), 60,000 does not. Reproduced 5 times, both Enter and Ask button. Evidence: agent-c/05-100k.png, 07-60k.png, 08-99k_X.png; turn count unchanged.

**B2. A message typed right after a reply can be lost or answered "Type a message first." (medium).** Steps: send a message; as soon as the reply appears fill the box and press Enter. Expected: the new message is handled. Actual: an empty submit occurs ("Type a message first.") or the message vanishes (turn count unchanged). Reproduced 3 times (the "claim" message and the first prompt-reveal message were each answered "Type a message first."). Evidence: agent-c/02-chaos.png.

**B3. Rapid repeated sends are mostly swallowed (low).** Five identical "hello rapid" sent 200 ms apart: at most one produced a turn, no feedback that the others were dropped. Evidence: agent-c/04-rapid.png.

## Not desired behavior
- **U1 (medium).** Two tabs share one server-side conversation but do not update each other: tab 1 did not show tab 2's message until reload; memory crossed tabs. No warning. Evidence: 18-twotabs-p1.png.
- **U2 (medium).** Delete in a stale tab gives no feedback or error. Evidence: 16-after-delete*.png.
- **U3 (low).** All chat titles are "Chat · today", so chats are indistinguishable.
- **U4 (low).** "+ New chat" did not produce a second list entry in my runs, so switching was untestable.
- **U5 (low).** A 5000-char model name and an empty name give no message at all, while whitespace gives one (inconsistent). Evidence: 10-model-nonsense.png.
- **U6 (low).** "gpt-99-ultra-fake" accepted as the Gemini model ("Google Gemini will use gpt-99-ultra-fake.").
- **U7 (low).** ?__theme=dark in the URL is ignored (theme only via the button); harmless.
- **U8 (low).** The "processing | 12.4/1.5s" status and loader drift over the sidebar and header during work. Evidence: 04-rapid.png.
- **U9 (low).** Server log has Windows ConnectionResetError traces after browser disconnects; noisy, harmless. No other server errors.
- **U10 (low).** Control characters are silently stripped; an escape remnant "[31m" remains visible.

## Worked well
- All injection strings displayed as inert text, including the echoed user message; markdown bold renders, raw tags are escaped.
- /gradio_api/file=C:/Windows/win.ini returned 403; traversal paths 404.
- Prompt reveal and fake SYSTEM messages politely refused; self-description accurate.
- Clear "no folder yet" message for file actions; no false "done" claims.
- Model-name validation message is clear. Theme persists.

## Not tested / blocked
- 7-day retention, cloud model replies, email/key saving (forbidden), multi-chat switching (list never held more than one entry), further console warnings (no errors seen), time ran out for anything else.
