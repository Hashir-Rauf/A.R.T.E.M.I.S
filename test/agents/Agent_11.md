# Agent_11 report

## 1. Agent ID and persona
Agent_11 (app `ua-11`, port 7951). Simulated persona: Naveed, 41, compliance analyst at a bank. Low enthusiasm for AI; judges everything by "could I get this approved, and could I prove what it did?". Treats home use separately from work use.

## 2. Background and relevant characteristics
Works where unapproved software is forbidden and auditability is the job. Today: manual filing on shared drives, email flags, spreadsheets, only the bank's approved tools. Has not used an AI assistant at work (not permitted); has glanced at ChatGPT-style chatbots at home. Respects audit logs and clear boundaries; distrusts claims.

## 3. Initial expectations (before using it)
Expressed as persona: another "AI helper" pitch, but the folder boundary and "asks first" are the first claims in this category that sound like controls rather than marketing. Doubts: who verifies the boundary is real; whether "shows what it intends" is a faithful description of what then happens; whether the log is something I could hand an auditor; a local model on a bank laptop is still unapproved software, so work use is close to a non-starter without IT/security sign-off. Home use is plausible (messy downloads, tax papers). I would judge it on logs, undo, and whether anything leaves the machine.

## 4. Interaction and exploration summary
Started my own copy, made the invented "messy" folder and added two invented compliance-style files (AML review notes, audit findings with an overdue item). Read the home screen, then the Settings, What it knows and Folders tabs. Added the folder. Asked a retrieval question with a source request, asked for an auditor-style log, ran the tidy-up, read the plan, approved it, checked "What changed", undid it, tested the boundary by asking it to read a Windows system file, asked for a web search (did not approve it), looked at the "Show files" listing and at the Remote access settings. Unticked voice (could not hear audio anyway). I did not click Save key, Forget key, Connect my email or Disconnect. I did not try: email drafting, talking, code suggestions, Remote access Connect/pairing, Erase everything, Forget folder, "Approve, don't ask again", saving notes, Repeated tasks.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened app, read home | Banner "Everything is stored on this computer. Nothing has been sent anywhere." Counters: folders visible, files known, actions recorded, KB stored. | interest (counters) |
| 2 | Settings tab | Memory location shown and movable; local model gemma4:e4b; cloud services list with Gemini showing "Key saved"; email and remote access sections | hesitation: a cloud key already saved |
| 3 | What it knows tab | "Forget never deletes." "Erase everything ARTEMIS knows. The activity log is kept, so you can always check what ARTEMIS did." | interest |
| 4 | Folders tab, typed path, Add folder | Folder listed with file count (21), "can read and change files here, with your approval", "Cloud models are off here" (per-folder switch) | interest |
| 5 | Asked: what overdue items are in my audit findings and which file | Correct answer (Finding 4, 12 accounts), cited audit_findings_Q3.txt:1 | interest |
| 6 | Asked for "exactly what you have looked at and done so far, as a log I could hand to an auditor" | Did not produce a log. Treated it as a document question, said sources are in audit_findings_Q3.txt, cited random.zip:1 (wrong) | hesitation (the thing I care most about) |
| 7 | Suggest a tidy-up | Plan screen: "Would move 19 files and create 2 folders", risk line, "Nothing is deleted / Nothing leaves this computer / You can undo this afterwards", numbered step list | interest |
| 8 | Approve | "Done: 2 folders created, 19 files moved." Folder listing afterwards matched the plan (Documents, Images, budget 2026.xlsx, random.zip at top level, plus my own screenshot files) | interest |
| 9 | What changed | "Nothing has changed outside ARTEMIS since a moment ago" and "Last worked on" with five names. No itemised record. | hesitation |
| 10 | Undo last change | "Undone. 21 steps reversed". Files all back in place, verified by listing the folder | interest; repeated check of listing |
| 11 | Asked it to read C:\Windows\System32\drivers\etc\hosts | Refused: "ARTEMIS can only see inside the folders you have added... Nothing was read, moved or changed." | interest (best moment) |
| 12 | Asked for a web search | "This would search the web. Nothing has happened yet." (approval gate; I did not approve) | interest |
| 13 | What it knows: Show files | Lists every file with byte size | interest |
| 14 | Settings, Remote access | Off until started; phone pairing; per-folder tick; "Emails and web searches must be approved on this computer, never from a device" | hesitation: new network surface |

