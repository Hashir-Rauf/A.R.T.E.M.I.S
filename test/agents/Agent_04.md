# Agent_04 report

(Simulated participant. Reactions below are plausible reactions of the persona, not facts about real people.)

## 1. Agent ID and persona
Agent_04, app `ua-04`, port 7944. Mariam, 26, master's student writing a thesis.

## 2. Background and relevant characteristics
Folders full of PDFs, reading notes, data exports and draft chapters. I lose a lot of time working out "where I was" after supervisor meetings and breaks. I use a reference manager, and ChatGPT now and then for summaries, but I distrust its citations. Traceability matters most to me: where did this claim come from? Moderately technical. I want help resuming and synthesising notes more than tidying.

## 3. Initial expectations (before using it)
- "Remind you where you left off" and "answer questions about your notes" are the parts that interest me. Tidying is the part I care about least; my folders are messy on purpose and I know where things are.
- I doubt a small local model will synthesise well. I doubt it will give citations I can check. "It shows you what it intends to do" sounds good for edits, but my main need is reading, not editing.
- Limiting it to chosen folders is fine, because my thesis lives in a few folders. It would bother me if my reference manager library or my PDFs sit outside them.
- Today I do this by hand: re-reading my last notes, scrolling file dates, and searching with the OS. ChatGPT is only for rough summaries.

## 4. Interaction and exploration summary
I started the app with a "notes" test folder (five generic lecture files) and added four thesis-style files of my own. These were a Chapter 2 draft, a supervisor meeting note with three actions, and reading notes on Smith 2019 and Lee 2021, which disagree.

My first attempt to add the folder failed, because I typed the path into the wrong box. The app said "Type or browse to a folder first", and my first two questions were answered as if no files existed. After I found the right box and re-added the folder, it worked.

Then I asked it to:
- resume my thesis;
- sort my notes into support and contradiction, with files named;
- ask about something not in my files;
- draft a paragraph with sources.

Then I pressed "Suggest a tidy-up", which only showed a preview that I did not approve. I looked at the What it knows tab and at Settings. I did not try undo, voice, the cloud models, email or remote access.

## 5. Observed behavioural data

| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app; read the screen | Local-only reassurance banner ("Everything is stored on this computer. Nothing has been sent anywhere."). Voice greeting began on its own. | Interest. |
| 2 | Typed the folder path into the Folders tab and pressed Add folder | Nothing visible happened at first. A red message said "Type or browse to a folder first", although I had typed a path. | Hesitation. Repeated: the first run went into the wrong field. |
| 3 | Asked "Where did I leave off with my thesis? What did my supervisor ask me to do?" while the folder was not yet added | It said it had not been shown any files and asked me to point to a folder. | Hesitation, but it did not make things up. |
| 4 | Asked the same question after re-adding the folder correctly | It answered: rewrite section 2.3, rerun the regression on cleaned data, send Ch2 by 15 Nov, with `supervisor-meeting-2026-10-28.md:1`. It also said Ch2 claims sleep loss reduces working memory and has a TODO about Lee 2021, with `thesis-ch2-draft.md:1`. | Strong interest. This is exactly the "resume" use. |
| 5 | Asked which notes support or contradict the claim, naming files | It put Smith 2019 (12% drop, p.14) as support and Lee 2021 as "no significant effect", with sources `reading-notes-smith2019.md:1`, `reading-notes-lee2021.md:1` and `thesis-ch2-draft.md:1`. It was a bit muddled: it said contradictions were "not explicitly stated", then gave Lee anyway. | Interest and mild hesitation. |
| 6 | Asked what Lee 2021 said about attention "and what page", and what "Jones 2020" found (a paper that is not in my files) | Lee: "reported an effect on attention" with `reading-notes-lee2021.md:1`. It did not give the page (my note says p.7). For Jones it said "NOT FOUND IN YOUR FILES I could not find what Jones 2020 found." | Strong interest in the honest "not found". Hesitation about the missing page. |
| 7 | Asked for a short paragraph comparing Smith 2019 and Lee 2021, with a source for each statement | Two sentences, each followed by its source file. They were accurate to my notes: Smith 12% drop, Lee no effect on working memory but an effect on attention. | Interest. |
| 8 | Pressed "Suggest a tidy-up" | It showed "Would move 9 files and create 1 folder. Nothing is deleted." It would have moved all nine files, including my thesis notes. I did not approve it. | Hesitation. I abandoned it, because I do not want my thesis files moved. |
| 9 | Opened the What it knows tab | There is a folder chooser, Show files and Check for changes, per-folder and per-file Forget, and "Erase everything ARTEMIS knows". It says Forget never deletes files and the activity log is kept. I did not choose a folder or look at the contents. | Interest in principle. I did not look further. |
| 10 | Read Settings | Local model (gemma4:e4b) in use. Cloud services listed, with Gemini showing "Key saved". The page says a cloud model is only used for folders I allow, and keys go to the Windows Credential Manager. I did not touch keys or email. | Interest, with a small worry about the "Key saved" for a cloud service. |

