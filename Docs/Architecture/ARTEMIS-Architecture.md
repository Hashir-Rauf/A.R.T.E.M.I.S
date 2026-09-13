# A.R.T.E.M.I.S. — System Architecture (Proof of Concept)

**Adaptive Reasoning, Task Execution and Multi-agent Intelligence System**
FAST NUCES Final Year Project · F26-008 · Architecture Revision 2

> Revision 2 restructures the original six-box sketch into a layered architecture with
> two cross-cutting planes (Security/Trust and Execution/Performance), decomposes the
> AI Gateway from a monolithic brain into four cooperating components, and separates
> the remote-access plane from the core execution path.

---

## 1. Architectural Thesis

ARTEMIS is defined by one sentence, and every structural decision below follows from it:

> **Local-first, cloud-optional, remotely accessible — but never cloud-dependent for
> core operation, and never in possession of scope the user has not explicitly granted.**

This is not a deployment preference. It is the architectural encoding of the project's
central research hypothesis — *that restricting an assistant's scope increases user trust
and adoption without meaningfully hurting its usefulness*. The architecture must make
that restriction structural rather than behavioural: it must be **impossible by
construction**, not merely **discouraged by prompt**.

### 1.1 Degradation Contract

The system's correctness is defined by how it behaves as capabilities are withdrawn.
Each row is a testable acceptance criterion, not an aspiration.

| Withdrawn capability | Required behaviour |
| --- | --- |
| Internet connectivity lost | Full local operation continues. Only cloud model calls, web search, and mail send are disabled — each fails as an explicit, retryable queued action, never a silent drop. |
| All cloud LLM APIs unavailable or unconfigured | Falls back to the configured local model (Ollama). Features that exceed local capability degrade to a stated limitation, not an error dialog. |
| Local model unavailable | Falls back forward to the cloud chain, if and only if the user has enabled cloud fallback for that workspace. |
| Remote device disconnects | Host ARTEMIS continues uninterrupted. In-flight approvals revert to pending and surface on the host UI. |
| Cloudflare edge unreachable | Local operation entirely unaffected — the remote plane is not on the execution path. |
| Workspace not explicitly granted | ARTEMIS cannot see it. Not "declines to touch it" — the path is not resolvable through the workspace broker at all. |

### 1.2 Non-Goals

Stated explicitly, because an architecture is defined as much by what it refuses:

- **No hosted user data.** Documents, embeddings, session history, memory, credentials
  and audit logs never leave the host machine. The only outbound telemetry is anonymous,
  opt-in, schema-fixed diagnostic logs.
- **No autonomous outward action.** No email, no web request, no file mutation without
  passing an approval gate.
- **No ambient surveillance.** No background browsing, no screen scraping, no keylogging,
  no always-on recording. The voice session is explicitly armed by the user.
- **No self-modifying execution.** The agent cannot write and run arbitrary code against
  the host as part of its own plan.

---

## 2. Layered Overview

Six layers on the execution path, two planes crossing all of them.

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                        S E C U R I T Y   /   T R U S T   P L A N E                ║
║           (cross-cutting — see §9; every arrow below crosses this plane)          ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║  │ LAYER 1 · PRESENTATION                                                      │  ║
║  │                                                                             │  ║
║  │    CLI (Typer)        Local GUI (Gradio)         Remote PWA (§8)            │  ║
║  │         │                    │                         │                    │  ║
║  │         └────────────────────┴─────────────────────────┘                    │  ║
║  │                              ▼                                              │  ║
║  │                   ARTEMIS CONTROL PANEL — one shared view model             │  ║
║  │      Chat · Monitor · Configure · Approve/Reject · Undo · What I Know        │  ║
║  └──────────────────────────────────┬──────────────────────────────────────────┘  ║
║                                     │ local HTTP + WebSocket (loopback only)      ║
║  ┌──────────────────────────────────▼──────────────────────────────────────────┐  ║
║  │ LAYER 2 · INTERACTION & SESSION                                             │  ║
║  │                                                                             │  ║
║  │   Voice Session Manager              Text Stream Manager                    │  ║
║  │   VAD · STT · barge-in · TTS         tokens · partials · cancel             │  ║
║  │         │                                    │                              │  ║
║  │         └───────────────┬────────────────────┘                              │  ║
║  │                         ▼                                                   │  ║
║  │              TURN NORMALISER  →  modality-neutral Turn object               │  ║
║  │        (every downstream layer is blind to whether input was voice or text) │  ║
║  └──────────────────────────────────┬──────────────────────────────────────────┘  ║
║                                     │                                             ║
║  ┌──────────────────────────────────▼──────────────────────────────────────────┐  ║
║  │ LAYER 3 · AI GATEWAY  (orchestrator — NOT a monolith; see §5)               │  ║
║  │                                                                             │  ║
║  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐            │  ║
║  │   │   Model    │  │  Context   │  │   Policy   │  │   Agent    │            │  ║
║  │   │   Router   │  │   Engine   │  │   Engine   │  │  Planner   │            │  ║
║  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘            │  ║
║  │                              │                                              │  ║
║  │                     ┌────────▼────────┐                                     │  ║
║  │                     │ TOOL DISPATCHER │  ← the single chokepoint            │  ║
║  │                     └────────┬────────┘                                     │  ║
║  └──────────────────────────────┼──────────────────────────────────────────────┘  ║
║                                 │                                                 ║
║  ┌──────────────────────────────▼──────────────────────────────────────────────┐  ║
║  │ LAYER 4 · CAPABILITY SERVICES  (the 9 features; see §6)                     │  ║
║  │                                                                             │  ║
║  │  Session Resume   Folder Tidy    Notes Synthesis   Pattern Watcher          │  ║
║  │  Code Assistant   Web Search     Mail Composer     Document Drafter         │  ║
║  │                                                                             │  ║
║  │  Support: Workspace Broker · Indexer · Undo Journal · Approval Broker       │  ║
║  │                    ALL EXECUTING INSIDE THE USER'S MACHINE                  │  ║
║  └──────────────────────────────┬──────────────────────────────────────────────┘  ║
║                                 │                                                 ║
║  ┌──────────────────────────────▼──────────────────────────────────────────────┐  ║
║  │ LAYER 5 · DATA PLANE  (see §7)                                              │  ║
║  │                                                                             │  ║
║  │   SQLite (metadata·sessions·rules·audit)      Vector Index (per workspace)  │  ║
║  │   Key-Value Memory Store                       Snapshot Store (undo)        │  ║
║  │   Credential Vault (OS keyring)                Content-Addressed Blob Cache │  ║
║  │                                                                             │  ║
║  │              LOCAL ONLY — NEVER UPLOADED TO ANY ARTEMIS SERVER              │  ║
║  └─────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                   ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║              E X E C U T I O N   /   P E R F O R M A N C E   P L A N E             ║
║                        (cross-cutting — see §10)                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝

           LAYER 6 · REMOTE ACCESS PLANE (§8) — deliberately drawn OUTSIDE
              the stack above, because nothing in Layers 1–5 depends on it.
