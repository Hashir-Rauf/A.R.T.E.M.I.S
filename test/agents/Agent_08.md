# Agent_08 report (simulated participant)

## 1. Agent ID and persona
Agent_08, app copy `ua-08`, port 7948. Persona: Zara, 29, freelance graphic designer and copywriter, five regular clients. This is a simulated persona; reactions are plausible reactions, not facts about real people.

## 2. Background and relevant characteristics
Folders hold client briefs, contracts/NDAs, invoices, copy drafts and image assets, under confidentiality clauses. I use Canva and some AI image/text tools but never upload client documents. I send many emails and invoices and lose time finding the latest file version ("final", "final_final"). Moderate technical skill, practical, price-sensitive. Would adopt a tool that saves billable hours if it cannot leak client material.

## 3. Initial expectations (before using it)
Sounds like a local-only helper, which is what my NDAs need. I expect "where is the latest brief / which invoices are unpaid / draft the chasing email" to be the useful part. Doubts: a small local model may be weak; tidy-up might mangle my naming; "asks before everything" might get tiring; I doubt it beats a ChatGPT-style chatbot on non-confidential bits. Today I use manual search, Explorer sort-by-date, Canva, and a chatbot only for anonymised text. Price matters: I would not pay much for a prototype-grade assistant.

## 4. Interaction and exploration summary
I made a small invented client folder (8 text files: three Brightleaf brief versions, a Northwind NDA, two invoices, a copy draft, a todo). I added it in Folders, asked factual questions on the Work tab, asked for an email draft, tried tidy-up (declined once, then approved and undid), and looked at What it knows and Settings. I did not use voice, Remote access, cloud keys or email connection (as instructed), and did not try images, zip files, the notes feature, "Repeated tasks" or saved chats.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app, read home | Local-only banner, empty "cannot see anything" state, voice greeting text | interest (clear message) |
| 2 | Folders tab, typed path, Add folder | Folder listed with "8 files", "Cloud models are off here" | interest; liked per-folder cloud switch |
| 3 | Asked: latest Brightleaf brief, deadline, budget? | Picked v2_FINAL_final, 20 Dec, 1500, with source file name | strong interest (my exact pain) |
| 4 | Asked: which invoices are still unpaid? | Asked me which folder to look in; no answer | hesitation |
| 5 | Asked: draft polite email chasing invoice 0042 | Asked for recipient address | neutral |
| 6 | Asked unpaid invoices again (while it still wanted an address) | Said it still needed an email address, "say cancel to drop it" | hesitation / annoyed |
| 7 | Asked NDA question (still mid-email) | Ignored; only a status line | hesitation |
| 8 | Gave address, asked for chase email | Plan "Send 1 email", risk "sends something off this computer", full email text shown; warned no mail account set up | interest; liked seeing the exact text; did not connect email |
| 9 | Suggest a tidy-up | Plan: make one folder "Documents", move all 8 files into it | hesitation (wrong for how I work) |
| 10 | Clicked No, leave it | "Okay then." Nothing changed | decision: decline |
| 11 | NDA question after cancel | Correct: must not share client materials with third parties, with source | interest |
| 12 | Asked unpaid invoices and total owed | Again asked me to point to the folder | repeated, hesitation |
| 13 | Asked to summarise todo | Listed the 3 items with source | interest |
| 14 | What it knows tab | Lists every file and size; Forget folder/file; Erase everything | interest |
| 15 | Settings tab | Local model gemma4:e4b, storage location, cloud services, email setup, remote access. A Gemini key already showed "Key saved" in this copy; I did not touch it | hesitation (cloud options exist) |
| 16 | Tidy-up again, Approve | 1 folder created, 8 files moved; confirmed on disk | tested undo |
| 17 | What changed | Listed files last worked on | neutral |
| 18 | Undo last change | "9 steps reversed"; all 8 files back in place (checked on disk) | strong interest, trust gained |
| 19 | Asked: which invoice files in my clients folder are unpaid? | Correctly: only Invoice 0042 Northwind, with source | interest; that wording worked |

