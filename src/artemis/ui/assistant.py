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
import threading
import time
from dataclasses import dataclass
from typing import Any

from artemis.core.actions import OUTWARD_OPS, READ_OPS, ToolCall
from artemis.core.gateway import Gateway, TurnOutcome
from artemis.core.router import ModelRouter, NoModelAvailable
from artemis.core.providers import OllamaProvider
from artemis.data.store import Store
from artemis.services.patterns import PatternWatcher
from artemis.services.resume import ResumeService
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
        return "Search the web"
    if operation == "send_mail":
        return "Send an email"
    return describe


def _outcome_in_plain_words(plan) -> str:
    """What a finished plan did, counted by kind rather than by function name.

    `plan.summarise()` is written for logs and reads as "2 create dirs, 5 move
    files". Both the approval card and the result line show this instead, so
    the person reading them never meets an operation name.
    """
    counts: dict[str, int] = {}
    for call in plan:
        counts[call.operation] = counts.get(call.operation, 0) + 1

    words = {
        "create_dir": ("folder created", "folders created"),
        "move_file": ("file moved", "files moved"),
        "rename": ("file renamed", "files renamed"),
        "write_file": ("file written", "files written"),
        "append_file": ("file added to", "files added to"),
    }
    parts = []
    for operation, count in counts.items():
        singular, plural = words.get(
            operation, (operation.replace("_", " "), operation.replace("_", " "))
        )
        parts.append(f"{count} {singular if count == 1 else plural}")
    return ", ".join(parts) if parts else "nothing"



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
        self.state = AssistantState()

    # -- asking ------------------------------------------------------------

    def ask_streaming(self, workspace_id: int | None, text: str):
        """`ask`, but yielding progress while the model works.

        Yields the same (conversation, approval card) pair that `ask` returns,
        several times: a thinking line that updates as output arrives, then the
        real answer. The work is not faster. What changes is that the page shows
        something after about a second instead of greying out for six.

        The gateway call is blocking, so it runs on a worker thread and reports
        progress through a queue. Every decision still happens inside the
        gateway on that thread; this method only renders what it reports.
        """
        text = (text or "").strip()
        if not workspace_id:
            yield self._say("Choose a folder first, so ARTEMIS knows where to look."), ""
            return
        if not text:
            yield self._say("Type what you would like ARTEMIS to do."), ""
            return

        chat = _conversational_reply(text)
        if chat is not None:
            yield self._say(chat), ""
            return

        # Tidying is a rule, not a judgement. Answer it directly.
        cleaned = text.strip().lower().rstrip("!.?").strip()
        if cleaned in _TIDY_PHRASES:
            yield self.suggest_tidy(workspace_id)
            return

        # "What changed?" is a question about recorded facts, not a plan.
        if cleaned in _RESUME_PHRASES:
            yield self.answer_what_changed(workspace_id)
            return

        # Say what ARTEMIS cannot do, rather than planning something adjacent.
        refusal = _boundary_reply(text)
        if refusal is not None:
            yield self._say(refusal, warn=True), ""
            return

        progress: queue.Queue[int] = queue.Queue()
        box: dict[str, Any] = {}

        def work() -> None:
            try:
                box["outcome"] = self._gateway.handle(
                    workspace_id,
                    text,
                    on_token=lambda cycle, pieces: progress.put(pieces),
                )
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

        yield self._render_outcome(box["outcome"], text)

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

    def _render_outcome(self, outcome: TurnOutcome, text: str) -> tuple[str, str]:
        """Turn a finished turn into what the page shows.

        Shared by `ask` and `ask_streaming` so the two paths cannot drift: a
        plan that needs approval must look identical whichever one produced it.
        """
        self.state.outcome = outcome

        # Checked before the approval card is built. A plan whose only step
        # leaves the machine, for a request that never mentioned the folder, is
        # the planner reaching for the one operation that could answer
        # anything: "sing me a song" became a web search with an egress warning
        # to approve, which misrepresents what ARTEMIS is for.
        if _is_off_topic(outcome):
            self.state.outcome = None
            return self._say(
                "That is outside what ARTEMIS does. It works with the files in "
                "folders you have added: tidying them up, telling you what "
                "changed, and finding things in them."
            ), ""

        if outcome.needs_approval:
            # Say what the plan would do, not what the user typed. Echoing the
            # request back tells them nothing they do not already know, and the
            # question being asked is about the consequences.
            return (
                self._say(
                    f"This would {_outcome_in_plain_words(outcome.plan)}. "
                    "Nothing has happened yet."
                ),
                self.approval_html(outcome),
            )

        # A model that is not running is not an unclear request. Saying "I
        # could not turn that into steps" here sends the user off to rephrase a
        # request that was perfectly clear.
        if outcome.planning.no_model:
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
                "I could not turn that into steps I am allowed to take. Try "
                "naming a folder action, such as tidying up or checking what "
                "changed.",
                warn=True,
            ), ""

        self.state.last_plan_id = outcome.plan.plan_id
        self.state.last_summary = outcome.plan.summarise()
        described = self._describe_result(outcome)
        if isinstance(described, _Markup):
            return self._show(described), ""
        return self._say(described), ""

    def ask(self, workspace_id: int | None, text: str) -> tuple[str, str]:
        """Send a request to the gateway. Returns (conversation, approval card).

        Nothing here decides anything. If the plan needs approval the card is
        rendered and the turn is held; if it does not, the gateway has already
        run the reads and this reports what came back.
        """
        text = (text or "").strip()
        if not workspace_id:
            return self._say("Choose a folder first, so ARTEMIS knows where to look."), ""
        if not text:
            return self._say("Type what you would like ARTEMIS to do."), ""

        # Answer conversational input without a model call. Planning a greeting
        # takes about fifteen seconds and always fails.
        chat = _conversational_reply(text)
        if chat is not None:
            return self._say(chat), ""

        # Tidying is a rule, not a judgement. Answer it directly.
        cleaned = text.strip().lower().rstrip("!.?").strip()
        if cleaned in _TIDY_PHRASES:
            return self.suggest_tidy(workspace_id)

        # "What changed?" is a question about recorded facts, not a plan.
        if cleaned in _RESUME_PHRASES:
            return self.answer_what_changed(workspace_id)

        # Say what ARTEMIS cannot do, rather than planning something adjacent.
        refusal = _boundary_reply(text)
        if refusal is not None:
            return self._say(refusal, warn=True), ""

        try:
            outcome = self._gateway.handle(workspace_id, text)
        except NoModelAvailable as exc:
            return self._say(
                f"No model is available right now. {exc}", warn=True
            ), ""
        except Exception as exc:  # pragma: no cover - surfaced, never swallowed
            return self._say(f"Something went wrong: {exc}", warn=True), ""

        return self._render_outcome(outcome, text)

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
            return "Nothing ran."

        found = self._describe_findings(outcome)
        if found:
            # Already-escaped markup, so it is returned as a marked string the
            # caller shows without escaping a second time.
            return _Markup(found)

        parts = [f"Done: {_outcome_in_plain_words(outcome.plan)}."]
        if result.skipped:
            parts.append(f"{_plural(len(result.skipped), 'step')} could not run.")
        return " ".join(parts)

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
        self.state.last_plan_id = outcome.plan.plan_id
        self.state.last_summary = outcome.plan.summarise()
        self.state.outcome = None

        # Snapshot after the change, so "what changed?" reports what ARTEMIS
        # just did rather than comparing against a folder it has already moved.
        if outcome.plan.calls:
            self._resume.checkpoint(
                outcome.plan.calls[0].workspace_id,
                recent_files=[
                    path for call in outcome.plan.calls for path in call.paths
                ],
            )

        message = f"Done: {_outcome_in_plain_words(outcome.plan)}."
        if remember:
            message += " I will not ask again for this kind of change in this folder."
        if result.skipped:
            message += f" {_plural(len(result.skipped), 'step')} could not run."
        return self._say(message), ""

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
            ("What it does", _outcome_in_plain_words(outcome.plan)),
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
            f'<span class="a-step-t">{_esc(_in_plain_words(step, outcome))}</span>'
            "</div>"
            for i, step in enumerate(preview["steps"], start=1)
        )

        return (
            '<div class="a-approval">'
            '<div class="a-approval-head">Approve these changes?</div>'
            '<div class="a-approval-sub">Nothing has happened yet. Read the '
            "steps, then choose below.</div>"
            f'<div class="a-facts">{fact_rows}</div>'
            f'<div class="a-assures">{assurance_html}</div>'
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
                '<div class="a-steps-head">ARTEMIS asked about this last time</div>'
                f'<div class="a-changes">{items}</div>'
            )

        return (
            '<div class="a-resume">'
            f'<div class="a-resume-line">{_esc(report.summary())}</div>'
            f"{changes}{proposals}</div>"
        )

    def suggest_tidy(self, workspace_id: int | None) -> tuple[str, str]:
        """Offer a tidy without going through the model.

        Tidying is a deterministic rule, so asking a model to produce the plan
        would add latency and a chance of error for no benefit. The plan still
        goes through policy and approval exactly like any other.
        """
        if not workspace_id:
            return self._say("Choose a folder first."), ""

        proposal = self._tidy.propose(workspace_id)
        if not proposal.is_worth_doing:
            return self._say(proposal.summary()), ""

        plan = self._tidy.to_plan(proposal)
        verdicts = self._gateway.policy.classify_plan(plan)
        pending = self._gateway.approvals.submit(plan, verdicts)

        outcome = TurnOutcome(
            plan=plan,
            verdicts=verdicts,
            context=self._gateway.context_engine.assemble(workspace_id, "tidy"),
            planning=None,  # type: ignore[arg-type]
            pending=pending,
        )
        self.state.outcome = outcome

        return self._say(proposal.summary()), self.approval_html(outcome)

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
