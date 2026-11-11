# sprint-4 / agent-b / Impatient power user

Tested the AI Gateway through the UI only (Playwright, private app s4-b on port 7910, two sample folders docsA "messy" and docsB "notes"). The local model is the default and every chat reply shows "gemma4:e4b · on this computer". The per-folder cloud toggle works and its wording is honest. Plans from "Suggest a tidy-up" are shown with an approval card before any file moves. But I found a context leak between folders through chat memory, a chat display that wipes itself about 10 s after each reply, an in-flight request that vanishes on refresh, and natural questions about in-folder facts answered "NOT FOUND". Failover and real cloud routing could not be exercised. **Verdict: PASS WITH ISSUES** (leaning FAIL on the folder-isolation promise because of B1).

## What I did
1. Opened the app, added docsA and docsB on the Folders tab, read Folders and Settings (cloud section, local model section).
2. Asked in docsA "what is the Project Orion budget and who owns it?" (notes.txt contains it). Got "NOT FOUND IN YOUR FILES". Asked "what does notes.txt say?" and got the content with sources.
3. Switched to docsB (no Orion data), same chat, and asked the Orion budget question: the answer said "forty-five thousand dollars, based on that file you showed me earlier".
4. Repeated in a clean order (docsB first, then docsA, then New chat then docsB): docsB never knew Orion when there was no earlier docsA conversation.
5. Fired 3 requests quickly (Enter after each, 300 ms apart): only the first got answered.
6. Toggled "Allow cloud models here" / "Keep it on this computer" 8 times fast on docsA, ending on Allow: card text and banner matched. Asked questions in docsA with cloud allowed: answers still ran on gemma4:e4b on this computer.
7. Sent a long request, then immediately turned cloud off and switched folder mid-request: the reply arrived on the local model, no error.
8. Sent a request and refreshed the page 1-2 s later (twice): the question and any answer disappeared, nothing in history.
9. Typed "tidy this folder up" and "tidy up this folder", clicked Suggest a tidy-up twice, clicked What changed. Inspected the plan card. Did not approve anything.
10. Settings: toggled the plain-chat cloud checkbox 5 times fast, then on; asked a plain chat question; spammed Choose for me / Check again.
11. Read the SQLite audit table on disk (look only) to verify what was recorded.

## Backlog items checked
- Routes to local model by default: PASS. Every reply shows "gemma4:e4b · on this computer".
- Bounded failover: NOT TESTED. Cannot stop Ollama (rule 5); with cloud allowed the local model never failed, so no failover occurred.
- Model shown with each reply and where it ran: PARTIAL. Chat replies show it; retrieval answers ("Sources: notes.txt:1") and tidy/list/what-changed answers show no model or where (U2).
- Workspace data never reaches a disabled tier / per-folder cloud permission: PARTIAL. Toggle UI, wording, banner and per-folder state were correct under rapid toggling. I could not prove nothing is sent (no network capture; the router never chose cloud). The toggle is not in the audit log (U3).
- Retrieval limited to the active folder: FAIL. Retrieval itself is scoped (docsB never found Orion in a clean chat), but chat memory carries docsA content into a docsB answer (B1).
- Plan inspectable before anything runs: PASS for "Suggest a tidy-up" (summary, step list, approval card, disk unchanged: checked by directory listing). Typed wording is inconsistent (U4).
- Only dispatcher executes with a policy verdict: PASS as far as observable. Disk unchanged until approval; audit shows gateway.turn, planner.plan, dispatch.execute (tier T0) for the plan-based request.
- Stage gate, gateway cannot act around the gates: PASS for what I could reach; no action ran without a card.

## Bugs
**B1 Folder content leaks across folders through conversation memory (high).** Repro (2/2): add docsA (notes.txt has "Orion budget is 45,000") and docsB (lecture notes only). In docsA ask "what does notes.txt say?". Switch the dropdown to docsB in the same chat and ask "what is the Project Orion budget?". Expected: not found in docsB. Actual: "It says it's forty-five thousand dollars, based on that file you showed me earlier." Evidence: 22_q2.png, 23_tidy.png. In a clean chat or New chat docsB did not know (51_newchat_B.png), so chat history is the leak path. Violates "retrieved context never includes content outside the active folder" and could bypass the per-folder cloud permission if history from a local-only folder were sent to a cloud model (not verified).