```

### 2.1 Why Two Planes Rather Than Two More Layers

Security and performance are not stages a request passes through — they are properties
every stage must hold. Drawing them as layers would imply a request could be "past"
security, which is exactly the reasoning error that produces confused-deputy bugs. They
are drawn as planes to signal that **every arrow in the diagram crosses both**.

---

## 3. Component Inventory

| # | Component | Layer | Responsibility | One thing it must never do |
| --- | --- | --- | --- | --- |
| 1 | CLI | 1 | Scriptable control surface | Bypass the approval broker |
| 2 | Gradio GUI | 1 | Visual control panel, loopback-bound | Bind to a non-loopback interface |
| 3 | Control Panel view model | 1 | Single source of UI truth across surfaces | Hold state the backend doesn't own |
| 4 | Voice Session Manager | 2 | VAD, STT, barge-in, TTS | Record when not explicitly armed |
| 5 | Text Stream Manager | 2 | Token streaming, cancellation | Buffer past a cancel |
| 6 | Turn Normaliser | 2 | Modality-neutral `Turn` | Leak modality downstream |
| 7 | Model Router | 3 | Select + fail over across models | Send workspace data to a disabled tier |
| 8 | Context Engine | 3 | Assemble bounded, cited context | Include out-of-workspace content |
| 9 | Policy Engine | 3 | Classify risk, decide gating | Be consulted after execution |
| 10 | Agent Planner | 3 | LangGraph multi-step plan | Execute anything itself |
| 11 | Tool Dispatcher | 3 | Sole execution chokepoint | Accept a call lacking a policy verdict |
| 12 | Capability Services | 4 | The 9 features | Touch the filesystem directly |
| 13 | Workspace Broker | 4 | Path resolution + confinement | Resolve a path outside a grant |
| 14 | Indexer | 4 | Incremental embedding/index | Block the interactive path |
| 15 | Undo Journal | 4 | Snapshot + inverse operations | Record an action after the fact |
| 16 | Approval Broker | 4 | Hold pending actions, fan out to surfaces | Auto-approve on timeout |
| 17 | Data Plane stores | 5 | Local persistence | Serialise outside the host |
| 18 | Remote Access Plane | 6 | Authenticated relay | Store or read plaintext user data |

---

## 4. The Request Lifecycle

The single most important path in the system. Every user request — voice or text, local
or remote — traverses exactly this sequence. No shortcuts exist.

```
  Input (voice | text | remote)
        │
        ▼
  ┌─────────────────┐
  │ Turn Normaliser │   modality erased here
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ Context Engine  │   retrieve within workspace bounds only
  └────────┬────────┘     ↳ returns context + citations + provenance
           ▼
  ┌─────────────────┐
  │  Model Router   │   choose tier; enforce data-egress policy
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  Agent Planner  │   produce an explicit, inspectable PLAN
  └────────┬────────┘     ↳ Plan = ordered list of proposed ToolCalls
           ▼
  ┌─────────────────┐
  │  Policy Engine  │   classify EACH ToolCall: read | reversible | outward
  └────────┬────────┘
           ▼
     ┌─────────────┐
     │  risk tier? │
     └──┬───────┬──┘
        │       │
   auto │       │ gated
        │       ▼
        │  ┌──────────────────┐        ┌──────────────┐
        │  │ Approval Broker  │───────▶│ USER DECIDES │
        │  │ preview + diff   │◀───────│ approve/edit │
        │  └────────┬─────────┘        │   / reject   │
        │           │                  └──────────────┘
        │           │ approved                │ rejected
        └─────┬─────┘                         ▼
              ▼                        record + explain,
     ┌──────────────────┐              plan halts cleanly
     │  Undo Journal    │  snapshot BEFORE mutation
     └────────┬─────────┘
              ▼
     ┌──────────────────┐
     │ Tool Dispatcher  │  the only component that may act
     └────────┬─────────┘
              ▼
     ┌──────────────────┐
     │ Capability Svc   │  via Workspace Broker for all I/O
     └────────┬─────────┘
              ▼
     ┌──────────────────┐
     │   Audit Log      │  append-only, hash-chained
     └────────┬─────────┘
              ▼
        Result → Control Panel (+ TTS if voice turn)
```

**Invariants enforced on this path:**

1. The Policy Engine is consulted **before** the Tool Dispatcher, never after.
2. The Undo Journal snapshots **before** mutation, never after.
3. The Audit Log entry is written **even when the action is rejected**.
4. A `ToolCall` without a signed policy verdict is rejected by the Dispatcher.
5. Voice and text turns are indistinguishable from the Planner onward — this is what
   makes voice parity structural rather than a second implementation.

---

## 5. Layer 3 — The AI Gateway, Decomposed

The original design made the Gateway responsible for routing, context, memory, planning,
policy and dispatch simultaneously. That is untestable and academically hard to defend.
Revision 2 splits it into four components with a single shared chokepoint.

```
                          ┌───────────────────┐
                          │  Normalised Turn  │
                          └─────────┬─────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐          ┌────────────────┐          ┌────────────────┐
