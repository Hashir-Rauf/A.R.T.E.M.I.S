"""The Tool Dispatcher, and the Sprint 3 stage gate.

The stage gate is: *gates hold against placeholder tools*. That is what the
final tests here check, end to end, against real files on disk.

Testing the gates before any model exists is deliberate. A failing gate at this
stage is a deterministic bug with a short reproduction. The same defect found
after the planner exists would arrive intermittently, inside generated plans,
and be far harder to pin down.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.actions import Decision, Plan, Tier, ToolCall, Verdict
from artemis.core.approval import ApprovalBroker
from artemis.core.broker import WorkspaceBroker
from artemis.core.dispatch import DispatchRefused, ToolDispatcher, default_handlers
from artemis.core.policy import PolicyEngine
from artemis.core.undo import UndoJournal
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


@pytest.fixture
def policy(store: Store, broker: WorkspaceBroker) -> PolicyEngine:
    return PolicyEngine(store, broker)


@pytest.fixture
def approvals(store: Store, policy: PolicyEngine) -> ApprovalBroker:
    return ApprovalBroker(store, policy)


@pytest.fixture
def journal(store: Store) -> UndoJournal:
    return UndoJournal(store)


@pytest.fixture
def dispatcher(
    store: Store,
    broker: WorkspaceBroker,
    approvals: ApprovalBroker,
    journal: UndoJournal,
) -> ToolDispatcher:
    dispatcher = ToolDispatcher(store, broker, approvals, journal)
    for operation, handler in default_handlers().items():
        dispatcher.register(operation, handler)
    return dispatcher


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


# -- the four refusals ---------------------------------------------------------


def test_a_call_with_no_verdict_is_refused(
    dispatcher: ToolDispatcher, workspace_id: int
) -> None:
    """Invariant four: no verdict, no execution."""
    call = ToolCall("read_file", workspace_id, ("readme.txt",))
    with pytest.raises(DispatchRefused, match="no policy verdict"):
        dispatcher.execute(call, None, "plan-x")


def test_a_verdict_for_a_different_call_is_refused(
    dispatcher: ToolDispatcher, policy: PolicyEngine, workspace_id: int
) -> None:
    """Stops a call being classified as one thing and executed as another."""
    innocent = ToolCall("read_file", workspace_id, ("readme.txt",))
    verdict = policy.classify(innocent)
    substituted = ToolCall("write_file", workspace_id, ("readme.txt",))

    with pytest.raises(DispatchRefused, match="different call"):
        dispatcher.execute(substituted, verdict, "plan-x")


def test_a_denied_call_never_executes(
    dispatcher: ToolDispatcher, policy: PolicyEngine, workspace_id: int, sandbox: Path
) -> None:
    call = ToolCall("delete_file", workspace_id, ("readme.txt",))
    verdict = policy.classify(call)

    with pytest.raises(DispatchRefused):
        dispatcher.execute(call, verdict, "plan-x")

    assert (sandbox / "readme.txt").exists()


def test_a_gated_call_without_approval_is_refused(
    dispatcher: ToolDispatcher, policy: PolicyEngine, workspace_id: int, sandbox: Path
) -> None:
    """The dispatcher asks the broker; a caller cannot vouch for itself."""
    call = ToolCall("write_file", workspace_id, ("readme.txt",), {"content": "new"})
    verdict = policy.classify(call)

    with pytest.raises(DispatchRefused, match="needs approval"):
        dispatcher.execute(call, verdict, "unapproved-plan")

    assert (sandbox / "readme.txt").read_text(encoding="utf-8") == "hello"


def test_an_unregistered_operation_cannot_run(
    dispatcher: ToolDispatcher, workspace_id: int
) -> None:
    """Registration is an allowlist, not a convenience."""
    call = ToolCall("read_file", workspace_id, ("readme.txt",))
    verdict = Verdict(call.call_id, Tier.READ, Decision.ALLOW, "", "test")
    bare = ToolDispatcher(
        dispatcher._store, dispatcher._broker, dispatcher._approvals, dispatcher._journal  # noqa: SLF001
    )

    with pytest.raises(DispatchRefused, match="no handler"):
        bare.execute(call, verdict, "plan-x")


def test_a_path_outside_the_workspace_is_refused_at_execution_too(
    dispatcher: ToolDispatcher, workspace_id: int
) -> None:
    """The dispatcher re-checks rather than trusting the earlier check."""
    call = ToolCall("read_file", workspace_id, ("../private/passwords.txt",))
    verdict = Verdict(call.call_id, Tier.READ, Decision.ALLOW, "", "forged")

    with pytest.raises(DispatchRefused, match="outside the workspace"):
        dispatcher.execute(call, verdict, "plan-x")


# -- permitted work ------------------------------------------------------------


def test_a_read_runs_without_approval(
    dispatcher: ToolDispatcher, policy: PolicyEngine, workspace_id: int
) -> None:
    call = ToolCall("read_file", workspace_id, ("readme.txt",))
    result = dispatcher.execute(call, policy.classify(call), "plan-read")
    assert result == "hello"


def test_an_approved_change_runs_and_is_snapshotted_first(
    dispatcher: ToolDispatcher,
    policy: PolicyEngine,
    approvals: ApprovalBroker,
    journal: UndoJournal,
    workspace_id: int,
    sandbox: Path,
) -> None:
    """Invariant two: the snapshot exists before the file changes."""
    plan = Plan(
        (ToolCall("write_file", workspace_id, ("readme.txt",), {"content": "rewritten"}),)
    )
    verdicts = policy.classify_plan(plan)
    approvals.submit(plan, verdicts)
    approvals.approve(plan.plan_id)

    dispatcher.execute_plan(plan, verdicts)

    assert (sandbox / "readme.txt").read_text(encoding="utf-8") == "rewritten"
    assert journal.entries_for_plan(plan.plan_id), "nothing was recorded for undo"


# -- the stage gate ------------------------------------------------------------


def test_stage_gate_a_full_plan_is_gated_executed_and_undone(
    dispatcher: ToolDispatcher,
    policy: PolicyEngine,
    approvals: ApprovalBroker,
    journal: UndoJournal,
    workspace_id: int,
    sandbox: Path,
    store: Store,
) -> None:
    """Classify, refuse to run, approve, run, then take it all back."""
    plan = Plan(
        (
            ToolCall("create_dir", workspace_id, ("Drafts",)),
            ToolCall(
                "move_file",
                workspace_id,
                ("readme.txt",),
                {"destination": "Drafts/readme.txt"},
            ),
        ),
        intent="Tidy up",
    )
    verdicts = policy.classify_plan(plan)
    assert policy.plan_needs_approval(verdicts)

    # Before approval, nothing happens.
    blocked = dispatcher.execute_plan(plan, verdicts)
    assert blocked.executed == ()
    assert (sandbox / "readme.txt").exists()
    assert not (sandbox / "Drafts").exists()

    # After approval, it runs.
    approvals.submit(plan, verdicts)
    approvals.approve(plan.plan_id)
    done = dispatcher.execute_plan(plan, verdicts)

    assert len(done.executed) == 2
    assert (sandbox / "Drafts" / "readme.txt").exists()
    assert not (sandbox / "readme.txt").exists()

    # And it can be taken back as one unit.
    reversed_count, problems = journal.undo_plan(plan.plan_id)

    assert problems == []
    assert reversed_count == 2
    assert (sandbox / "readme.txt").exists()
    assert not (sandbox / "Drafts").exists()
    assert store.verify_audit_chain()


def test_stage_gate_every_refusal_reaches_the_audit_log(
    dispatcher: ToolDispatcher, policy: PolicyEngine, workspace_id: int, store: Store
) -> None:
    """Invariant three: refusals are recorded, not only successes."""
    denied = ToolCall("delete_file", workspace_id, ("readme.txt",))
    with pytest.raises(DispatchRefused):
        dispatcher.execute(denied, policy.classify(denied), "plan-a")

    gated = ToolCall("write_file", workspace_id, ("readme.txt",), {"content": "x"})
    with pytest.raises(DispatchRefused):
        dispatcher.execute(gated, policy.classify(gated), "plan-b")

    refusals = [
        row
        for row in store.list_audit()
        if row["event"] == "dispatch.execute" and row["outcome"] == "refused"
    ]
    assert len(refusals) == 2
    assert store.verify_audit_chain()


def test_stage_gate_a_mixed_plan_runs_only_what_is_permitted(
    dispatcher: ToolDispatcher,
    policy: PolicyEngine,
    approvals: ApprovalBroker,
    workspace_id: int,
    sandbox: Path,
) -> None:
    """A denied step is skipped; the rest of the plan still reports honestly."""
    plan = Plan(
        (
            ToolCall("read_file", workspace_id, ("readme.txt",)),
            ToolCall("delete_file", workspace_id, ("readme.txt",)),
        )
    )
    verdicts = policy.classify_plan(plan)
    approvals.submit(plan, verdicts)
    approvals.approve(plan.plan_id)

    result = dispatcher.execute_plan(plan, verdicts)

    assert len(result.executed) == 1
    assert len(result.skipped) == 1
    assert (sandbox / "readme.txt").exists()
