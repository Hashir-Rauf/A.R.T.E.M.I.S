"""The ARTEMIS window, driven headless.

These tests exist in the shape they do because of a bug they failed to catch.

The first version of this file tested `revoke_workspace()` and `forget_file()`
directly, on the grounds that the button handlers raise modal dialogues and are
therefore awkward to drive. Both passed. But the button on screen called
`on_revoke()`, which read a selection the user had no reason to have made, and
so did nothing at all. The tests were green and the feature was broken.

So: every test here goes through the method the button is actually connected to,
with the dialogue stubbed to a chosen answer. Testing the layer beneath the one
that failed is not testing the feature.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Qt must be told to run without a display before QApplication is constructed.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="PySide6 is not installed")

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton  # noqa: E402

from artemis.core.indexer import Indexer  # noqa: E402
from artemis.core.workspace import WorkspaceManager  # noqa: E402
from artemis.data.store import Store  # noqa: E402
from artemis.ui.panel import ALL_WORKSPACES, KnowledgeWindow, WorkspaceCard  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """One QApplication for the whole session; Qt permits only one."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp: QApplication, store: Store) -> KnowledgeWindow:
    win = KnowledgeWindow(store)
    yield win
    win.close()


@pytest.fixture
def answer_dialogues(monkeypatch: pytest.MonkeyPatch):
    """Stub QMessageBox so a confirmation resolves without a human.

    `exec` returns immediately and `clickedButton` reports whichever role we
    choose, which is how the destructive confirmations are driven below.
    """

    def choose(role: str) -> None:
        def fake_exec(self) -> int:
            self._chosen_role = role  # noqa: SLF001
            return 0

        def fake_clicked(self):
            for button in self.buttons():
                if self.buttonRole(button).name.lower().startswith(
                    self._chosen_role  # noqa: SLF001
                ):
                    return button
            return None

        monkeypatch.setattr(QMessageBox, "exec", fake_exec, raising=False)
        monkeypatch.setattr(QMessageBox, "clickedButton", fake_clicked, raising=False)

    return choose


def _row(window: KnowledgeWindow, label: str):
    return next(r for r in window._rows if r.label == label)  # noqa: SLF001


def _cards(window: KnowledgeWindow) -> list[WorkspaceCard]:
    layout = window.cards_layout
    found = []
    for i in range(layout.count()):
        widget = layout.itemAt(i).widget()
        if isinstance(widget, WorkspaceCard):
            found.append(widget)
    return found


# -- the regression the old tests missed ---------------------------------------


def test_forgetting_a_folder_works_straight_after_adding_it(
    window: KnowledgeWindow, sandbox: Path, store: Store, answer_dialogues
) -> None:
    """The exact sequence that used to fail.

    Add a folder, then immediately press its forget button. The old layout
    required selecting the folder in a list first, and silently did nothing when
    the user had not.
    """
    window.grant_folder(sandbox, name="Thesis")
    ws = WorkspaceManager(store).list()[0]

    answer_dialogues("destructive")
    window.confirm_forget_workspace(ws.id)

    assert WorkspaceManager(store).list() == []
    assert _cards(window) == []


def test_keeping_a_folder_leaves_it_alone(
    window: KnowledgeWindow, sandbox: Path, store: Store, answer_dialogues
) -> None:
    window.grant_folder(sandbox)
    ws = WorkspaceManager(store).list()[0]

    answer_dialogues("reject")
    window.confirm_forget_workspace(ws.id)

    assert len(WorkspaceManager(store).list()) == 1


def test_every_card_carries_its_own_actions(
    window: KnowledgeWindow, sandbox: Path, tmp_path: Path
) -> None:
    """No action depends on a prior selection, which is what caused the bug.

    Each card must carry the full set of actions for its own folder, so that a
    button can never be ambiguous about which folder it means.
    """
    other = tmp_path / "second"
    other.mkdir()
    (other / "only.txt").write_text("x", encoding="utf-8")

    window.grant_folder(sandbox, name="First")
    window.grant_folder(other, name="Second")

    cards = _cards(window)
    assert len(cards) == 2
    for card in cards:
        labels = {b.text() for b in card.findChildren(QPushButton)}
        assert labels == {"Show files", "Check for changes", "Forget this folder"}


def test_forgetting_the_second_folder_leaves_the_first(
    window: KnowledgeWindow, sandbox: Path, tmp_path: Path, store: Store,
    answer_dialogues,
) -> None:
    other = tmp_path / "second"
    other.mkdir()
    (other / "only.txt").write_text("x", encoding="utf-8")

    window.grant_folder(sandbox, name="First")
    window.grant_folder(other, name="Second")
    second = WorkspaceManager(store).list()[1]

    answer_dialogues("destructive")
    window.confirm_forget_workspace(second.id)

    remaining = WorkspaceManager(store).list()
    assert len(remaining) == 1
    assert remaining[0].name == "First"