│ MODEL ROUTER  │          │ CONTEXT ENGINE │          │ POLICY ENGINE  │
│               │          │                │          │                │
│ • capability  │          │ • RAG retrieve │          │ • risk class   │
│   probe       │          │ • memory merge │          │ • scope check  │
│ • tier select │          │ • token budget │          │ • gate/allow   │
│ • failover    │          │ • citation map │          │ • egress rules │
│ • egress gate │          │ • bounds check │          │ • rate limits  │
└───────┬───────┘          └────────┬───────┘          └────────┬───────┘
        │                           │                           │
        │   ┌───────────────────────┴───────────────────────┐   │
        │   │                                               │   │
        ▼   ▼                                               ▼   ▼
┌─────────────────────────┐                    ┌──────────────────────────┐
│      AGENT PLANNER      │                    │   verdicts attached to   │
│      (LangGraph)        │───── Plan ────────▶│   each proposed call     │
│                         │                    └────────────┬─────────────┘
│ • decompose intent      │                                 │
│ • order steps           │                                 │
│ • declare tool calls    │                                 │
│ • NEVER executes        │                                 │
└─────────────────────────┘                                 │
                                                            ▼
                                            ┌───────────────────────────┐
                                            │     TOOL DISPATCHER       │
                                            │  single execution point   │
                                            │  • verifies verdict       │
                                            │  • enforces timeout       │
                                            │  • emits audit record     │
                                            └─────────────┬─────────────┘
                                                          │
                        ┌─────────────────┬───────────────┼───────────────┬─────────────────┐
                        ▼                 ▼               ▼               ▼                 ▼
                  File Service      Code Service    Search Service   Mail Service    Doc Service
```

### 5.1 Model Router

Owns tier selection and, critically, **data-egress enforcement**. The router is the
component that knows a given workspace's cloud policy, so it is the correct place to
block egress — not the tool layer, and not the prompt.

```
                    ┌──────────────────────────┐
                    │   Routing Decision       │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
      task complexity     workspace cloud     model health /
      + context size      policy (opt-in)     availability
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 ▼
         ┌────────────────────────────────────────────────┐
         │  TIER 0 · Local (Ollama)          ← default    │
         │  TIER 1 · Gemini                               │
         │  TIER 2 · OpenAI                  ← only if    │
         │  TIER 3 · Anthropic                 workspace  │
         │                                     allows     │
         │  Any OpenAI-compatible endpoint (user-added)   │
         └────────────────────────────────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │ EGRESS GATE                          │
              │ if tier > 0 and workspace.cloud=off  │
              │     → refuse, degrade, explain       │
              │ else → redact PII, attach budget,    │
              │        record egress in audit log    │
              └──────────────────────────────────────┘
```

The fallback order **Ollama → Gemini → OpenAI → Anthropic** is retained from the
proposal. Any OpenAI-compatible endpoint (Grok, Kimi, DeepSeek, a self-hosted vLLM) can
be registered as an additional tier without code changes — the router treats providers as
configuration, not as branches.

**Failover is bounded:** one retry per tier, then advance. A workspace that has disabled
cloud has exactly one tier, and its failure is a clean degradation message, not a hang.

### 5.2 Context Engine

Assembles the model's working context and is the enforcement point for the bounded-scope
hypothesis on the *read* side (the Workspace Broker enforces it on the *write* side).

```
        ┌──────────────────────────────────────────────────────┐
        │                  CONTEXT ASSEMBLY                    │
        └──────────────────────────────────────────────────────┘
                                 │
   ┌──────────┬──────────┬───────┴───────┬──────────┬──────────┐
   ▼          ▼          ▼               ▼          ▼          ▼
 Current   Session    Long-Term      Workspace   Retrieved   Tool
 Turn      Memory     Memory (KV)    Index       Chunks      Results
   │          │          │               │          │          │
   └──────────┴──────────┴───────┬───────┴──────────┴──────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │      BOUNDS ASSERTION        │
                  │ every chunk carries a        │
                  │ workspace_id; any chunk not  │
                  │ matching the active grant is │
                  │ DROPPED and the drop logged  │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │      TOKEN BUDGETER          │
                  │ tier-aware; recency + score  │
                  │ weighted; never silently     │
                  │ truncates a citation source  │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │     CITATION MAP             │
                  │ chunk → file → line/page     │
                  │ carried through to the answer│
                  └──────────────────────────────┘
```

The citation map is what makes Feature 3 (Pull Together Notes) verifiable, and directly
addresses LR Theme 7 (RAG citation accuracy) and Theme 6 (hallucination). A synthesis
answer whose claims cannot be traced back through this map is rendered with the claim
marked unsupported rather than presented as fact.

### 5.3 Policy Engine — the component the original design was missing

This is the most important addition in Revision 2. It converts the research finding
*"approval-first, configurable"* from a UI behaviour into an enforced architectural
component.

Every proposed tool call is classified into exactly one tier:

| Tier | Definition | Default | Undo |
| --- | --- | --- | --- |
| **T0 — Read** | Reads inside the granted workspace. No mutation, no egress. | Auto-execute | n/a |
| **T1 — Reversible** | Mutates workspace state, fully invertible via snapshot. | Configurable: auto / batch-approve / per-action | Full |
| **T2 — Outward** | Leaves the machine: mail send, web request, cloud model call with workspace content. | **Always gated. Not configurable.** | Partial — logged, recallable only where the protocol allows |
| **T3 — Destructive** | Deletion, overwrite without snapshot, out-of-workspace write. | **Refused. Not gated — structurally unavailable.** | n/a |

The T3 tier is what makes "deletes nothing" a property of the system rather than a promise
of the model. There is no approval dialog for T3 because there is no code path to it.

**Evaluation order** (first match wins, so a deny cannot be argued past):

```
   1. Workspace grant check      → outside grant?        DENY (T3)
   2. Destructive-op check       → delete/overwrite?     DENY (T3)
   3. Egress check               → leaves machine?       GATE (T2)
   4. Mutation check             → changes state?        tier per user config (T1)
   5. Otherwise                                          ALLOW (T0)
