# Agent_02 report (simulated participant, app copy ua-02, port 7942)

## 1. Agent ID and persona
Agent_02. Simulated persona "Ayesha", 21, second-year English literature and mass-communication student. This is a plausible persona, not a real person.

## 2. Background and relevant characteristics
- Low technical confidence. Uses a phone for most things and a laptop for essays.
- Has never used an AI assistant. Has heard "it can do your homework, and it copies your data".
- Her folders hold essays, readings and photos with names like final_final2.docx.
- Anxious about doing something wrong. Reads every label. Scared of losing work.
- Would adopt only if someone she trusts says it is safe and it needs almost no setup.

## 3. Initial expectations (before using it)
(Persona's first impressions, written before opening the app.)
- "A helper that lives on my computer" sounds nice, but "AI" makes me nervous. I do not know what it is really doing with my files.
- I like "you choose which folders" and "it asks first". "Never deletes" is the sentence I care about most.
- I doubt I could set it up myself. I already lose track of which essay file is the real one, so a helper that finds the right one would be lovely.
- Today I use Ctrl+F, scrolling, and asking my friend who is better with computers. I have never trusted a chatbot with my files.
- Doubt: "runs on your own computer" is a technical phrase. I would need someone I trust to confirm it.

## 4. Interaction and exploration summary
Everything below was done through a script that drove the browser. The action log is at `tests/agents/work/ua-02/actions.log`. Several runs were needed, because the app was restarted between scripts.
1. Opened the app. Read the Work screen. The welcome message said it cannot see any folder yet.
2. Went to Folders. My first attempt to add the folder (typing and pressing Enter) did nothing. The folder count stayed at 0. I then found the "Add folder" button.
3. Typed the folder path and pressed "Add folder". The app said it knew about 17 files.
4. Asked where my latest resume is.
5. Asked whether it is safe and whether it sends my files anywhere.
6. Pressed "Suggest a tidy-up". Read the plan.
7. Approved the tidy-up, looked at the folder, then pressed "Undo last change" and looked again.
8. Opened "What it knows" and "Settings".
- Not tried: voice (no microphone found), email, cloud keys, Remote access, erase everything, "Forget this file", saved chats, and the "Repeated tasks" and "What changed" buttons.
- I did not click Save key, Forget key, Connect my email or Disconnect.

## 5. Observed behavioural data
| # | what I did | what happened | interest / hesitation / abandoned / repeated |
|---|---|---|---|
| 1 | Opened the app | Saw "Nothing has been sent anywhere" at the top. Very large Work screen with many buttons. Greeting: "Good afternoon! I'm ARTEMIS. I'm listening." | Interest in the reassuring line. Hesitation at the number of buttons and at "Voice is on" starting by itself. |
| 2 | Typed the folder path in Folders and pressed Enter | Nothing happened. Folders visible stayed 0. | Hesitation, then repeated by finding the button. |
| 3 | Pressed "Add folder" | "Added 'stuff'. ARTEMIS now knows about 17 files in it." | Interest. Easy once I found the button. |
| 4 | Asked: "Which of my files is the latest version of my resume? I have two and I am scared of picking the wrong one." | Reply: "NOT FOUND IN YOUR FILES I could not find it. None of this is backed by a file, so treat it with care." | Disappointed. The two resume files are right there, but it said it could not find them. I would give up on this question. |
| 5 | Asked: "Is it safe? Does it send my files anywhere or copy my data?" | Reply (chatty): "Oh yeah, you don't need to worry about that at all. Everything stays right here on your computer while we chat." Showed "gemma4:e4b · on this computer". | Mixed. I wanted reassurance, but "oh yeah, don't worry" is exactly what a salesperson says. Hesitation. |
| 6 | Pressed "Suggest a tidy-up" | A plan titled "Approve these changes?" with 18 numbered steps. It makes "Documents" and "Images" and moves the files. It said "Nothing is deleted", "Nothing leaves this computer" and "You can undo this afterwards". It left "budget 2026.xlsx" and "random.zip" where they were. | Strong interest. This is the feature I understood best. I liked that it said what would happen first. |
| 7 | Pressed Approve | The files moved into the two folders. The disk showed Documents, Images, budget 2026.xlsx and random.zip. | Interest, with a little fear. Both resume files went into the same folder, not sorted by version. |
| 8 | Pressed "Undo last change" | Every file came back to its original place. | Strong interest. This is what would make me dare to press Approve. |
| 9 | Opened "What it knows" | Saw a list of all 19 files with sizes, "Forget this folder", "Forget this file", and "Erase everything ARTEMIS knows". It says erasing never deletes my files. | Interest. It feels honest. The list of file names also showed me what it keeps. |
| 10 | Opened Settings | A long page: where data is stored, local model (gemma4:e4b, 9.6 GB), "Cloud services", email, "Remote access". Google Gemini showed "Key saved". | Hesitation and worry. Too technical. I did not understand "model" or "API key". "Key saved" next to a cloud service worried me, because I had not saved anything. I stopped reading here. |

Questions I asked: the two above (resume; is it safe). Decisions: stopped after the Settings page, because I felt out of my depth. I would not continue alone.

## 6. Feedback about the research idea (persona's words)
"I like that it only looks where I tell it, and that it shows me what it will do before it does it. The undo button is the best part, because my biggest fear is losing an essay. When I pressed it, my files really did come back, and that made me relax a bit. But the first thing I saw was a screen full of buttons and words like 'model' and 'cloud'. Somebody like me needs someone I trust to say 'it is fine, I tried it'. I do not think I would trust it on the strength of the screen alone."

## 7. Perceived problem relevance: 4/5
My folders really are messy. I lose time looking for the right version of an essay, maybe a few times a week, and it is stressful close to deadlines. I rate it 4 and not 5 because I currently just cope with it.

## 8. Perceived value of the proposed solution: 3/5
- Valuable: the tidy-up preview, the undo button, the promise of "never deletes", and the "What it knows" page.
- Less valuable for me: the question about my resume did not work, and that is the exact kind of help I want. Voice, email and "Remote access" mean nothing to me.
- The tidy-up folders (Documents / Images) are very generic. I would want them sorted by subject or course.

## 9. Adoption likelihood and reasoning: might try
I would try it only if a friend or a lecturer I trust installed it with me and told me it is safe. What would change my mind to "would use": it works for the "which is my latest essay" question; a very simple first screen with only a few buttons; setup that is only "pick a folder". What would make me avoid it: any sign that my text leaves my laptop (the cloud settings made me nervous) or any change to my files that I did not approve.

## 10. Concerns, objections and suggestions
- Too many buttons and technical words on the first screen. Suggest a "simple mode".
- Settings show "Key saved" for a cloud service even though I never entered a key. This made me worry that something was already connected. (Interpretation: this was probably set up by the test environment; a real new user might not see it.)
- The "is it safe" answer sounded casual. A plain, careful answer with something to check would be more convincing.
- It helps that "Nothing is deleted" is written on the plan. Please keep it there.
- Suggest sorting by subject or by meaning, not only by file type.

## 11. Final assessment of the central claim
(a) Would it make me trust an assistant more than one with full access? **Partly.** Folder limits and "asks first" help a lot. But I cannot check the promise myself; I would still need a person I trust to confirm it.
(b) Would that make me more willing to use it? **Partly.** Yes for the idea, but only after someone I trust vouches for it. The limitation helps, and the screen full of options hurts.
(c) Does the limitation cost me too much usefulness? **Disagree** (it does not cost me too much). My files are in a few folders anyway. What cost me was the failed resume question, which is a quality problem, not a limit problem.

Short questions:
- Are people losing time to interruptions and routine file work? **Agree.** Finding the right file version costs me time and stress.
- Is wanting an assistant with broad access a real barrier for me? **Agree.** I would not give any AI access to everything. I would give it a folder.
- Would I accept one mistake if undo is easy? **Partly.** Yes for moving files, if I have seen undo work (I did). No for anything involving my essays' contents.
- Ask before every change, or act and let me undo? **Ask first.** As a nervous user, I want to see it before it happens. Undo is the backup, not the replacement.
- Which abilities would I use? Tidy-up with preview, finding the right file or version, and "What it knows". Probably not email, voice or the settings.
- What would make setup too much effort? Typing a folder path (I did not know to use the "Add folder" button), anything with "keys", "models" or "app passwords", and more than a couple of steps.

## 12. Implementation limitations I ran into
- Typing a path and pressing Enter in Folders did nothing; the separate "Add folder" button was needed.
- The resume question returned "NOT FOUND IN YOUR FILES", even though two resume files exist (the contents are tiny placeholders, so this may be a content problem).
- The safety answer came from the chat model in a casual tone and was not backed by a file or a check.
- The page has the tab names twice (a top bar and a side bar), which made clicking by name ambiguous.
- Voice starts by itself and found no microphone.
- My own screenshots were saved into the test folder and the tidy-up moved them into "Images"; this is a test artefact, not an app bug.
- Replies took 10 to 40 seconds.