def test_forget_file_button_goes_through_the_handler(
    window: KnowledgeWindow, sandbox: Path, store: Store
) -> None:
    """`on_forget_item` is what the button calls, so that is what is tested."""
    window.grant_folder(sandbox)
    ws = WorkspaceManager(store).list()[0]
    window.show_files_for(ws.id)

    index = next(
        i
        for i in range(window.detail_list.count())
        if window.detail_list.item(i).text() == "readme.txt"
    )
    window.detail_list.setCurrentRow(index)
    window.on_forget_item()

    assert store.count_files(ws.id) == 1
    assert (sandbox / "readme.txt").exists()


def test_erase_everything_clears_all_folders(
    window: KnowledgeWindow, sandbox: Path, tmp_path: Path, store: Store,
    answer_dialogues,
) -> None:
    other = tmp_path / "second"
    other.mkdir()
    (other / "only.txt").write_text("x", encoding="utf-8")
    window.grant_folder(sandbox)
    window.grant_folder(other)

    answer_dialogues("destructive")
    window.confirm_erase_everything()

    assert WorkspaceManager(store).list() == []
    assert (sandbox / "readme.txt").exists()
    assert (other / "only.txt").exists()


# -- the rest of the surface ---------------------------------------------------


def test_window_opens_holding_nothing(window: KnowledgeWindow) -> None:
    """An empty store is a legitimate state: ARTEMIS can see nothing."""
    assert _cards(window) == []
    assert "cannot see" in window.summary_label.text().lower() or "Nothing stored" in (
        window.summary_label.text()
    )


def test_adding_a_folder_shows_a_card(window: KnowledgeWindow, sandbox: Path) -> None:
    assert window.grant_folder(sandbox, name="Thesis") is True
    cards = _cards(window)
    assert len(cards) == 1
    assert _row(window, "Files indexed").count == 2


def test_adding_a_missing_folder_is_reported_not_raised(
    window: KnowledgeWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "artemis.ui.panel.QMessageBox.warning", lambda *a, **k: None
    )
    assert window.grant_folder(tmp_path / "nope") is False
    assert _cards(window) == []


def test_audit_row_is_never_deletable(window: KnowledgeWindow, sandbox: Path) -> None:
    """A log the subject can erase is not an audit log."""
    window.grant_folder(sandbox)
    assert _row(window, "Actions recorded").deletable is False


def test_files_are_hidden_until_asked_for(
    window: KnowledgeWindow, sandbox: Path, store: Store
) -> None:
    # isVisibleTo, not isVisible: a child reports itself invisible while no
    # top-level window has been shown, which is always the case headless.
    window.grant_folder(sandbox)
    assert window.files_panel.isVisibleTo(window) is False

    ws = WorkspaceManager(store).list()[0]
    window.show_files_for(ws.id)
    assert window.files_panel.isVisibleTo(window) is True
    assert window.detail_list.count() == 2


def test_forget_file_button_is_disabled_with_no_selection(
    window: KnowledgeWindow, sandbox: Path, store: Store
) -> None:
    window.grant_folder(sandbox)
    ws = WorkspaceManager(store).list()[0]
    window.show_files_for(ws.id)
    window.detail_list.setCurrentRow(-1)
    assert window.forget_file_button.isEnabled() is False


def test_file_list_closes_when_its_folder_is_forgotten(
    window: KnowledgeWindow, sandbox: Path, store: Store, answer_dialogues
) -> None:
    window.grant_folder(sandbox)
    ws = WorkspaceManager(store).list()[0]
    window.show_files_for(ws.id)
    assert window.files_panel.isVisibleTo(window) is True

    answer_dialogues("destructive")
    window.confirm_forget_workspace(ws.id)
    assert window.files_panel.isVisibleTo(window) is False


def test_panel_reflects_changes_made_outside_it(
    window: KnowledgeWindow, sandbox: Path, store: Store
) -> None:
    """The window is a query, not a cache."""
    window.grant_folder(sandbox)
    ws = WorkspaceManager(store).list()[0]

    (sandbox / "late.txt").write_text("added later", encoding="utf-8")
    Indexer(store, window._broker).scan(ws.id)  # noqa: SLF001
    window.refresh()

    assert _row(window, "Files indexed").count == 3


def test_rescan_picks_up_a_deleted_file(
    window: KnowledgeWindow, sandbox: Path, store: Store
) -> None:
    window.grant_folder(sandbox)
    ws = WorkspaceManager(store).list()[0]
    (sandbox / "readme.txt").unlink()
    window.rescan_workspace(ws.id)
    assert _row(window, "Files indexed").count == 1


def test_rescan_says_when_nothing_changed(
    window: KnowledgeWindow, sandbox: Path, store: Store
) -> None:
    window.grant_folder(sandbox)
    ws = WorkspaceManager(store).list()[0]
    window.rescan_workspace(ws.id)
    assert "nothing has changed" in window.statusBar().currentMessage().lower()


def test_summary_is_written_in_plain_words(
    window: KnowledgeWindow, sandbox: Path
) -> None:
    window.grant_folder(sandbox)
    text = window.summary_label.text()
    assert "2 files" in text
    assert "this computer only" in text


def test_selected_workspace_defaults_to_all(window: KnowledgeWindow) -> None:
    assert window.selected_workspace_id() == ALL_WORKSPACES
