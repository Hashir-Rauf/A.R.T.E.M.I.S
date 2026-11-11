# Agent_14 report

## 1. Agent ID and persona
Agent_14, simulated persona "Hira", 23, postgraduate student. App `ua-14`, port 7954. (Simulated persona; reactions below are plausible reactions, not facts about real people.)

## 2. Background and relevant characteristics
Already very organised: strict folder structure, naming convention (date-prefixed file names), weekly review, Notion for tasks, a daily journal of where she stopped. She does not feel she has a context-recovery or messy-files problem. Has tried ChatGPT a few times and finds it fine. Moderate technical skill. Will not pretend a need she does not feel.

## 3. Initial expectations (before using it)
- (Expressed) "It sounds like a tool for people whose desktop is a mess. Mine is not. I already know where I stopped because I write it down every evening."
- Doubt: "remind me where I left off" duplicates my journal. "Tidy a messy folder" is a problem I do not have, and I would be nervous about a tool re-arranging a structure I built on purpose.
- Mildly interesting: local-only model and the "it asks first" promise, since I would not paste thesis data into a cloud chatbot without thinking. ChatGPT already covers drafting and questions for me.
- Expected: little value for me, perhaps some for friends who keep everything in Downloads.

## 4. Interaction and exploration summary
Opened the app (a voice greeting started; I ignored it, the microphone was not available in the test browser). Went to Folders, and added a small invented folder of lecture notes plus two files I wrote to mimic my habits (a dated journal entry "Stopped at: methods chapter, section 3.2..." and a weekly review with a to-do list). Asked it questions about where I stopped and what I still need to do. Pressed "Suggest a tidy-up" and read the plan but did not approve it. Looked at "What it knows" and Settings. Did not try undo (nothing was approved), voice, web search, drafting, the email feature, the key buttons, cloud, or remote access.

## 5. Observed behavioural data

| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app, read home screen | Counters at 0 folders; text "Everything is stored on this computer. Nothing has been sent anywhere." Voice greeting started | Mild interest in the privacy line; ignored voice |
| 2 | Tried to add a folder (first attempts) | I typed the path into the wrong box more than once; message "Type or browse to a folder first."; several attempts lost | Repeated, annoyed (see limitations) |
| 3 | Added my notes folder in Folders | "Added 'stuff'. ARTEMIS now knows about 11 files in it." Folder shows "can read and change files here, with your approval" and "Cloud models are off here" | Interest in the per-folder cloud switch |
| 4 | Asked "What is on my weekly review to do list?" | Listed the three items and cited 2026-11-weekly-review.md:1 | Interest, but I thought "I can open that file myself" |
| 5 | Asked "Where did I stop on my thesis?" | "In the methods chapter, section 3.2." with source 2026-11-08_journal.md:1, plus lit review done, methods draft 60% | Interest, then hesitation: correct, but only because I had already written it down |
| 6 | Asked "What do I still need to do this week?" | "Book viva slot and fix reference list." with source | Mild interest; Notion already does this |
| 7 | Pressed "Suggest a tidy-up" on my already ordered folder | "Would move 13 files and create 2 folders. Nothing is deleted." 15 steps: made "Documents" and "Images", moved my dated journal, weekly review and lecture notes into Documents and screenshots into Images. Risk labelled "changes files, and can be undone" | Hesitation / strong dislike: it would override my own structure. Did not approve |
| 8 | Opened "What it knows" | Lists every file it holds with sizes, "Forget this folder", "Forget this file", "Erase everything ARTEMIS knows"; says forgetting never deletes my files | Interest; the part I liked most |
| 9 | Opened Settings | Local model (gemma4:e4b, 9.6 GB), cloud keys section, email via app password, remote access (collapsed) | Hesitation: a lot of setup surface; skimmed, did not click keys or email |

Questions I asked: the three above. Features explored: add folder, Q&A, tidy-up proposal, What it knows, Settings. Skipped: approving a tidy-up, undo, voice, web search, drafting, email, remote access, repeated tasks, notes for next time. Decision: declined to approve the tidy-up because it would break my naming scheme; stopped at about 30 tool calls.

