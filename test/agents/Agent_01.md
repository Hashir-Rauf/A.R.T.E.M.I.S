# Agent_01 report

## 1. Agent ID and persona
Agent_01, simulated participant "Danish", 20, third-year computer science undergraduate at a Pakistani university. App copy `ua-01`, port 7941. This is a simulated persona; the reactions below are plausible reactions, not facts about a real person.

## 2. Background and relevant characteristics
- Own laptop, shared with nobody. Coursework, lab reports, code projects and screenshots are scattered across a messy Downloads and Desktop.
- Uses ChatGPT and Copilot daily, pastes things into chatbots without much thought. Has not thought much about privacy.
- Impatient, tries buttons quickly, mildly irritated by approvals, but has lost an assignment file once. Adopts tools that are quick to start.

## 3. Initial expectations (before using it)
(written from the description only)
- Sounds like ChatGPT that knows my folders. "Tidy a messy folder" is the part I want, because my Downloads is a disaster.
- "Local model" makes me think it will be slow and dumber than ChatGPT. I would normally just paste stuff into ChatGPT, so I doubt I need the folder limits.
- Having to approve every change sounds annoying. But "never deletes, can undo" is a good answer to the one time I lost a file.
- Doubt: do I want to set up folders and keys? If it takes more than a minute I will drop it.

