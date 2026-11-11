# Agent_12 report

## 1. Agent ID and persona
Agent_12, simulated persona "Dr. Kamran", 48, university lecturer and researcher. App copy `ua-12`, port 7952. This is a simulated persona; reactions below are plausible reactions, not facts about a real person.

## 2. Background and relevant characteristics
Folders hold lecture slides, student submissions, grant drafts and papers. Skeptical of AI summaries because of hallucinated citations. Cares about academic integrity and student privacy (submissions must not leave the machine). Heavy email user. Moderate tech skill, little patience for tools that need babysitting. Currently: manual search in folders, email, occasionally a ChatGPT-style chatbot (which he does not trust with student work).

## 3. Initial expectations (before using it)
- The "only folders you choose" and "asks first" ideas are attractive, especially for student submissions. I would like it to stay on my machine.
- Doubt: a small local model will probably hallucinate, and "answer questions about your notes" is exactly where fabricated citations appear. My bar is: every claim points to a file and place, and it says "I don't know" otherwise.
- Doubt: "draft emails" is useful, but I do not want anything sent without me reading it.
- I expected setup to be fiddly.

## 4. Interaction and exploration summary
Opened the app and read the Work screen. Added my invented folder (5 lecture files plus 3 files I wrote: a student submission with a dubious citation, a grant draft, paper notes). Unticked voice. Asked it which file discusses Lee et al. 2021 and what it says (citations worked). Asked it to verify the Smith 2019 reference in a student submission (it went wrong). Asked for a summary with sources from the submission (it flagged things as not found). Asked for an email draft to the student (it asked for an address and then got stuck). Asked about the grant draft (the reply was still the email address prompt). Pressed "Suggest a tidy-up" and did not approve it. Looked at What it knows, Folders and Settings (read only). Did not click Save key, Forget key, Connect my email or Disconnect. Did not try undo, voice, remote access, the web search, or the approval flow.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened the app | Header says "Everything is stored on this computer. Nothing has been sent anywhere." Counters show 0 folders, 0 files | interest |
| 2 | Folders tab, typed path, Add folder | Folder accepted; counters became 1 folder, 8 files known | interest |
| 3 | Unticked "Voice is on" | "Voice is off. Nothing is recorded." | neutral |
| 4 | Asked: which files discuss Lee et al. 2021 and what about compression, quote and say where | Correct file `paper-notes.md`, correct fact (40% reduction, page 14 table 3), each line tagged `paper-notes.md:1`, plus a "Sources:" line | strong interest (this is what I care about); hesitation: only line-level "1", no quote of exact text |
| 5 | Asked it to read Ali's assignment and say if Smith 2019 is real | It talked about a file "Ali_Assignment_2.pdf", which does not exist in my folder, said it could not read PDFs and could not verify citations | hesitation, distrust (invented a file name) |
| 6 | Asked for a summary of `submission-ali-assignment2.md` with sources only from that file | Output marked each statement "NOT FOUND IN YOUR FILES" and ended "None of this is backed by a file, so treat it with care." The content it repeated was in fact in the file | confused; the warning is the right instinct but wrongly applied here |
| 7 | Asked for a polite email draft to Ali, "do not send" | "Who should it go to? Type their email address" | hesitation: I wanted a draft first |
| 8 | Asked about the grant draft and what is left to do | Reply was "I still need an email address to send it to... Say cancel to drop it." My question was not answered | abandoned that line; annoyed |
| 9 | Pressed Suggest a tidy-up | "Would move 8 files and create 1 folder. Nothing is deleted." I did not approve | interest, not approved |
| 10 | What it knows tab | Lists the files with sizes, "Forget this file", "Erase everything ARTEMIS knows"; says the activity log is kept | interest |
| 11 | Folders tab | "Cloud models are off here: everything stays on this computer." with a per-folder cloud toggle | strong interest |
| 12 | Settings tab (read only) | Local model gemma4:e4b "on this computer"; Gemini already shows "Key saved"; email not connected; keys in Windows Credential Manager | hesitation about Gemini already shown as saved |

