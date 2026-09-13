"""The Policy Engine.

Classifies every proposed tool call into exactly one risk tier and decides
whether it may run, must be approved, or is refused outright. This is the
component that turns the research finding "approval-first, configurable" into
enforced structure rather than an interface convention (Architecture 5.3).

Two properties matter more than the code itself.

**The order is fixed and denials come first.** Evaluation runs grant check,
destructive check, egress check, mutation check, and only then allow. First
match wins, so no later rule can grant what an earlier one refused. Reordering
these is not a refactor; it is a change to what the system promises.

**T3 has no approval path.** A destructive call is refused and that is the end
of it. There is deliberately no "are you sure" dialogue, because a gate the user
can click through is a policy, whereas a gate that does not exist is an
architecture.

The engine reads the ToolCall and nothing else. It never sees the model's
reasoning text, so nothing written inside a document can argue its way to a
different verdict (Architecture 9.1, defence three).
"""

from __future__ import annotations

from artemis.core.actions import (
    DESTRUCTIVE_OPS,
    OUTWARD_OPS,
    READ_OPS,
    REVERSIBLE_OPS,
    Decision,
    Plan,
    Tier,
    ToolCall,
    Verdict,
)
from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.errors import BoundaryRefusal
from artemis.data.store import Store

#: How the user wants reversible operations handled. Only T1 is configurable:
#: T0 always runs, T2 is always gated, T3 is always refused.
AUTO = "auto"
ASK = "ask"

DEFAULT_T1_MODE = ASK


