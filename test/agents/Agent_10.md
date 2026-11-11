# Agent_10 report (simulated participant)

## 1. Agent ID and persona
Agent_10. Farah, 33, operations coordinator at a mid-sized logistics company (simulated persona; reactions below are plausible reactions, not facts about a real person). App copy `ua-10`, port 7950. Action log: `tests/agents/work/ua-10/actions.log` (screenshots in the same folder).

## 2. Background and relevant characteristics
Handles reports, schedules, vendor emails and shared-drive files. Uses Microsoft Office and Teams. Company allows only approved tools; IT has warned against pasting company data into chatbots. Moderately comfortable with computers, short on time, interrupted constantly, often loses track of what she was doing. Open to help if it is allowed and easy.

## 3. Initial expectations (before using it)
Expressed feedback: "Remembering where I left off" and tidying the shared folder sound genuinely useful; I lose my place several times a day. "Runs on your own computer" is the first thing that makes me think IT might not shout. But: I cannot install anything myself, so is it even allowed? Is it Microsoft-approved? My work is in Outlook/Teams/SharePoint, and this talks about "folders" and a Gmail-style email; would it see my real work files at all? I doubt a local model is as good as Copilot or ChatGPT. "It always asks first" sounds like extra clicks when I am already rushed.

## 4. Interaction and exploration summary
Started the app, looked at the home screen, opened Folders and added a folder of invented files (18 files: invoices, resumes, budget, notes, screenshots). Asked it where I left off and what was in the folder, asked about invoices, asked for a vendor email draft, asked for a tidy-up (typed, then the button), declined the tidy-up plan, tried "What changed" and "Repeated tasks", then read What it knows and Settings. I did not approve a change, did not try Undo, did not use voice (I unticked it), did not search the web, did not touch the key/email buttons.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app | Header says "Everything is stored on this computer. Nothing has been sent anywhere"; counters show 0 folders, 0 files; voice greeting text present | interest (the reassurance line) |
| 2 | Folders tab, typed path, pressed Add | First attempts showed "Type or browse to a folder first." (my script typed into the wrong box, 2 attempts); third attempt worked: "Added 'stuff'. ARTEMIS now knows about 18 files" | repeated (my own mistake, not the app's) |
| 3 | Read folder row | "ARTEMIS can read and change files here, with your approval"; "Cloud models are off here" | interest |
| 4 | Asked "What is in my folder? Anything about invoices or reports?" (first session, before folder was registered) | "That works on a folder, and there is none yet. Open the Folders tab and add one." | neutral; clear message |
| 5 | Asked "Where did I leave off? What is in this folder?" | Listed the 18 files by name. Did not say what I was doing last; chat showed repeated "Hi again. Let's pick up where we left off. What's next?" | mild disappointment |
| 6 | Asked "Which files are invoices and what do they say?" | Named Invoice_March.pdf and invoice-april.pdf; then "NOT FOUND IN YOUR FILES The passages do not say what the invoices contain", with source random.zip | interest in the honest "not found"; confusion at the odd source |
| 7 | Asked "Draft a short polite email to a vendor asking about the late April invoice" | Replied "Who should it go to? Type their email address" and did not show a draft | hesitation |
| 8 | Next asked "Suggest a tidy-up of this folder" (typed) | Replied "I still need an email address to send it to... Say cancel to drop it." It stayed stuck in the email request | annoyed; abandoned this route |
| 9 | Clicked "Suggest a tidy-up" button | Showed "Approve these changes?" with a plain table: create 2 folders, move 16 files, "Nothing is deleted / Nothing leaves this computer / You can undo", 18 numbered steps | strong interest |
| 10 | Clicked "No, leave it" | Plan dismissed, nothing changed | decision: not approving in a trial |
| 11 | Clicked "What changed" and "Repeated tasks" | "Nothing has changed outside ARTEMIS since 4 minutes ago"; Repeated tasks showed nothing visible I could read | no payoff, moved on |
| 12 | What it knows tab | Lists each file with size; buttons Forget this folder / Forget this file / Erase everything; "Forget never deletes... your files stay where they are" | interest |
| 13 | Settings tab | Memory location, local model gemma4:e4b, cloud services with keys (Gemini "Key saved"), email setup via app password, remote access section | hesitation (see concerns) |

Questions asked: 4 typed (where I left off; which are invoices; draft vendor email; tidy-up). Features explored: folders, chat Q&A, tidy-up plan, what-it-knows, settings. Skipped: approve and undo, voice, web search, notes, email connect, remote access.

## 6. Feedback about the research idea
"The tidy-up screen is the thing I liked: every step in order, 'nothing is deleted', 'you can undo'. I could actually show that to IT. The folder boundary is easy to understand: it only sees what I add. For my job that is reassuring, because my shared-drive folders have vendor and pricing data. But I am not sure the limit is the reason I would trust it. I would trust it because it is local and approved, not just because I picked folders. If IT has not approved it, the nice design does not matter." (Interpretation: the folder limit is a necessary condition for her, not sufficient; organisational approval dominates.)

## 7. Perceived problem relevance: 4/5
Losing my place after interruptions and messy shared folders (Invoice_March vs invoice-april, resume_final_v3_REAL) is daily. Not "terrible", but a steady drain, several times a day.

## 8. Perceived value of the proposed solution: 3/5
Valuable: the approval screen, listing everything it holds with Erase, local by default. Not valuable yet for me: "where did I leave off" just listed files; it could not read invoice contents in my test; drafting an email wanted an address first and then got stuck; my work is in Outlook/Teams, not Gmail and plain folders.

## 9. Adoption likelihood: might try
Only if IT approves it and it works with Office files and Outlook. What would change my mind upward: a clear one-page statement I can forward to IT, working "where did I leave off" that tells me my last task, drafts into Outlook. Downward: any need to install by myself, or cloud keys being prominent.

## 10. Concerns, objections and suggestions
- Settings shows cloud keys, Gemini "Key saved", "use cloud models for plain chat... what you type is sent to the cloud". IT warned about exactly this; I would want a way to lock cloud off entirely.
- Does it handle Word/Excel/PDF contents, SharePoint/OneDrive-synced folders?
- Approving 18 steps each time is fine for tidy-ups, but would be too much for small things; "Approve, don't ask again" is tempting but worries me.
- Suggest: a short "last session" summary on opening (what I was doing, last files touched).

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: **agree**, with a caveat. I would trust it far more than something that sees my whole PC and mail; the visible boundary and plan screen are concrete. The caveat: trust at work comes from IT approval.
(b) More willing to use it: **partly**. Willingness rises, but approval and Office compatibility decide.
(c) Limitation costs too much usefulness: **cannot say**. My work files are in a few folders so the limit would cost little in principle; I did not see enough capability to judge what I give up.
- Are people losing time to interruptions and routine file work: **agree**.
- Is wanting broad access a real barrier for me: **agree** (it is not me, it is IT policy; I could not use a full-access tool at all).
- Accept one mistake if undo is easy: **partly**; fine for file moves, not for anything that sends email or touches shared files colleagues use. I did not test undo, so I cannot say it works.
- Ask before every change or act-then-undo: **partly**; ask for anything that moves many files or sends, act-then-undo for small things.
- Abilities I would actually use: where-I-left-off, tidy-up, finding files, email drafts. Not code, probably not voice in an open office.
- Setup too much effort: needing to type folder paths, creating a Gmail app password, picking models, anything needing admin rights.

## 12. Implementation limitations I ran into
- Folder add gave the error "Type or browse to a folder first" in my first two tries; this was my automation typing in the wrong box, not necessarily an app bug.
- "Where did I leave off" only listed files, with repeated "Hi again" messages stacking in the chat.
- Invoice question: source cited was random.zip and the content was not found.
- Email draft request got stuck waiting for an address and swallowed the next request (the tidy-up request) instead of dropping the stuck request.
- "What changed" and "Repeated tasks" showed little I could use.
- Replies took about 45 seconds each (shared model).
- Screenshots I took inside the folder were added to its file list (my own doing).