```

A worked example, the "clean this folder" case:

```
   User: "Tidy up my thesis folder."
              │
              ▼
   Planner emits 4 proposed calls:
     ① list_dir(/Projects/Thesis)
     ② read_metadata(*.pdf, *.docx)
     ③ create_dir(/Projects/Thesis/Drafts)
     ④ move_files(12 files → /Projects/Thesis/Drafts)
              │
              ▼
   Policy Engine classifies:
     ① T0 read       → auto
     ② T0 read       → auto
     ③ T1 reversible → gated (user config: per-action)
     ④ T1 reversible → gated (user config: per-action)
              │
              ▼
   ┌──────────────────────────────────────────────────┐
   │ APPROVAL REQUIRED                                │
   │                                                  │
   │ Workspace : /Projects/Thesis        (granted)    │
   │ Operation : create 1 folder, move 12 files       │
   │ Risk      : T1 — reversible                      │
   │ Undo      : available for 30 days                │
   │ Outside   : nothing outside the workspace        │
   │ Egress    : none                                 │
   │                                                  │
   │ ▸ Preview all 12 moves          [expand]         │
   │                                                  │
   │   [ Approve ]  [ Approve & remember ]            │
   │   [ Edit ]     [ Reject ]                        │
   └──────────────────────────────────────────────────┘
              │ approved
              ▼
   Snapshot → Execute → Audit → "Done. Undo available."
```

Note `[Approve & remember]`: this is how the *configurable* half of the research finding
is implemented. It writes a scoped policy rule (this operation type, this workspace,
this shape of action) rather than globally lowering the user's protection.

### 5.4 Agent Planner

LangGraph, per the existing stack decision. The architectural constraint is that the
Planner **emits a plan and never executes it**. This separation is what makes the pause
point before workspace-changing calls structural.

```
   Intent ──▶ Decompose ──▶ Order ──▶ Declare tool calls ──▶ PLAN (data, not action)
                  ▲                                              │
                  │                                              ▼
                  └────────── Reflect on result ◀────── Dispatcher executes
                             (bounded: max N cycles)
```

The reflection loop (LR Theme 3 — Reflexion, ReAct) is bounded by an explicit cycle cap
and a wall-clock budget. An agent that cannot converge surfaces its partial plan and asks,
rather than looping.

---

## 6. Layer 4 — Capability Services

The nine proposal features map onto services. Every service is a plugin behind a uniform
tool contract; none touches the filesystem, network, or database directly.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          TOOL DISPATCHER                                 │
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────────┘
    │      │      │      │      │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
  ┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐
  │ F1 ││ F2 ││ F3 ││ F4 ││ F5 ││ F6 ││ F7 ││ F8 ││ F9 │
  └─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘
    └─────┴─────┴─────┴─────┴──┬──┴─────┴─────┴─────┘
                               ▼
       ┌───────────────────────────────────────────────┐
       │  SHARED SUBSTRATE (services never bypass)     │
       │                                               │
       │  Workspace Broker  — all path resolution      │
       │  Undo Journal      — all snapshots            │
       │  Approval Broker   — all gating               │
       │  Data Plane        — all persistence          │
       └───────────────────────────────────────────────┘
```

| # | Service | Highest tier it can request | Notes |
| --- | --- | --- | --- |
| F1 | Session Resume | T0 | No AI in v1 — deterministic replay of last session state. |
| F2 | Folder Tidy | T1 | Move/group only. Never delete — no code path to it. |
| F3 | Notes Synthesis | T0 | Read + generate. Output is a proposal until F8 saves it. |
| F4 | Pattern Watcher | T1 (to *offer*) | Detects 3+ repeats; may only propose an automation rule. Cannot install one. |
| F5 | Code Assistant | T0 | Explains and produces a **diff**. Never writes, never executes. |
| F6 | Web Search | T2 | On-demand only. No background browsing. Every query logged. |
| F7 | Mail Composer | T2 | Draft → approve → send. Sending is always gated regardless of config. |
| F8 | Document Drafter | T1 | Always writes a **new** file. Never overwrites an existing one. |
| F9 | Speech I/O | — | Not a capability; a Layer-2 modality over identical gates. |

**Structural claim worth defending in the report:** F9 is deliberately *not* a service.
Voice is normalised at Layer 2 into the same `Turn` object as text, so it inherits every
approval gate automatically. This addresses LR Theme 4 (voice interaction parity) — parity
is achieved by construction, not by re-implementing the gates for the voice path.

### 6.1 Workspace Broker

The single component that turns a logical reference into a real filesystem path, and the
enforcement point for the bounded-scope hypothesis on the write side.

```
   Service asks for:   "notes/chapter3.md"  (workspace-relative, always)
                              │
                              ▼
        ┌─────────────────────────────────────────────────┐
        │             WORKSPACE BROKER                    │
        │                                                 │
        │  1. resolve against active grant root           │
        │  2. canonicalise (realpath — resolve symlinks)  │
        │  3. assert canonical path is under grant root   │
        │  4. assert not in deny-list (system, hidden,    │
        │     credential paths)                           │
        │  5. assert operation ≤ granted permission       │
        │                                                 │
        │  any assertion fails → raise, log, do not act   │
        └─────────────────────────────────────────────────┘
                              │
                              ▼
                    real path, or refusal
```

Step 2 is not incidental — canonicalising before the bounds check is what prevents
symlink and `../` traversal escapes. This is the difference between a boundary and a
suggestion.

