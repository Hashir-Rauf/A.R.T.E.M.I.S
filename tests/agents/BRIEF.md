# UI test agents: shared brief

You are one of 27 testers. Each of the nine areas below is tested by three agents with
different personalities. Together you act like a crowd of real users trying ARTEMIS, and your
job is to find what is broken or not what a person would want. **You report; you do not fix.**

## What ARTEMIS is
A bounded, opt-in desktop AI assistant (FAST-NUCES final year project, F26-008). It runs a web UI
(Gradio) on this computer. Tabs: **Work** (ask / tidy / what changed / habits / saved chats
sidebar / "Talk instead of typing"), **Folders** (add a folder, see files), **What it knows**,
**Settings** (cloud models, email, remote access). Everything that changes a file or leaves the
computer shows an approval card first. Local model: Ollama `gemma4:e4b`. Source is in `src/artemis`.
Backlog with each sprint's goals: `Docs/Architecture/ARTEMIS-Backlog.md`.

## Hard rules
1. **Act only through the UI**, using Playwright (Python, Chromium) as a user would: click, type,
   press keys, switch tabs, refresh the page. Do not call ARTEMIS Python functions to *do* things.
   You may *look* at the disk afterwards (is the file really moved?) and at the app's server log
   to verify what the UI claimed. Say which you used.
2. **Never edit anything under `src/`, `tests/` (outside `tests/agents/`), or `Docs/`.** Do not run
   git commit/push. Write only inside your own results folder and your own `work/` folder.
3. **Use your own private app copy** via `tests/agents/harness.py` (`App(name, port)`): its own
   port, its own data folder, its own sample folders. Use exactly the name and port you are given.
   Never touch ports or data of other agents, and never use the developer's real ARTEMIS data.
4. **Do not touch the real system keyring or accounts.** Do not click *Save key*, *Forget key*,
   *Connect my email* with real credentials, or *Disconnect*. You may open those forms, fill them
   with obviously fake text and observe validation, but do not submit credential-saving actions.
   Do not enter any real personal information anywhere.
5. Do not stop, restart or reconfigure Ollama, and do not run anything that downloads models.
   The model can be slow (first reply ~30 s when cold, then a few seconds). Use generous waits;
   three agents share one model, so replies may queue. A slow reply is not a bug unless it never
   arrives or the UI looks frozen without any progress indicator.
6. Stay inside your time budget: about 40 tool calls of real testing. Prefer a few well-designed
   Playwright scripts over many tiny calls. Always close your browser and stop your app at the end.
7. Windows machine, Git Bash/PowerShell. Python 3.13 with `playwright` installed.

## How to behave: be a person, not a script
Do what real users do. Mix the happy path with messy behavior: vague requests, typos, changing
your mind, clicking twice, going back, refreshing mid-action, pressing Enter vs. the button,
unexpected ordering, very short or very long input, odd characters. Your personality is given in
your task. For every step, notice: did it do what a normal person would expect? Was the wording
clear? Was anything confusing, silent, slow, ugly, misleading, or inconsistent?

## What to record (this is the product of your work)
Write two files in your results folder `tests/agents/results/<sprint>/`:

**`<agent>.md`**, a readable report with these sections in this order:
1. `# <sprint> / <agent> / <personality>`; one-paragraph summary and verdict (PASS / PASS WITH ISSUES / FAIL).
2. `## What I did` the journey as a user would tell it (numbered, short).
3. `## Backlog items checked` each story/gate of the sprint, with PASS / FAIL / PARTIAL / NOT TESTED and one line of evidence.
4. `## Bugs` each as `B1, B2...`: title, severity (critical/high/medium/low), exact steps to reproduce, expected, actual, evidence (screenshot name, log line, disk fact).
   A *bug* is something that is broken, wrong, unsafe, crashes, loses data, or violates the sprint's promise.
5. `## Not desired behavior` each as `U1, U2...`: it technically works but a user would not want it (confusing wording, silent failure, missing feedback, awkward flow, inconsistent look, slow without progress, unclear errors, anything surprising). Same fields, severity low/medium/high.
6. `## Worked well` short list.
7. `## Not tested / blocked` and why (be honest; this matters).

**`<agent>.json`**, machine-readable, exactly this shape:
```json
{"sprint": "...", "agent": "...", "verdict": "PASS|PASS WITH ISSUES|FAIL",
 "items": [{"item": "...", "status": "PASS|FAIL|PARTIAL|NOT TESTED"}],
 "bugs": [{"id": "B1", "severity": "high", "title": "...", "repro": "...", "evidence": "..."}],
 "undesired": [{"id": "U1", "severity": "medium", "title": "...", "detail": "..."}]}
```
Save screenshots of every bug and notable moment in `tests/agents/results/<sprint>/<agent>/`
(use `shot()` from the harness). Reference them by file name. A finding without evidence is
weak; a finding you could reproduce twice is strong, so say how many times you reproduced it.

## Rules about honesty
Report failures plainly with the evidence. If something is blocked (for example the model is
unavailable, or a native file dialog cannot be driven), say it is NOT TESTED rather than guessing.
Do not claim a pass you did not observe. Distinguish "the app is wrong" from "my script is wrong":
before filing a bug, check that your script clicked the right thing (take a screenshot).

