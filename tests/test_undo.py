"""The Undo Journal: taking back a plan the user approved.

The two properties under test are the ones the architecture is specific about:
snapshots are taken before a change rather than after, and a plan is reversed as
one unit in reverse order. Both are easy to get subtly wrong in ways that only
show up when someone actually needs their files back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.undo import UndoJournal
from artemis.core.workspace import WorkspaceManager
from artemis.data import paths
from artemis.data.store import Store


@pytest.fixture
def journal(store: Store) -> UndoJournal:
    return UndoJournal(store)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


def test_a_snapshot_captures_the_file_as_it_was(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    target = sandbox / "readme.txt"
    original = target.read_text(encoding="utf-8")

    journal.record_write("plan-1", workspace_id, target)
    target.write_text("overwritten", encoding="utf-8")
    journal.undo_plan("plan-1")

    assert target.read_text(encoding="utf-8") == original


def test_undoing_a_created_file_removes_it(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    """A file that did not exist before should not exist after undo."""
    target = sandbox / "brand-new.txt"
    journal.record_write("plan-2", workspace_id, target)
    target.write_text("new content", encoding="utf-8")

    journal.undo_plan("plan-2")
    assert not target.exists()


def test_undoing_a_move_puts_the_file_back(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    import shutil

    source = sandbox / "readme.txt"
    destination = sandbox / "notes" / "readme.txt"

    journal.record_move("plan-3", workspace_id, source, destination)
    shutil.move(str(source), str(destination))
    assert not source.exists()

    journal.undo_plan("plan-3")
    assert source.exists()
    assert not destination.exists()


def test_a_whole_plan_reverses_as_one_unit(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    """The plan is the unit the user approved, so it is the unit undo works at."""
    import shutil

    drafts = sandbox / "Drafts"
    journal.record_mkdir("tidy", workspace_id, drafts)
    drafts.mkdir()

    moved = []
    for name in ("readme.txt", "notes/chapter3.md"):
        source = sandbox / name
        destination = drafts / Path(name).name
        journal.record_move("tidy", workspace_id, source, destination)
        shutil.move(str(source), str(destination))
        moved.append((source, destination))

    for source, destination in moved:
        assert destination.exists() and not source.exists()

    reversed_count, problems = journal.undo_plan("tidy")

    assert problems == []
    assert reversed_count == 3
    for source, destination in moved:
        assert source.exists() and not destination.exists()
    assert not drafts.exists(), "the created folder should be gone too"


def test_reversal_happens_in_reverse_order(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    """Files must leave a folder before the folder itself can be removed.

    Forward order would try to remove the directory while it still held the
    moved files, and the removal would silently do nothing.
    """
    import shutil

    drafts = sandbox / "Drafts"
    journal.record_mkdir("ordered", workspace_id, drafts)
    drafts.mkdir()

    source = sandbox / "readme.txt"
    destination = drafts / "readme.txt"
    journal.record_move("ordered", workspace_id, source, destination)
    shutil.move(str(source), str(destination))

    journal.undo_plan("ordered")

    assert source.exists()
    assert not drafts.exists()


def test_a_folder_the_user_filled_is_not_removed(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    """Undo must not delete something the user put there afterwards."""
    drafts = sandbox / "Drafts"
    journal.record_mkdir("plan-4", workspace_id, drafts)
    drafts.mkdir()
    (drafts / "the-users-own-file.txt").write_text("mine", encoding="utf-8")

    journal.undo_plan("plan-4")

    assert drafts.exists()
    assert (drafts / "the-users-own-file.txt").exists()


def test_snapshots_are_shared_by_content(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    """Identical content is stored once, so repeated snapshots stay cheap."""
    first = sandbox / "readme.txt"
    second = sandbox / "copy.txt"
    second.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")

    entry_one = journal.record_write("plan-5", workspace_id, first)
    entry_two = journal.record_write("plan-5", workspace_id, second)

    assert entry_one.snapshot_ref == entry_two.snapshot_ref
    assert len(list(paths.blobs_dir().iterdir())) == 1


def test_undoing_an_unknown_plan_reports_rather_than_raises(
    journal: UndoJournal,
) -> None:
    reversed_count, problems = journal.undo_plan("never-existed")
    assert reversed_count == 0
    assert problems


def test_a_reversed_plan_is_cleared_from_the_journal(
    journal: UndoJournal, workspace_id: int, sandbox: Path
) -> None:
    target = sandbox / "readme.txt"
    journal.record_write("plan-6", workspace_id, target)
    target.write_text("changed", encoding="utf-8")

    journal.undo_plan("plan-6")

    assert journal.entries_for_plan("plan-6") == []


def test_undo_is_recorded_in_the_audit_log(
    journal: UndoJournal, workspace_id: int, sandbox: Path, store: Store
) -> None:
    target = sandbox / "readme.txt"
    journal.record_write("plan-7", workspace_id, target)
    target.write_text("changed", encoding="utf-8")
    journal.undo_plan("plan-7")

    undos = [row for row in store.list_audit() if row["event"] == "undo.plan"]
    assert len(undos) == 1
    assert store.verify_audit_chain()