### 6.2 Undo Journal

```
   Before any T1 operation:
        │
        ▼
   ┌───────────────────────────────────────────────┐
   │ Choose strategy by cost:                      │
   │                                               │
   │  small file  → content snapshot (blob store)  │
   │  large file  → copy-on-write hardlink         │
   │  move/rename → inverse operation record only  │
   │  new file    → deletion record                │
   └───────────────────────────┬───────────────────┘
                               ▼
   ┌───────────────────────────────────────────────┐
   │ Journal entry:                                │
   │   action_id · workspace · timestamp           │
   │   forward op · inverse op · snapshot ref      │
   │   plan_id (groups an entire multi-step plan)  │
   └───────────────────────────┬───────────────────┘
                               ▼
                     execute forward op
```

Undo operates at **plan granularity**, not operation granularity. "Undo tidy folder"
reverses all 12 moves as one unit, in reverse order, because that is the unit the user
approved. Per-operation undo is available but secondary.

---

## 7. Layer 5 — Data Plane

### 7.1 Store Map

```
   ~/.artemis/
   ├── artemis.db                SQLite — the system of record
   │     ├── workspaces          grants, roots, permissions, cloud policy
   │     ├── sessions            session index, resume state
   │     ├── turns               conversation history, multi-chat
   │     ├── memory_kv           long-term facts, preferences
   │     ├── file_index          path · mtime · hash · type · workspace
   │     ├── automation_rules    F4 proposals and accepted rules
   │     ├── policy_rules        user-configured approval preferences
   │     ├── audit_log           append-only, hash-chained
   │     └── undo_journal        forward/inverse ops, snapshot refs
   │
   ├── index/<workspace_id>/     vector index, one per workspace
   ├── blobs/                    content-addressed snapshots (dedup by hash)
   ├── cache/                    derived artefacts, safely deletable
   └── config.toml               non-secret settings
       (secrets live in the OS keyring — never on disk in this tree)
```

**Per-workspace index isolation is deliberate.** It means a workspace's embeddings
cannot be retrieved while another workspace is active, even in the event of a query bug —
the index simply is not open. It also makes "revoke this workspace" a directory deletion,
and bounds the rebuild-time risk flagged in the open questions.

### 7.2 Memory Architecture

The differentiator, and worth its own diagram in the report.

```
                        ┌──────────────────────┐
                        │   ARTEMIS MEMORY     │
                        └──────────┬───────────┘
                                   │
        ┌──────────────┬───────────┼───────────┬──────────────┐
        ▼              ▼           ▼           ▼              ▼
  ┌───────────┐ ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐
  │SHORT-TERM │ │ EPISODIC  │ │LONG-TERM│ │WORKSPACE │ │ PROCEDURAL│
  │           │ │           │ │  (KV)   │ │  MEMORY  │ │           │
  │ current   │ │ session   │ │ prefs   │ │ file     │ │ learned   │
  │ turn      │ │ index +   │ │ facts   │ │ index    │ │ task      │
  │ active    │ │ summaries │ │ config  │ │ folder   │ │ patterns  │
  │ plan      │ │ across    │ │ named   │ │ state    │ │ (F4)      │
  │ scratch   │ │ chats     │ │ entities│ │ relations│ │           │
  └─────┬─────┘ └─────┬─────┘ └────┬────┘ └────┬─────┘ └─────┬─────┘
        │             │            │           │             │
     volatile      SQLite       SQLite      SQLite +      SQLite
     (RAM)                                  vector idx
        │             │            │           │             │
        └─────────────┴────────────┼───────────┴─────────────┘
                                   ▼
                        ┌──────────────────────┐
                        │   CONTEXT ENGINE     │
                        │  merge · budget ·    │
                        │  bounds-assert       │
                        └──────────┬───────────┘
                                   ▼
                             AI GATEWAY
```

**The distinction that matters,** and which the report should state explicitly:

| | Question it answers | Nature |
| --- | --- | --- |
| **OS / File Index** | *"What exists, and where?"* | Mechanical. Derived from the filesystem. Rebuildable at any time. Carries no interpretation. |
| **ARTEMIS Memory** | *"What do I know about this workspace, this task, this user's preferences, and what happened before?"* | Interpretive. Accumulated. Lost if deleted. Requires consent to build. |

Conflating them is the mistake that turns a bounded assistant into a surveillance tool.
The file index is scoped to granted workspaces and holds paths and hashes — not content
interpretation. Memory is what ARTEMIS has *learned*, and every entry is visible and
individually deletable in the "What ARTEMIS Knows" panel.

### 7.3 "What ARTEMIS Knows" — a Query, Not a Report

The panel is not a summary the system writes about itself. It is a live query across
every store, which is what makes it trustworthy:

```
   Panel renders:                     Sourced from:
   ─────────────────────────────────────────────────────────────
   Workspaces granted            ←    workspaces
   Files indexed (count + list)  ←    file_index
   Chunks embedded               ←    index/<ws>/
   Facts remembered              ←    memory_kv
   Sessions retained             ←    sessions + turns
   Automation rules              ←    automation_rules
   Policy exceptions granted     ←    policy_rules
   Actions taken (+ undo state)  ←    audit_log + undo_journal
   Data sent to cloud (what/when)←    audit_log (egress records)
   Credentials held (names only) ←    OS keyring index
```

Every row is deletable from the panel, and deletion is a real cascade — dropping a
workspace drops its index directory, its file rows, its embeddings and its memory
entries. This makes the trust claim falsifiable, which is stronger than making it
persuasive.

---

## 8. Layer 6 — Remote Access Plane

Drawn outside the core stack because **nothing in Layers 1–5 depends on it**. Removing
this entire plane leaves a fully functional single-machine ARTEMIS. That is the test of
whether the separation is real.

