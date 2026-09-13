"""The Approval Broker: nothing runs until a person says so.

The central test here is the one that asserts a negative. There is no timeout
that grants permission and no state in which a plan becomes approved without
somebody approving it, so several of these tests exist to check that nothing
quietly happens.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.actions import Plan, ToolCall
from artemis.core.approval import ApprovalBroker, Outcome
from artemis.core.broker import WorkspaceBroker
from artemis.core.policy import PolicyEngine
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


@pytest.fixture
def policy(store: Store, broker: WorkspaceBroker) -> PolicyEngine:
    return PolicyEngine(store, broker)


@pytest.fixture
def approvals(store: Store, policy: PolicyEngine) -> ApprovalBroker:
    return ApprovalBroker(store, policy)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


def _tidy_plan(workspace_id: int) -> Plan:
    return Plan(
        (
            ToolCall("list_dir", workspace_id),
            ToolCall("create_dir", workspace_id, ("Drafts",)),
            ToolCall(
                "move_file",
                workspace_id,
                ("readme.txt",),
                {"destination": "Drafts/readme.txt"},
            ),
        ),
        intent="Tidy up my thesis folder",
    )


def test_a_submitted_plan_starts_pending_and_stays_pending(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    """Nothing approves itself. This is the whole point of the component."""
    plan = _tidy_plan(workspace_id)
    pending = approvals.submit(plan, policy.classify_plan(plan))

    assert pending.outcome is Outcome.PENDING
    assert approvals.is_approved(plan.plan_id) is False
    assert len(approvals.pending()) == 1


def test_the_preview_says_what_will_and_will_not_happen(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    """A person answers faster when told what is not at stake."""
    plan = _tidy_plan(workspace_id)
    preview = approvals.submit(plan, policy.classify_plan(plan)).preview

    assert preview["risk"] == "T1"
    assert preview["reversible"] is True
    assert preview["leaves_machine"] is False
    assert preview["deletes_anything"] is False
    assert len(preview["steps"]) == 3


def test_a_preview_flags_when_something_leaves_the_machine(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    plan = Plan((ToolCall("send_mail", workspace_id),))
    preview = approvals.submit(plan, policy.classify_plan(plan)).preview

    assert preview["risk"] == "T2"
    assert preview["leaves_machine"] is True


def test_approving_marks_the_plan_approved(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    plan = _tidy_plan(workspace_id)
    approvals.submit(plan, policy.classify_plan(plan))

    approvals.approve(plan.plan_id)

    assert approvals.is_approved(plan.plan_id) is True
    assert approvals.pending() == []


def test_rejecting_never_becomes_approval(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    plan = _tidy_plan(workspace_id)
    approvals.submit(plan, policy.classify_plan(plan))

    approvals.reject(plan.plan_id, reason="not what I meant")

    assert approvals.is_approved(plan.plan_id) is False
    assert approvals.get(plan.plan_id).outcome is Outcome.REJECTED


def test_expiry_is_not_approval(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    """A plan that is cleared away must never become executable."""
    plan = _tidy_plan(workspace_id)
    approvals.submit(plan, policy.classify_plan(plan))

    approvals.expire(plan.plan_id)

    assert approvals.is_approved(plan.plan_id) is False
    assert approvals.get(plan.plan_id).outcome is Outcome.EXPIRED


def test_a_plan_cannot_be_decided_twice(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    plan = _tidy_plan(workspace_id)
    approvals.submit(plan, policy.classify_plan(plan))
    approvals.approve(plan.plan_id)

    with pytest.raises(ValueError, match="already"):
        approvals.reject(plan.plan_id)


def test_approve_and_remember_only_covers_the_gated_calls(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    """Remembering a tidy must not also remember sending mail."""
    plan = _tidy_plan(workspace_id)
    approvals.submit(plan, policy.classify_plan(plan))
    approvals.approve(plan.plan_id, remember=True)

    remembered = {row["operation"] for row in policy.rules(workspace_id)}
    assert remembered == {"create_dir", "move_file"}
    assert "send_mail" not in remembered


def test_remembering_an_outward_action_is_refused_even_when_asked(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int
) -> None:
    plan = Plan((ToolCall("send_mail", workspace_id),))
    approvals.submit(plan, policy.classify_plan(plan))
    approvals.approve(plan.plan_id, remember=True)

    assert policy.rules(workspace_id) == []


def test_both_outcomes_are_written_to_the_audit_log(
    approvals: ApprovalBroker, policy: PolicyEngine, workspace_id: int, store: Store
) -> None:
    """A rejection is recorded as fully as an approval."""
    first = _tidy_plan(workspace_id)
    approvals.submit(first, policy.classify_plan(first))
    approvals.approve(first.plan_id)

    second = _tidy_plan(workspace_id)
    approvals.submit(second, policy.classify_plan(second))
    approvals.reject(second.plan_id)

    decided = [row for row in store.list_audit() if row["event"] == "approval.decided"]
    outcomes = {row["outcome"] for row in decided}
    assert outcomes == {"approved", "rejected"}
    assert store.verify_audit_chain()


def test_deciding_an_unknown_plan_raises(approvals: ApprovalBroker) -> None:
    with pytest.raises(KeyError):
        approvals.approve("never-submitted")