class PolicyEngine:
    """Decides what may run, what must be asked about, and what is refused."""

    def __init__(self, store: Store, broker: WorkspaceBroker) -> None:
        self._store = store
        self._broker = broker

    # -- classification ----------------------------------------------------

    def classify(self, call: ToolCall) -> Verdict:
        """Return the verdict for one call. Never raises: a problem is a DENY.

        Rules are applied in the order given in Architecture 5.3. Each returns
        immediately, so the first match is the answer.
        """
        # 1. Is every path this call touches inside the grant?
        outside = self._first_path_outside_grant(call)
        if outside is not None:
            return self._deny(
                call,
                Tier.DESTRUCTIVE,
                f"{outside!r} is outside the granted workspace",
                "grant-check",
            )

        # 2. Is the operation itself destructive?
        if call.operation in DESTRUCTIVE_OPS:
            return self._deny(
                call,
                Tier.DESTRUCTIVE,
                f"{call.operation} destroys data and is not available",
                "destructive-check",
            )

        # 3. Does it leave the machine? Always gated, never configurable.
        if call.operation in OUTWARD_OPS:
            return Verdict(
                call_id=call.call_id,
                tier=Tier.OUTWARD,
                decision=Decision.GATE,
                reason="this leaves your computer, so it always needs approval",
                rule_applied="egress-check",
            )

        # 4. Does it change anything? Gated unless the user said otherwise.
        if call.operation in REVERSIBLE_OPS:
            remembered = self._remembered_decision(call)
            if remembered == AUTO:
                return Verdict(
                    call_id=call.call_id,
                    tier=Tier.REVERSIBLE,
                    decision=Decision.ALLOW,
                    reason="you chose to allow this kind of change without asking",
                    rule_applied="mutation-check",
                    remembered=True,
                )
            return Verdict(
                call_id=call.call_id,
                tier=Tier.REVERSIBLE,
                decision=Decision.GATE,
                reason="this changes your files, so it needs approval",
                rule_applied="mutation-check",
            )

        # 5. Anything left is a read. An operation nobody declared is treated
        #    as unknown rather than as a read, because silently permitting
        #    unrecognised operations is how a boundary erodes.
        if call.operation in READ_OPS:
            return Verdict(
                call_id=call.call_id,
                tier=Tier.READ,
                decision=Decision.ALLOW,
                reason="reads inside the workspace run without asking",
                rule_applied="read-check",
            )

        return self._deny(
            call,
            Tier.DESTRUCTIVE,
            f"{call.operation} is not an operation ARTEMIS knows",
            "unknown-operation",
        )

    def classify_plan(self, plan: Plan) -> dict[str, Verdict]:
        """Classify every call in a plan, keyed by call id."""
        return {call.call_id: self.classify(call) for call in plan}

    @staticmethod
    def plan_needs_approval(verdicts: dict[str, Verdict]) -> bool:
        return any(v.needs_approval for v in verdicts.values())

    @staticmethod
    def plan_refused(verdicts: dict[str, Verdict]) -> list[Verdict]:
        return [v for v in verdicts.values() if v.refused]

    @staticmethod
    def highest_tier(verdicts: dict[str, Verdict]) -> Tier:
        """The most sensitive tier in a plan, which is what the user is told."""
        order = [Tier.READ, Tier.REVERSIBLE, Tier.OUTWARD, Tier.DESTRUCTIVE]
        highest = Tier.READ
        for verdict in verdicts.values():
            if order.index(verdict.tier) > order.index(highest):
                highest = verdict.tier
        return highest

    # -- remembered approvals ---------------------------------------------

    def remember(self, call: ToolCall, mode: str = AUTO) -> None:
        """Record that this shape of call may run without asking again.

        Scoped to one operation in one workspace, which is how "approve and
        remember" avoids becoming a blanket permission. Outward and destructive
        calls are never remembered, whatever is requested here.
        """
        if call.operation in OUTWARD_OPS or call.operation in DESTRUCTIVE_OPS:
            return
        with self._store._write() as conn:  # noqa: SLF001 - store-owned table
            conn.execute(
                "INSERT INTO policy_rules (workspace_id, operation, decision, created_at)"
                " VALUES (?, ?, ?, datetime('now'))",
                (call.workspace_id, call.operation, mode),
            )
        self._store.append_audit(
            event="policy.remember",
            outcome="recorded",
            workspace_id=call.workspace_id,
            detail={"operation": call.operation, "mode": mode},
        )

    def forget_rule(self, rule_id: int) -> None:
        with self._store._write() as conn:  # noqa: SLF001
            conn.execute("DELETE FROM policy_rules WHERE id = ?", (rule_id,))

    def rules(self, workspace_id: int | None = None) -> list:
        if workspace_id is None:
            return self._store.query("SELECT * FROM policy_rules ORDER BY id")
        return self._store.query(
            "SELECT * FROM policy_rules WHERE workspace_id = ? ORDER BY id",
            (workspace_id,),
        )

    def _remembered_decision(self, call: ToolCall) -> str | None:
        row = self._store.query_one(
            "SELECT decision FROM policy_rules"
            " WHERE workspace_id = ? AND operation = ?"
            " ORDER BY id DESC LIMIT 1",
            (call.workspace_id, call.operation),
        )
        return row["decision"] if row else None

    # -- internals ---------------------------------------------------------

    def _first_path_outside_grant(self, call: ToolCall) -> str | None:
        """The first path the broker refuses, or None if all are inside.

        Asking the broker rather than reimplementing containment means there is
        one boundary check in the system, not two that can drift apart.
        """
        wanted = (
            Operation.WRITE
            if call.operation in REVERSIBLE_OPS or call.operation in DESTRUCTIVE_OPS
            else Operation.READ
        )
        for path in call.paths:
            try:
                self._broker.resolve(call.workspace_id, path, wanted)
            except BoundaryRefusal:
                return path
        return None

    def _deny(self, call: ToolCall, tier: Tier, reason: str, rule: str) -> Verdict:
        """Build a denial and record it. A refusal is logged like any action."""
        self._store.append_audit(
            event="policy.classify",
            outcome="refused",
            workspace_id=call.workspace_id,
            detail={
                "operation": call.operation,
                "call": call.describe(),
                "reason": reason,
                "rule": rule,
            },
        )
        return Verdict(
            call_id=call.call_id,
            tier=tier,
            decision=Decision.DENY,
            reason=reason,
            rule_applied=rule,
        )