```
        ┌──────────────────────────────────────┐
        │  PHONE / TABLET / SECOND LAPTOP      │
        │  Remote PWA (installable)            │
        └──────────────────┬───────────────────┘
                           │ HTTPS
                           ▼
        ┌──────────────────────────────────────┐
        │  CLOUDFLARE PAGES                    │
        │  static PWA shell — no user data     │
        └──────────────────┬───────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  CLOUDFLARE WORKER                   │
        │  • device auth / pairing             │
        │  • session token issue + revoke      │
        │  • rate limiting                     │
        │  • routes to the right DO            │
        │  stores: no user content             │
        └──────────────────┬───────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  DURABLE OBJECT — one per pairing    │
        │                                      │
        │  HOLDS:                              │
        │   • which authenticated device is    │
        │     connected to which ARTEMIS host  │
        │   • connection liveness              │
        │   • opaque E2E-encrypted frames      │
        │     in transit                       │
        │                                      │
        │  NEVER HOLDS:                        │
        │   • plaintext messages               │
        │   • workspace content                │
        │   • embeddings, memory, credentials  │
        │   • decryption keys                  │
        └──────────────────┬───────────────────┘
                           │  WebSocket
                           │  E2E encrypted (keys exchanged at
                           │  pairing; edge cannot read frames)
                           ▼
        ┌──────────────────────────────────────┐
        │  ARTEMIS HOST MACHINE                │
        │  Remote Bridge (outbound conn only — │
        │  no inbound port, no NAT punch)      │
        │            │                         │
        │            ▼                         │
        │  Same Control Panel view model as    │
        │  the local GUI. Same Layer 2 entry.  │
        │  Same gates. No privileged path.     │
        └──────────────────────────────────────┘
```

### 8.1 Pairing

```
  HOST                          EDGE                        DEVICE
   │                             │                            │
   │─ request pairing ──────────▶│                            │
   │                             │                            │
   │◀─ pairing code + DO id ─────│                            │
   │                             │                            │
   │  [displays code + QR on local GUI]                       │
   │                             │                            │
   │                             │◀── scan / enter code ──────│
   │                             │                            │
   │                             │─── challenge ─────────────▶│
   │                             │◀── response ───────────────│
   │                             │                            │
   │◀════════ E2E key exchange (edge relays, cannot read) ════│
   │                             │                            │
   │─ HOST OWNER MUST CONFIRM ON THE LOCAL MACHINE ──────────▶│
   │                             │                            │
   │◀═══════ encrypted session established ══════════════════▶│
```

The host-side confirmation step is deliberate: possession of the pairing code alone is
never sufficient. Compromising the edge cannot pair a device.

### 8.2 Remote Constraints

The remote plane is a **control surface, not a privilege escalation**:

- Remote sessions run at **equal or lower** privilege than local — never higher.
- A workspace can be marked *local-only*; it is then invisible to remote sessions.
- T2 (outward) actions may be configured to require **local** approval regardless of
  where they were requested. Default: on.
- Sessions expire on a fixed TTL and on host sleep. No indefinite sessions.
- Every remote-originated action is tagged with its device in the audit log.
- Revocation is instant and unilateral from the host: kill the DO session, rotate keys.
- If the edge is unreachable, the host simply has no remote clients. Nothing else changes.

---

## 9. Security / Trust Plane (cross-cutting)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  CONTROL                    ENFORCED AT                  RESEARCH LINK        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Workspace confinement      Workspace Broker (§6.1)      Theme 2 — bounded    ║
║  Explicit grant model       Workspaces table + UI        Theme 2 — trust      ║
║  Tool allowlisting          Tool Dispatcher (§5)         Theme 2 — attack sfc ║
║  Approval gates             Policy Engine (§5.3)         Theme 3 — undo/plan  ║
║  Risk classification        Policy Engine (§5.3)         Theme 2              ║
║  Destructive-op refusal     Policy T3 — no code path     Theme 2              ║
║  Encryption at rest         SQLCipher + OS keyring       Theme 2              ║
║  Encryption in transit      TLS + E2E on remote (§8)     Theme 2              ║
║  Credential vault           OS keyring, never on disk    Theme 2              ║
║  Prompt-injection defence   §9.1 below                   Theme 2 — Kim et al. ║
║  Egress control             Model Router gate (§5.1)     Theme 2 — privacy    ║
║  Append-only audit log      Hash-chained, SQLite         Theme 2 — assurance  ║
║  One-click undo             Undo Journal (§6.2)          Theme 3 — recovery   ║
║  Remote device auth         Worker + host confirm (§8.1) Theme 2              ║
║  Session expiry             DO TTL + host sleep hook     Theme 2              ║
║  Least privilege            Remote ≤ local privilege     Theme 2              ║
║  Citation grounding         Context Engine map (§5.2)    Themes 6, 7          ║
║  Human review of code       F5 emits diffs only          Theme 5              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 9.1 Prompt Injection — the threat this architecture is actually shaped around

ARTEMIS reads documents, code and web results, all of which are attacker-influenceable
(LR Theme 2, Kim et al.). The defence is not detection — it is that **retrieved content
can never become an authorised instruction**:

```
   ┌────────────────────────────────────────────────────────────┐
   │ 1. PROVENANCE TAGGING                                      │
   │    Every context chunk is tagged: user | workspace-file |   │
   │    web | tool-result. Only `user` chunks may originate an   │
   │    intent. The Planner treats all others as data.           │
   ├────────────────────────────────────────────────────────────┤
   │ 2. PLAN, NOT PROSE, IS THE INTERFACE                       │
   │    The Planner emits a structured Plan. A tool call must    │
   │    be a well-formed declaration — text in a document        │
   │    cannot become one by being persuasive.                   │
   ├────────────────────────────────────────────────────────────┤
   │ 3. POLICY IS OUT-OF-BAND                                   │
   │    The Policy Engine reads the ToolCall, never the model's  │
   │    reasoning text. Nothing written in a document can        │
   │    change a verdict.                                        │
   ├────────────────────────────────────────────────────────────┤
   │ 4. THE USER IS THE LAST GATE                               │
   │    Every T2 action shows the user a concrete preview of     │
   │    what will happen — recipient, content, destination.      │
   │    An injected exfiltration attempt must survive a human    │
   │    reading it in plain language.                            │
   ├────────────────────────────────────────────────────────────┤
   │ 5. BOUNDS SHRINK THE BLAST RADIUS                          │
   │    Even a fully successful injection is confined to one     │
   │    granted workspace, cannot delete, and cannot exceed      │
   │    that workspace's egress policy.                          │
   └────────────────────────────────────────────────────────────┘
```

