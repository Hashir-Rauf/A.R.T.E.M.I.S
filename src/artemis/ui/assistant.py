"""The assistant surface: asking ARTEMIS to do something, and deciding about it.

This is where four sprints of machinery become visible. The gateway plans, the
policy engine classifies, the approval broker waits and the undo journal
remembers; none of that was reachable by a person until now.

The rendering decisions here are not decoration. The approval card is the only
moment a user sees before a change happens, so it is written to be answerable
in a few seconds by someone who has not read the architecture:

* **What will not happen is stated as plainly as what will.** "Nothing is
  deleted" and "Nothing leaves this computer" are the facts that let a person
  approve quickly, and they are rendered as facts rather than reassurances.
* **Every step is listed.** The user approves twelve specific moves, not "tidy
  my folder". A collapsed summary would be easier to read and would make the
  approval meaningless.
* **Undo is offered after the fact, not promised before it.** The button
  appears once there is something to undo, with the plan it would reverse.

The class holds the pending turn between the request and the answer, because a
Gradio event handler cannot pass a Python object to the next one. That state is
UI-local: the authoritative record of what is pending lives in the approval
broker, and this is only a handle for the button to use.
"""

from __future__ import annotations

import html
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from artemis.core.actions import OUTWARD_OPS, READ_OPS, REVERSIBLE_OPS, Plan, ToolCall
from artemis.core.answer import Answer, AnswerService
from artemis.core.code_diff import CodeAssistant, DiffResult
from artemis.core.embedder import OllamaEmbedder
from artemis.core.index_worker import IndexWorker
from artemis.core.indexer import Indexer
from artemis.core.intent import CODE, DRAFT, MAIL, QUESTION, SEARCH, classify
from artemis.core.gateway import Gateway, TurnOutcome
from artemis.core.router import ModelRouter, NoModelAvailable
from artemis.core.providers import OllamaProvider
from artemis.data.store import Store
from artemis.services.drafter import DocumentDrafter
from artemis.services.mail import MailError
from artemis.services.mail import load_settings as load_mail_settings
from artemis.services.patterns import PatternWatcher
from artemis.services.resume import ResumeService
from artemis.services.search import SearchError
from artemis.services.tidy import TidyService


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _in_plain_words(step: dict[str, Any], outcome: TurnOutcome) -> str:
    """One step, written as a sentence rather than as a function call.

    The person approving this has not read the code, so `move_file(notes.pdf)`
    tells them almost nothing: it does not say where the file is going, which
    is the only part they need in order to object. Falling back to the raw
    description keeps an unrecognised operation visible rather than hidden.
    """
    describe = str(step.get("describe", ""))
    operation = describe.split("(", 1)[0]
    inside = describe[describe.find("(") + 1 : describe.rfind(")")]
    first = inside.split(",")[0].strip()

    call = next(
        (c for c in outcome.plan if c.describe() == describe),
        None,
    )
    destination = str(call.arguments.get("destination", "")) if call else ""

    if operation == "create_dir":
        return f"Make a folder called “{first}”"
    if operation in ("move_file", "rename"):
        if destination:
            folder = destination.rsplit("/", 1)[0] if "/" in destination else ""
            where = f"into “{folder}”" if folder else f"to “{destination}”"
            return f"Move {first} {where}"
        return f"Move {first}"
    if operation == "write_file":
        if call and call.arguments.get("create_only"):
            return f"Save a new file called “{first}”"
        return f"Write to {first}"
    if operation == "append_file":
        return f"Add to the end of {first}"
    if operation == "read_file":
        return f"Read {first}"
    if operation == "list_dir":
        return f"Look at what is in {first or 'this folder'}"
    if operation == "read_metadata" or operation == "stat":
        return f"Check the details of {first}"
    if operation == "search_index":
        return "Search this folder"
    if operation == "web_search":
        query = str(call.arguments.get("query", "")) if call else ""
        return f"Search the web for “{query}”" if query else "Search the web"
    if operation == "send_mail":
        to = call.arguments.get("to", []) if call else []
        who = ", ".join(to) if isinstance(to, (list, tuple)) else str(to)
        return f"Send an email to {who}" if who else "Send an email"
    return describe


def _details_html(details: dict[str, Any]) -> str:
    """The exact recipient, subject, body, query or file text, if a step has it.

    Shown under the step so the person approves what will really be sent or
    written, not a summary of it. Everything is escaped, because a mail body or
    a drafted document is text the person did not type.
    """
    if not details:
        return ""
    style = (
        'style="display:block;margin-top:6px;white-space:pre-wrap;'
        'font-size:.88em;opacity:.9"'
    )
    lines: list[str] = []
    if "to" in details:
        lines.append(f"To: {', '.join(details['to'])}")
        lines.append(f"Subject: {details.get('subject', '')}")
        lines.append("")
        lines.append(str(details.get("body", "")))
    elif "query" in details:
        lines.append(f"Search for: {details['query']}")
    elif "content_preview" in details:
        lines.append(str(details["content_preview"]))
        if details.get("truncated"):
            lines.append("… (the rest is written too; this shows the first part)")
    if not lines:
        return ""
    return f"<span {style}>{_esc(chr(10).join(lines))}</span>"