Questions I asked: 4 (listed above). Features explored: folder add, citations, summary, email draft, tidy-up suggestion, knowledge page, folder cloud setting, settings. Skipped: undo, approval of any change, voice, web search, remote access, saved chats, habits.

## 6. Feedback about the research idea (persona's words)
Limiting it to chosen folders is the right shape for me. Student submissions must stay on my machine, and "cloud is off per folder, default" is the first time a tool has told me that plainly. The "asks first" part matters less to me than the "shows where each claim came from" part. The Lee et al. answer, with file and line, is what I would want. But then the Smith 2019 question gave me a made-up file name, which is exactly the behaviour I fear. A limit on folders does not stop a small model from making things up inside those folders, so the idea only earns my trust if the source check is strict.

## 7. Perceived problem relevance: 4/5
Finding which paper note or draft said what, across years of folders, is a real recurring waste of time, weekly. Marking-related admin and email follow-ups are also frequent. It is a real problem; it is not painful enough that I would tolerate a babysitting tool.

## 8. Perceived value of the proposed solution: 3/5
Valuable: local by default, per-folder cloud switch, source tags on answers, the "NOT FOUND IN YOUR FILES" idea, the "what it knows" page with erase. Not valuable yet: the invented PDF, wrong "not found" labels, and the email flow that trapped the next question. Interpretation: the value rests on the citation behaviour being reliable, which I saw in one of three tries.

## 9. Adoption likelihood: might try
I would try it on a folder of old lecture notes and papers, not on student work, until I had tested it with citations I know are wrong. What would change my mind to "would use": it never names a file that is not there, it quotes the exact sentence it relied on, it can show the page or line, and email drafting works without asking for an address first. What would make me avoid it: one more fabricated reference.

## 10. Concerns, objections and suggestions
- Hallucinated citations: it cannot verify an outside reference (Smith 2019) and should say so plainly, not invent a file.
- Student privacy: I want a clear, visible statement of which folders can use a cloud model, and a warning if a folder with submissions is switched to cloud. Gemini showing "Key saved" at first sight made me ask who saved it.
- Email: I want a draft shown for review without needing the recipient first; and an easy "cancel" that does not swallow my next question.
- Academic integrity: it should not offer to judge or rewrite student work as if it were verified.
- Suggestion: show exact quoted text with the line, not just "file:1".

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: **agree**. Knowing it can only see chosen folders and that cloud is off per folder is what makes me willing to put submissions near it at all.
(b) More willing to use it: **partly**. Willing to try it, but a model that makes up a file name loses that goodwill quickly; the boundary solves the access worry, not the accuracy worry.
(c) Does the limit cost too much usefulness: **disagree** (it does not cost me much). All my material is in a few folders. I did not hit the folder limit as a problem.

Short questions:
- Are people really losing time to interruptions and routine file work: **agree**. Finding things in old notes and chasing email is routine for me.
- Is wanting broad access a real barrier for me: **agree**. I would not give a tool my whole disk because of student data.
- Would I accept one mistake if undo is easy: **partly**. For file moves yes. For a wrong citation, no, because I might not notice. I did not test undo.
- Ask before every change or act and let me undo: **partly**. Ask first for anything that sends or moves student files; for simple reading no need.
- Abilities I would actually use: question-answering with sources over my notes and papers, email drafts for review, maybe tidy-up of the downloads folder. Probably not voice.
- What would make setup too much effort: needing an app password for Gmail and 2-step setup is already borderline; any need to retype folder paths or fix the model myself would be too much.

## 12. Implementation limitations I ran into
- Invented a non-existent file ("Ali_Assignment_2.pdf") and said it was a PDF it could not read.
- Marked content that was in the file as "NOT FOUND IN YOUR FILES".
- Email draft required an address first; the pending prompt then answered my next, unrelated question ("I still need an email address") instead of the question asked.
- Source tags show only `file:1`, not a useful location.
- The Work page showed repeated "Hi again. Let's pick up where we left off" lines.
- Replies took about 40 to 45 seconds each (shared model).
- Folder add via the browse box needed me to type the path; the first status after add was not obvious.
- I did not test undo, voice, web search or remote access.
