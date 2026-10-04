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
from dataclasses import dataclass
from typing import Any

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

        try:
            outcome = self._gateway.handle(workspace_id, text)
        except NoModelAvailable as exc:
            return self._say(
                f"No model is available right now. {exc}", warn=True
            ), ""
        except Exception as exc:  # pragma: no cover - surfaced, never swallowed
            return self._say(f"Something went wrong: {exc}", warn=True), ""

        self.state.outcome = outcome

        if outcome.needs_approval:
            return (
                self._say(f"Here is what I would do for: {text}"),
                self.approval_html(outcome),
            )

        if not outcome.plan.calls:
            note = outcome.notes[0] if outcome.notes else (
                "I could not work out a set of steps for that."
            )
            return self._say(note, warn=True), ""

        self.state.last_plan_id = outcome.plan.plan_id
        self.state.last_summary = outcome.plan.summarise()
        return self._say(self._describe_result(outcome)), ""

    def _describe_result(self, outcome: TurnOutcome) -> str:
        result = outcome.result
        if result is None:
            return "Nothing to do."
        done = len(result.executed)
        skipped = len(result.skipped)
        parts = [f"Done: {_outcome_in_plain_words(outcome.plan)}."]
        if skipped:
            parts.append(f"{_plural(skipped, 'step')} could not run.")
        return " ".join(parts) if done else "Nothing ran."

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
        tone = "a-msg warn" if warn else "a-msg"
        return f'<div class="{tone}">{_esc(message)}</div>'

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
