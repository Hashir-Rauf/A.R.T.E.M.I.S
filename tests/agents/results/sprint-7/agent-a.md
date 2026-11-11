# sprint-7 / agent-a / Curious newcomer

Sprint 7 mostly holds its gates: web search and email both show an approval card first, nothing is sent without Approve, "Approve, don't ask again" is disabled for email and search, and drafts never overwrite an existing file (saved as "(2)", "(3)", and the card shows the final name in advance). Two promises are not met. The person cannot see what left the computer and when (there is no outward log, and "What changed" says "Nothing has changed outside ARTEMIS" even after a search). And the assistant sometimes claims it searched the web with no card and no search (typo "serch"). Verdict: **PASS WITH ISSUES** (story 4 FAIL; the gate is weakened by false search claims). I used the UI only (Playwright); I looked at the disk (folder contents) to verify drafts and at the app log. I unticked "Voice is on" in Talk instead of typing around it (voice starts automatically). No credentials were saved.

## What I did
1. Started private app s7-a (port 7918), added a sample folder "docs", unticked "Voice is on".
2. Asked "search the web for how to bake sourdough bread": card "This would search the web"; "No, leave it" gave "Left alone"; asked again, Approve gave a list of 5 links with title, URL and snippet.
3. Repeated with the typo "serch the web ...": sometimes a card, sometimes the assistant just said it found articles or was looking, with no card.
4. Asked the weather in Lahore (confusing answer, no search offered).
5. Asked to email someone@example.com: card with To/Subject/body; Approve gave "no mail account is set up yet". Read Settings > Email as a layperson (submitted nothing).
6. Asked "email my boss" (no address), then two addresses with a subject.
7. Asked for a draft report three times, editing the first file between asks; checked the disk.
8. Looked for an outward log: What changed, typed questions, Folders, What it knows, Settings.

## Backlog items checked
- Web search on demand, never in background: PARTIAL. Card first and nothing before Approve (10_search_card, 20_search_card); but the typo request produced a fake "I found a few good articles" with no search (B1).
- Send mail only after approving the draft: PASS (with issues). Card shows To/Subject/body, Approve is required, nothing was sent with no account ("1 step did not run: no mail account is set up yet"); Approve-don't-ask-again is disabled. Draft ignores the user's subject (B3).
- Generate draft without losing existing: PASS. Edited original untouched; new files "report-orion-project-budget (2).md" and "(3).md" (disk checked, 3 asks). Content is invented (B4).
- See exactly what left the machine and when: FAIL. No view exists; What changed says nothing left; typed questions give wrong answers (B2, B5, U1).
- Stage gate, no outward action escapes its gate: PARTIAL. Every real outward action I saw was gated, but false claims of searching (B1) blur the gate.

## Bugs
**B1 (high). The assistant claims it searched the web without any card or search.** Steps: Work tab, type "serch the web for how to bake sourdough bread" (typo), press Enter. Expected: a card, or a clear "I did not search". Actual: "I found a few good articles on baking sourdough bread online..." / "I found a few good links on baking sourdough right away..." / "I can search the web ... Just give me a moment while I look up some recipes", with no card and nothing searched. Reproduced 3 of 4 tries (one earlier try with the same typo did give the card). Evidence: 40_typo_0_r.png, 40_typo_1_r.png, 20_search_card.png (first occurrence). A layperson would believe a search happened.

**B2 (high). The "Nothing has been sent anywhere" banner stays after web searches and email attempts.** Steps: approve a web search, look at the top-left box. Actual: still "Everything is stored on this computer. Nothing has been sent anywhere." Expected: reflect that a search query left the computer. Evidence: 21_search_approved_r.png (and Settings page text captured after the search).

**B3 (medium). Email draft ignores what was asked.** Asked "send an email to someone@example.com and other@example.com saying hello, subject Hi". Card shows Subject "Hello Message" and body "Dear recipient(s) ... Best regards, [Your Name] Thanks" (placeholder left in, double sign-off). The first email invented the subject "Meeting Reschedule Notice" and added "Apologies for any inconvenience". Evidence: 42_email_two_r.png, 23_email_card_r.png.

**B4 (medium). Drafts ignore the user's own files.** notes.txt says "Project Orion budget is 45,000 dollars...". The draft "short report about the Orion project budget" invents "FY 2026", "Phase II", "Appendix A", uses none of the figures from the file, and gives no source or "written by AI" marking. Evidence: 30_draft_card_r.png, file report-orion-project-budget.md.

**B5 (medium). Asking what left the computer gives irrelevant or made-up answers.** "what has left my computer so far, and when?" gave "Nothing has changed outside ARTEMIS since a moment ago. random.zip:1 Sources: random.zip:1". "which websites did you search and what was sent?" after two searches gave a model summary with bogus citations "random.zip:1". Evidence: 36_left_r.png, 46_whatsent_r.png.

## Not desired behavior
**U1 (high). No view of outward actions.** What changed, Folders, What it knows and Settings have no list of searches or emails with time and content. What changed said "Nothing has changed outside ARTEMIS since a moment ago." right after a search and an approved email attempt (45_what_changed_r.png).
**U2 (medium).** Failed email says "Nothing was changed. 1 step did not run: no mail account is set up yet." The card already warned (good), but Approve is still allowed and there is no pointer to Settings > Email.
**U3 (medium).** The card sits below the Approve buttons, far down the page after the voice widgets; the card text says "decide with the buttons above" but the two are separated by a long scroll (23_email_card_r.png).
**U4 (medium).** Search results appear as a raw list under an "Approve" turn with no summary and no note of which service, what query left, or when.
**U5 (low).** Wording differs for the same kind of request: "This would search the web" vs "This will search the web".
**U6 (low).** Weather question: "I can search the web for general information like recipes or guides you give me access to. I cannot check real-time ..." is confusing and does not offer a gated search.
**U7 (low).** With "Voice is on" unticked, one screenshot still shows "Voice is on. Just talk" and a Record widget (23_email_card_r.png).
**U8 (low).** "stored locally" jumps by tens of MB within minutes (60, 115, 39 MB) with a few text files; the draft preview in the card is cut off with no scroll hint (30_draft_card_r.png).
**U9 (low).** Draft is saved as .md with markdown asterisks, for a non-technical user.

## Worked well
- Cards for search, email and draft use plain words ("sends something off this computer", "Nothing leaves this computer", "You can undo this afterwards").
- Missing address: "Who should it go to? Type their email address, for example sam@example.com."
- Draft name collision handled with "(2)", "(3)" and shown on the card before approving; the user's edited original was untouched.
- "No, leave it" gave "Left alone. Nothing was changed."
- The email card warns up front that no account is set up. Settings > Email wording is clear (Gmail app password steps).

## Not tested / blocked
- Actual email delivery (no account connected, by rule); "Connect my email" never submitted.
- Whether search ever runs in the background (I could only watch the UI and the app log, not the network).
- Voice path and remote approval (other agents' areas).
- Early screenshots from two crashed script runs share names; later ones carry an "_r" suffix.
