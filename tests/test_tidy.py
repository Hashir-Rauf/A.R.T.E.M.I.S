"""F2: Tidy up a folder.

The central test is `test_the_service_has_no_way_to_delete`: a capability that
cannot destroy anything is a stronger guarantee than one that is merely
refused when it tries. The rest check that the proposal is honest about what it
would do, and that it declines to suggest work that is not worth doing.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from artemis.core.broker import WorkspaceBroker
from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.services import tidy as tidy_module
from artemis.services.tidy import TidyService


@pytest.fixture
def tidy(store: Store, broker: WorkspaceBroker) -> TidyService:
    return TidyService(store, broker)


@pytest.fixture
def messy(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path) -> int:
    """A folder with enough loose files of mixed kinds to be worth tidying."""
    folder = tmp_path / "messy"
    folder.mkdir()
    for name in (
        "thesis.pdf", "notes.pdf", "refs.pdf",
        "data.csv", "results.csv",
        "photo.png", "diagram.png",
        "stray.xyz",
    ):
        (folder / name).write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Messy").id
    indexer.scan(workspace_id)
    return workspace_id


def test_loose_files_are_grouped_by_kind(tidy: TidyService, messy: int) -> None:
    proposal = tidy.propose(messy)

    groups = proposal.groups()
    assert set(groups) == {"Documents", "Spreadsheets", "Images"}
    assert len(groups["Documents"]) == 3


def test_every_move_is_visible_before_anything_happens(
    tidy: TidyService, messy: int
) -> None:
    """The user approves twelve specific moves, not 'tidy my folder'."""
    proposal = tidy.propose(messy)

    assert len(proposal.moves) == 7
    for move in proposal.moves:
        assert move.filename in move.describe()
        assert move.group in move.describe()


def test_a_lone_file_of_its_kind_is_left_alone(
    tidy: TidyService, messy: int
) -> None:
    """A group of one is a file with a folder around it."""
    proposal = tidy.propose(messy)
    assert "stray.xyz" in proposal.left_alone


def test_the_summary_says_nothing_is_deleted(
    tidy: TidyService, messy: int
) -> None:
    assert "Nothing is deleted" in tidy.propose(messy).summary()


def test_an_already_tidy_folder_is_not_disturbed(
    tidy: TidyService, manager: WorkspaceManager, indexer: Indexer, tmp_path: Path
) -> None:
    """Suggesting work that is not worth doing is its own kind of annoyance."""
    folder = tmp_path / "already-tidy"
    folder.mkdir()
    (folder / "one.txt").write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Tidy").id
    indexer.scan(workspace_id)

    proposal = tidy.propose(workspace_id)

    assert proposal.is_worth_doing is False
    assert "tidy enough" in proposal.summary()


def test_files_already_filed_in_subfolders_are_ignored(
    tidy: TidyService, manager: WorkspaceManager, indexer: Indexer, tmp_path: Path
) -> None:
    """Reorganising someone's existing structure is a ruder operation."""
    folder = tmp_path / "part-filed"
    (folder / "Already").mkdir(parents=True)
    for name in ("a.pdf", "b.pdf", "c.pdf", "d.pdf"):
        (folder / name).write_text("x", encoding="utf-8")
    (folder / "Already" / "filed.pdf").write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Part").id
    indexer.scan(workspace_id)

    proposal = tidy.propose(workspace_id)
    moved = {move.rel_path for move in proposal.moves}

    assert "Already/filed.pdf" not in moved
    assert len(moved) == 4


def test_a_name_collision_gets_a_new_name_not_an_overwrite(
    tidy: TidyService, manager: WorkspaceManager, indexer: Indexer, tmp_path: Path
) -> None:
    """Overwriting is destructive, and this service has no destructive path."""
    folder = tmp_path / "collide"
    (folder / "Documents").mkdir(parents=True)
    (folder / "Documents" / "report.pdf").write_text("the original", encoding="utf-8")
    for name in ("report.pdf", "other.pdf", "third.pdf", "fourth.pdf"):
        (folder / name).write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Collide").id
    indexer.scan(workspace_id)

    proposal = tidy.propose(workspace_id)
    destinations = {move.destination for move in proposal.moves}

    assert "Documents/report (2).pdf" in destinations
    assert (folder / "Documents" / "report.pdf").read_text(encoding="utf-8") == "the original"


def test_grouping_by_date_is_available(tidy: TidyService, messy: int) -> None:
    proposal = tidy.propose(messy, by_date=True)
    assert proposal.is_worth_doing
    assert all(len(group) == 7 and group[4] == "-" for group in proposal.groups())


def test_the_plan_creates_folders_before_moving_into_them(
    tidy: TidyService, messy: int
) -> None:
    plan = tidy.to_plan(tidy.propose(messy))
    operations = [call.operation for call in plan]

    assert operations.count("create_dir") == 3
    first_move = operations.index("move_file")
    assert all(op == "create_dir" for op in operations[:first_move])


def test_proposing_changes_nothing_on_disk(
    tidy: TidyService, messy: int, store: Store
) -> None:
    """The service proposes. Executing is the dispatcher's job."""
    root = Path(store.get_workspace(messy)["root"])
    before = sorted(p.name for p in root.iterdir())

    tidy.propose(messy)
    tidy.to_plan(tidy.propose(messy))

    assert sorted(p.name for p in root.iterdir()) == before


def test_the_service_has_no_way_to_delete(tidy: TidyService) -> None:
    """A capability that cannot destroy is stronger than one that is refused.

    Checked against the source rather than by behaviour, because the claim is
    about what the module is able to do at all.
    """
    source = inspect.getsource(tidy_module)
    for forbidden in ("unlink(", "rmtree(", "os.remove", "shutil.rmtree"):
        assert forbidden not in source, f"tidy service can call {forbidden}"