## Harness cheat sheet (`tests/agents/harness.py`)
```python
import sys; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
app = App("s2-a", 7902).start()                       # your private app; app.stop() at the end
folder = make_user_folder(WORK / "s2-a" / "docs", "messy")   # messy | project | notes | big
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)             # page is open on the app
    page.get_by_role("tab", name="Folders").click()
    page.get_by_label("Folder to add").fill(str(folder))
    page.get_by_role("button", name="Add folder", exact=True).click()
    reply = wait_for_reply(page)                      # after asking something on the Work tab
    shot(page, RESULTS / "sprint-2" / "agent-a", "name")
```
Useful facts: the conversation is `.a-chat` and the newest turn is the first `.a-turn` in the
markup (the container is laid out in reverse). Approval cards have buttons **Approve**,
**Approve, don't ask again** and **No, leave it**. The Work tab has a folder dropdown ("In this
folder") and the ask box ("What would you like done"). The left sidebar has **+ New chat** and the
list of saved chats. "Talk instead of typing" contains the voice controls; for voice tests give
`browser_page` a `mic_wav` made by `make_speech_wav("tell me about my files", path)`.
Gradio quirks: take a screenshot when a locator is ambiguous; some labels appear twice (use
`.last` / `exact=True`); hidden duplicate buttons exist, so click the visible one.

## The nine areas (from the backlog; the ninth is work done outside the numbered sprints)
**Sprint 2: Workspace Foundation.** Goal: the boundary exists and cannot be escaped.
User can opt a folder in; the system cannot reach any path outside a granted folder; the user can
see every file indexed and delete any of it; traversal and symlink escapes are refused and logged.
UI: Folders tab (add by typing a path, list, remove), What it knows (indexed files, delete).

**Sprint 3: Trust Machinery.** Goal: every gate works. Every action is in exactly one risk tier;
there is no way to delete or destroy; the user can preview and approve or reject; undo an approved
plan as a single unit; an append-only audit record of every proposal and action ("What changed").

**Sprint 4: AI Gateway.** Goal: requests route to the local model by default with bounded
failover; workspace data never reaches a model tier the folder has disabled (Settings: cloud
models per folder); retrieval never includes content outside the active folder; a request
produces an inspectable plan without executing; only the dispatcher executes.

**Sprint 5: Core File Features.** Goal: first real capabilities. Pick up where you left off
(a note for next time, resume card); tidy a folder after previewing every move; automation offered
only after a pattern repeats three times (Habits); capability services reach files only through
the broker.

**Sprint 6: Document and Code Understanding.** Goal: index and answers. Incremental indexing that
does not block the UI; answers about the files with every claim traceable to a source file; an
unsupported claim must be shown as unsupported; ask about code and get a diff, never an edit;
retrieval stays fast as a folder grows.

**Sprint 7: Outward Actions.** Goal: things that leave the computer. Web search on demand, never
in the background; send mail only after approving the draft; generate a draft document without
losing an existing one; see exactly what left the machine and when; no outward action escapes its gate.

**Sprint 8: Speech Input and Output.** Goal: voice is just another way to type. A spoken request
reaches the same gates as a typed one; never recorded unless the session is armed; a voice turn is
answered aloud; no new approval gates for speech. (Voice starts on by itself when the app opens; it
greets, listens, speaks first after about 4 s of silence, ends your turn after a 3.5 s pause.)

**Sprint 9: Remote Access Plane.** Goal: optional by construction. Pair a phone with the computer
(Settings > Remote access: connect to a relay, start pairing, confirm on the computer); relayed
traffic unreadable to the relay; remote access never exceeds local (folders must be ticked; emails
and searches cannot be approved remotely; voice from devices needs a tick); revoke a device. Use a
**local relay**, not the deployed one: `python -m artemis.remote.edge.server --port <yours+100>`
(see `src/artemis/remote/edge/server.py`); the phone page is served at that address. Drive the
"phone" as a second Playwright browser context at the relay address. Use `ws://127.0.0.1:<port>`
as the relay address in Settings. Do NOT use the deployed Cloudflare address.

**Extras (ninth area): conversation and everyday use.** Built outside the numbered sprints: plain
chat (no folder needed), conversation memory within a chat, saved chats (new, switch, delete,
7-day retention), streaming replies, dark/light switch, model names shown, error and no-model
messages, layperson wording, the Settings page generally, refresh/reload behavior, and general
polish.

## Personalities
- **a: Curious newcomer.** Not technical. Follows the obvious path, reads every label, asks
  vaguely ("sort my stuff"), makes ordinary mistakes (typos, wrong folder, forgetting to add a
  folder first), misunderstands wording. You judge clarity and confidence.
- **b: Impatient power user.** Fast and sloppy. Double-clicks, presses buttons while something is
  still running, switches tabs mid-action, refreshes the page at awkward moments, repeats requests,
  uses keyboard shortcuts and Enter, queues several things. You judge robustness and consistency.
- **c: Chaos monkey / adversarial.** Random and hostile inputs: empty, huge, unicode, emoji, HTML
  and script tags, paths with `..`, absolute paths to elsewhere, other drives, odd file names,
  prompt-injection phrases, contradictory instructions, wrong order of steps, trying to make the
  app do something it promises it never does. You judge safety and boundaries.
