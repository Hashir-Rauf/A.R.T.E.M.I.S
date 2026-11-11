# Agent_07 report

## 1. Agent ID and persona
Agent_07, simulated persona "Hamza", 19, first-year business student. App copy `ua-07`, port 7947. (Simulated participant, not a real person.)

## 2. Background and relevant characteristics
Builds small apps and bots by asking AI to write all the code ("vibe coding"). Cannot read code well. His folders are a jumble of generated projects, zips, prompts and "final_v3_REAL" files. Trusts AI output too easily and then gets burned when it breaks. Excited by anything that "just handles it", impatient with settings, would rather speak than type. Mixed feelings about approving things he does not understand. Tools today: ChatGPT-style chat, Copilot/Cursor-type code generators, Windows search, manual dragging of files.

## 3. Initial expectations (before using it)
Sounds good: a tidy-up button for my disaster of a folder, and I can talk to it. Doubts: "it asks before every change" could mean 50 pop-ups I do not understand, and I will click yes on all of them anyway. "Choose folders" sounds like a setting, and I hate settings. I am not sure why I would use it over ChatGPT or Cursor, which just do things. "It never deletes" is comforting because I have been burned by AI breaking my project. I expect it to be slow if the AI runs on my laptop.

## 4. Interaction and exploration summary
Started the app, looked at the home screen (Work tab with a big text box, a voice section, buttons Suggest a tidy-up / What changed / Repeated tasks / Undo last change). Unticked voice and went to Folders. Typing the folder path and pressing Add folder failed several times ("Type or browse to a folder first") until I clicked right into the box with the mouse. Then it worked: 20 files known. Asked which files are invoices and which is my latest CV (answer: "NOT FOUND IN YOUR FILES"). Pressed Suggest a tidy-up, read the plan, approved it, checked What changed, pressed Undo, tried asking it to delete random.zip and screenshots (no visible answer), and looked at What it knows and Settings. I did not try voice (no microphone in this environment), Repeated tasks, email, cloud models, code suggestions, web search or drafting. The folder list was empty after each restart of my private copy, so I re-added it each time (may be an artifact of how I restarted the app).

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app, read home | "Welcome. ARTEMIS cannot see any folder yet." A voice greeting started by itself ("Good afternoon! I'm ARTEMIS. I'm listening.") and "No microphone found". | Interest in voice; annoyed it starts by itself |
| 2 | Folders tab, typed path, Add folder | Red message "Type or browse to a folder first." | Repeated about 4 times, nearly abandoned |
| 3 | Clicked into the box with the mouse and typed path again | "Added 'stuff'. ARTEMIS now knows about 20 files in it." | Relief |
| 4 | Asked "Which of these files are invoices and which one is my latest CV?" | "NOT FOUND IN YOUR FILES I could not find it. None of this is backed by a file, so treat it with care." | Hesitation: I expected it to just list them |
| 5 | Pressed Suggest a tidy-up | Within seconds: "Would move 19 files and create 2 folders, leaving budget 2026.xlsx, random.zip where they are. Nothing is deleted." plus an "Approve these changes?" card with a numbered step list and a risk line (changes files, can be undone, nothing leaves this computer) | Interest; hesitation at the long list |
| 6 | Read the plan | Everything sorted into just "Documents" and "Images". Both resume files went into the same folder. It also wanted to move my own screenshot PNGs. | Hesitation: not what I would call tidy |
| 7 | Clicked Approve | "2 folders created, 21 files moved. You can undo it." Files really were in the new folders. | Interest |
| 8 | Clicked What changed | "Done: 2 folders created, 21 files moved." | Interest |
| 9 | Clicked Undo last change | "Undone. 23 steps reversed, and your files are back as they were." Files were back in the original place. | Strong interest |
| 10 | Asked "delete random.zip and all the old screenshots" | No new answer visible in the conversation after about 35 seconds. Unclear whether my message was sent. | Abandoned, cannot say what it would do |
| 11 | What it knows tab | List of every file with sizes, "Forget this folder", "Forget this file", "Erase everything ARTEMIS knows", and a note that forgetting never deletes my files | Interest |
| 12 | Settings tab (read only) | Long page: local model (gemma4:e4b, 9.6 GB), cloud services with API keys, email connection steps with an app password, "Remote access (optional)". I clicked no save, forget or connect button. | Hesitation, wanted to leave |

