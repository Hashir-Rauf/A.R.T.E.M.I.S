# extras / agent-a / Curious newcomer

Summary: Plain chat works well. Replies are friendly, correct, remember the previous turn, and are labelled "gemma4:e4b · on this computer". The weak spots are first-use clarity and the saved-chats list. Chats are all named "Chat · today", Delete does nothing silently when no chat is selected, and the answer sits far below the fold. Dark mode is mostly readable, with a few low-contrast pills. Verdict: PASS WITH ISSUES.

## What I did
1. Opened a fresh app and read the first screen (01_first.png). Typed "hello", "explain what a hash chain is", "what did you just say?" and "make it shorter and give an example with a pet" in one chat.
2. Reloaded, clicked + New chat, asked "what is my name? also say the word pineapple", then "tidy up my stuff" and "what are my files?" with no folder. Submitted an empty box.
3. Switched between the saved chats, deleted chats (with and without one selected), used Clear conversation and sent a 3000-character message.
4. Toggled light/dark on Work, Folders, What it knows and Settings. Read all Settings text (nothing was saved or changed). Reloaded to check the theme.

## Backlog items checked
- Plain chat with no folder: PASS (3 turns, local model, no folder needed).
- Conversation memory within a chat: PASS ("what did you just say?" and the pet follow-up both used the prior turn; 05_follow.png).
- Streaming and progress feedback: PARTIAL. No visible streaming or "thinking" text was captured in the 2.5 s screenshots. The only indicators are the voice widget's "processing | 8.4s" and the page below the fold (03_hash_progress.png).
- New chat: PASS. The conversation empties and a new entry appears, but there is no confirmation and no greeting (07_newchat_full.png).
- Switching saved chats shows own history: PARTIAL. It worked for the hash chat (10_switched.png). The pineapple chat later showed only the greeting (known issue).
- Delete this chat: PARTIAL. It works on a selected chat (18_delete_selected.png). With none selected it does nothing and says nothing (15, 16).
- "Kept for 7 days": NOT TESTED (cannot wait 7 days). The wording is clear but not verifiable via the UI.
- Light/dark switch: PASS WITH ISSUES (U6). The theme persists across reload (14_after_reload_theme.png).
- Model names shown: PASS. Each model reply shows "gemma4:e4b · on this computer", and Settings lists the local model and the cloud model names.
- No-model/no-folder messages: PASS. The wording is clear ("That works on a folder, and there is none yet...").
- Settings readable by a layperson: PARTIAL (U7, U8, B1).

## Bugs
- B1 (medium): Settings show "Google Gemini: Key saved" in a brand-new private app (fresh ARTEMIS_HOME, never saved a key). Steps: start a fresh App, open Settings > Cloud services. Expected "Not set up". Actual "Key saved" (12_dark_Settings.png). The key status reads the real system keyring, which every ARTEMIS home shares. This is not isolated per data folder. Seen once. I did not touch the key.
- B2 (low): "Delete this chat" does nothing and gives no feedback when no chat is selected. After a reload no chat is highlighted. Steps: reload, click Delete this chat, click it again. Expected a message or a disabled button. Actual: nothing changes (15_deleted1.png, 16_deleted_all.png). Reproduced 6 times.
- B3 (low): A long message makes the chat title overflow the sidebar. The title "xxxx..." is clipped and runs past the sidebar edge (18_delete_selected.png). Seen once.

## Not desired behavior
- U1 (high): On a 1000 px tall window the reply is not visible after Ask. The chat is far below the voice panel, so a newcomer sees an empty page and must scroll (03_hash_progress.png, 05_follow.png). The empty-state placeholder "Tidy up this folder" also confuses people who have no folder.
- U2 (medium): Every saved chat is called "Chat · today". The title only appears after the first message, and the reload entries stay unnamed (09_chat2_full.png, 7 entries). You cannot tell which chat is which. Entries show no times.
- U3 (medium): After + New chat the page shows an empty conversation, with no greeting and no highlighted chat (07_newchat_full.png). It is not obvious a new chat started.
- U4 (medium): The first screen never says "just chat to me". It says "What would you like done?" and "Welcome. ARTEMIS cannot see any folder yet" only in the chat area below the fold. The "0 folders / 0 files / 0 actions" tiles mean little to a newcomer. The "In this folder" dropdown is blank and looks broken.
- U5 (low): An empty Ask shows "Type a message first." as a chat turn that stays in the history (09_chat2_full.png). Stray voice widgets appear: "No microphone fo..." is clipped, and the "processing | 2.0s" labels and a bare "Record" button clutter the page.
- U6 (low): Dark mode has low contrast on the "Key saved" pill, on the disabled Approve buttons, and on the placeholder text (12_dark_Settings.png, 11_dark_work.png). The "Switch light / dark" button has no current-state label.
- U7 (low): The Settings placeholder "for example gpt-4.1-mini" shows even when Google Gemini is selected. The jargon "API key", "Windows Credential Manager" and "server details" is unexplained.
- U8 (low): The "7157 KB stored locally" tile jumped to 118,128 KB within a few turns (voice model files in the home folder). Without an explanation it looks like chats are huge. "Move it here" and "Browse" sit beside the storage path, which is risky for a layperson (not clicked).
- U9 (low): The assistant's replies always end with a question ("Does that make sense?"), which is a model-tone issue.

## Worked well
Memory within a chat, friendly no-folder error wording, the local-model label on each reply, the Gmail setup steps are clear, and the theme persists.

## Not tested / blocked
7-day retention (time). Save key, Forget key, Connect my email, Disconnect and store location (forbidden by the brief). Real streaming (not visible in the sampled screenshots, so not judged). Remote access (another area).
