"""F4: Notice a repeated task.

Two rules define this feature, and both are tested as negatives because both
are about what ARTEMIS does *not* do: it says nothing before the third
repetition, and it cannot install an automation even once the user has
accepted one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.services.patterns import (
    ACCEPTED,
    DECLINED,
    PROPOSED,
    REPEAT_THRESHOLD,
    PatternWatcher,
)


@pytest.fixture
def watcher(store: Store) -> PatternWatcher:
    return PatternWatcher(store)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


def _did(store: Store, workspace_id: int, call: str, times: int = 1) -> None:
    """Record `times` executions of the same action in the audit log."""
    for _ in range(times):
        store.append_audit(
            event="dispatch.execute",
            outcome="executed",
            workspace_id=workspace_id,
            detail={"call": call, "tier": "T1"},
        )


# -- the threshold -------------------------------------------------------------


def test_nothing_is_offered_after_two_repetitions(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    """Twice is coincidence often enough that asking would be noise."""
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=2)
    assert watcher.detect(workspace_id) == []


def test_a_pattern_is_offered_on_the_third(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=REPEAT_THRESHOLD)

    patterns = watcher.detect(workspace_id)

    assert len(patterns) == 1
    assert patterns[0].occurrences == REPEAT_THRESHOLD
    assert "PDF files" in patterns[0].description


def test_the_same_kind_of_file_counts_as_one_pattern(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    """Three different PDFs into Documents is one habit, not three events."""
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        _did(store, workspace_id, f"move_file(Documents/{name})")

    patterns = watcher.detect(workspace_id)
    assert len(patterns) == 1
    assert patterns[0].occurrences == 3


def test_reads_are_never_counted(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    """Noticing that someone opens a file a lot is surveillance."""
    _did(store, workspace_id, "read_file(diary.md)", times=10)
    assert watcher.detect(workspace_id) == []


def test_a_refused_action_is_not_a_pattern(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    """Counting things the user was prevented from doing is backwards."""
    for _ in range(5):
        store.append_audit(
            event="dispatch.execute",
            outcome="refused",
            workspace_id=workspace_id,
            detail={"call": "move_file(Documents/a.pdf)"},
        )
    assert watcher.detect(workspace_id) == []


# -- proposing, never installing -----------------------------------------------


def test_a_proposal_starts_and_stays_proposed(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)
    pattern = watcher.detect(workspace_id)[0]

    rule_id = watcher.propose(workspace_id, pattern)

    rule = store.query_one("SELECT * FROM automation_rules WHERE id = ?", (rule_id,))
    assert rule["status"] == PROPOSED


def test_the_watcher_cannot_create_an_accepted_rule(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    """There is no method here that installs an automation."""
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)
    watcher.propose_new(workspace_id)

    assert store.list_rules(workspace_id, status=ACCEPTED) == []
    assert len(store.list_rules(workspace_id, status=PROPOSED)) == 1


def test_accepting_is_a_separate_act_by_the_user(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)
    rule_id = watcher.propose_new(workspace_id)[0]

    watcher.accept(workspace_id, rule_id)

    assert len(store.list_rules(workspace_id, status=ACCEPTED)) == 1


def test_a_declined_pattern_is_never_raised_again(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    """Asking again after being told no is worse than never asking."""
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)
    rule_id = watcher.propose_new(workspace_id)[0]
    watcher.decline(workspace_id, rule_id)

    _did(store, workspace_id, "move_file(Documents/d.pdf)", times=3)

    assert watcher.detect(workspace_id) == []
    assert watcher.propose_new(workspace_id) == []


def test_the_same_pattern_is_not_proposed_twice(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)
    first = watcher.propose_new(workspace_id)
    second = watcher.propose_new(workspace_id)

    assert len(first) == 1
    assert second == []


def test_open_proposals_read_as_plain_words(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)
    watcher.propose_new(workspace_id)

    proposals = watcher.open_proposals(workspace_id)
    assert len(proposals) == 1
    assert "moving PDF files" in proposals[0]["description"]


def test_decisions_are_recorded_in_the_audit_log(
    watcher: PatternWatcher, store: Store, workspace_id: int
) -> None:
    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)
    rule_id = watcher.propose_new(workspace_id)[0]
    watcher.decline(workspace_id, rule_id)

    decisions = [row for row in store.list_audit() if row["event"] == "patterns.decide"]
    assert decisions[0]["outcome"] == DECLINED
    assert store.verify_audit_chain()


def test_one_workspace_pattern_does_not_leak_into_another(
    watcher: PatternWatcher, store: Store, manager: WorkspaceManager,
    workspace_id: int, tmp_path: Path,
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    (other / "x.txt").write_text("x", encoding="utf-8")
    other_id = manager.grant(other, name="Other").id

    _did(store, workspace_id, "move_file(Documents/a.pdf)", times=3)

    assert watcher.detect(other_id) == []