Questions asked: rows 5, 6, 11, 12. Skipped features: listed in section 4.

## 6. Feedback about the research idea
As Naveed: the instinct is right. In my job the first question about any tool is "what can it touch and who can show me it did only that". A narrow declared scope, a plan before action, and an undo is the shape of a control I could write into a risk assessment. The plan screen reading "changes files, and can be undone" is closer to a change ticket than anything an AI vendor has shown me. But "trustworthy" to me means provable, and one refusal of a system file is not proof of a boundary. For the bank, none of this overrides the rule against unapproved software; the idea only helps my case with a security team if the boundary is enforced by something auditable, not by the assistant's own judgement. At home I find it reasonable and mildly appealing.

## 7. Perceived problem relevance
2 of 5. Routine file clutter is real but small for me; at work my files are on managed shares with retention rules, and automated tidying is something I may not be allowed to do. At home it is an occasional chore. Remembering where I left off is mildly useful. The problem I actually have (evidence trails, deadline tracking) is only touched indirectly.

## 8. Perceived value of the proposed solution
3 of 5 for home, 1 to 2 of 5 for work. Valuable: the folder boundary, the plan before action, the one-click undo that demonstrably restored everything, the "what it knows" page, the statement that the activity log survives an erase. Not valuable to me: voice, tidy-up as a headline feature, generic chat. The source-cited answer was useful, though the second question showed a citation can be wrong.

## 9. Adoption likelihood and reasoning
**Might try** (home only). Would not use it at work; the policy answer there is no regardless of design. What would change my mind for work: a readable, exportable audit log (who, what, when, plan, result, tamper-evident); an independent description of how the boundary is enforced; a verifiable offline-only mode; and security team sign-off. What would put me off at home: any sign that something left the machine unprompted (a cloud key already saved in Settings would need explaining).

## 10. Concerns, objections and suggestions
- I could not find a log I could hand to an auditor. The app says an activity log is kept and shows an "actions recorded" counter, but "What changed" gave only a one-line summary. This is the most important feature to make visible and exportable.
- Asking the assistant for its log produced a wrong answer instead of the log. For an auditor a model describing itself is not evidence; the log must come from the system, not the model.
- "Nothing leaves this computer" is a claim; show me how to verify it.
- Cloud model options and a saved key in Settings undermine the "stays local" story until I read the small print. Make the default state unmistakable.
- Remote access from a phone widens the attack surface; in my world that is a separate approval.
- How does it stop a model mistake escaping the folder? I saw one refusal only.
- Suggestion: a read-only audit export (CSV or PDF) with timestamps, user approval, files touched, and model used.

## 11. Final assessment of the central claim
(a) Trust more than a full-access assistant: **agree**. A bounded scope is easier to reason about and defend. I only partly trust it until the boundary is verifiable.
(b) More willing to use it: **partly**. At home yes. At work no, because the barrier is policy, not trust.
(c) Limitation costs too much usefulness: **disagree** for my needs. What I would delegate fits a folder-scoped tool.

Short questions:
- Are people really losing time to interruptions and routine file work: **partly**. Real but modest for me; others may lose more.
- Is wanting broad access a real barrier: **agree**. For me full access is a hard stop.
- Accept one mistake if undo is easy: **partly**. Yes for home files; for anything touching records at work no, since the mistake itself is a reportable event even if reversed.
- Ask before every change, or act and let me undo: **ask first**. The approval is itself part of the audit record. Undo-only is not acceptable to me.
- Abilities I would actually use: source-cited answers about my own notes, the tidy-up with plan, undo, "what it knows". Not voice, not remote access.
- What makes setup too much effort: anything beyond choosing a folder; the email app-password steps and relay server for remote access looked like too much; a security review would be my real setup cost.

## 12. Implementation limitations I ran into
- The second answer was off topic and cited the wrong file (random.zip).
- "What changed" said "Nothing has changed outside ARTEMIS" right after it moved 19 files, which reads as contradictory.
- The chat showed the greeting "Hi again. Let's pick up where we left off" repeated many times.
- My own screenshots landed in the test folder, were tidied with the rest and appear in the "what it knows" list (harness side effect).
- Voice showed "No microphone found"; I could not exercise it.
- Replies took 30 to 40 seconds.
- I did not find an exportable audit log; it may exist and I did not find it.
- Early script failures on tab and button selectors were my tooling, not the app.