Questions asked: latest brief/deadline/budget; unpaid invoices (three wordings); NDA third-party clause; todo summary; chase-email draft. Skipped: voice, images, zip, notes, saved chats, cloud, email connection, remote access, Repeated tasks.

## 6. Feedback about the research idea
For me the limit is the selling point. My contracts forbid uploading client files, so a tool that is local and only sees folders I choose is the first one I could use without worrying. The file list on "What it knows" and the "Nothing leaves this computer" line on plans made it feel believable. But I trust it only because it showed me; a promise alone would not do it. I would still check the folder isolation before putting a second client's folder in.

## 7. Perceived problem relevance: 4/5
Finding the current version of a brief, checking what is unpaid, and writing chasing emails happen several times a week and cost real minutes, perhaps 3-5 hours a month. Not 5 because I cope with sort-by-date and a spreadsheet.

## 8. Perceived value of the proposed solution: 3/5
Valuable: answers with source file names; showing the exact email before sending; undo that really worked; per-folder control; a page showing what it holds. Not yet valuable: tidy-up dumped everything in one "Documents" folder, ignoring client/project structure; it often asked for a folder that was already added; the pending-email state swallowed other questions. A 3 because the core promise works but everyday answers were inconsistent.

## 9. Adoption likelihood: might try
I would try it on one low-risk client folder. Would move to "would use" if: cross-file questions (unpaid invoices, totals) work first time; tidy-up respects my client folder structure and naming; it can send email through my normal account with a review step; it is free or cheap and runs on my laptop. I would drop it if anything went to the cloud without clear notice or basics needed a subscription.

## 10. Concerns, objections and suggestions
- Settings offers cloud models and keys; I want a hard "never use cloud" switch and a visible log of anything sent out.
- Understand "client" folders and invoice status across files (a small tracker view).
- Tidy-up should group by client or project and keep the names I use.
- Email draft should pull client, amount and due date itself.
- I would want proof that files outside chosen folders are unreadable.
- Gmail app-password setup is a lot for me; I would likely skip email.

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: **agree**. The scope limit and visible plans are what make it eligible for client material at all.
(b) More willing to use it: **agree**. With my NDAs it is the reason I would try it; a full-access tool I would not install.
(c) Limitation costs too much usefulness: **partly**. The folder limit costs me almost nothing (client work lives in a few folders); the patchy answers cost more, but that looks like prototype quality (interpretation), not the limit.

Short questions:
- Are people really losing time to interruptions and routine file work: **agree** (version hunting, chasing invoices).
- Is wanting broad access a real barrier for me: **agree**; contractual, not just a feeling.
- Accept one mistake if undo is easy: **agree** for file moves (I saw undo work on 8 files); **disagree** for sent emails.
- Ask before every change or act-then-undo: **partly**. Ask for sending email and anything leaving the computer; for moves inside a folder act-then-undo would be fine. Asking for every small change would wear me out.
- Abilities I would use: finding the latest file and answers with sources, email drafts, searching contracts, tidy-up if it respects structure. Probably not: voice, remote access.
- Too much setup effort: email app passwords, picking models, re-explaining folders to it.

## 12. Implementation limitations I ran into
- "Which invoices are unpaid" got a clarifying question asking for the folder twice, even though the folder was added; rewording to "invoice files in my clients folder" worked.
- A half-finished email request kept taking my next messages as the recipient until I typed "cancel".
- Tidy-up put all files in a single "Documents" folder.
- Replies took roughly 10-20 seconds; apostrophes/quotes around folder names displayed as "?" in my capture.
- Email not connected, so I could not test sending.
- Voice greeting text appeared on its own; no microphone in the browser.
- A Gemini key was already marked saved in this copy (not touched by me).

Evidence: `test/agents/work08/actions.log` and scripts s1-s6.py in the same folder.