def _outcome_in_plain_words(plan, would: bool = False) -> str:
    """A plan counted by kind rather than by function name.

    `plan.summarise()` is written for logs and reads as "2 create dirs, 5 move
    files". Both the approval card and the result line show this instead, so
    the person reading them never meets an operation name. `would` picks the
    future form for something not yet approved ("create 2 folders") over the
    past form for something that ran ("2 folders created"): "This would 2
    folders created" was the sentence the person was shown before.
    """
    counts: dict[str, int] = {}
    for call in plan:
        counts[call.operation] = counts.get(call.operation, 0) + 1

    if would:
        words = {
            "create_dir": ("create {n} folder", "create {n} folders"),
            "move_file": ("move {n} file", "move {n} files"),
            "rename": ("rename {n} file", "rename {n} files"),
            "write_file": ("save {n} new file", "save {n} new files"),
            "append_file": ("add to {n} file", "add to {n} files"),
            "web_search": ("search the web", "search the web {n} times"),
            "send_mail": ("send {n} email", "send {n} emails"),
        }
    else:
        words = {
            "create_dir": ("{n} folder created", "{n} folders created"),
            "move_file": ("{n} file moved", "{n} files moved"),
            "rename": ("{n} file renamed", "{n} files renamed"),
            "write_file": ("{n} file saved", "{n} files saved"),
            "append_file": ("{n} file added to", "{n} files added to"),
            "web_search": ("searched the web", "searched the web {n} times"),
            "send_mail": ("{n} email sent", "{n} emails sent"),
        }
    parts = []
    for operation, count in counts.items():
        fallback = operation.replace("_", " ")
        singular, plural = words.get(operation, (fallback, fallback))
        parts.append((singular if count == 1 else plural).format(n=count))
    return ", ".join(parts) if parts else "nothing"


def _plain_reason(reason: str) -> str:
    """A refusal reason a person can follow, not a policy rule name."""
    lowered = reason.lower()
    if "outside" in lowered:
        return "it would reach outside the folders ARTEMIS can see"
    if "destroys data" in lowered or "not available" in lowered:
        return "ARTEMIS never deletes or overwrites files"
    if "already exists" in lowered or "create_only" in lowered:
        return "a file with that name already exists"
    if "no handler" in lowered:
        return "ARTEMIS cannot do that yet"
    return reason.rstrip(".")


def _draft_filename(request: str) -> str:
    """A short file name for a draft, from the words of the request."""
    skip = {
        "a", "an", "the", "one", "page", "from", "my", "of", "for", "on", "about",
        "please", "draft", "write", "compose", "create", "make", "me", "up", "and",
        "to", "with", "using", "short", "new", "first", "based", "into", "in",
    }
    words = [w for w in re.findall(r"[A-Za-z0-9]+", request.lower()) if w not in skip]
    return "-".join(words[:4]) or "draft"


#: Input that is plainly not a request for work. Matched whole, lowercased and
#: stripped of punctuation, so "tidy" or "hide this file" never match.
_GREETINGS = frozenset({
    "hi", "hey", "hello", "yo", "hiya", "howdy",
    "good morning", "good afternoon", "good evening",
    "thanks", "thank you", "ty", "cheers", "ok", "okay", "k",
    "test", "testing", "ping",
})

_HELP_WORDS = frozenset({
    "help", "what can you do", "what do you do", "how does this work",
    "what is this", "who are you", "?",
})


#: Phrasings that mean "tidy this folder". Routed to the deterministic tidy
#: service rather than the model: the grouping rule is exact, so a model adds
#: latency and a chance of error for no benefit. Matched on the whole input, so
#: "tidy up the invoices and email them" still goes to the planner.
_TIDY_PHRASES = frozenset({
    "tidy", "tidy up", "tidy this folder", "tidy up this folder",
    "tidy the folder", "tidy up the folder", "tidy my folder",
    "clean up", "clean up this folder", "clean this folder",
    "organise this folder", "organize this folder",
    "sort this folder", "sort out this folder",
})


#: How many changed files to list in a chat answer before summarising.
MAX_CHANGES_IN_CHAT = 8


#: Phrasings that mean "what changed since I was last here". Routed to the
#: resume service, which replays recorded facts and involves no model at all.
#:
#: Without this the planner receives the question, cannot see the folder, and
#: answers `list_dir`, which reads the directory and reports nothing about what
#: changed. The deterministic answer is both correct and instant, and this
#: feature matters most exactly when the user cannot remember what they were
#: doing, so a plausible reconstruction would be worse than useless.
_RESUME_PHRASES = frozenset({
    "what changed", "what changed recently", "what has changed",
    "what's changed", "whats changed", "what changed since last time",
    "what did i do", "what was i doing", "what was i working on",
    "where did i leave off", "where was i", "pick up where i left off",
    "catch me up", "what happened", "recent changes",
})


def _is_off_topic(outcome: TurnOutcome) -> bool:
    """Whether a plan is the planner guessing at a request about nothing local.

    True only when every step leaves the machine and none of them names a file.
    A genuine outward request keeps its approval card: "email my notes to my
    supervisor" names a file and is a real, if consequential, instruction.
    """
    calls = outcome.plan.calls
    if not calls:
        return False
    return all(
        call.operation in OUTWARD_OPS and not call.paths for call in calls
    )


class _Markup(str):
    """A string that is already safe HTML.

    A separate type rather than a boolean, so a value that must not be escaped
    cannot be passed to the escaping path by accident: the distinction travels
    with the value.
    """


#: How many entries to list before saying "and N others".
MAX_LISTED_IN_CHAT = 20

#: How much of a file to quote back when it was read.
MAX_QUOTED_CHARS = 700


def _render_finding(call: ToolCall, value: object) -> str:
    """Turn one read result into a sentence a person can use.

    Each read operation returns a different shape, so each is described in its
    own terms: a listing is a list, a file is its text, metadata is a fact. The
    alternative, printing the operation name and a count, tells the user the
    machine did something without telling them what it found.
    """
    where = call.paths[0] if call.paths else "."
    pretty = "this folder" if where in (".", "") else where

    if call.operation == "list_dir" and isinstance(value, (list, tuple)):
        if not value:
            return f"There is nothing in {_esc(pretty)}."
        shown = [str(v) for v in value[:MAX_LISTED_IN_CHAT]]
        more = len(value) - len(shown)
        rows = "".join(
            f'<div class="a-file-name">{_esc(name)}</div>' for name in shown
        )
        if more > 0:
            rows += f'<div class="a-change">and {_plural(more, "other")}</div>'
        return (
            f"{_plural(len(value), 'thing')} in {_esc(pretty)}:"
            f'<div class="a-changes">{rows}</div>'
        )

    if call.operation == "read_file" and isinstance(value, str):
        if not value.strip():
            return f"{_esc(pretty)} is empty."
        text = value[:MAX_QUOTED_CHARS]
        clipped = " (shortened)" if len(value) > MAX_QUOTED_CHARS else ""
        return (
            f"{_esc(pretty)} says{clipped}:"
            f'<div class="a-quote">{_esc(text)}</div>'
        )

    if call.operation in ("stat", "read_metadata") and isinstance(value, dict):
        facts = ", ".join(f"{_esc(k)} {_esc(v)}" for k, v in list(value.items())[:6])
        return f"{_esc(pretty)}: {facts}."

    if isinstance(value, (list, tuple)):
        return f"Found {_plural(len(value), 'result')} in {_esc(pretty)}."

    return ""


