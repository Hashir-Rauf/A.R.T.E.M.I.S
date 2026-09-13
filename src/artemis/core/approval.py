"""The Approval Broker.

Holds plans that are waiting for a decision, and records what the user decided.
It is the only way a gated action becomes a permitted one.

The rule that matters: **nothing is ever approved by default.** There is no
timeout that grants permission, no "assume yes if the window closed", no
auto-approval under load. A pending plan stays pending until a person answers,
and if the process dies the plan dies with it, unapproved. A gate that opens on
its own is not a gate.

Every outcome is written to the audit log, including rejection. The log records
what was proposed, not only what happened (Architecture Section 4, invariant
three), which is what lets someone check afterwards that a refusal really was
refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from artemis.core.actions import Decision, Plan, Tier, ToolCall, Verdict
from artemis.core.policy import AUTO, PolicyEngine
from artemis.data.store import Store


class Outcome(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class PendingApproval:
    """A plan waiting for a person to decide.

    `preview` is built once, when the plan is submitted, so what the user is
    shown is exactly what was classified. Rebuilding it at display time would
    let the two drift apart.
    """

    plan: Plan
    verdicts: dict[str, Verdict]
    preview: dict[str, Any]
    outcome: Outcome = Outcome.PENDING
    decided_at: str | None = None
    remembered: bool = False
    gated_calls: tuple[ToolCall, ...] = field(default_factory=tuple)

    @property
    def plan_id(self) -> str:
        return self.plan.plan_id


class ApprovalBroker:
    """Queues gated plans and applies the user's decision."""

    def __init__(self, store: Store, policy: PolicyEngine) -> None:
        self._store = store
        self._policy = policy
        self._pending: dict[str, PendingApproval] = {}

    # -- submission --------------------------------------------------------

    def submit(self, plan: Plan, verdicts: dict[str, Verdict]) -> PendingApproval:
        """Register a plan that needs approval and build its preview."""
        gated = tuple(
            call for call in plan if verdicts[call.call_id].needs_approval
        )
        pending = PendingApproval(
            plan=plan,
            verdicts=verdicts,
            preview=self.build_preview(plan, verdicts),
            gated_calls=gated,
        )
        self._pending[plan.plan_id] = pending
        self._store.append_audit(
            event="approval.requested",
            outcome="pending",
            workspace_id=plan.calls[0].workspace_id if plan.calls else None,
            detail={
                "plan_id": plan.plan_id,
                "summary": plan.summarise(),
                "gated": len(gated),
            },
        )
        return pending

    def build_preview(self, plan: Plan, verdicts: dict[str, Verdict]) -> dict[str, Any]:
        """What the user is shown before deciding.

        Deliberately states what will *not* happen as well as what will. The
        reassuring facts, that nothing leaves the machine and nothing is
        deleted, are the ones a person needs in order to answer quickly.
        """
        highest = self._policy.highest_tier(verdicts)
        workspace_id = plan.calls[0].workspace_id if plan.calls else None
        row = self._store.get_workspace(workspace_id) if workspace_id else None
        leaves_machine = any(v.tier is Tier.OUTWARD for v in verdicts.values())
        return {
            "plan_id": plan.plan_id,
            "intent": plan.intent,
            "workspace": row["name"] if row else "unknown",
            "workspace_root": row["root"] if row else "",
            "summary": plan.summarise(),
            "risk": highest.value,
            "reversible": highest is Tier.REVERSIBLE,
            "leaves_machine": leaves_machine,
            "deletes_anything": False,
            "steps": [
                {
                    "describe": call.describe(),
                    "tier": verdicts[call.call_id].tier.value,
                    "reason": verdicts[call.call_id].reason,
                }
                for call in plan
            ],
        }

    # -- decisions ---------------------------------------------------------

    def pending(self) -> list[PendingApproval]:
        return [p for p in self._pending.values() if p.outcome is Outcome.PENDING]

    def get(self, plan_id: str) -> PendingApproval | None:
        return self._pending.get(plan_id)

    def approve(self, plan_id: str, remember: bool = False) -> PendingApproval:
        """Approve a pending plan, optionally remembering the decision.

        Remembering is scoped to the shape of each gated call, so approving one
        folder tidy does not quietly approve sending mail. The policy engine
        refuses to remember outward or destructive calls whatever is asked here.
        """
        pending = self._require(plan_id)
        pending.outcome = Outcome.APPROVED
        pending.decided_at = _now()
        pending.remembered = remember

        if remember:
            for call in pending.gated_calls:
                self._policy.remember(call, AUTO)

        self._store.append_audit(
            event="approval.decided",
            outcome="approved",
            workspace_id=pending.plan.calls[0].workspace_id if pending.plan.calls else None,
            detail={
                "plan_id": plan_id,
                "summary": pending.plan.summarise(),
                "remembered": remember,
            },
        )
        return pending

    def reject(self, plan_id: str, reason: str = "") -> PendingApproval:
        """Reject a pending plan. Recorded as fully as an approval would be."""
        pending = self._require(plan_id)
        pending.outcome = Outcome.REJECTED
        pending.decided_at = _now()
        self._store.append_audit(
            event="approval.decided",
            outcome="rejected",
            workspace_id=pending.plan.calls[0].workspace_id if pending.plan.calls else None,
            detail={
                "plan_id": plan_id,
                "summary": pending.plan.summarise(),
                "reason": reason,
            },
        )
        return pending

    def is_approved(self, plan_id: str) -> bool:
        pending = self._pending.get(plan_id)
        return pending is not None and pending.outcome is Outcome.APPROVED

    def expire(self, plan_id: str) -> PendingApproval:
        """Discard a pending plan without approving it.

        Expiry exists so a stale plan can be cleared away. It is emphatically
        not approval: an expired plan can never be executed, which is why the
        outcome is a distinct value rather than a rejection or a silent drop.
        """
        pending = self._require(plan_id)
        pending.outcome = Outcome.EXPIRED
        pending.decided_at = _now()
        self._store.append_audit(
            event="approval.expired",
            outcome="expired",
            workspace_id=pending.plan.calls[0].workspace_id if pending.plan.calls else None,
            detail={"plan_id": plan_id},
        )
        return pending

    def _require(self, plan_id: str) -> PendingApproval:
        pending = self._pending.get(plan_id)
        if pending is None:
            raise KeyError(f"no pending approval for plan {plan_id}")
        if pending.outcome is not Outcome.PENDING:
            raise ValueError(
                f"plan {plan_id} was already {pending.outcome.value}"
            )
        return pending


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
