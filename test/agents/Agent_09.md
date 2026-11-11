# Agent_09 report (simulated participant)

## 1. Agent ID and persona
Agent_09, "Tariq", 45, freelance bookkeeper and tax consultant for small shops. Simulated persona; reactions below are plausible reactions, not facts about real people.

## 2. Background and relevant characteristics
Low-to-moderate tech skill. Lives in Excel and email. His folders hold clients' spreadsheets, scanned receipts and tax filings, which are highly sensitive. He believes any AI that sees client data is a legal risk. He has never used an AI assistant on work files. He is cautious, slow to trust, and asks "who is responsible if it goes wrong?". He would adopt it only if the safeguards are obvious and simple.

## 3. Initial expectations (before using it)
Expressed feedback: "A helper that only sees the folders I pick sounds better than the things that want my whole computer. But 'AI' and 'client files' in one sentence makes me nervous. My clients trusted me with their tax numbers and sales figures; if something leaks it is my licence, not the software maker's. I want to know: does anything leave the machine, can I see what it kept, and who answers if it makes a mistake? 'Runs on your own computer' is the line I care about most. 'Asks before it changes anything' is good, but I would still worry about what it reads, not just what it changes. Today I do everything by hand: Excel, folders named by client and year, email, and my own memory for deadlines."

## 4. Interaction and exploration summary (in order)
I started my private copy (ua-09, port 7949) and read the home screen: a green box saying "Everything is stored on this computer. Nothing has been sent anywhere", and counters (0 folders visible, 0 files known, 0 actions recorded). I made an invented folder (the harness "messy" kind, plus two files of mine: a fake client sales CSV and a fake tax-notes text file). I read the Settings page, then tried many times to add the folder in the Folders tab; it never worked. I tried the Work tab buttons with no folder, then the What it knows page, then tried typing questions about client data safety. I got no answer to those typed safety questions. I stopped after about 20 tool calls because I could not reach the core (folder, tidy-up, undo). Not tried: tidy-up on real files, the approval screen, undo of a real change, Remote access, Erase everything, drafts or email, voice, the cloud-allow toggle on a folder.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened home screen | Green "stored on this computer, nothing sent anywhere" notice; four counters; Welcome message saying it cannot see any folder yet | interest (the first thing that speaks to my worry) |
| 2 | Clicked through Folders, What it knows, Settings (read text) | Folders: "ARTEMIS cannot see anything on this computer... only looks inside the folders you choose". Settings: local model gemma4:e4b "In use"; cloud services listed, Gemini shown as "Key saved"; email section; Remote access (optional) | hesitation: "Gemini: Key saved" and "Cloud services" made me ask whether my data could go there |
| 3 | Typed my folder path in Folders and clicked Add folder | Field emptied at once and red message "Type or browse to a folder first" | repeated about 6 times |
| 4 | Tried pressing Enter, Tab, a keyboard-only route, waiting before clicking | Same: value cleared as soon as the field lost focus or I pressed Add; "Choose a folder first" | repeated, then abandoned |
| 5 | Clicked Browse | Nothing visible happened in the page after 5 seconds | abandoned |
| 6 | Work tab, asked "What is in this folder? Which files are about Rana Traders?" (no folder added) | Reply: "That works on a folder, and there is none yet. Open the Folders tab and add one." | hesitation |
| 7 | Asked whether anything leaves my computer and who is responsible (three attempts, different wording) | No reply appeared in the conversation, only the greeting stayed | abandoned (cannot say whether the question was received) |
| 8 | Clicked Suggest a tidy-up, Undo last change, What changed with no folder | "Choose a folder first." / "There is nothing to undo." | interest in the plain wording, nothing to judge |
| 9 | Opened What it knows | "Choose a folder above to see what ARTEMIS knows"; a "Forget this file" button and "Erase everything ARTEMIS knows" with a note that the activity log is kept | interest: an erase button and a log are what I want to see |

Questions I asked it: file listing for a client; whether anything leaves the computer; who is responsible for mistakes. Only the first got an answer (a "add a folder first" message). Decisions: I did not click Save key, Forget key, Connect my email or Disconnect.

