"""The Tool Dispatcher: the only component in ARTEMIS that may act.

Everything else proposes, classifies, previews or records. Execution happens
here and nowhere else, which is what makes the guarantees checkable: there is
one place to audit rather than one per feature.

Four refusals are enforced on every call, in this order:

1. **No verdict, no execution.** A call arriving without a policy verdict is
   rejected outright (Architecture Section 4, invariant four).
2. **The verdict must belong to this call.** Verdicts carry the call id they
   were issued for, so a call cannot be classified as a read and then swapped
   for something else before it runs.
3. **A denial is final.** T3 never executes, and there is no argument that
   changes that here.
4. **A gated call needs a recorded approval.** Not a flag passed in by the
   caller: the dispatcher asks the approval broker, so a service cannot claim
   its own permission.

Mutations are snapshotted before they happen, never after (invariant two), and
every execution and every refusal is written to the audit log (invariant three).

Sprint 3 ships this with placeholder handlers. The gates are what is being
proven, and proving them against inert tools is the point: a failing gate at
this stage is a deterministic bug with a short reproduction, which stops being
true once a model is generating the plans.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from artemis.core.actions import (
    OUTWARD_OPS,
    REVERSIBLE_OPS,
    Decision,
    Plan,
    ToolCall,
    Verdict,
)
from artemis.core.approval import ApprovalBroker
from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.errors import BoundaryRefusal
from artemis.core.undo import UndoJournal
from artemis.data.store import Store

#: A handler receives the resolved paths and the call, and returns a result.
Handler = Callable[["ExecutionContext"], Any]


class DispatchRefused(Exception):
    """Raised when the dispatcher declines to execute a call."""

    def __init__(self, call: ToolCall, reason: str) -> None:
        self.call = call
        self.reason = reason
        super().__init__(f"refused {call.describe()}: {reason}")


@dataclass(frozen=True)
class ExecutionContext:
    """What a handler is given. Paths are already resolved and bounds-checked.

    `destination` is the resolved form of a `destination` argument, for the
    operations that have one. It is resolved once, by the dispatcher, and shared
    with the undo journal, so the snapshot and the operation can never disagree
    about where a file ended up.
    """

    call: ToolCall
    resolved: tuple[Path, ...]
    plan_id: str
    destination: Path | None = None


@dataclass(frozen=True)
class ExecutionResult:
    """What happened when a plan ran."""

    plan_id: str
    executed: tuple[str, ...]
    skipped: tuple[str, ...]
    results: dict[str, Any]

    @property
    def did_anything(self) -> bool:
        return bool(self.executed)


class ToolDispatcher:
    """Executes approved calls, and refuses everything else."""

    def __init__(
        self,
        store: Store,
        broker: WorkspaceBroker,
        approvals: ApprovalBroker,
        journal: UndoJournal,
    ) -> None:
        self._store = store
        self._broker = broker
        self._approvals = approvals
        self._journal = journal
        self._handlers: dict[str, Handler] = {}

    # -- registration ------------------------------------------------------

    def register(self, operation: str, handler: Handler) -> None:
        """Attach a handler to an operation.

        Registration is an allowlist. An operation with no handler cannot run,
        so adding a capability is a deliberate act rather than a side effect of
        the planner inventing a name (Architecture Table 2, component 11).
        """
        self._handlers[operation] = handler

    def registered(self) -> frozenset[str]:
        return frozenset(self._handlers)

    # -- execution ---------------------------------------------------------

    def execute_plan(
        self, plan: Plan, verdicts: dict[str, Verdict]
    ) -> ExecutionResult:
        """Run every call in a plan that is permitted to run.

        Denied and unapproved calls are skipped rather than aborting the plan,
        so the outcome states exactly what did and did not happen. Silently
        running a subset would be worse; silently running none of it would hide
        which step was the problem.
        """
        executed: list[str] = []
        skipped: list[str] = []
        results: dict[str, Any] = {}

        for call in plan:
            verdict = verdicts.get(call.call_id)
            try:
                results[call.call_id] = self.execute(call, verdict, plan.plan_id)
                executed.append(call.call_id)
            except DispatchRefused as refusal:
                skipped.append(call.call_id)
                results[call.call_id] = {"refused": refusal.reason}
            except Exception as problem:
                # A handler declining one step is a skip, not a plan-wide
                # abort. A tidy of twelve files should not lose eleven of them
                # because the twelfth would have landed on an existing name.
                # The step is reported rather than swallowed, so the result
                # still says exactly what did and did not happen.
                skipped.append(call.call_id)
                results[call.call_id] = {"refused": str(problem)}

        return ExecutionResult(
            plan_id=plan.plan_id,
            executed=tuple(executed),
            skipped=tuple(skipped),
            results=results,
        )

    def execute(
        self, call: ToolCall, verdict: Verdict | None, plan_id: str
    ) -> Any:
        """Run one call, or refuse it. The only path to a side effect."""
        self._check_permitted(call, verdict, plan_id)

        handler = self._handlers.get(call.operation)
        if handler is None:
            raise self._refuse(call, plan_id, "no handler is registered for this")

        resolved = self._resolve_paths(call, plan_id)
        if call.arguments.get("create_only") and any(p.exists() for p in resolved):
            raise self._refuse(call, plan_id, "create_only: that file already exists")
        destination = self._resolve_destination(call, plan_id)

        # Snapshot before touching anything. After the fact is too late: the
        # original state is already gone.
        if call.operation in REVERSIBLE_OPS:
            self._snapshot(call, plan_id, resolved, destination)

        context = ExecutionContext(
            call=call, resolved=resolved, plan_id=plan_id, destination=destination
        )
        try:
            result = handler(context)
        except Exception as exc:
            self._store.append_audit(
                event="dispatch.execute",
                outcome="failed",
                workspace_id=call.workspace_id,
                detail={"call": call.describe(), "error": str(exc)},
            )
            raise

        self._store.append_audit(
            event="dispatch.execute",
            outcome="executed",
            workspace_id=call.workspace_id,
            detail={
                "call": call.describe(),
                "tier": verdict.tier.value if verdict else "?",
                "plan_id": plan_id,
            },
        )
        return result

    # -- the four refusals -------------------------------------------------

    def _check_permitted(
        self, call: ToolCall, verdict: Verdict | None, plan_id: str
    ) -> None:
        if verdict is None:
            raise self._refuse(call, plan_id, "no policy verdict")

        if not verdict.matches(call):
            raise self._refuse(
                call, plan_id, "the verdict belongs to a different call"
            )

        if verdict.decision is Decision.DENY:
            raise self._refuse(call, plan_id, verdict.reason)

        if verdict.decision is Decision.GATE and not self._approvals.is_approved(
            plan_id
        ):
            raise self._refuse(call, plan_id, "this needs approval and has none")

    def _resolve_paths(self, call: ToolCall, plan_id: str) -> tuple[Path, ...]:
        """Resolve every path through the broker, refusing if any is outside.

        The policy engine already checked these. Checking again here is not
        redundant: the dispatcher must not depend on an earlier component having
        done its job, because that assumption is what confused-deputy bugs are
        made of.
        """
        wanted = (
            Operation.WRITE if call.operation in REVERSIBLE_OPS else Operation.READ
        )
        resolved: list[Path] = []
        for path in call.paths:
            try:
                resolved.append(self._broker.resolve(call.workspace_id, path, wanted).path)
            except BoundaryRefusal as refusal:
                raise self._refuse(
                    call, plan_id, f"{path!r} is outside the workspace"
                ) from refusal
        return tuple(resolved)

    def _resolve_destination(self, call: ToolCall, plan_id: str) -> Path | None:
        """Resolve a `destination` argument through the broker, if there is one.

        Done once and passed to both the journal and the handler, so a move
        cannot be snapshotted against one target and executed against another.
        """
        destination = call.arguments.get("destination")
        if not destination:
            return None
        try:
            return self._broker.resolve(
                call.workspace_id, str(destination), Operation.WRITE
            ).path
        except BoundaryRefusal as refusal:
            raise self._refuse(
                call, plan_id, f"destination {destination!r} is outside the workspace"
            ) from refusal

    def _snapshot(
        self,
        call: ToolCall,
        plan_id: str,
        resolved: tuple[Path, ...],
        destination: Path | None,
    ) -> None:
        """Record how to reverse this call, before it runs."""
        if call.operation == "move_file" and resolved and destination is not None:
            self._journal.record_move(
                plan_id, call.workspace_id, resolved[0], destination
            )
            return
        if call.operation == "create_dir":
            for path in resolved:
                self._journal.record_mkdir(plan_id, call.workspace_id, path)
            return
        for path in resolved:
            self._journal.record_write(plan_id, call.workspace_id, path)

    def _refuse(self, call: ToolCall, plan_id: str, reason: str) -> DispatchRefused:
        """Log the refusal, then build the exception for the caller."""
        self._store.append_audit(
            event="dispatch.execute",
            outcome="refused",
            workspace_id=call.workspace_id,
            detail={"call": call.describe(), "reason": reason, "plan_id": plan_id},
        )
        return DispatchRefused(call, reason)


# ---------------------------------------------------------------------------
# Placeholder handlers
# ---------------------------------------------------------------------------
# Sprint 3 proves the gates, not the capabilities. These do the smallest real
# thing their operation implies, so the surrounding machinery is exercised
# against actual files rather than mocks, and Sprint 5 replaces them with the
# real services.


def handle_read_file(context: ExecutionContext) -> str:
    return context.resolved[0].read_text(encoding="utf-8", errors="replace")


def handle_list_dir(context: ExecutionContext) -> list[str]:
    root = context.resolved[0] if context.resolved else None
    if root is None or not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir())


def handle_write_file(context: ExecutionContext) -> int:
    content = str(context.call.arguments.get("content", ""))
    target = context.resolved[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    if context.call.arguments.get("create_only"):
        with target.open("x", encoding="utf-8") as handle:
            handle.write(content)
        return len(content)
    target.write_text(content, encoding="utf-8")
    return len(content)


def handle_create_dir(context: ExecutionContext) -> str:
    target = context.resolved[0]
    target.mkdir(parents=True, exist_ok=True)
    return str(target)


def handle_move_file(context: ExecutionContext) -> str:
    """Move a file to a workspace-relative destination.

    The destination is resolved the same way the snapshot resolved it, through
    the broker on `context.destination`. An earlier version computed it relative
    to the source's own parent instead, so the journal recorded one target and
    the move produced another, and undo would have restored to the wrong place.
    """
    import shutil

    target = context.destination
    if target is None:
        raise ValueError("move_file needs a 'destination' argument")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(context.resolved[0]), str(target))
    return str(target)


def default_handlers() -> dict[str, Handler]:
    """The placeholder set, wired by name."""
    return {
        "read_file": handle_read_file,
        "list_dir": handle_list_dir,
        "write_file": handle_write_file,
        "create_dir": handle_create_dir,
        "move_file": handle_move_file,
    }


# Kaam karne ka tareeqa (execute)
# 1. 4 checks
# 2. Handler hai? (jis kaam ka handler nahi, wo chal hi nahi sakta)
# 3. Paths ko dobara darban (broker) se guzaro
# 4. BACKUP pehle (undo ke liye)
# 5. Asal kaam karo
# 6. Log mein likho (kamyab ho ya nakaam)
# Do cheezein khaas hain:

# Paths dobara check hote hain, chahe pehle ho chuke hon. Wajah:
# "pichle ne check kar liya hoga" wali soch hi bugs ki jar hai.
# Backup pehle, kaam baad mein. Kaam ke baad purani halat mil hi nahi sakti.
# Ye file kaam karne wala mazdoor hai. 
# Poore ARTEMIS mein sirf yehi file asal kaam karti hai (file parhna, likhna, move karna). 
# Baqi sab files sirf sochti, poochti ya likhti hain.
# Allowlist: register()
# python
# self._handlers[operation] = handler

# Sirf wahi kaam chalte hain jin ka handler jaan boojh kar register kiya gaya ho. 
# Agar AI koi naya naam gharh le (jaise "delete_everything"), to us ka handler hi nahi,
# aur kaam nahi chalega.

# Poora plan chalana (execute_plan)

# Plan ki har call ek ek kar ke chalti hai. Agar ek call fail ya mana ho jaye, 
# to baqi chalti rehti hain, aur nateeje mein saaf likha hota hai ke kya hua aur kya nahi.

# Misal: 12 files move karni thin, 12vi ke naam par pehle se file hai. 
# To 11 ho jati hain, 12vi "skipped" likhi jati hai wajah ke saath.
# Do honest observations (viva ke liye)
# Approval plan level par hai. Dispatcher sirf is_approved(plan_id) dekhta hai. 
# Yani plan approve hone par uski saari gated calls chal sakti hain, 
# isliye preview mein har step dikhana zaroori hai.
# handle_write_file purani file ko overwrite kar deta hai.
# write_file ko "reversible" (T1) kaha gaya hai kyunke pehle snapshot banta hai (record_write). 
# Is ka asal sach undo.py mein pata chalega ke snapshot waqai purani content bachata hai ya nahi. Wo file bhej dein.
# Poori file ek line mein

# Ye file ARTEMIS ka akela "kaam karne wala" hai: har kaam se pehle 4 checks,
# paths ki dobara jaanch, backup, aur phir kaam, aur sab kuch log mein likhta hai.