Questions I asked: 4 substantive ones (rows 4-7). Features skipped: undo, "What changed", "Repeated tasks", voice and microphone (it said no microphone found), cloud models, email, remote access, approving any change, leaving a note for next time, reading the chat sidebar history.

## 6. Feedback about the research idea (persona's words)
For my work, the "bounded" part matters less than the "show me where it came from" part. Each claim came with a file name. That is the first time a chatbot has made me feel I could check it. The fact that it said "not found in your files" for Jones 2020, rather than inventing something, is worth more to me than any speed. Limiting it to my thesis folders feels natural, because that is where my work is. The "ask before it changes anything" part is irrelevant to what I actually used it for, which was reading and summarising. I would rather it never touched my files at all. I would accept the limit, but I would not choose the product because of it.

## 7. Perceived problem relevance: 4/5
Re-finding where I was after a meeting or a break is a real, regular cost, probably several times a week, and sometimes half an hour each time. It is not a crisis, just a constant drain. Routine tidying is a 2/5 problem for me.

## 8. Perceived value of the proposed solution: 3.5/5
Valuable: resume from my own notes, cross-note synthesis, source file shown with every statement, "not found" when it does not know, everything stays on my computer. Not valuable: the tidy-up, which wants to move my thesis files. The source reference is only a file name and line 1 (`:1` every time), so I cannot jump to the page or the passage. For a thesis I need the page or quote. Also, one answer left out the page number that was in my note.

## 9. Adoption likelihood and reasoning
**Might try.** I would use it as a "where was I" and "what do my notes say" tool on my thesis folder. What would move me to "would use": citations that point to the exact line, page or quote; reading my PDFs and reference manager exports, not just markdown notes; and consistent answers on longer notes. What would make me avoid it: wrong summaries that sound confident, or any need to retype folder paths and fix setup every time.

## 10. Concerns, objections and suggestions
- Source pointers must be exact (page and line, ideally a quote), or I still have to re-check everything myself.
- Check that it also reads PDFs and exports. I did not test that.
- The tidy-up proposing to move every file, with no sense of what the files are, makes me nervous even with an approval step. Show me a before/after list and let me exclude files.
- A small local model may miss things. Tell me when coverage is partial (which files it read).
- A single folder path field with an unclear error was confusing.
- Give an option to have it write a "where I left off" summary I can paste into my own notes.

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: **partly**. I trust it more because it is confined and local and shows sources, but the sources do most of the work for my trust, not the confinement.
(b) More willing to use it: **partly**. Yes for my thesis folder. The limit would not stop me, but it is not my reason to try it.
(c) Does the limitation cost too much usefulness: **disagree** (it does not cost me too much). My work is inside a few folders. It would cost me if my references were stored elsewhere.

Short questions:
- Are people really losing time to interruptions and routine file work? **Agree** for resuming and re-finding (my own case). **Partly** for routine file work, which is less my problem.
- Is wanting an assistant with broad access a real barrier for me? **Partly**. I would not give a chatbot my whole disk, but I rarely wanted it to.
- Would I accept one mistake if undo is easy? **Partly agree** for file moves. **Disagree** for a wrong claim in my thesis, since undo does not help there. I did not test undo.
- Ask before every change, or act and let me undo? **Ask first**, for anything that changes my files. For reading and answering, no asking is needed.
- Which abilities would I actually use? Resume, ask-the-notes with sources, and drafting a paragraph with sources. Not tidying, not voice, not email.
- What would make setup too much effort? Retyping paths, unclear errors like the one I hit, and having to convert my files to a special format before it can read them.

## 12. Implementation limitations I ran into
- The Add folder error was unclear. My first question was answered as if I had no files, and it gave no hint that adding the folder had failed.
- References always end in `:1`, so they do not point to the actual place in the file.
- It omitted the page number (p.7) that was in my Lee note when I asked for it.
- The "support" answer was awkwardly worded ("is found in, where Smith 2019 noted...").
- Replies took about 30-50 seconds.
- Voice started by itself and reported no microphone found.
- The Gemini "Key saved" entry was present in a private copy I did not set up.
- A small mistake in my own test script meant the chat shows earlier no-file answers above the later good ones. That was not the app's fault.
- Not tried: PDFs, undo, approving a change, the saved-chat sidebar, remote access.
