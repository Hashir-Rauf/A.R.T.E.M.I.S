"""The AI Gateway: the one path a request travels.

Composes the four Layer 3 components and the Sprint 3 gates into the lifecycle
the architecture specifies (Section 4):

    turn -> context -> route -> plan -> classify -> gate -> dispatch -> audit

The gateway is a coordinator, not a shortcut. It holds no authority of its own:
it cannot classify, cannot approve, and cannot execute. Each of those belongs to
the component that owns it, and the gateway's only job is to call them in the
right order and refuse to skip one.

Three properties this file exists to guarantee:

**There is no path from a plan to execution that misses the policy engine.**
`handle` classifies every call before the dispatcher sees it, and the dispatcher
independently refuses anything arriving without a matching verdict. Two checks
rather than one, because the second does not trust the first.

**A gated plan stops here.** The gateway returns the plan and its preview and
waits. It does not execute on the user's behalf, and there is no argument, flag
or configuration that makes it do so.

**Nothing the model says becomes authority.** The intent is read from `user`
chunks only; a model reply is parsed for tool calls and otherwise discarded. The
gateway never acts on prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from artemis.core.actions import Plan, Verdict
from artemis.core.approval import ApprovalBroker, PendingApproval
from artemis.core.broker import WorkspaceBroker
from artemis.core.context import AssembledContext, Chunk, ContextEngine
from artemis.core.dispatch import ExecutionResult, ToolDispatcher, default_handlers
from artemis.core.planner import AgentPlanner, PlanningResult
from artemis.core.policy import PolicyEngine
from artemis.core.router import ModelRouter
from artemis.core.undo import UndoJournal
from artemis.data.store import Store


@dataclass
class TurnOutcome:
    """What happened to one request, and what the user is asked next.

    Deliberately explicit about the three ways a turn can end: nothing to do,
    done already, or waiting for you. A caller cannot mistake "waiting" for
    "finished" because the pending approval is present and the result is not.
    """

    plan: Plan
    verdicts: dict[str, Verdict]
    context: AssembledContext
    planning: PlanningResult
    pending: PendingApproval | None = None
    result: ExecutionResult | None = None
    refusals: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def needs_approval(self) -> bool:
        return self.pending is not None

    @property
    def did_anything(self) -> bool:
        return self.result is not None and self.result.did_anything

    @property
    def preview(self) -> dict[str, Any] | None:
        return self.pending.preview if self.pending else None


@dataclass
class Gateway:
    """Runs the request lifecycle, and refuses to skip a step in it."""

    store: Store
    broker: WorkspaceBroker
    router: ModelRouter
    context_engine: ContextEngine
    policy: PolicyEngine
    approvals: ApprovalBroker
    journal: UndoJournal
    dispatcher: ToolDispatcher
    planner: AgentPlanner

    @classmethod
    def build(cls, store: Store, router: ModelRouter) -> Gateway:
        """Wire a gateway with the standard components and placeholder tools.

        The handlers are Sprint 3's placeholders; Sprint 5 replaces them with
        real services. Registration is explicit here so the set of things the
        system can do is visible in one place rather than discovered at runtime.
        """
        broker = WorkspaceBroker(store)
        policy = PolicyEngine(store, broker)
        approvals = ApprovalBroker(store, policy)
        journal = UndoJournal(store)
        dispatcher = ToolDispatcher(store, broker, approvals, journal)
        for operation, handler in default_handlers().items():
            dispatcher.register(operation, handler)
        return cls(
            store=store,
            broker=broker,
            router=router,
            context_engine=ContextEngine(store),
            policy=policy,
            approvals=approvals,
            journal=journal,
            dispatcher=dispatcher,
            planner=AgentPlanner(store=store, router=router),
        )

    # -- the lifecycle -----------------------------------------------------

    def handle(
        self,
        workspace_id: int,
        user_text: str,
        session_id: int | None = None,
        token_budget: int = 3000,
    ) -> TurnOutcome:
        """Take one request as far as it may go without the user's permission.

        Reads run. Anything that changes a file or leaves the machine stops at
        the approval broker and comes back as a preview.
        """
        self.store.append_audit(
            event="gateway.turn",
            outcome="received",
            workspace_id=workspace_id,
            detail={"text": user_text[:200]},
        )

        retrieved: list[Chunk] = self.context_engine.chunks_from_index(
            workspace_id, user_text
        )
        context = self.context_engine.assemble(
            workspace_id,
            user_text,
            retrieved=retrieved,
            token_budget=token_budget,
            session_id=session_id,
        )

        planning = self.planner.plan(workspace_id, context)
        plan = planning.plan

        if not plan.calls:
            return TurnOutcome(
                plan=plan,
                verdicts={},
                context=context,
                planning=planning,
                notes=planning.notes,
            )

        # Classify before anything else looks at the plan. Nothing downstream
        # is permitted to run a call that has not been through here.
        verdicts = self.policy.classify_plan(plan)
        refusals = tuple(
            v.reason for v in self.policy.plan_refused(verdicts)
        )

        if self.policy.plan_needs_approval(verdicts):
            pending = self.approvals.submit(plan, verdicts)
            return TurnOutcome(
                plan=plan,
                verdicts=verdicts,
                context=context,
                planning=planning,
                pending=pending,
                refusals=refusals,
                notes=planning.notes,
            )

        # Reads only. The dispatcher still checks every verdict itself.
        result = self.dispatcher.execute_plan(plan, verdicts)
        return TurnOutcome(
            plan=plan,
            verdicts=verdicts,
            context=context,
            planning=planning,
            result=result,
            refusals=refusals,
            notes=planning.notes,
        )

    # -- after the user answers -------------------------------------------

    def approve_and_run(
        self, outcome: TurnOutcome, remember: bool = False
    ) -> ExecutionResult:
        """Run a plan the user approved.

        Approval is recorded through the broker first, so the dispatcher's own
        check has something real to find. Passing approval as an argument would
        let this method vouch for the user, which is exactly the shortcut the
        design exists to prevent.
        """
        if outcome.pending is None:
            raise ValueError("this turn was not waiting for approval")
        self.approvals.approve(outcome.plan.plan_id, remember=remember)
        return self.dispatcher.execute_plan(outcome.plan, outcome.verdicts)

    def reject(self, outcome: TurnOutcome, reason: str = "") -> None:
        """Record that the user said no. The plan can never run afterwards."""
        if outcome.pending is None:
            raise ValueError("this turn was not waiting for approval")
        self.approvals.reject(outcome.plan.plan_id, reason=reason)

    def undo(self, plan_id: str) -> tuple[int, list[str]]:
        """Take back an executed plan, as one unit."""
        return self.journal.undo_plan(plan_id)
