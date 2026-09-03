# A.R.T.E.M.I.S.

**Adaptive Reasoning, Task Execution and Multi-agent Intelligence System**

A bounded, opt-in desktop AI assistant. ARTEMIS only ever knows about the files, tabs, and notes you explicitly add to a workspace folder you create — it has no access outside it, deletes nothing, and every file-changing or outbound action (email, web search) goes through **preview → approve**, with undo available afterward. A "What ARTEMIS Knows" panel always shows everything the system currently holds.

This bounded-scope design is the project's central hypothesis: *restricting an assistant's scope increases user trust and adoption without meaningfully hurting its usefulness.*

> FAST NUCES final-year project (F26-008). Previously named A.E.G.I.S.

## Team

| Name | Roll No. |
| --- | --- |
| Hashir Rauf | 23L-2572 |
| Hira Khalid | 23L-2594 |
| Doureesha Batool | 23L-2651 |

## Features (build order)

1. **Pick Up Where You Left Off** — session resume, no AI
2. **Tidy Up a Folder** — approval-based file grouping
3. **Pull Together Notes** — citation-grounded synthesis across a few documents
4. **Notice a Repeated Task** — offers automation after 3+ repeats, never auto-imposes
5. **Code Assistant** — explains and diffs fixes; never writes or executes code autonomously
6. **Web Search** — on-demand only, no background browsing
7. **Mailing** — draft → approve → send, logged
8. **Document Drafting** — first-draft generation, saved as a new file
9. **Speech Input/Output** — alternate interaction mode over the same approval steps

*Stretch goal:* workspace change summary / diff since last session.

## Tech stack

- **Language:** Python throughout
- **Agent:** [LangGraph](https://langchain-ai.github.io/langgraph/) — explicit multi-step plans with a pause point before any workspace-changing or outward tool call (this is what implements preview / approve / undo)
- **LLM access:** local-first via [Ollama](https://ollama.com/), falling back in order Gemini → OpenAI → Anthropic when the local model can't handle a task
- **Storage:** local SQLite (workspace metadata, notes, automation rules, activity/undo log) + a local vector index for document/code embeddings, scoped per workspace and rebuilt incrementally — no hosted database
- **Desktop UI:** PySide or a local webview served from the Python backend *(not yet finalized)*

## Build sequence

Staged for early feasibility validation:

1. **Workspace foundation** — SQLite + file watcher + "What ARTEMIS Knows" panel (no AI)
2. **Agent + approval loop** — LangGraph + model fallback chain *(highest-risk stage, prioritized first)*
3. **Core file features** — session resume, tidy folder, repeated task
4. **Document / code understanding** — notes synthesis, code assistant
5. **Outward actions** — web search, mailing, document drafting
6. **Speech I/O** — last

## Repository layout

```
Docs/
  Data Collection/   Interview guides, questionnaires, raw research input
  Proposal/          Official FYP proposal (F26-008)
  Research Docs/      Proposal drafts, competitive landscape, scope updates
```

The ARTEMIS-named docs in `Docs/Research Docs/` are current; the AEGIS-named ones are superseded history.

## Status

Sprint 0 — planning and research complete, implementation not yet started. Work begins at Stage 1 (workspace foundation).

## License

Academic project — not currently licensed for external use.
