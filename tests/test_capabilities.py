"""Sprint 5 stage gate: three features run end to end through real gates.

Sprint 3 proved the gates hold against placeholder tools. Sprint 4 added a
planner that produces plans automatically. This sprint replaces the placeholders
with the capability services the nine features actually use, which reopens the
question those earlier sprints answered: now that the handlers do real work, can
anything reach the filesystem without passing through the broker, policy and
approval?

The tests below try to find such a path, and also cover FA-VNGA directly: that
capability services reach the filesystem only through the Workspace Broker.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from artemis.core.actions import Tier, ToolCall
from artemis.core.dispatch import DispatchRefused
from artemis.core.gateway import Gateway
from artemis.core.indexer import Indexer
from artemis.core.providers import ModelTier, StubProvider
from artemis.core.router import ModelRouter
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.services import registry
from artemis.services.tidy import TidyService

TIDY_REPLY = (
    '{"steps": ['
    '{"operation": "create_dir", "paths": ["Documents"], "arguments": {}},'
    '{"operation": "move_file", "paths": ["readme.txt"],'
    ' "arguments": {"destination": "Documents/readme.txt"}}]}'
)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


def _gateway(store: Store, *replies: str) -> Gateway:
    router = ModelRouter(store=store)
    router.register(
        StubProvider(name="stub", tier=ModelTier.LOCAL, model="s", replies=list(replies))
    )
    return Gateway.build(store, router)


# -- FA-VNGA: only through the broker ------------------------------------------


def test_handlers_never_construct_a_path_of_their_own(store: Store) -> None:
    """The structural guarantee, checked against the source.

    A handler receives paths the dispatcher resolved through the broker. If one
    ever built its own path from a workspace root, confinement would depend on
    that handler being careful rather than on the broker being the only route.
    """
    source = inspect.getsource(registry)
    for forbidden in ("Path.home(", "os.getcwd(", "artemis_home(", "os.environ"):
        assert forbidden not in source, f"a capability handler reaches for {forbidden}"


def test_no_capability_can_delete_or_overwrite(store: Store) -> None:
    """There is no delete, no overwrite and no execute in the registry."""
    source = inspect.getsource(registry)
    for forbidden in ("unlink(", "rmtree(", "os.remove", "subprocess", "os.system"):
        assert forbidden not in source, f"a capability handler can call {forbidden}"

    registered = set(registry.capability_handlers())
    assert not registered & {"delete_file", "delete_dir", "overwrite_file", "truncate"}


def test_an_operation_absent_from_the_registry_cannot_run(
    store: Store, workspace_id: int
) -> None:
    """Registration is an allowlist, so a new capability is a visible edit."""
    gateway = _gateway(store)
    assert "delete_file" not in gateway.dispatcher.registered()


def test_a_handler_refuses_to_move_onto_an_existing_file(
    store: Store, workspace_id: int, sandbox: Path
) -> None:
    """Landing on a file would destroy it, which is a T3 this system lacks."""
    gateway = _gateway(store)
    (sandbox / "notes" / "readme.txt").write_text("the original", encoding="utf-8")

    call = ToolCall(
        "move_file",
        workspace_id,
        ("readme.txt",),
        {"destination": "notes/readme.txt"},
    )
    verdicts = {call.call_id: gateway.policy.classify(call)}
    from artemis.core.actions import Plan

    plan = Plan((call,))
    gateway.approvals.submit(plan, verdicts)
    gateway.approvals.approve(plan.plan_id)

    result = gateway.dispatcher.execute_plan(plan, verdicts)

    assert len(result.executed) == 0
    assert (sandbox / "notes" / "readme.txt").read_text(encoding="utf-8") == "the original"


def test_a_capability_still_refuses_a_path_outside_the_grant(
    store: Store, workspace_id: int
) -> None:
    """The handler is real now, but the boundary is unchanged."""
    gateway = _gateway(store)
    call = ToolCall("read_file", workspace_id, ("../private/passwords.txt",))
    from artemis.core.actions import Decision, Verdict

    forged = Verdict(call.call_id, Tier.READ, Decision.ALLOW, "", "forged")

    with pytest.raises(DispatchRefused, match="outside the workspace"):
        gateway.dispatcher.execute(call, forged, "plan-x")


# -- the stage gate: three features end to end ---------------------------------


def test_stage_gate_tidy_plans_stops_runs_and_undoes(
    store: Store, broker, indexer: Indexer, manager: WorkspaceManager, tmp_path: Path
) -> None:
    """F2 through the real gates, with real handlers, on real files."""
    folder = tmp_path / "messy"
    folder.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf", "d.csv", "e.csv"):
        (folder / name).write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Messy").id
    indexer.scan(workspace_id)

    gateway = _gateway(store)
    proposal = TidyService(store, broker).propose(workspace_id)
    plan = TidyService(store, broker).to_plan(proposal)
    verdicts = gateway.policy.classify_plan(plan)

    # Nothing happens before approval.
    blocked = gateway.dispatcher.execute_plan(plan, verdicts)
    assert blocked.executed == ()
    assert (folder / "a.pdf").exists()
    assert not (folder / "Documents").exists()

    # It runs once approved.
    gateway.approvals.submit(plan, verdicts)
    gateway.approvals.approve(plan.plan_id)
    done = gateway.dispatcher.execute_plan(plan, verdicts)

    assert len(done.executed) == len(plan)
    assert (folder / "Documents" / "a.pdf").exists()
    assert (folder / "Spreadsheets" / "d.csv").exists()
    assert not (folder / "a.pdf").exists()

    # And it can be taken back as one unit.
    reversed_count, problems = gateway.undo(plan.plan_id)

    assert problems == []
    assert (folder / "a.pdf").exists()
    assert not (folder / "Documents").exists()
    assert store.verify_audit_chain()


def test_stage_gate_resume_reports_what_the_tidy_changed(
    store: Store, broker, indexer: Indexer, manager: WorkspaceManager, tmp_path: Path
) -> None:
    """F1 and F2 composing: a tidy happens, and resume describes it."""
    from artemis.services.resume import ResumeService

    folder = tmp_path / "work"
    folder.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf", "d.pdf"):
        (folder / name).write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Work").id
    indexer.scan(workspace_id)

    resume = ResumeService(store, broker)
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id, note="tidying up before the deadline")

    gateway = _gateway(store)
    plan = TidyService(store, broker).to_plan(
        TidyService(store, broker).propose(workspace_id)
    )
    verdicts = gateway.policy.classify_plan(plan)
    gateway.approvals.submit(plan, verdicts)
    gateway.approvals.approve(plan.plan_id)
    gateway.dispatcher.execute_plan(plan, verdicts)
    indexer.scan(workspace_id)

    report = resume.report(workspace_id)

    assert report.note == "tidying up before the deadline"
    assert any(c.change == "added" for c in report.changes)
    assert any(c.change == "removed" for c in report.changes)


def test_stage_gate_repeated_tidies_produce_an_offer_not_an_action(
    store: Store, broker, indexer: Indexer, manager: WorkspaceManager, tmp_path: Path
) -> None:
    """F4 on top of real executions: three moves, one offer, nothing installed."""
    from artemis.services.patterns import ACCEPTED, PatternWatcher

    folder = tmp_path / "repeat"
    folder.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf", "d.pdf"):
        (folder / name).write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Repeat").id
    indexer.scan(workspace_id)

    gateway = _gateway(store)
    plan = TidyService(store, broker).to_plan(
        TidyService(store, broker).propose(workspace_id)
    )
    verdicts = gateway.policy.classify_plan(plan)
    gateway.approvals.submit(plan, verdicts)
    gateway.approvals.approve(plan.plan_id)
    gateway.dispatcher.execute_plan(plan, verdicts)

    watcher = PatternWatcher(store)
    proposed = watcher.propose_new(workspace_id)

    assert proposed, "four moves of the same kind should be noticed"
    assert store.list_rules(workspace_id, status=ACCEPTED) == []


def test_stage_gate_a_read_only_turn_still_runs_without_asking(
    store: Store, workspace_id: int
) -> None:
    """Approval fatigue is a real cost; reads must not incur it."""
    gateway = _gateway(store, '{"steps": [{"operation": "list_dir", "paths": []}]}')

    outcome = gateway.handle(workspace_id, "what is in this folder")

    assert outcome.needs_approval is False
    assert outcome.result is not None
    assert all(v.tier is Tier.READ for v in outcome.verdicts.values())


def test_stage_gate_the_gateway_uses_the_capability_registry(
    store: Store, workspace_id: int
) -> None:
    """The placeholders are gone; the real capabilities are what is wired."""
    gateway = _gateway(store)
    registered = gateway.dispatcher.registered()

    assert "read_metadata" in registered
    assert "append_file" in registered
    assert registered == set(registry.capability_handlers())
