"""The Policy Engine: what may run, what must be asked, what is refused.

The evaluation order is the substance of these tests, not an implementation
detail. Denials are checked before gates and gates before permissions, so no
later rule can grant what an earlier one refused. If someone reorders those
checks, several of these fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.actions import Decision, Plan, Tier, ToolCall
from artemis.core.broker import WorkspaceBroker
from artemis.core.policy import AUTO, PolicyEngine
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


@pytest.fixture
def policy(store: Store, broker: WorkspaceBroker) -> PolicyEngine:
    return PolicyEngine(store, broker)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


# -- the five rules, in order --------------------------------------------------


def test_a_read_inside_the_workspace_runs(policy: PolicyEngine, workspace_id: int) -> None:
    verdict = policy.classify(ToolCall("read_file", workspace_id, ("readme.txt",)))
    assert verdict.tier is Tier.READ
    assert verdict.decision is Decision.ALLOW


def test_a_change_to_files_is_gated(policy: PolicyEngine, workspace_id: int) -> None:
    verdict = policy.classify(ToolCall("write_file", workspace_id, ("readme.txt",)))
    assert verdict.tier is Tier.REVERSIBLE
    assert verdict.decision is Decision.GATE


def test_anything_leaving_the_machine_is_gated(
    policy: PolicyEngine, workspace_id: int
) -> None:
    verdict = policy.classify(ToolCall("send_mail", workspace_id))
    assert verdict.tier is Tier.OUTWARD
    assert verdict.decision is Decision.GATE


def test_destructive_operations_are_refused(
    policy: PolicyEngine, workspace_id: int
) -> None:
    """T3 has no approval path. This is the 'deletes nothing' guarantee."""
    verdict = policy.classify(ToolCall("delete_file", workspace_id, ("readme.txt",)))
    assert verdict.tier is Tier.DESTRUCTIVE
    assert verdict.decision is Decision.DENY


def test_a_path_outside_the_grant_is_refused_before_anything_else(
    policy: PolicyEngine, workspace_id: int
) -> None:
    """The grant check runs first, so even a read cannot escape."""
    verdict = policy.classify(
        ToolCall("read_file", workspace_id, ("../private/passwords.txt",))
    )
    assert verdict.decision is Decision.DENY
    assert verdict.rule_applied == "grant-check"


def test_an_unknown_operation_is_refused_rather_than_assumed_safe(
    policy: PolicyEngine, workspace_id: int
) -> None:
    """Silently permitting unrecognised operations is how a boundary erodes."""
    verdict = policy.classify(ToolCall("rm_rf", workspace_id))
    assert verdict.decision is Decision.DENY
    assert verdict.rule_applied == "unknown-operation"


# -- remembered approvals ------------------------------------------------------


def test_remembering_lets_a_change_run_without_asking_again(
    policy: PolicyEngine, workspace_id: int
) -> None:
    call = ToolCall("move_file", workspace_id, ("readme.txt",))
    assert policy.classify(call).decision is Decision.GATE

    policy.remember(call, AUTO)

    later = ToolCall("move_file", workspace_id, ("something-else.txt",))
    verdict = policy.classify(later)
    assert verdict.decision is Decision.ALLOW
    assert verdict.remembered is True


def test_remembering_is_scoped_to_one_operation(
    policy: PolicyEngine, workspace_id: int
) -> None:
    """Approving a folder tidy must not quietly approve everything else."""
    policy.remember(ToolCall("move_file", workspace_id, ("a.txt",)), AUTO)
    other = policy.classify(ToolCall("write_file", workspace_id, ("b.txt",)))
    assert other.decision is Decision.GATE


def test_remembering_is_scoped_to_one_workspace(
    policy: PolicyEngine, manager: WorkspaceManager, workspace_id: int, tmp_path: Path
) -> None:
    second = tmp_path / "second"
    second.mkdir()
    (second / "x.txt").write_text("x", encoding="utf-8")
    other_id = manager.grant(second).id

    policy.remember(ToolCall("move_file", workspace_id, ("a.txt",)), AUTO)

    verdict = policy.classify(ToolCall("move_file", other_id, ("x.txt",)))
    assert verdict.decision is Decision.GATE


def test_outward_actions_can_never_be_remembered(
    policy: PolicyEngine, workspace_id: int
) -> None:
    """Always gated, whatever the user configures."""
    call = ToolCall("send_mail", workspace_id)
    policy.remember(call, AUTO)
    assert policy.classify(call).decision is Decision.GATE


def test_destructive_actions_can_never_be_remembered(
    policy: PolicyEngine, workspace_id: int
) -> None:
    call = ToolCall("delete_file", workspace_id, ("readme.txt",))
    policy.remember(call, AUTO)
    assert policy.classify(call).decision is Decision.DENY


# -- plans ---------------------------------------------------------------------


def test_a_plan_takes_the_highest_tier_it_contains(
    policy: PolicyEngine, workspace_id: int
) -> None:
    plan = Plan(
        (
            ToolCall("list_dir", workspace_id),
            ToolCall("create_dir", workspace_id, ("Drafts",)),
            ToolCall("send_mail", workspace_id),
        )
    )
    verdicts = policy.classify_plan(plan)
    assert policy.highest_tier(verdicts) is Tier.OUTWARD
    assert policy.plan_needs_approval(verdicts) is True


def test_a_read_only_plan_needs_no_approval(
    policy: PolicyEngine, workspace_id: int
) -> None:
    plan = Plan(
        (
            ToolCall("list_dir", workspace_id),
            ToolCall("read_file", workspace_id, ("readme.txt",)),
        )
    )
    verdicts = policy.classify_plan(plan)
    assert policy.plan_needs_approval(verdicts) is False
    assert policy.highest_tier(verdicts) is Tier.READ


def test_refusals_are_written_to_the_audit_log(
    policy: PolicyEngine, workspace_id: int, store: Store
) -> None:
    """The log records what was proposed, not only what happened."""
    policy.classify(ToolCall("delete_file", workspace_id, ("readme.txt",)))

    refusals = [
        row
        for row in store.list_audit()
        if row["event"] == "policy.classify" and row["outcome"] == "refused"
    ]
    assert len(refusals) == 1
    assert store.verify_audit_chain()