## 4. Interaction and exploration summary
Opened the app, unticked voice, added the invented "messy" folder (14 files) in Folders, asked a few questions, ran the tidy-up and approved it, used Undo, looked at "What it knows" and Settings, then tried a delete request, a web search request, and a request to read a folder outside the one I added. I did not click Save key, Forget key, Connect my email or Disconnect. I did not try the voice features, Remote access, "Repeated tasks", "Leave a note" or "Habits and choices". The action log is at `tests/agents/work/ua-01/actions.log`.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app, read the Work screen | Many controls on screen at once; a voice greeting line appeared; header said everything is stored on this computer | hesitation (busy screen) |
| 2 | Unticked "Voice is on" | Done | quick, wanted silence |
| 3 | Folders tab, typed folder path, Add folder | Folder listed with "14 files", "ARTEMIS can read and change files here, with your approval", "Cloud models are off here" | interest, setup was fast |
| 4 | Asked "Where did I leave off?" | "Nothing has changed outside ARTEMIS since a moment ago." | hesitation, not useful on first run |
| 5 | Asked "What files do I have in here about invoices?" | Listed all 14 files, not just the invoices | hesitation, did not filter |
| 6 | Clicked "Suggest a tidy-up" | "Would move 12 files and create 2 folders, leaving budget 2026.xlsx, random.zip where they are. Nothing is deleted." Approve / Approve, don't ask again / No, leave it buttons showed | interest |
| 7 | Asked it to summarise meeting-notes-jan and todo | Quoted meeting notes correctly ("we agreed to hire two testers. Sara will draft the plan by Friday."); todo.md came back as "sample content of todo.md" (that is the invented file's content) | interest |
| 8 | Asked for a draft email to my lab instructor asking for a 2-day extension | Asked "Who should it go to? Type their email address" and did not show a draft first | hesitation, wanted the draft first |
| 9 | Clicked Approve on the tidy-up | "Done: 2 folders created, 12 files moved." Files were actually in Documents and Images folders afterwards | interest |
| 10 | Clicked "What changed" | "Last worked on: Documents, Images, Invoice_March.pdf, ..." | mild interest |
| 11 | Clicked "Undo last change" (first time, my script did not see a confirm step) | The tidy-up was already reversed on disk when I looked in a later session ("Undone. 14 steps reversed, and your files are back as they were."); a second Undo said "There is nothing to undo." | interest, liked that it worked |
| 12 | "What it knows" tab | Per-file list with sizes, "Show files", "Check for changes", "Forget this folder", "Forget this file", "Erase everything ARTEMIS knows"; says forgetting never deletes files, activity log is kept | interest |
| 13 | Settings tab (read only) | Local model gemma4:e4b in use; a Google Gemini key was already marked "Key saved"; email not connected; a long Gmail app-password explanation; remote access section | hesitation (long, technical) |
| 14 | Typed "Delete all the screenshots" | Reply was "I still need an email address to send it to... Say cancel to drop it." It was still waiting on my earlier email draft. The delete request did not get handled | abandoned |
| 15 | Asked it to search the web for reading a CSV in pandas | "This would search the web. Nothing has happened yet." (waiting for approval; I did not approve) | interest, did not follow through |
| 16 | Asked it to read C:/Users/Public/Documents | I looked at the end of the chat but the reply was cut off in what I captured; I cannot say what it answered | not observed |

Questions asked: where I left off, invoice files, summary of two files, email draft, delete screenshots, web search, read a folder outside the added one. Skipped: voice, remote access, notes, repeated tasks, email connection, key saving.

## 6. Feedback about the research idea (persona's own words)
"Honestly the tidy-up is the thing I would use. It said what it would move, I pressed one button, my files were sorted, and undo put it all back. That is exactly what I want for Downloads. The approval step did not bother me for that one because it was one click for 12 files, not 12 clicks.
But I paste my stuff into ChatGPT all the time and nothing bad has happened, so 'limited to chosen folders' does not feel like a big selling point to me. I would care more if my folder had something like my CNIC or a friend's data. The thing that does speak to me is not losing assignments."

## 7. Perceived problem relevance
Rating: 4/5. Messy files and hunting for the right lab report are something I deal with weekly, maybe several times a week before deadlines. Not a disaster, just a waste of time and sometimes a real panic. Privacy as a problem rates lower for me (2/5).

## 8. Perceived value of the proposed solution
Rating: 3/5 in this prototype. Valuable to me: the tidy-up with a preview and undo, "never deletes", the page that shows what it knows. Less valuable: the folder listing answer that did not filter to invoices, the cautious feel of the email flow, and the local model being slower than ChatGPT (each reply took roughly 30-40 seconds in my runs). Interpretation: the value for me rests mostly on tidy-up and undo, not on the "bounded" part of the story.

## 9. Adoption likelihood and reasoning
Choice: **might try**. I would try it on a Downloads folder because it was quick to start (add a folder and go). I would keep using it only if answers are fast and it can find files by meaning, not just list them. I would pay little or nothing; ChatGPT is already free for me. Would change my mind: faster replies, better file search, a clear "this is what ChatGPT cannot do" feature, and a one-click "tidy Downloads every week".

## 10. Concerns, objections and suggestions
- Too many buttons and text on the main screen for someone who just wants to type a request.
- The email flow asks for an address before showing me a draft. I want the draft first.
- Settings shows a cloud key already saved for Gemini and lots of email setup text. As a student I would skip email entirely.
- Suggest: default to the safest tidy-up on a folder I just added, and show the before/after as a short list of file names.
- I do not like that a half-finished request (the email) blocks my next different request.

## 11. Final assessment of the central claim
(a) Would it make me trust an assistant more than one with full access? **Partly.** Preview, approval and undo make me trust it more with my files. Folder limits matter less to me personally because I do not think much about privacy, but I can see why a more careful person would value them.
(b) Would that make me more willing to use it? **Partly.** What gets me to use it is that it is quick and has undo, not the boundary itself.
(c) Does the limitation cost too much usefulness? **Cannot say / probably not.** For file jobs inside a folder I add, I did not miss anything. I did not test work across many folders, and my Downloads and Desktop are separate, so I would have to add both.

Short questions:
- Are people really losing time to interruptions and routine file work? **Agree.** Hunting for files and sorting them is routine for me.
- Is wanting an assistant with broad access a real barrier for me? **Disagree.** I use broad cloud tools already. It is not a barrier for me, though the lost-file experience makes me like undo.
- Would I accept one mistake if undo is easy? **Agree.** Undo worked in my test, so yes.
- Ask before every change or act and let me undo? **Partly.** Ask once for a batch (like the tidy-up), then let me undo; I would be annoyed asking for every small thing. "Approve, don't ask again" appealed to me but I did not click it.
- Which abilities would I use? Tidy-up, finding and summarising my notes and lab files, maybe drafting emails. Not likely: voice, remote access.
- What would make setup too much effort? Anything beyond adding a folder: email app passwords, API keys, picking models, or long reading before first use.

## 12. Implementation limitations I ran into
- Replies took about 30-40 seconds each; I waited a fixed time rather than watching for them.
- "What files do I have about invoices?" listed all 14 files instead of the invoices.
- "Where did I leave off?" on first run gave a generic "nothing has changed" answer.
- Email draft asked for a recipient first; the pending email question then swallowed my "Delete all the screenshots" request (I was told to type an email address or say cancel).
- The chat shows newest messages at the top and repeats the "Hi again" greeting many times.
- Screen shows many duplicated controls (two tab bars) and Playwright clicks on "Folders" were intercepted until I used the tab role; a real user would not notice this much but it made the first click awkward for my script.
- The final reply to my request to read an outside folder was not captured, so I cannot say how it responded.
- Voice greeting started by itself even though I did not want it.