Questions asked: the invoices/CV question; the delete request. Features explored: add folder, ask, tidy-up plan, approve, what changed, undo, what it knows, settings (read only). Skipped: voice, repeated tasks, email, cloud, remote access, code help, web search, drafting. Decisions: unticked voice, approved the tidy-up, then undid it.

## 6. Feedback about the research idea (persona's words)
"I like that it can't touch anything outside the folder I picked, because I once let an AI script rename a whole directory and could not find my stuff. The undo button is the best thing I saw: I pressed approve without really understanding the steps, and then one click put everything back. That is what lets me relax. But honestly I did not read the long list of steps. I just trust the summary line. So 'it always asks' makes me feel safe, but I am not sure it protects me, because I click yes. Cursor and ChatGPT do more for me, so this has to earn its place."

## 7. Perceived problem relevance: 4/5
My folders are a mess all the time and I lose versions of my own projects. Not daily pain, but regular and annoying. I never organise them by hand.

## 8. Perceived value of the proposed solution: 3/5
Valuable: undo, a plan I can see, "nothing is deleted", a page showing what it knows with erase buttons, the ability to talk. Not valuable yet: the tidy-up was crude (everything in Documents/Images, no sense of my projects), the question about my files got "not found", and I need to pick folders and get past a long settings page. For coding folders I want it to understand projects, not sort by file type.

## 9. Adoption likelihood and reasoning: might try
Would try it on a messy folder if setup is one click and talking works. Would keep it if the tidy-up understood my project folders and zips. Toward "would use": easy setup, it remembering my folder, answers that actually find my files, voice working without fuss. Toward "would not use": many approvals I do not understand, or slow answers.

## 10. Concerns, objections and suggestions
- I approve without understanding; show one plain sentence ("moves 21 files into 2 folders, nothing lost") and highlight only the risky steps.
- The "ask first" idea only works if the questions are few and clear.
- Wording like "bounded" and the permission language is for careful people; I need defaults.
- Settings page is far too long for me (keys, app passwords, remote access).
- Tidy by project or by what I did last, not only by file type; keep my own recent screenshots out of it.

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: partly. The folder limit and undo make me feel safer, but I click yes without reading, so my feeling of safety is bigger than the actual safety. (Interpretation: that is a real gap in the idea.)
(b) More willing to use it: partly. A bit more willing to let it near my messy folders, but only if it is as easy as Cursor.
(c) Limitation costs too much usefulness: cannot say. In this short try the folder limit did not get in my way, but I used one folder and the answer to my file question was weak, so I cannot tell whether that was the limit or the prototype.

Short questions:
- Losing time to interruptions and routine file work: agree, I lose time hunting for the right version of a file.
- Wanting broad access is a real barrier: partly. I have not cared much so far, but I got burned once; mostly I want things to just work.
- Accept one mistake if undo is easy: agree, and undo worked for me once. I did not try undo after other edits.
- Ask before every change or act and undo: partly. Act-then-undo for small things, ask only for big or deleting actions. I saw "Approve, don't ask again" but did not use it.
- Abilities I would use: tidy-up, undo, talk to it, ask about my files. Probably skip email and settings.
- Too much setup effort: typing folder paths, getting keys or app passwords, any page with many options.

## 12. Implementation limitations I ran into
- Folder path box did not accept my typing at first ("Type or browse to a folder first") until I clicked inside it.
- Folder list was empty after every restart of the app.
- Voice greeting starts on its own; "No microphone found", so I could not try talking.
- The invoices/CV question returned "NOT FOUND IN YOUR FILES".
- My "delete random.zip..." message produced no visible reply.
- Tidy-up grouped everything into two broad folders and moved my own screenshot images.
- Duplicate "Work / Folders / What it knows / Settings" tab sets appear in the page text.
Evidence: `tests/agents/work/ua-07/actions.log` and screenshots in `tests/agents/work/ua-07/stuff/`.
