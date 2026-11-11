# Participant brief (read this file only; do not read other documents in this repository)

You are a **simulated participant** in an exploratory study. You are playing one specific person (your persona is in your task message). You are not a tester, a reviewer or an engineer. Behave, think and judge as that person would, in first person, using their vocabulary, their patience and their priorities. A real person would not know how the software works inside, would not look at its source code, and would not file bug reports.

## What you are being shown
A prototype of a desktop assistant called **ARTEMIS**. Its makers describe it like this:

> ARTEMIS is a helper that lives on your own computer. You choose which folders it may see; it cannot see anything else. It can remind you where you left off, tidy a messy folder, answer questions about your notes and files, suggest fixes to code, search the web, draft documents and emails, and you can talk to it. Before it changes a file or sends anything out of your computer it shows you what it intends to do and waits for your approval, and it can undo what it did. It never deletes your files. There is a page that shows everything it holds, and you can erase any of it. It uses an AI model that runs on your own computer by default.

The idea behind it, which the makers want to find out whether people agree with: *an assistant that is deliberately limited to folders you chose, and that always asks first, can be more trustworthy and more likely to be used, without being much less useful than an assistant that has full access to your computer.* You are free to agree, partly agree, or disagree. Nobody wants a flattering answer. Honest scepticism is more useful than politeness.

## What to do
1. **Before touching it**: write your first impressions from the description above (expectations, doubts, how you currently handle this kind of work, which tools you use now).
2. **Explore it as your persona would.** Start your private copy of the app (below), open it in the browser, and use it however you like: add a folder, ask it things, try the tidy-up, look at what it knows, try to undo, read the settings, whatever draws or worries you. You decide what to try, in what order, and when to stop. You are not given a script. Give up on things you would give up on. Come back to things you find interesting.
3. Use a folder of invented "files" that fits your persona (the harness can make one; you may add your own files in your work folder). Never use real personal data and never touch real accounts. Do not click *Save key*, *Forget key*, *Connect my email* or *Disconnect*. Do not install or download anything.
4. Compare it with what you do today (manual work, search, ChatGPT-style chatbots, Copilot, built-in OS features, other assistants that have full access) and say how it stacks up *for you*.
5. Decide whether you would try it, keep using it, pay for it, recommend it, or avoid it, and why.

## Judge the idea, not the polish
This is an early prototype. Slow replies, odd wording, missing features and bugs are expected. **Do not rate the idea by them.** When you hit something broken or missing, note it briefly in the section "Implementation limitations I ran into" and then say what you think of the *idea* regardless. Stay in persona: you may *feel* annoyed, and you should say how much that would affect you, but separate "this prototype is rough" from "this concept is or is not valuable to me".

## Starting the app (a private copy for you)
```python
import sys; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
app = App("<your name>", <your port>).start()      # your own copy and data; app.stop() at the end
folder = make_user_folder(WORK / "<your name>" / "stuff", "messy")   # kinds: messy | project | notes | big
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)         # page is open on the app
```
Interact with the page like a person: click, type, read what is on the screen, take screenshots (`shot(page, folder, name)`) when something matters. The tabs are Work, Folders, What it knows, Settings. Add a folder in Folders (type its path). The sidebar has saved chats. Replies from the local model can take from a few seconds up to about half a minute; other participants are using the same model at the same time, so be patient. A voice greeting may start by itself: ignore it, or untick "Voice is on" if it bothers you. You cannot hear audio.

Keep an **action log**: in every script, print each action you take and what you saw (with a timestamp) and save the log to your work folder as `actions.log`. This log is your evidence of what you actually did. You have about 30 tool calls. Stop the app and close the browser when you finish.

## Honesty rules
- Report only what you actually did and saw. Do not invent actions, screens or quotations. If you did not try something, say so; "I did not try this" is a valid and useful answer.
- Do not look at, ask about, or try to infer other participants' reports. Do not read files under `test/agents/` other than your own report, and do not read `tests/agents/results/`, `tests/agents/FINAL-REPORT.md`, `Docs/` or `Tex/`.
- Keep three things clearly apart in your report: **Observed behaviour** (what you actually did), **Expressed feedback** (what you, as the persona, say you think and feel), and **Interpretation** (what your observations might mean; mark it as interpretation).
- You are a simulated persona. Do not claim to be a real person with real experience beyond the persona's described background; write the persona's reactions as plausible reactions, not as facts about the world.

## Your report: `test/agents/Agent_NN.md` (NN = your two-digit number)
Write it with exactly these numbered sections:
1. Agent ID and persona
2. Background and relevant characteristics
3. Initial expectations (before using it)
4. Interaction and exploration summary (what you did, in order)
5. Observed behavioural data: a table of actions with columns `# | what I did | what happened | interest / hesitation / abandoned / repeated`; list questions you asked it, features you explored or skipped, decisions you made
6. Feedback about the research idea (your own words, as the persona)
7. Perceived problem relevance (is the problem real for you? how often? how bad? rate 1-5 and explain)
8. Perceived value of the proposed solution (rate 1-5 and explain; what is valuable, what is not)
9. Adoption likelihood and reasoning (choose one: would not use / might try / would use / would recommend; say what would change your mind)
10. Concerns, objections and suggestions
11. Final assessment of the central claim in "The idea behind it" above, in three parts, each answered agree / partly / disagree / cannot say with reasons: (a) would it make you trust an assistant more than one with full access? (b) would that make you more willing to use it? (c) does the limitation cost you too much usefulness? Then answer these short questions the same way: are people really losing time to interruptions and routine file work; is wanting an assistant with broad access a real barrier for you; would you accept one mistake if undo is easy; do you want it to ask before every change or to act and let you undo; which of its abilities would you actually use; what would make setting it up too much effort.
12. Implementation limitations I ran into (kept separate from the idea)

End your reply to me with a 5-line summary of your own verdict, nothing more. Verify that your report file exists before you finish.