#: Words that mean the user is asking for something ARTEMIS cannot do, mapped
#: to the explanation. Answered before planning, because the honest reply is a
#: sentence about the boundary rather than a plan that works around it.
#:
#: Asking to delete used to return a directory listing: the planner substituted
#: the nearest permitted operation, so the user was shown a plan that quietly
#: was not what they asked for. Saying so outright is both clearer and the
#: feature working as designed.
_REFUSAL_WORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("delete", "remove", "erase", "wipe", "get rid of", "trash", "shred"),
        "ARTEMIS cannot delete anything. There is no delete in it at all, so "
        "nothing it does can lose a file. You can move files somewhere else, "
        "and undo it afterwards if you change your mind.",
    ),
    (
        ("overwrite", "replace the contents", "truncate", "empty the file"),
        "ARTEMIS will not overwrite a file in place, because that cannot be "
        "undone. It can write to a new file instead.",
    ),
)


def _boundary_reply(text: str) -> str | None:
    """An explanation when the request is outside what ARTEMIS can do.

    Matched on substrings rather than whole input, because "delete the old
    invoices" is as much a deletion request as "delete everything", and both
    deserve the same answer.
    """
    lowered = text.strip().lower()
    for words, explanation in _REFUSAL_WORDS:
        if any(word in lowered for word in words):
            return explanation
    return None


def _conversational_reply(text: str) -> str | None:
    """An answer for input that is not a task, or None to plan normally.

    Exists because sending a greeting to a local model takes about fifteen
    seconds and cannot produce a file operation. Answering instantly is both
    faster and more honest than a failed planning pass.
    """
    cleaned = text.strip().lower().rstrip("!.?").strip()
    if cleaned in _GREETINGS:
        return (
            "Hello. Tell me what you would like done with a folder, for example "
            "\u201ctidy up this folder\u201d, or use one of the buttons above."
        )
    if cleaned in _HELP_WORDS:
        return (
            "ARTEMIS works inside folders you have added. It can tidy a folder, "
            "tell you what changed since last time, and notice tasks you repeat. "
            "It shows every step and never changes anything until you approve it."
        )
    return None


@dataclass
class AssistantState:
    """What the surface is holding between one click and the next."""

    outcome: TurnOutcome | None = None
    last_plan_id: str | None = None
    last_summary: str = ""
    #: The last plan that ran, in plain words, for the line under the buttons.
    last_words: str = ""
    last_workspace_id: int | None = None


