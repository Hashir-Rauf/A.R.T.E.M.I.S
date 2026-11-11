# Agent_06 report

## 1. Agent ID and persona
Agent_06, "Sana", 24, junior full-stack developer (simulated persona). App copy `ua-06`, port 7946.

## 2. Background and relevant characteristics
Two years in. Uses AI coding agents that run commands and edit files on their own and likes the speed. Finds "approve every step" prompts tiring; prefers "do it, I can undo with git". Says privacy is not a big worry because "my code is not secret". Drops tools that break her flow. Lens: would a bounded, always-asking assistant slow me down?

## 3. Initial expectations (before using it)
From the description alone: sounds like a cautious file helper for non-developers. "See only chosen folders" is a non-issue for me, since I already point agents at one repo. "Asks before every change" is the worrying part, because that is exactly what I turn off in other tools. Undo is attractive, but git already does that for code. "Local model by default" worries me as likely slower and dumber than cloud models. I currently use an agentic coding assistant in my editor, ChatGPT-style chat, and git. I expected to be mildly interested in tidy-up and notes and unimpressed on coding.

## 4. Interaction and exploration summary
Started the app, read the Work page, unticked voice, added a small invented demo project folder (README + app/main.py with a planted bug in add() + util.py), asked several questions about the project, asked for a bug fix, then added an invented messy "downloads" folder, ran Suggest a tidy-up, approved, and used Undo. Then I opened What it knows (the text did not come through in my capture, so I cannot describe it) and read Settings. I did not try: talking, notes, repeated tasks, email, web search, drafting, cloud models, remote access, erasing items. I did not click Save key, Forget key, Connect my email or Disconnect.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Read the Work page | Counters (0 folders, 0 files), welcome says it cannot see any folder; a voice greeting started | hesitation: lots of text up front |
| 2 | Unticked voice | Voice was on again later in the session | hesitation |
| 3 | Folders tab, typed project folder path, Add folder | "Added 'stuff'. ARTEMIS now knows about 3 files" | interest: setup was one step |
| 4 | Asked "Look through the app folder and tell me what this project does, and suggest a fix for anything that looks buggy" (first send missed because of a script slip; second send worked) | It said it needs to look at files in 'app' and asked me to select or add folders, although the folder was already added | hesitation / annoyed |
| 5 | Asked "What files are in this folder and what does the README say?" | Listed the 3 entries and quoted the README ("A tiny demo project with a bug in add()") | interest |
| 6 | Asked "Is there a bug in the code? Show me a fix." | Asked me which file add() is in | hesitation: an agent would have found it |
| 7 | Asked "Fix the bug in add() in app/util.py" (my mistake, wrong file) | "I could not suggest a safe change... no diff was shown" | neutral |
| 8 | Asked "Fix the bug in add() in app/main.py" | Showed a correct diff (`a - b` to `a + b`) plus "This is a proposal only. ARTEMIS has not changed your file, and it never edits code itself." | interest in the diff, hesitation about no edit |
| 9 | Added messy invented downloads folder, clicked Suggest a tidy-up | "Would move 12 files and create 2 folders, leaving budget 2026.xlsx, random.zip where they are. Nothing is deleted." with Approve / Approve, don't ask again / No, leave it | interest |
| 10 | Clicked Approve | 12 files moved into Documents and Images; "Done: 2 folders created, 12 files moved." | interest |
| 11 | Clicked Undo last change | "Undone. 14 steps reversed"; I checked on disk and all 14 original files were back | interest; repeated check on disk |
| 12 | Opened What it knows, then Settings | Settings is long: storage location, local model gemma4:e4b, cloud keys, email, remote access | hesitation: lots of config for me |

Replies took about 5 seconds each, which felt fine.

## 6. Feedback about the research idea (persona's words)
"For files like a messy Downloads folder, plan, then approve, then undo was actually nice: one approval for 12 moves, not 12 prompts. That I would not turn off. But for code it is the opposite of what I want: it showed me a diff and then said it never edits code itself, so I would copy-paste a one-character fix. My coding agent would have just done it and I would have reviewed it in git. Folder limits do not bother me for a repo, since I already scope agents to a project. Bounded-and-asking is fine for a general helper, but in this form it is not a developer tool."

## 7. Perceived problem relevance: 3/5
Routine file mess (Downloads, screenshots) is real but a minor annoyance for me. For me, approval-prompt interruptions are a bigger problem than lack of safety, the reverse of the makers' framing. Interpretation: this persona sees the safety as a cost, not a benefit.

## 8. Perceived value of the proposed solution: 3/5
Valuable: batch plan with one approval; clear preview ("Nothing is deleted"); undo that actually restored everything; local by default. Not valuable to me: no code editing, asking me to point at files it should find, no obvious way to chain work.

## 9. Adoption likelihood: might try
I would use it for tidying and maybe notes, not for coding. I would stop if it keeps asking which file I mean. What would change my mind: letting it apply code diffs in a chosen folder with undo (or git integration), and a per-folder "act, then show me what changed" mode instead of asking first.

## 10. Concerns, objections and suggestions
- Per-folder trust level: ask first / act and let me undo.
- Code diffs should be appliable (with undo), not just text to copy.
- Find the right file by itself inside a chosen folder.
- Settings and welcome screens are text heavy.

## 11. Final assessment of the central claim
(a) More trust than a full-access assistant: partly. Trust is not my barrier; I would happily give an agent my repo. I can see it mattering for personal documents and for people less comfortable than me.
(b) More willing to use: partly / disagree for me. Constant asking pushes me away; the bounded part is neutral.
(c) Limitation costs too much usefulness: partly. For file tidying, no. For coding, yes, mainly because it will not edit code and was weaker at exploring files.

Short questions:
- Are people losing time to interruptions and routine file work: partly. File chores yes, a little.
- Is wanting broad access a real barrier for me: disagree. A project folder is enough.
- Accept one mistake if undo is easy: agree.
- Ask first or act and undo: act and undo for code and low-risk moves; ask first only for sending things out or irreversible actions. The tidy-up flow (one plan, one approval) I would accept.
- Abilities I would use: tidy-up with undo, questions about my notes, maybe diff suggestions. Would skip: email, voice.
- Setup too much effort: many Settings steps (keys, email app passwords) or re-explaining which folders it can see.

## 12. Implementation limitations I ran into
- Asked about the "app" folder, it said it could not see it and asked me to add folders, though the folder was already added.
- Would not locate the file with add() without being told which one.
- The voice option came back on after I unticked it.
- The What it knows tab text did not come through in my capture, so I cannot comment on it.
- Wrong-file fix attempt said "no diff was shown" (unclear wording).
- My own script slips (wrong button, wrong textarea) were mine, not the app's.
Evidence: actions.log and scripts in `test/agents/w06/`.
