# Agent_03 report

## 1. Agent ID and persona
Agent_03, simulated participant "Bilal", 22, final-year electrical engineering student. App copy `ua-03`, port 7943. This is a simulated persona; reactions below are plausible reactions, not facts about a real person.

## 2. Background and relevant characteristics
- Privacy-conscious. Dual-boots Linux, blocks trackers, refuses to upload documents to cloud AI, has read that companies train on user data.
- Tried local models once and found them slow.
- Skeptical of marketing ("show me where the data goes"). Would adopt a tool only if the privacy claims are verifiable from what he can see.
- Current workflow: manual folder tidying, grep/find and a file manager, notes in plain text/Markdown, no AI assistant on personal files.

## 3. Initial expectations (before using it)
- The description sounds like marketing for "trust me, it's local". "It cannot see anything else" is a claim, not proof. How would I check it? Is it a real sandbox or just a setting the app honours?
- "Runs on your own computer by default" - "by default" worries me. What is the non-default, and how easily can it be flipped, by me or by the software?
- "Sends anything out of your computer" implies some features (web search, email) do send things. I want to see exactly what leaves.
- Approval prompts are good only if the prompt is honest and complete. A summary like "organise files" is useless; I want every step.
- Doubt: a small local model will be slow and a bit dumb. I would accept that for privacy, but not if it is useless.

## 4. Interaction and exploration summary
Order of events (full timestamped log in `tests/agents/work/ua-03/actions.log`):
1. Started the app. Read the home screen first: header banner "Everything is stored on this computer. Nothing has been sent anywhere", counters (0 folders, 0 files, 0 actions, KB stored). A first scripted attempt at clicking tabs timed out because the tab buttons exist twice on the page (a duplicate tab bar); I switched to the tab role selector.
2. Read Settings before doing anything else (the privacy-minded thing to do). Found the model section (local `gemma4:e4b`, 9.6 GB), a "Cloud services" section with Google Gemini listed as "Key saved" on a fresh install, email setup, and a collapsed "Remote access (optional)" section.
3. Read "What it knows" (empty, with Show files / Forget this folder / Forget this file / Erase everything buttons).
4. Folders tab: first attempt to add a folder failed ("Type or browse to a folder first") because I typed into the wrong field; then added a folder of invented messy files (25 files). The folder row said "Cloud models are off here: everything stays on this computer."
5. Work tab: asked "Where does my data go when you answer this?", asked what files are in the folder, asked "Tidy up this folder", used the "Suggest a tidy-up", "What changed", "Undo last change" buttons, asked for a web search and for an email.
6. Second session with a small notes folder (5 files): asked it to quote my notes, tidied, approved, checked the disk, undid, checked the disk again, toggled "Allow cloud models here" and back, clicked "Erase everything" (stopped at its confirmation question), opened the Remote access section.
7. Did not click Save key, Forget key, Connect my email or Disconnect.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Read home screen text | Banner and counters say everything is local and nothing sent. 20-27 MB "stored locally" at start, growing to ~100+ MB as I used it | interest, but a claim I cannot check from here |
| 2 | Opened Settings | Local model gemma4:e4b; Gemini shows "Key saved" without my doing anything; OpenAI, Anthropic "Not set up" | hesitation: why is a cloud key already saved on a clean copy? |
| 3 | Opened What it knows (empty) | Buttons to forget folder/file or erase everything; says forget never deletes my files and the activity log is kept | interest |
| 4 | Typed folder path in the wrong box, clicked Add | "Type or browse to a folder first." | repeated: retyped in the correct box |
| 5 | Added invented messy folder | "25 files"; "ARTEMIS can read and change files here, with your approval"; "Cloud models are off here" | interest |
| 6 | Read What it knows with folder added | Lists each file with its size in bytes | interest: this is the "show me what you hold" view I wanted, but it is file names and sizes only |
| 7 | Asked "Where does my data go when you answer this? Show me exactly which things leave my computer." | Answer: nothing leaves just by chatting, responses generated locally; only email or web search if I approve. Label "gemma4:e4b - on this computer" under the answer | mixed: the label is useful; the answer is the model talking, not a log, so I do not trust it as evidence |
| 8 | Asked what files are in the folder and which is most private | Listed files (reported "27 things" while the folder panel said 25, because my own screenshots were also saved in the folder); did not answer the "most private" part | hesitation (minor) |
| 9 | Asked "Tidy up this folder" | A plan card: "Approve these changes?", "Nothing has happened yet", risk "changes files, and can be undone", "Nothing is deleted", "Nothing leaves this computer", then every step numbered (create Documents, Images, move each file by name). Left budget 2026.xlsx and random.zip in place | strong interest: this is the first thing that looked checkable |
| 10 | Pressed Suggest a tidy-up, What changed, Undo last change (before approving anything) | Same plan; "Nothing has changed outside ARTEMIS since a moment ago"; "There is nothing to undo." | interest: honest empty states |
| 11 | Asked web search about AI companies training on user data | Plan card, risk reads "sends something off this computer", step shows the exact search string. I did not approve | interest: this is the right label for it |
| 12 | Asked it to send an email to my professor | Asked for an email address first. Email not connected, so I stopped there | not pursued |
| 13 | Second session: asked "What do my notes say I need to do next? Quote the file" in a 5-file folder | "I don't have access to your personal files right now..." and told me to point it at a folder, although I had just added one | annoyed, abandoned that question |
| 14 | Tidy up on the 5-file folder, pressed Approve | Disk before: 5 lecture files. After: only a folder "Documents". UI: "Done: 1 folder created, 5 files moved." and "You can undo it." | interest |
| 15 | Pressed Undo last change | "Undone. 6 steps reversed, and your files are back as they were." I compared the disk listing: identical to before | strong interest: the one claim I could verify myself, and it held |
| 16 | Folders: pressed "Allow cloud models here", then "Keep it on this computer" | Row text changed to "Cloud models are allowed here: what you type may leave this computer", then back to "off here: everything stays on this computer" | interest: per-folder switch, plain wording. I did not send anything to a cloud model |
| 17 | What it knows: pressed "Erase everything ARTEMIS knows" | A confirmation appeared ("Forget all 1 folder? None of your files are touched. The activity log is kept.") with Yes / Cancel. I did not confirm. 5 files still on disk | interest; stopped at the confirmation |
| 18 | Opened Settings > Remote access (optional) | "Off until you press Start", messages scrambled on the phone and unscrambled here, relay cannot read them; folder permissions for a paired device; "audio turned into words here and never kept" | hesitation: a relay server is a new thing that is in the picture |