class AssistantPanel:
    """Renders the conversation, the approval card, and what happened."""

    def __init__(self, store: Store) -> None:
        self._store = store
        self._router = ModelRouter(store=store)
        self._router.register(OllamaProvider())
        self._gateway = Gateway.build(store, self._router)
        self._resume = ResumeService(store, self._gateway.broker)
        self._tidy = TidyService(store, self._gateway.broker)
        self._patterns = PatternWatcher(store)
        self._indexer = Indexer(store, self._gateway.broker)
        self._drafter = DocumentDrafter(store, self._gateway.broker, self._router)
        self._code = CodeAssistant(self._gateway.broker, self._router)
        # Meaning-based search is optional. It needs numpy and an embedding
        # model on this computer; without either, answers fall back to matching
        # file names, which is the documented behaviour, not a failure.
        self._index_worker: IndexWorker | None = None
        vectors = None
        try:
            from artemis.core.vector_index import VectorIndex

            vectors = VectorIndex(store, self._gateway.broker, OllamaEmbedder())
            self._index_worker = IndexWorker(store, vectors)
        except ImportError:
            pass
        self._answers = AnswerService(
            self._gateway.context_engine,
            self._gateway.broker,
            self._router,
            vectors,
        )
        self.state = AssistantState()

    # -- asking ------------------------------------------------------------

    def _prepare(self, workspace_id: int | None, text: str):
        """Decide how a typed request is answered.

        Returns ("now", (conversation, card)) for an answer that needs no model,
        or ("work", job) where `job(on_token)` does the model work and returns
        the same pair. Keeping the decision in one place means `ask` and
        `ask_streaming` cannot route the same words differently.
        """
        text = (text or "").strip()
        if not workspace_id:
            if self._store.list_workspaces():
                return "now", (self._say("Choose a folder from the list first."), "")
            return "now", (
                self._say(
                    "There is no folder to work in yet. Open the Folders tab, "
                    "add one, then come back here."
                ),
                "",
            )
        if not text:
            return "now", (self._say("Type what you would like ARTEMIS to do."), "")

        chat = _conversational_reply(text)
        if chat is not None:
            return "now", (self._say(chat), "")

        # Tidying is a rule, not a judgement. Answer it directly.
        cleaned = text.strip().lower().rstrip("!.?").strip()
        if cleaned in _TIDY_PHRASES:
            return "now", self.suggest_tidy(workspace_id)

        # "What changed?" is a question about recorded facts, not a plan.
        if cleaned in _RESUME_PHRASES:
            return "now", self.answer_what_changed(workspace_id)

        # Say what ARTEMIS cannot do, rather than planning something adjacent.
        refusal = _boundary_reply(text)
        if refusal is not None:
            return "now", (self._say(refusal, warn=True), "")

        outside = self._outside_reference(workspace_id, text)
        if outside is not None:
            return "now", (self._say(outside, warn=True), "")

        files = [row["rel_path"] for row in self._store.list_files(workspace_id)]
        intent = classify(text, files)

        if intent.kind == SEARCH:
            return "now", self._propose_search(workspace_id, intent)
        if intent.kind == MAIL:
            if not intent.recipients:
                return "now", (
                    self._say(
                        "Who should it go to? Include their email address, for "
                        "example: email sam@example.com to say I will be late."
                    ),
                    "",
                )
            return "work", lambda on_token: self._propose_mail(workspace_id, intent)
        if intent.kind == DRAFT:
            return "work", lambda on_token: self._propose_draft(workspace_id, intent)
        if intent.kind == CODE and intent.file:
            return "work", lambda on_token: self._suggest_code_change(workspace_id, intent)
        if intent.kind == QUESTION:
            return "work", lambda on_token: self._answer_question(workspace_id, intent)

        return "work", lambda on_token: self._render_outcome(
            self._gateway.handle(workspace_id, text, on_token=on_token), text
        )

    def ask_streaming(self, workspace_id: int | None, text: str):
        """`ask`, but yielding progress while the model works.

        Yields the same (conversation, approval card) pair that `ask` returns,
        several times: a thinking line that updates as output arrives, then the
        real answer. The work is not faster. What changes is that the page shows
        something after about a second instead of greying out for six.

        The work is blocking, so it runs on a worker thread and reports progress
        through a queue. Every decision still happens inside the gateway on that
        thread; this method only renders what it reports.
        """
        mode, payload = self._prepare(workspace_id, text)
        if mode == "now":
            yield payload
            return

        progress: queue.Queue[int] = queue.Queue()
        box: dict[str, Any] = {}

        def work() -> None:
            try:
                box["result"] = payload(lambda cycle, pieces: progress.put(pieces))
            except BaseException as exc:  # reported, never swallowed
                box["error"] = exc
            finally:
                progress.put(-1)

        worker = threading.Thread(target=work, daemon=True)
        worker.start()

        started = time.monotonic()
        pieces = 0
        yield self._thinking(0, 0.0), ""

        while True:
            try:
                item = progress.get(timeout=0.25)
            except queue.Empty:
                yield self._thinking(pieces, time.monotonic() - started), ""
                continue
            if item < 0:
                break
            pieces = item
            yield self._thinking(pieces, time.monotonic() - started), ""

        worker.join()

        error = box.get("error")
        if isinstance(error, NoModelAvailable):
            yield self._say(f"No model is available right now. {error}", warn=True), ""
            return
        if error is not None:
            yield self._say(f"Something went wrong: {error}", warn=True), ""
            return

        yield box["result"]

    @staticmethod
    def _thinking(pieces: int, elapsed: float) -> str:
        """The line shown while the model is still producing its answer.

        It reports elapsed time rather than a percentage, because there is no
        honest way to know how much is left: the model stops when it stops.
        """
        detail = f"{elapsed:.0f}s" if pieces == 0 else f"{elapsed:.0f}s, still writing"
        return (
            '<div class="a-msg a-thinking">'
            '<span class="a-dots"><i></i><i></i><i></i></span>'
            f"Working on it ({_esc(detail)})"
            "</div>"
        )

    # -- reaching outside the folder --------------------------------------

    def _outside_reference(self, workspace_id: int, text: str) -> str | None:
        """An explanation if the request names a path outside the folder.

        Checked before any model is asked. The boundary would stop such a step
        anyway, but a request to read "../Private/passwords.txt" used to come
        back as "I could not turn that into steps", which does not tell the
        person why, and "Nothing ran", which does not tell them anything.
        """
        row = self._store.get_workspace(workspace_id)
        if row is None:
            return None
        root = Path(row["root"]).resolve()
        reaches = bool(re.search(r"(^|[\s\"'(])\.\.[\\/]", text))
        for match in re.finditer(r"[A-Za-z]:[\\/][^\s\"']*|\\\\[^\s\"']+", text):
            try:
                Path(match.group()).resolve().relative_to(root)
            except (ValueError, OSError):
                reaches = True
        if not reaches:
            return None
        return (
            f"ARTEMIS can only see inside the folders you have added. That "
            f"reaches outside “{row['name']}”, so it was not done. "
            "Nothing was read, moved or changed."
        )

    # -- questions, code, drafts, mail and search -------------------------

    def _answer_question(self, workspace_id: int, intent) -> tuple[str, str]:
        """Answer a question from the folder's files, labelling what is unsupported."""
        self.state.outcome = None
        answer = self._answers.ask(workspace_id, intent.text)
        return self._answer_html(answer), ""

    def _answer_html(self, answer: Answer) -> str:
        if not answer.claims:
            return self._say(
                answer.text or "I could not find anything in these files to answer that.",
                warn=True,
            )
        rows = []
        for claim in answer.claims:
            if claim.supported:
                rows.append(
                    f'<div class="a-claim">{_esc(claim.text)} '
                    f'<span class="a-cite">{_esc(", ".join(claim.sources))}</span></div>'
                )
            else:
                rows.append(
                    '<div class="a-claim a-unsupported"><span class="a-flag">'
                    f"not found in your files</span> {_esc(claim.text)}</div>"
                )
        if answer.sources:
            foot = "Sources: " + ", ".join(answer.sources)
        else:
            foot = "None of this is backed by a file, so treat it with care."
        return self._show(
            "".join(rows) + f'<div class="a-card-meta">{_esc(foot)}</div>'
        )

    def _suggest_code_change(self, workspace_id: int, intent) -> tuple[str, str]:
        """Show a proposed change to one file as a diff. Never edits it."""
        self.state.outcome = None
        result = self._code.ask(workspace_id, intent.file, intent.text)
        return self._diff_html(result, intent.file), ""

    def _diff_html(self, result: DiffResult, path: str) -> str:
        if not result.ok:
            return self._say(
                f"I could not suggest a safe change to {path}: {result.message}.",
                warn=True,
            )
        if not result.diff:
            return self._say(f"No change is needed in {path}.")
        lines = []
        for line in result.diff.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                kind = "a-d-head"
            elif line.startswith("@@"):
                kind = "a-d-hunk"
            elif line.startswith("+"):
                kind = "a-d-add"
            elif line.startswith("-"):
                kind = "a-d-del"
            else:
                kind = "a-d-ctx"
            lines.append(f'<div class="{kind}">{_esc(line) or "&nbsp;"}</div>')
        return self._show(
            f"A proposed change to {_esc(path)}:"
            f'<div class="a-diff">{"".join(lines)}</div>'
            '<div class="a-card-meta">This is a proposal only. ARTEMIS has not '
            "changed your file, and it never edits code itself.</div>"
        )

    def _propose_draft(self, workspace_id: int, intent) -> tuple[str, str]:
        """Write a first draft and offer to save it as a new file."""
        passages = self._answers.read_passages(workspace_id, intent.text)
        context = self._gateway.context_engine.assemble(
            workspace_id, intent.text, retrieved=passages
        )
        content = self._drafter.generate(workspace_id, intent.text, context)
        if not content.strip():
            return self._say("The model did not write anything. Try again.", warn=True), ""
        plan = self._drafter.propose(workspace_id, _draft_filename(intent.text), content)
        outcome = self._gateway.submit_plan(workspace_id, plan, intent.text)
        return self._render_outcome(outcome, intent.text, from_service=True)

    def _propose_mail(self, workspace_id: int, intent) -> tuple[str, str]:
        """Write the email, then hold it for approval with its exact text."""
        subject, body = self._write_mail(workspace_id, intent)
        if not body:
            return self._say(
                "I could not write that email. Try saying what it should say.",
                warn=True,
            ), ""
        try:
            plan = self._gateway.mail.compose(
                workspace_id, list(intent.recipients), subject, body
            )
        except MailError as exc:
            return self._say(f"That email cannot be sent: {exc}.", warn=True), ""
        note = ""
        if load_mail_settings() is None:
            note = (
                " No mail account is set up yet, so sending will fail until one is."
            )
        outcome = self._gateway.submit_plan(workspace_id, plan, intent.text)
        return self._render_outcome(outcome, intent.text, from_service=True, note=note)

    def _write_mail(self, workspace_id: int, intent) -> tuple[str, str]:
        prompt = (
            "Write a short, polite email for the user. Reply in exactly this "
            "format and nothing else:\nSUBJECT: <one line>\nBODY:\n<the email>\n"
            "Do not use placeholders such as [Name]. End with the word Thanks.\n\n"
            f"The user asked: {intent.text}\n"
        )
        decision = self._router.complete(workspace_id, prompt, max_tokens=400)
        reply = decision.completion.text.strip()
        match = re.search(r"SUBJECT:\s*(.+?)\s*\n+\s*BODY:\s*(.+)", reply, re.S | re.I)
        if not match:
            return "", ""
        return match.group(1).strip(), match.group(2).strip()

    def _propose_search(self, workspace_id: int, intent) -> tuple[str, str]:
        """Hold a web search for approval. It does not search until approved."""
        try:
            plan = self._gateway.search.propose(workspace_id, intent.query)
        except SearchError as exc:
            return self._say(f"That search cannot be done: {exc}.", warn=True), ""
        outcome = self._gateway.submit_plan(workspace_id, plan, intent.text)
        return self._render_outcome(outcome, intent.text, from_service=True)

    def index_in_background(self, workspace_id: int | None) -> None:
        """Index a folder for meaning-based search without making anyone wait."""
        if workspace_id and self._index_worker is not None:
            self._index_worker.start(workspace_id)

    def _render_outcome(
        self,
        outcome: TurnOutcome,
        text: str,
        from_service: bool = False,
        note: str = "",
    ) -> tuple[str, str]:
        """Turn a finished turn into what the page shows.

        Shared by every route so a plan that needs approval looks identical
        whichever one produced it.
        """
        self.state.outcome = outcome

        # Checked before the approval card is built, and only for plans the
        # *model* made. A plan whose only step leaves the machine, for a request
        # that never mentioned the folder, is the planner reaching for the one
        # operation that could answer anything: "sing me a song" became a web
        # search with an egress warning to approve. A plan a service built after
        # the user asked for a search or an email is exactly what was asked for.
        if not from_service and _is_off_topic(outcome):
            self.state.outcome = None
            return self._say(
                "That is outside what ARTEMIS does. It works with the files in "
                "folders you have added: tidying them up, answering questions "
                "about them, and finding things in them."
            ), ""

        if outcome.needs_approval:
            # Say what the plan would do, not what the user typed. Echoing the
            # request back tells them nothing they do not already know, and the
            # question being asked is about the consequences.
            message = f"This would {_outcome_in_plain_words(outcome.plan, would=True)}."
            message += " Nothing has happened yet." + note
            if outcome.refusals:
                message += (
                    f" {_plural(len(outcome.refusals), 'step')} will be skipped: "
                    + _plain_reason(outcome.refusals[0]) + "."
                )
            return self._say(message), self.approval_html(outcome)

        # A model that is not running is not an unclear request. Saying "I
        # could not turn that into steps" here sends the user off to rephrase a
        # request that was perfectly clear.
        if outcome.planning is not None and outcome.planning.no_model:
            return self._say(
                "ARTEMIS could not reach the model on this computer, so it "
                "cannot work out what to do. Check that Ollama is running, "
                "then try again. Tidying up and checking what changed still "
                "work without it.",
                warn=True,
            ), ""

        if not outcome.plan.calls:
            # `outcome.notes` holds planner diagnostics such as "pass 1: no
            # usable steps in the reply". Those belong in the audit log, not in
            # front of a person: they describe the planner's internals rather
            # than telling the user anything they can act on.
            return self._say(
                "I could not turn that into steps I am allowed to take. ARTEMIS "
                "works with files inside your folders. Try something like "
                "“move the PDFs into a folder called Finance”, or ask a "
                "question about a file.",
                warn=True,
            ), ""

        if outcome.result is not None:
            self._after_run(outcome, outcome.result)
        described = self._describe_result(outcome)
        if outcome.result is not None and outcome.result.executed and any(
            v.remembered for v in outcome.verdicts.values()
        ):
            described = _Markup(
                (described if isinstance(described, _Markup) else _esc(described))
                + " "
                + _esc("You chose not to be asked about this kind of change here.")
            )
        if isinstance(described, _Markup):
            return self._show(described), ""
        return self._say(described), ""

    def _after_run(self, outcome: TurnOutcome, result) -> None:
        """Bookkeeping once a plan has run, shared by every way a plan can run.

        Only a plan that changed files can be undone, so only then is it offered
        for undo. The index is refreshed straight away: it used to be left
        showing a moved file at its old place until someone pressed "Check for
        changes", which made ARTEMIS look wrong about its own work.
        """
        ran = set(result.executed)
        changed = [
            c for c in outcome.plan if c.call_id in ran and c.operation in REVERSIBLE_OPS
        ]
        if not changed:
            return
        workspace_id = changed[0].workspace_id
        self.state.last_plan_id = outcome.plan.plan_id
        self.state.last_summary = outcome.plan.summarise()
        self.state.last_words = _outcome_in_plain_words(Plan(calls=tuple(changed)))
        self.state.last_workspace_id = workspace_id
        self._rescan(workspace_id)
        # Snapshot after the change, so "what changed?" reports what ARTEMIS
        # just did rather than comparing against a folder it has already moved.
        self._resume.checkpoint(
            workspace_id,
            recent_files=[path for call in changed for path in call.paths],
        )
        self.index_in_background(workspace_id)

    def _rescan(self, workspace_id: int) -> None:
        try:
            self._indexer.scan(workspace_id)
        except Exception:  # pragma: no cover - a stale index is not worth a crash
            pass

    def ask(self, workspace_id: int | None, text: str) -> tuple[str, str]:
        """Send a request. Returns (conversation, approval card).

        Nothing here decides anything. If the plan needs approval the card is
        rendered and the turn is held; if it does not, the gateway has already
        run the reads and this reports what came back.
        """
        mode, payload = self._prepare(workspace_id, text)
        if mode == "now":
            return payload
        try:
            return payload(None)
        except NoModelAvailable as exc:
            return self._say(
                f"No model is available right now. {exc}", warn=True
            ), ""
        except Exception as exc:  # pragma: no cover - surfaced, never swallowed
            return self._say(f"Something went wrong: {exc}", warn=True), ""

    def _describe_result(self, outcome: TurnOutcome) -> str:
        """Report what a turn found, not merely that it ran.

        A read whose answer is thrown away has not answered anything. Asking
        "what files do I have" used to execute a directory listing and reply
        "Done: 1 list dir", which is both jargon and a non-answer: the listing
        was sitting in the result the whole time. Reads now show what they
        found; changes still report what they did, because for those the fact
        of the change is the answer.
        """
        result = outcome.result
        if result is None:
            return "Nothing to do."
        if not result.executed:
            if outcome.refusals:
                return _Markup(
                    _esc("Nothing was done: " + _plain_reason(outcome.refusals[0]) + ".")
                )
            return "Nothing ran."

        found = self._describe_findings(outcome)
        if found:
            # Already-escaped markup, so it is returned as a marked string the
            # caller shows without escaping a second time.
            return _Markup(found)

        return _Markup(self._run_report(outcome.plan, result))

    def _run_report(self, plan: Plan, result, remember: bool = False) -> str:
        """What a plan really did, as escaped markup.

        Built from the steps that ran, never from the plan as proposed. It used
        to say "Done: 1 file moved" for a move the boundary had blocked, because
        the sentence was counted from the plan. A message that claims a change
        which did not happen is worse than no message.
        """
        ran = set(result.executed)
        done = Plan(calls=tuple(c for c in plan if c.call_id in ran), intent=plan.intent)
        lines: list[str] = []

        plain = [c for c in done if c.operation not in ("web_search", "send_mail")]
        if plain:
            lines.append(_esc("Done: " + _outcome_in_plain_words(Plan(calls=tuple(plain), intent=plan.intent)) + "."))

        for call in done:
            value = result.results.get(call.call_id)
            if call.operation == "web_search" and isinstance(value, list):
                lines.append(self._search_results_html(call, value))
            elif call.operation == "send_mail":
                sent_to = value.get("sent_to", []) if isinstance(value, dict) else []
                who = ", ".join(sent_to) or "the recipient"
                lines.append(_esc(f"Email sent to {who}."))

        skipped = [c for c in plan if c.call_id in set(result.skipped)]
        if skipped:
            reasons = []
            for call in skipped:
                why = result.results.get(call.call_id)
                reason = why.get("refused", "") if isinstance(why, dict) else ""
                reasons.append(_plain_reason(str(reason)) if reason else "it could not run")
            unique = "; ".join(dict.fromkeys(reasons))
            if not done:
                lines.insert(0, _esc("Nothing was changed."))
            lines.append(_esc(f"{_plural(len(skipped), 'step')} did not run: {unique}."))
        if not lines:
            lines.append(_esc("Nothing ran."))
        if remember and done:
            lines.append(_esc("I will not ask again for this kind of change in this folder."))
        return " ".join(lines)

    @staticmethod
    def _search_results_html(call: ToolCall, results: list) -> str:
        query = str(call.arguments.get("query", ""))
        if not results:
            return _esc(f"The search for “{query}” found nothing.")
        rows = "".join(
            '<div class="a-claim">'
            f'<strong>{_esc(r.get("title", ""))}</strong><br>'
            f'<span class="a-cite">{_esc(r.get("url", ""))}</span><br>'
            f'{_esc(r.get("snippet", ""))}</div>'
            for r in results
        )
        return f"Results for “{_esc(query)}”:<div class=\"a-changes\">{rows}</div>"

    def _describe_findings(self, outcome: TurnOutcome) -> str:
        """What the reads in this plan actually returned, in plain words.

        Returns "" when the plan read nothing, so the caller falls back to
        describing the change instead.
        """
        result = outcome.result
        if result is None or not isinstance(result.results, dict):
            return ""

        pieces: list[str] = []
        for call in outcome.plan.calls:
            if call.operation not in READ_OPS:
                continue
            value = result.results.get(call.call_id)
            if value is None:
                continue
            rendered = _render_finding(call, value)
            if rendered:
                pieces.append(rendered)

        return " ".join(pieces)

    # -- deciding ----------------------------------------------------------

    def approve(self, remember: bool = False) -> tuple[str, str]:
        """Run the held plan. The approval broker records the decision first."""
        outcome = self.state.outcome
        if outcome is None or not outcome.needs_approval:
            return self._say("There is nothing waiting for an answer.", warn=True), ""

        result = self._gateway.approve_and_run(outcome, remember=remember)
        self.state.outcome = None
        self._after_run(outcome, result)
        return self._show(self._run_report(outcome.plan, result, remember=remember)), ""

    def reject(self) -> tuple[str, str]:
        outcome = self.state.outcome
        if outcome is None or not outcome.needs_approval:
            return self._say("There is nothing waiting for an answer.", warn=True), ""

        self._gateway.reject(outcome, reason="declined in the interface")
        self.state.outcome = None
        return self._say("Left alone. Nothing was changed."), ""

    def undo_last(self) -> str:
        """Reverse the last executed plan, as one unit."""
        plan_id = self.state.last_plan_id
        if not plan_id:
            return self._say("There is nothing to undo.", warn=True)

        reversed_count, problems = self._gateway.undo(plan_id)
        self.state.last_plan_id = None
        self.state.last_words = ""
        if self.state.last_workspace_id:
            self._rescan(self.state.last_workspace_id)
            # Undoing is ARTEMIS's own change, like the plan it takes back, so
            # the "what changed" baseline moves too. Otherwise the files coming
            # back were reported as 12 new and 12 gone, as if somebody else had
            # done it.
            self._resume.checkpoint(self.state.last_workspace_id)

        if problems:
            return self._say(
                f"Undid {_plural(reversed_count, 'step')}, but "
                f"{_plural(len(problems), 'step')} could not be reversed: "
                + "; ".join(problems[:2]),
                warn=True,
            )
        return self._say(
            f"Undone. {_plural(reversed_count, 'step')} reversed, and your files "
            "are back as they were."
        )

    @property
    def can_undo(self) -> bool:
        return self.state.last_plan_id is not None

    def welcome_html(self) -> str:
        """What a person with no folders yet is told to do first."""
        return self._say(
            "Welcome. ARTEMIS cannot see any folder yet. Open the Folders tab and "
            "add one, then come back here to tidy it, ask about its files, or "
            "draft something from them."
        )

    @property
    def has_pending(self) -> bool:
        """Whether a plan is waiting for the person to answer it.

        The page shows the Approve and No buttons from this, read after the
        answer has finished, rather than from a visibility flag carried inside a
        streamed answer. The flag was dropped on the streamed path, which left a
        card asking "Approve these changes?" with nothing to press.
        """
        outcome = self.state.outcome
        return outcome is not None and outcome.needs_approval

    # -- rendering ---------------------------------------------------------

    @staticmethod
    def _say(message: str, warn: bool = False) -> str:
        """A plain message. The text is escaped, so it is always safe.

        Anything containing markup ARTEMIS built itself goes through `_show`
        instead. Keeping the default escaping matters because these messages
        quote filenames and file contents, which are not trustworthy input.
        """
        tone = "a-msg warn" if warn else "a-msg"
        return f'<div class="{tone}">{_esc(message)}</div>'

    @staticmethod
    def _show(markup: str) -> str:
        """A message whose parts were escaped as they were assembled.

        Used for findings, where the structure is ARTEMIS's own markup and only
        the values inside it came from the filesystem. Every value is escaped by
        `_render_finding` at the point it is inserted, so nothing reaches here
        unescaped.
        """
        return f'<div class="a-msg">{markup}</div>'

    def approval_html(self, outcome: TurnOutcome) -> str:
        """The card a person reads before anything happens.

        Written so the three questions that actually matter are answered above
        the step list: can this be undone, does anything leave the computer, is
        anything deleted.
        """
        preview: dict[str, Any] | None = outcome.preview
        if preview is None:
            return ""

        risk_word = {
            "T0": "reads only",
            "T1": "changes files, and can be undone",
            "T2": "sends something off this computer",
        }.get(preview["risk"], preview["risk"])

        facts = [
            ("Folder", preview["workspace"]),
            ("What it does", _outcome_in_plain_words(outcome.plan, would=True).capitalize()),
            ("Risk", risk_word),
        ]
        fact_rows = "".join(
            f'<span class="a-fact-k">{_esc(k)}</span>'
            f'<span class="a-fact-v">{_esc(v)}</span>'
            for k, v in facts
        )

        assurances = []
        if not preview["deletes_anything"]:
            assurances.append("Nothing is deleted")
        if not preview["leaves_machine"]:
            assurances.append("Nothing leaves this computer")
        if preview["reversible"]:
            assurances.append("You can undo this afterwards")
        assurance_html = "".join(
            f'<span class="a-assure">{_esc(a)}</span>' for a in assurances
        )

        steps = "".join(
            f'<div class="a-step"><span class="a-step-n">{i}</span>'
            f'<span class="a-step-t">{_esc(_in_plain_words(step, outcome))}'
            f'{_details_html(step.get("details") or {})}</span>'
            "</div>"
            for i, step in enumerate(preview["steps"], start=1)
        )

        skipped_html = ""
        if outcome.refusals:
            reasons = "; ".join(dict.fromkeys(_plain_reason(r) for r in outcome.refusals))
            skipped_html = (
                '<div class="a-warn-line">'
                f"{_esc(_plural(len(outcome.refusals), 'step'))} will be skipped: "
                f"{_esc(reasons)}.</div>"
            )

        return (
            '<div class="a-approval">'
            '<div class="a-approval-head">Approve these changes?</div>'
            '<div class="a-approval-sub">Nothing has happened yet. Read the '
            "steps, then choose below.</div>"
            f'<div class="a-facts">{fact_rows}</div>'
            f'<div class="a-assures">{assurance_html}</div>'
            f"{skipped_html}"
            f'<div class="a-steps-head">Every step, in order</div>'
            f'<div class="a-steps">{steps}</div>'
            "</div>"
        )

    def answer_what_changed(self, workspace_id: int | None) -> tuple[str, str]:
        """Answer "what changed?" in the conversation, from recorded facts.

        The sidebar already shows this, but a question typed into the box has to
        be answered in the box: sending the user to look elsewhere for the
        answer is not answering. No model is involved, so this is immediate and
        every line of it is a fact rather than a reconstruction.
        """
        if not workspace_id:
            return self._say("Choose a folder first."), ""

        report = self._resume.report(workspace_id)
        lines = [_esc(report.summary())]

        if report.changes:
            shown = report.changes[:MAX_CHANGES_IN_CHAT]
            rows = "".join(
                f'<div class="a-change a-{_esc(c.change)}">{_esc(c.describe())}</div>'
                for c in shown
            )
            more = len(report.changes) - len(shown)
            if more > 0:
                rows += f'<div class="a-change">and {_plural(more, "other")}</div>'
            lines.append(f'<div class="a-changes">{rows}</div>')

        if report.recent_files:
            files = ", ".join(_esc(name) for name in report.recent_files[:5])
            lines.append(f'<div class="a-change">Last worked on: {files}</div>')

        return f'<div class="a-msg">{"".join(lines)}</div>', ""

    # -- the other two features --------------------------------------------

    def resume_html(self, workspace_id: int | None) -> str:
        """What changed since this folder was last open."""
        if not workspace_id:
            return ""
        report = self._resume.report(workspace_id)

        changes = ""
        if report.changes:
            shown = report.changes[:8]
            rows = "".join(
                f'<div class="a-change a-{_esc(c.change)}">{_esc(c.describe())}</div>'
                for c in shown
            )
            more = len(report.changes) - len(shown)
            if more > 0:
                rows += f'<div class="a-change">and {_plural(more, "other")}</div>'
            changes = f'<div class="a-changes">{rows}</div>'

        proposals = ""
        if report.open_proposals:
            items = "".join(
                f'<div class="a-change">{_esc(p)}</div>' for p in report.open_proposals
            )
            proposals = (
                '<div class="a-steps-head">ARTEMIS noticed</div>'
                f'<div class="a-changes">{items}</div>'
            )

        last = ""
        if (
            self.state.last_plan_id
            and self.state.last_words
            and self.state.last_workspace_id == workspace_id
        ):
            last = (
                '<div class="a-resume-line">ARTEMIS last did this here: '
                f"{_esc(self.state.last_words)}. You can undo it.</div>"
            )

        return (
            '<div class="a-resume">'
            f"{last}"
            f'<div class="a-resume-line">{_esc(report.summary())}</div>'
            f"{changes}{proposals}</div>"
        )

    def suggest_tidy(self, workspace_id: int | None) -> tuple[str, str]:
        """Offer a tidy without going through the model.

        Tidying is a deterministic rule, so asking a model to produce the plan
        would add latency and a chance of error for no benefit. The plan still
        goes through policy and approval exactly like any other, including a
        remembered "don't ask again": the button used to ask regardless, which
        contradicted the promise it had just made.
        """
        if not workspace_id:
            return self._say("Choose a folder first."), ""

        proposal = self._tidy.propose(workspace_id)
        if not proposal.is_worth_doing:
            return self._say(proposal.summary()), ""

        plan = self._tidy.to_plan(proposal)
        outcome = self._gateway.submit_plan(workspace_id, plan, "tidy this folder")
        message, card = self._render_outcome(outcome, "tidy", from_service=True)
        if outcome.needs_approval:
            return self._say(proposal.summary()), card
        return message, card

    def patterns_html(self, workspace_id: int | None) -> str:
        """Anything ARTEMIS has noticed you doing repeatedly."""
        if not workspace_id:
            return ""
        proposals = self._patterns.open_proposals(workspace_id)
        if not proposals:
            return ""
        items = "".join(
            f'<div class="a-change">{_esc(p["description"])}</div>' for p in proposals
        )
        return (
            '<div class="a-resume">'
            '<div class="a-steps-head">ARTEMIS has noticed a pattern</div>'
            f'<div class="a-changes">{items}</div>'
            '<div class="a-card-meta">ARTEMIS will not act on these unless you '
            "say so.</div></div>"
        )

    def look_for_patterns(self, workspace_id: int | None) -> str:
        if not workspace_id:
            return self._say("Choose a folder first.")
        created = self._patterns.propose_new(workspace_id)
        if not created:
            return self._say("Nothing repeated often enough to be worth automating yet.")
        return self._say(
            f"Noticed {_plural(len(created), 'thing')} you do repeatedly. "
            "ARTEMIS will not act on them unless you say so."
        )