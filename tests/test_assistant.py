"""The assistant surface: the first point where a person can drive the gates.

These tests exist because of a pattern this project has hit twice already: a
component works, its tests pass, and the button that calls it does nothing. So
everything here goes through the methods the buttons are actually wired to.

The most important test is `test_approving_is_what_makes_it_run`. Four sprints
of machinery exist to make that one assertion true from a user's point of view:
the plan is visible, nothing happens, and then the person decides.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.ui.assistant import AssistantPanel


@pytest.fixture
def assistant(store: Store) -> AssistantPanel:
    return AssistantPanel(store)


@pytest.fixture
def messy(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path) -> int:
    folder = tmp_path / "messy"
    folder.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf", "d.csv", "e.csv"):
        (folder / name).write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Messy").id
    indexer.scan(workspace_id)
    return workspace_id


def _root(store: Store, workspace_id: int) -> Path:
    return Path(store.get_workspace(workspace_id)["root"])


# -- the approval flow ---------------------------------------------------------


def test_a_tidy_is_offered_and_nothing_happens_yet(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The plan is shown. The folder is untouched."""
    before = sorted(p.name for p in _root(store, messy).iterdir())

    message, card = assistant.suggest_tidy(messy)

    assert "Would move" in message
    assert "needs your permission" in card
    assert sorted(p.name for p in _root(store, messy).iterdir()) == before


def test_the_card_says_what_will_not_happen(
    assistant: AssistantPanel, messy: int
) -> None:
    """The reassuring facts are what let a person answer quickly."""
    _, card = assistant.suggest_tidy(messy)

    assert "Nothing is deleted" in card
    assert "Nothing leaves this computer" in card
    assert "You can undo this afterwards" in card


def test_every_step_is_listed_not_summarised(
    assistant: AssistantPanel, messy: int
) -> None:
    """Approving 'tidy my folder' would make the approval meaningless."""
    _, card = assistant.suggest_tidy(messy)

    assert card.count('class="a-step"') == 7  # 2 folders + 5 moves


def test_approving_is_what_makes_it_run(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The assertion four sprints of machinery exist to support."""
    root = _root(store, messy)
    assistant.suggest_tidy(messy)

    assert (root / "a.pdf").exists(), "nothing should have happened yet"

    message, card = assistant.approve()

    assert "Done" in message
    assert card == "", "the card must be cleared once answered"
    assert (root / "Documents" / "a.pdf").exists()
    assert not (root / "a.pdf").exists()


def test_rejecting_changes_nothing(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    root = _root(store, messy)
    assistant.suggest_tidy(messy)

    message, card = assistant.reject()

    assert "Left alone" in message
    assert card == ""
    assert (root / "a.pdf").exists()
    assert not (root / "Documents").exists()


def test_a_rejected_plan_cannot_then_be_approved(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """Answering clears the held turn, so the buttons cannot both apply."""
    assistant.suggest_tidy(messy)
    assistant.reject()

    message, _ = assistant.approve()

    assert "nothing waiting" in message
    assert not (_root(store, messy) / "Documents").exists()


def test_approving_with_remember_says_so(
    assistant: AssistantPanel, messy: int
) -> None:
    assistant.suggest_tidy(messy)
    message, _ = assistant.approve(remember=True)

    assert "will not ask again" in message


def test_approving_nothing_is_reported_not_crashed(
    assistant: AssistantPanel,
) -> None:
    message, card = assistant.approve()
    assert "nothing waiting" in message
    assert card == ""


# -- undo ----------------------------------------------------------------------


def test_undo_puts_the_files_back(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    root = _root(store, messy)
    before = sorted(p.name for p in root.iterdir())

    assistant.suggest_tidy(messy)
    assistant.approve()
    message = assistant.undo_last()

    assert "Undone" in message
    assert sorted(p.name for p in root.iterdir()) == before


def test_undo_with_nothing_to_undo_says_so(assistant: AssistantPanel) -> None:
    assert "nothing to undo" in assistant.undo_last()


def test_undo_is_offered_only_after_something_ran(
    assistant: AssistantPanel, messy: int
) -> None:
    assert assistant.can_undo is False

    assistant.suggest_tidy(messy)
    assert assistant.can_undo is False, "proposing is not doing"

    assistant.approve()
    assert assistant.can_undo is True


# -- resume and patterns -------------------------------------------------------


def test_resume_reports_what_changed(
    assistant: AssistantPanel, messy: int, indexer: Indexer
) -> None:
    assistant.suggest_tidy(messy)
    assistant.approve()
    indexer.scan(messy)

    html = assistant.resume_html(messy)

    assert "a-resume" in html
    assert "first time" in html or "new" in html


def test_patterns_are_offered_never_applied(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The feature's whole point: it asks, it does not act."""
    assistant.suggest_tidy(messy)
    assistant.approve()

    message = assistant.look_for_patterns(messy)

    assert "will not act" in message or "Nothing repeated" in message
    assert store.list_rules(messy, status="accepted") == []


def test_an_already_tidy_folder_is_not_nagged(
    assistant: AssistantPanel, manager: WorkspaceManager, indexer: Indexer,
    tmp_path: Path,
) -> None:
    folder = tmp_path / "tidy"
    folder.mkdir()
    (folder / "only.txt").write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Tidy").id
    indexer.scan(workspace_id)

    message, card = assistant.suggest_tidy(workspace_id)

    assert "tidy enough" in message
    assert card == ""


# -- guard rails ---------------------------------------------------------------


def test_asking_without_a_folder_is_explained(assistant: AssistantPanel) -> None:
    message, card = assistant.ask(None, "tidy up")
    assert "Choose a folder" in message
    assert card == ""


def test_asking_nothing_is_explained(assistant: AssistantPanel, messy: int) -> None:
    message, _ = assistant.ask(messy, "   ")
    assert "Type what" in message


def test_a_workspace_name_is_escaped_into_the_card(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The card is raw HTML, so anything interpolated must be escaped."""
    with store._write() as conn:  # noqa: SLF001 - seeding a hostile value
        conn.execute(
            "UPDATE workspaces SET name = ? WHERE id = ?",
            ("<script>alert(1)</script>", messy),
        )

    _, card = assistant.suggest_tidy(messy)

    assert "<script>" not in card
    assert "&lt;script&gt;" in card