Layer 5 is the strongest argument for the bounded-scope hypothesis: it makes the *worst
case* bounded, not just the expected case.

### 9.2 Threat Model Summary

| Adversary | Capability assumed | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Malicious document/webpage | Injects instructions into context | §9.1 layers 1–5 | User approves a plausible-looking bad action |
| Compromised cloud LLM provider | Sees what is sent | Local-first default; per-workspace egress opt-in; redaction; egress log | Content sent under explicit opt-in |
| Cloudflare edge compromise | Sees relayed traffic, controls Worker | E2E encryption; host-side pairing confirm; DO holds no plaintext | Traffic metadata (timing, volume) |
| Stolen paired device | Holds a valid session | TTL expiry; host revocation; local-only workspaces; local approval for T2 | Actions within TTL before revocation |
| Local attacker with disk access | Reads `~/.artemis/` | SQLCipher at rest; keyring for secrets | Live-memory attack while running |
| ARTEMIS operators (us) | Run the telemetry endpoint | No user data collected by design; logs schema-fixed and opt-in | None for user content |

---

## 10. Execution / Performance Plane (cross-cutting)

The design rule: **the interactive path stays thin; everything expensive is asynchronous.**

```
   INTERACTIVE PATH — must feel immediate
   ═══════════════════════════════════════════════════════════════
     Input → Intent → Plan → Approve → Execute → Result
             (target: first token < 1s local, < 2s cloud)
   ═══════════════════════════════════════════════════════════════
                              │
                              │ never blocks on ↓
                              ▼
   BACKGROUND PATH — may take minutes, always cancellable
   ┌──────────────────────────────────────────────────────────────┐
   │                    PRIORITY WORK QUEUE                       │
   └───┬──────────┬──────────┬──────────┬──────────┬─────────────┘
       ▼          ▼          ▼          ▼          ▼
   ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
   │ File   ││ Embed  ││ RAG    ││ Model  ││ Remote │
   │ Watch  ││ Worker ││ Ingest ││ Warm   ││ Sync   │
   │ +Index ││ Pool   ││        ││        ││        │
   └────────┘└────────┘└────────┘└────────┘└────────┘
       │          │          │          │          │
       └──────────┴────┬─────┴──────────┴──────────┘
                       ▼
             progress → Control Panel
             (visible, pausable, cancellable — never a mystery spinner)
```

### 10.1 Queue Priorities

| Priority | Work | Behaviour |
| --- | --- | --- |
| P0 | User-initiated tool execution | Immediate, preempts all |
| P1 | Retrieval for an active turn | Immediate, budget-capped |
| P2 | Incremental index update for a changed file | Debounced ~2s |
| P3 | Initial workspace ingestion | Batched, throttled, resumable |
| P4 | Cache warming, maintenance, compaction | Idle only |

### 10.2 Performance Strategies

- **Incremental indexing.** File watcher → content hash → re-embed only changed chunks.
  A one-line edit re-embeds one chunk, not the file.
- **Two-stage retrieval.** Cheap vector recall (top ~50) → cross-encoder rerank (top ~8).
  Keeps the vector index small and quality high, which directly addresses the open
  question about index growth.
- **Model warm-keeping.** Local model held resident with an idle-unload timer, so first
  token isn't paying a cold load.
- **Backpressure, not queue growth.** Every queue is bounded. Full queue → shed lowest
  priority and surface it in the Control Panel. The system never silently falls behind.
- **Bounded resource envelope.** Configurable ceilings on RAM, index size and CPU share.
  ARTEMIS is a background resident on a student laptop; it must never be the reason the
  machine is slow.
- **Graceful ingestion.** Initial ingestion is resumable and throttled — the system is
  usable while it indexes, with reduced retrieval quality clearly indicated rather than
  silently degraded.

---

## 11. Process & Deployment Topology

```
   ┌───────────────────────────────────────────────────────────────────┐
   │ USER MACHINE                                                      │
   │                                                                   │
   │  ┌─────────────────────────────────────────────────────────────┐  │
   │  │ artemis-core        (Python, long-running background)       │  │
   │  │  Layers 2·3·4·5 + both planes                               │  │
   │  │  serves loopback HTTP + WebSocket, 127.0.0.1 only           │  │
   │  └──────┬──────────────────────┬───────────────────┬──────────┘  │
   │         │                      │                   │             │
   │  ┌──────▼──────┐        ┌──────▼──────┐     ┌──────▼──────────┐  │
   │  │ artemis-cli │        │ Gradio GUI  │     │ remote-bridge   │  │
   │  │ (Typer)     │        │ (browser)   │     │ (outbound WS)   │  │
   │  └─────────────┘        └─────────────┘     └──────┬──────────┘  │
   │                                                     │            │
   │  ┌─────────────────────────────────────────────┐   │            │
   │  │ ollama  (separate process, local models)    │   │            │
   │  └─────────────────────────────────────────────┘   │            │
   └─────────────────────────────────────────────────────┼────────────┘
                                                         │ outbound only
                                                         ▼
                                              Cloudflare (Worker + DO)
```

Three deliberate properties:

1. **`artemis-core` is the only process holding user data.** UIs are clients; killing a UI
   loses nothing.