Questions I asked it: where data goes; what is in the folder and what is most private; tidy up; web search; send an email; what do my notes say.
Features explored: Folders, What it knows, Settings (incl. cloud services, email section as text only, remote access), plan/approve, undo, what changed, per-folder cloud switch, erase (to the confirmation).
Skipped: voice (no microphone in this environment; I unticked it), cloud models actually answering, email connect, saving keys, "Repeated tasks", "Leave a note for next time", paired phone, the "Approve, don't ask again" button, searching the web for real (not approved), the activity log itself (I looked for it but only saw a counter, "actions recorded", not a visible list).
Decisions: not to approve the web search, never touched key or email buttons, stopped at the erase confirmation.

## 6. Feedback about the research idea (as Bilal)
The idea is aimed at something I actually care about, but I do not trust the pitch until I can verify it. What I liked is that the app puts the checkable stuff on the screen: a list of exactly which folders it sees, a per-folder switch for cloud use with a sentence that changes, a plan showing every file move, and an undo that really put my files back (I diffed the folder). That is more than most "AI helpers" give me.

What I do not buy yet: the main privacy claim is made by words on the screen. The header says "Nothing has been sent anywhere" and the model answers "nothing leaves your computer", but I cannot see a network log or a list of what was sent. The line "Nothing leaves this computer" on the plan card is also just text. If the local model is what writes the reassurance, it is not evidence. I want to see it from outside: run it with Wireshark or an offline firewall rule, and read the source. Closed software saying "trust us it is local" is the thing I already refuse.

"Bounded to folders you pick" is a good design principle, and I think it does make me trust it more than an assistant with full disk access, because that is just a bigger attack surface. But "the app only looks at what you add" is enforced by the app itself, not by the OS. A real boundary for me would be an OS-level sandbox or permission, not a promise.

## 7. Perceived problem relevance
Rating: 3 of 5. Messy download and notes folders and losing my place between tasks are real, but not severe; I solve them with a file manager and grep. The bigger real problem for me is "AI tools want my documents in the cloud", which this directly addresses, so the problem is relevant mostly as a privacy issue and less as a productivity one.