## 6. Feedback about the research idea (persona's words)
"The limits and the ask-first design are sensible, and I like that I can see and erase what it holds. But I have to be honest: I do not lose context. My journal and weekly review are my context-recovery system, and the one thing it did well (telling me where I stopped) it did only by reading my own journal. The tidy-up proposed putting my dated notes into a generic 'Documents' folder, which is worse than what I have. The trust angle is nice for people nervous about AI, but I am not nervous enough to need it, and I would not want yet another tool to maintain."

## 7. Perceived problem relevance
Rating 2 of 5 for me. I rarely lose where I stopped (daily journal, Notion), and routine file chores are nearly absent because of my structure. I can imagine the problem is real (maybe 3 to 4) for classmates with a cluttered Downloads folder or many courses and no system, but I would be guessing about them and I refuse to claim a need I do not feel. Interpretation: people who already have a system are probably not the target users; the tool partly automates a habit I already do by hand.

## 8. Perceived value of the proposed solution
Rating 2 of 5 for me. Valuable: the folder boundary, the visible list of what it holds, erase buttons, plans shown step by step, nothing deleted, local model. Not valuable for me: it re-answers what my journal already says, and the tidy-up was a mismatch for an organised user (it ignored my existing conventions). Question answering across many notes with sources might help a thesis with hundreds of papers, but I did not test a big collection.

## 9. Adoption likelihood and reasoning
Would not use (for me today). What would change my mind: if it respected my existing folder and naming structure, if it could search hundreds of papers and notes and answer with citations better than my own search, if it hooked into Notion so my task list was the source instead of a duplicate, or if my workload outgrew my habits. I might mention it to a friend with a chaotic desktop but would not recommend it strongly on this session.

## 10. Concerns, objections and suggestions
- Tidy-up should detect an already organised folder and say "nothing to do" instead of proposing to restructure.
- Respect existing naming conventions; ask me for my rules first.
- Another place for notes and tasks next to Notion; integration would matter more than a new inbox.
- Settings is crowded (cloud keys, email app password, remote access); fine for a developer, heavy for me.
- Value for someone like me would need to be shown on bigger sets of material than I tried.

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: partly. The folder limit and ask-first plan make me comfortable, but I am already fairly comfortable with ChatGPT for non-sensitive things; I cannot say how a person with strong privacy worries would feel.
(b) More willing to use it: partly. It removes one possible reason to refuse, but my reason for not using it is that I do not need it, not that I fear it.
(c) Does the limitation cost too much usefulness: disagree for my uses (I never wanted it to see my whole computer); cannot say for others.

Short questions:
- Are people really losing time to interruptions and routine file work: partly. Probably true for disorganised people, not for me; I am inferring about others.
- Is wanting broad access a real barrier for me: disagree. I just do not feel the need.
- Accept one mistake if undo is easy: partly yes for file moves, not for anything leaving my machine. I did not test undo.
- Ask before every change or act then undo: ask first, at least for moves and renames; maybe act-then-undo for trivial things after I have seen it behave well. The plan list was clear.
- Which abilities I would use: questions over my notes with sources, maybe; the "What it knows / erase" page. I would not use tidy-up, daily recovery, voice or email.
- What makes setup too much effort: a 9.6 GB model, entering keys or app passwords, and rebuilding my structure inside another tool.

## 12. Implementation limitations I ran into
- Adding a folder was fiddly: my first attempts failed with "Type or browse to a folder first." (partly my automation picking the wrong box; a hidden second input exists, a real user may not hit this). Interpretation: not a concept problem.
- Duplicate tab bars show in the page text; a voice greeting starts on its own; no microphone found.
- Replies took roughly 40 to 50 seconds (shared model).
- Answers repeated the same file citation several times; before I added a folder the greeting said "Welcome. ARTEMIS cannot see any folder yet" which is correct, but later the screen also showed an older "Good afternoon, I'm listening" greeting.
- The tidy-up plan included my own saved screenshots (the test harness writes them into the folder) and proposed moving them to "Images"; I did not approve, so nothing was changed.
- Not tried: undo, approve flow, voice, email, remote access.

Evidence: action log at test/agents/work14/actions.log (it also contains noisy page dumps from debugging attempts).