2. **No inbound listening port beyond loopback.** The remote bridge dials out. There is
   no port to scan, no NAT traversal, no firewall exception.
3. **Ollama runs separately.** A model crash cannot take down the workspace layer, and
   local models can be swapped without touching ARTEMIS.

---

## 12. Traceability — Architecture ↔ Research

Every non-obvious structural decision exists because of a specific finding. This table is
the defensible core of the architecture chapter.

| Architectural decision | Driven by | Section |
| --- | --- | --- |
| Workspace Broker as sole path resolver | Bounded scope hypothesis; questionnaire workspace-trust results | §6.1 |
| Policy Engine as a distinct component | *Approval-first, configurable* finding | §5.3 |
| T3 tier structurally unavailable | "Deletes nothing" must be a property, not a promise | §5.3 |
| Undo at plan granularity | Theme 3 — recovery is meaningful at the unit the user approved | §6.2 |
| Voice normalised at Layer 2 | Theme 4 — parity by construction, not re-implementation | §4, §6 |
| Citation map through the Context Engine | Themes 6 & 7 — hallucination and citation accuracy | §5.2 |
| F5 emits diffs only | Theme 5 — code assistance requires human review | §6 |
| Local-first with per-workspace egress opt-in | Local-vs-cloud questionnaire split; privacy claim | §5.1 |
| Provenance tagging of context | Theme 2 — Kim et al., agentic attack surface | §9.1 |
| Session index + resume as Layer-4 service with no AI | Theme 1 — interruption/resumption; also lowest-risk first feature | §6 |
| DO holds no plaintext | Privacy claim must survive edge compromise | §8 |
| Remote ≤ local privilege | Least privilege; remote convenience must not widen the trust boundary | §8.2 |
| Background queue with visible progress | "Never a mystery spinner" — trust requires legibility | §10 |

---

## 13. Build Sequence (revised)

The original six stages, adjusted so that the two components Revision 2 adds are built
early — both are load-bearing, and both are cheap before there are features to retrofit.

| Stage | Deliverable | Why here |
| --- | --- | --- |
| **1** | Workspace foundation: SQLite, **Workspace Broker**, file watcher, "What ARTEMIS Knows" panel. No AI. | The boundary must exist before anything can be bounded. |
| **2** | **Policy Engine + Approval Broker + Undo Journal**, with dummy tools. | Cheap now, extremely expensive to retrofit. Provable before any model is involved. |
| **3** | AI Gateway: Model Router (Ollama + one cloud tier), Context Engine, Agent Planner, Tool Dispatcher. | Highest-risk stage — validated against gates that already work. |
| **4** | Core file features F1, F2, F4. | First real capabilities; exercise T0/T1 end to end. |
| **5** | Understanding features F3, F5 — index, retrieval, citation map. | Adds the vector index once the boundary is proven. |
| **6** | Outward features F6, F7, F8 — first T2 actions. | Egress only after gates are demonstrated. |
| **7** | F9 Speech I/O over the existing Turn Normaliser. | Should require no new gates. **If it does, Layer 2 was designed wrong** — this stage is the test of §4's parity claim. |
| **8** | Remote Access Plane. | Genuinely optional. Ship-ready product exists without it. |

Stage 2 moving ahead of the AI work is the most consequential change from Revision 1. It
means the trust machinery is testable — and demonstrable to a supervisor — before any
model non-determinism enters the system.

---

## 14. Open Questions Carried Forward

Unchanged from the prototype plan, now with the architectural decision each one blocks:

| Question | Blocks | Deadline |
| --- | --- | --- |
| Which local model size is realistic on a typical student laptop? | Model Router Tier-0 default; the resource envelope in §10.2 | Stage 3 |
| PySide vs. local webview (Gradio)? | Layer 1. *Current lean: Gradio — one view model shared with the remote PWA, which halves Layer 1 work.* | Stage 1 |
| Are local STT/TTS accurate enough to avoid cloud fallback? | Whether Layer 2 voice ever becomes a T2 egress action | Stage 7 |
| How large can a workspace index grow before retrieval or rebuild degrades? | Per-workspace index sizing; two-stage retrieval thresholds (§10.2) | Stage 5 |

New questions raised by this revision:

| Question | Blocks |
| --- | --- |
| SQLCipher, or OS-level disk encryption plus keyring only? | §9 encryption-at-rest claim |
| Is a cross-encoder reranker affordable locally, or is vector-only retrieval sufficient? | §10.2 two-stage retrieval |
| Does the DO relay need message durability, or is a live-only channel acceptable? | §8 — live-only is simpler and strengthens the "holds no data" claim |

---

## 15. Summary of Changes from Revision 1

| # | Change | Rationale |
| --- | --- | --- |
| 1 | AI Gateway decomposed into Router / Context / Policy / Planner + Dispatcher | The monolith was untestable and hard to defend academically |
| 2 | **Policy Engine added** as a first-class component with four risk tiers | Converts the approval-first research finding into enforced structure |
| 3 | Security promoted from a box to a cross-cutting plane | Security is a property of every arrow, not a stage |
| 4 | Execution/Performance added as a second cross-cutting plane | Makes the sync/async split explicit and testable |
| 5 | Remote plane drawn outside the core stack | Proves the privacy claim: removing it changes nothing locally |
| 6 | Memory formally separated from the OS/file index | The single clearest differentiator; also the clearest privacy line |
| 7 | Turn Normaliser introduced at Layer 2 | Makes voice parity structural rather than duplicated |
| 8 | Workspace Broker made the sole path resolver | Turns bounded scope from a policy into an invariant |
| 9 | Undo moved to plan granularity | Matches the unit the user actually approved |
| 10 | Prompt injection addressed as an explicit five-layer defence | Directly answers LR Theme 2's core threat |
| 11 | Build sequence reordered — trust machinery before AI | Cheap now, near-impossible to retrofit later |
| 12 | Traceability matrix added (§12) | Every structural choice ties to a cited finding |