## 6. Feedback about the research idea (persona's words)
"The idea of limiting it to folders I choose is the first thing that has made me even consider an assistant. Right now my choice is 'no AI' or 'AI that sees everything', and I pick 'no AI'. A small named client folder, a plain statement that nothing has been sent anywhere, and a page that shows what it holds are the right ingredients. But I could not test the actual promise because I could not add a folder, so I cannot say whether it keeps it. I also noticed the settings page mentions cloud models and a saved key. For a tax consultant that has to be impossible to turn on by accident, and the screen must say clearly, per folder, 'this folder never leaves the machine'. And nothing I saw answered 'who is responsible'. That is a legal and contract question, not a button."

## 7. Perceived problem relevance
Rating 3 of 5. Interruptions and routine file work are real for me: finding last year's filing, chasing missing receipts, remembering which client owes what. But my bigger problems are deadlines and client chasing, which this does not obviously solve. Interpretation: the problem is moderately real for this persona; the pull would be "remind me where I left off with each client", not "tidy my folder".

## 8. Perceived value of the proposed solution
Rating 2 of 5 from what I could actually use, 3 of 5 for the concept. Valuable: the bounded-folder idea, the "nothing sent anywhere" notice, the erase button, a log that is kept. Not valuable to me yet: tidy-up (my folders are already organised by client), voice, email drafting. I could not evaluate asking questions about my files, or undo.

## 9. Adoption likelihood and reasoning
Might try (only on an invented test folder, never on real client files at first). What would move me towards using it: a one-sentence, per-folder promise that nothing leaves the machine, with a switch I can see is off; a short document I can show a client about how data is handled; an obvious place that shows exactly what it read; and the makers saying who is responsible. What would make me avoid it: any cloud option that is on by default or easy to enable, or unclear messages about where my words and files go.

## 10. Concerns, objections and suggestions
- Liability: if it summarises a client's figures wrongly and I act on it, that is on me. The product should say so honestly and make it easy to check the source file behind every answer.
- "Cloud models" and "Key saved" in Settings: I would want cloud off, with no keys at all, for sensitive folders, or hidden unless I ask.
- Reading is the risk for me, not only changing. I want to see which files it has read, not only which it changed.
- Plain wording was good ("There is nothing to undo."); keep it that way.
- Suggestion: a one-page "what this can and cannot do with my clients' files" screen at first start.

## 11. Final assessment of the central claim
(a) More trust than an assistant with full access? Agree. For me full access is a non-starter; chosen folders plus a visible log is the minimum. (From the idea and the screen text; I could not test enforcement.)
(b) More willing to use it? Partly. It gets me to try it on a test folder; it does not get me to put real client files in until I can see what it reads and who is liable.
(c) Does the limitation cost too much usefulness? Cannot say. My work is mostly inside client folders, so the limit should cost little, but I never got far enough to see what it does inside one.

Short questions:
- Are people losing time to interruptions and routine file work? Partly agree for me: finding the right file and chasing missing documents, yes; tidying, no.
- Is wanting broad access a real barrier? For me it is the opposite: broad access is my barrier. Agree that limited access removes a barrier.
- Would I accept one mistake if undo is easy? Partly. A wrongly renamed file, yes. A wrong number in a tax summary, no; undo does not help there.
- Ask before every change, or act and let me undo? Ask first for anything touching client files. Maybe less asking for obviously harmless things after long trust (I saw an "Approve, don't ask again" button; I would be wary of it).
- Which abilities would I use? Questions about my notes and files (finding a figure or a missing receipt), the "where did I leave off" notes, drafting a reminder email to a client. Not voice, not web search involving client data.
- What would make setup too much effort? Typing folder paths by hand, the long email app-password steps (seven steps for Gmail looked like too much), and anything where I must understand "models" and "keys".

## 12. Implementation limitations I ran into
- Add folder never worked for me: the typed path was cleared as soon as the field lost focus or I pressed Add, with "Type or browse to a folder first" / "Choose a folder first". Everything depending on a folder (tidy-up, undo, what it knows, file questions) was therefore not testable. Browse showed nothing in the page. (Interpretation: could be a bug in how the field is read, or an effect of my automated typing; I cannot tell which.)
- Typed questions about safety produced no visible answer; only the greeting stayed on screen. Again I cannot tell whether this is the prototype or how my input was delivered.
- Tab names appear twice in the page text; a voice greeting and "No microphone found" appear on their own; I ignored them.
- This is a prototype; none of this changes my view of the idea itself, only that I could not test much of it. Evidence: action log at E:\Education\FAST-NUCES\Final Year Project\A.R.T.E.M.I.S\test\agents\w09\actions.log, screenshots in tests\agents\work\ua-09\stuff.