## 8. Perceived value of the proposed solution
Rating: 3 of 5 as seen. Valuable: the plan-before-action screen, undo that worked, never deleting, per-folder cloud switch, "what it knows" with per-file forget and erase. Not valuable for me: tidy-up (I do not mind my own mess), email drafting, and voice. The value would be much higher if the "answer questions about my notes" feature worked reliably offline, because that is what I would actually use. In my test it did not (it said it had no access to my files).

## 9. Adoption likelihood and reasoning
**Might try.** I would install it in a VM or on a throwaway account first and watch its network traffic. I would use it for real only if: (1) the source is open or I can audit its outbound connections, (2) there is a plain, readable activity log of everything it did and everything that left the computer, (3) cloud keys are never pre-saved, and cloud off is the shipped default in an unmistakable way, (4) it runs on Linux, and (5) the local model is fast enough on my laptop. What would change my mind to "avoid": finding any traffic I did not approve, or a cloud key I did not enter.

## 10. Concerns, objections and suggestions
- Gemini showed "Key saved" on a clean copy. Even if the cloud is off per folder, I do not want a stored key I never entered. Explain it or remove it.
- Privacy statements are static text. Show a live list of outbound requests (destination, size, what was sent) so I can verify the banner.
- A model-generated answer to "where does my data go" is not trustworthy. Answer that question from the app's real settings/logs, not from the model.
- "What it knows" shows names and sizes only. I want to see what is stored about content (summaries, embeddings, text snippets) and where it is on disk.
- The activity log is kept even after "erase everything". Fine for audit, but I want to see it and to know whether it contains file content.
- Per-folder boundary is enforced by the app. Say how, and ideally use OS-level sandboxing.
- The remote-access relay (a phone page via a relay server) is a new trust element for a privacy-focused tool. Keep it clearly off and separate.
- Windows-centric wording (Credential Manager, Windows paths). I would need Linux.
- Local-model speed: replies took roughly 10-20 seconds in my tests; tolerable for chat, but I had been told local models are slow and this reinforced it.

## 11. Final assessment of the central claim
(a) Would it make me trust an assistant more than one with full access? **Partly.** A bounded design is structurally safer, but I only trust it as much as I can verify the boundary. Today I can verify the undo and the per-step plan, not the "nothing leaves" claim.
(b) Would that make me more willing to use it? **Partly.** Yes, I would try it instead of a full-access one; no, not as a daily tool until the verification is there.
(c) Does the limitation cost too much usefulness? **Cannot say.** The folders I chose were enough for tidy-up; the one thing I wanted (asking my notes) did not work in my session, so I could not judge what the limit costs.

Short questions:
- Are people really losing time to interruptions and routine file work? **Partly.** I lose some; not much to file tidying.
- Is wanting an assistant with broad access a real barrier for me? **Agree.** Broad access is the reason I use none.
- Would I accept one mistake if undo is easy? **Agree**, for file moves, since I saw undo restore the exact folder. **Disagree** for anything that leaves the computer; an undo cannot un-send data.
- Ask before every change, or act and let me undo? **Ask first** for anything involving files or sending; I would allow "act then undo" only for plain moves within a folder.
- Which abilities would I use? Answering questions about my notes and files (if it works), code suggestions, and perhaps tidy-up. I would not use email, voice, or the phone remote.
- What would make setup too much effort? Needing a cloud account or key, a big model download with no progress, Windows-only, or a long setup before the first useful answer. Adding a folder was easy once I used the right box.

## 12. Implementation limitations I ran into (separate from the idea)
- Duplicate tab bar in the DOM (two sets of Work / Folders / What it knows / Settings), which made automated clicking time out; a person would not notice.
- The Folders path field: typing in the wrong box produced "Type or browse to a folder first." with a placeholder that looks like a Windows path.
- "Which looks most private" was ignored; folder count said "27 things" while the panel said 25 files (my own screenshots landed in the folder).
- Asking about my notes in a freshly added 5-file folder returned "I don't have access to your personal files", though the folder was added.
- "Gemini Key saved" present on a clean install.
- No visible activity log listing; only an "actions recorded" counter.
- Voice autostarted and said "No microphone found" (no mic here); I could not test voice.
- I could not test real web search or email (I did not approve or connect them); I did not run any cloud model.
- The first scripted attempt left an earlier failed session recorded in my action log; the log is therefore longer than the final session (the runs are marked in it).