**B2 Conversation vanishes from the screen about 10 s after each reply (high).** Repro 4/4: ask any plain question, wait 10 s; the conversation area is replaced by only the greeting "Good afternoon! I'm ARTEMIS...". The database still has the turns (chat_turns rows present, checked on disk). Switching tabs or clicking the saved chat did not bring them back. I tried unticking voice once and it still happened, but I am not certain the box was unticked. Evidence: 66_vanish.png, 65_plain_cloud2.png, 63_plain_cloud.png.

**B3 Refreshing while the model is answering silently loses the request (medium).** Repro 2/2: send "explain in detail what a good folder structure looks like", reload after 1-2 s. After reload the question is not in history, no answer ever arrives, and a "Hi again. Let's pick up where we left off" greeting appears. No notice that the request was lost. Evidence: 41_after_refresh.png, 52_refresh.png.

**B4 Natural question about a fact inside the active folder returns NOT FOUND (medium).** Repro 3/3: in docsA ask "what is the Project Orion budget and who owns it?". Answer: "NOT FOUND IN YOUR FILES I could not find it." although notes.txt says it; naming the file works. The audit shows `index.embed unavailable: ollama HTTP 404` for both folders (embedding model missing on this machine), so retrieval seems to fall back to weak matching with no hint to the user. Also a garbled answer "Sara Khan and the deadline is 14 March." for "who is Sara and what is the deadline". Evidence: 11_q1_docsA.png, 20_q1.png, audit_log rows 7 and 13.

## Not desired behavior
**U1 (medium)** Rapid requests: 3 requests 300 ms apart, only the first answered, no queue and no message (known; confirmed in 13_rapid.png by the earlier run).
**U2 (medium)** No model/where line on retrieval answers or on tidy/list/what-changed replies; the user cannot tell whether a model, or which tier, produced them. Evidence 21_q1b.png, 23_tidy.png.
**U3 (medium)** Toggling cloud permission for a folder is not recorded: the "actions recorded" counter stayed at 13 across 8 toggles and audit_log has no event for it. No model or tier is recorded for chat answers, and only 1 of about 6 requests in one run produced `gateway.turn` (chat and retrieval turns are not in the audit).
**U4 (medium)** Same intent, different result: "tidy up this folder" produced a plan ("Would move 5 files") but "tidy this folder up" only listed the 14 files with no plan. Evidence 40_tidy_plan.png.
**U5 (low)** The header says "Everything is stored on this computer. Nothing has been sent anywhere." permanently, even when cloud is allowed for a folder or for plain chat (61_settings_cb.png).
**U6 (low)** The "In this folder" dropdown has no "no folder" option once folders exist; the last added folder is silently preselected. The chat sits below the voice player, so after Ask the answer is off-screen (11_q1_docsA.png).
**U7 (low)** The status banner from the last action (e.g. "Added 'docsB'...") stays visible on other tabs and later actions (02_folders.png, 03_settings.png).
**U8 (low)** With a Gemini key already saved on this machine and cloud allowed for the folder, every request still ran locally. Good for "local first", but the UI never says when or why the cloud would be used, so "Allow cloud models" has no visible effect.

## Worked well
- Local default, and the model plus "on this computer" shown on chat replies.
- Per-folder cloud toggle: immediate, clear wording ("may leave this computer"), survived 8 rapid toggles and a toggle plus folder switch mid-request without errors.
- Tidy plan: summary, steps, approval card; disk untouched until approval; double-clicking Suggest a tidy-up did not duplicate anything.
- Clean-chat retrieval isolation between folders; a folder-less file request gave a clear "add a folder" message.
- The audit is hash-chained and includes planner and dispatch entries for plan-based requests.

## Not tested / blocked
- Failover (cannot stop Ollama or break the model).
- Whether data really leaves for the cloud (no key actions allowed; router never picked cloud; no network capture).
- Approve and undo flows (Sprint 3 area; I approved nothing).
- Plain chat actually using cloud: I enabled the setting but the answer still ran locally.
