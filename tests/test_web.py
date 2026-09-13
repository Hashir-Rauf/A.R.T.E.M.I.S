"""The web interface, tested without a browser.

`WebPanel` holds every action and every piece of rendering, deliberately
separated from the Gradio wiring, so the behaviour can be tested directly. That
split exists because of two earlier defects in this project: a watcher that was
broken while its tests passed, and a revoke button whose handler was never
exercised. Both hid in a layer no test drove.

`build()` is also constructed here, because a mistake in the event wiring only
surfaces when the page is assembled.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("gradio", reason="Gradio is not installed")

from artemis.data.store import Store  # noqa: E402
from artemis.ui.web import WebPanel, _esc, _plural, build  # noqa: E402


@pytest.fixture
def panel(store: Store) -> WebPanel:
    return WebPanel(store)


# -- rendering -----------------------------------------------------------------


def test_empty_state_states_the_limit(panel: WebPanel) -> None:
    """The reassuring part is what ARTEMIS cannot do, so it leads."""
    markup = panel.cards_html()
    assert "cannot see anything" in markup
    assert "only ever looks inside the folders you choose" in markup


def test_a_added_folder_appears_as_a_card(panel: WebPanel, sandbox: Path) -> None:
    panel.add(str(sandbox))
    markup = panel.cards_html()
    assert sandbox.name in markup
    assert "2 files" in markup


def test_metrics_count_what_is_held(panel: WebPanel, sandbox: Path) -> None:
    panel.add(str(sandbox))
    markup = panel.metrics_html()
    assert "folders visible" in markup
    assert "files known" in markup
    assert "stored locally" in markup


def test_file_list_is_empty_until_a_folder_is_chosen(panel: WebPanel) -> None:
    assert "Choose a folder" in panel.files_html(None)


def test_file_list_shows_known_files(panel: WebPanel, sandbox: Path) -> None:
    panel.add(str(sandbox))
    ws = panel.workspaces()[0]
    markup = panel.files_html(ws.id)
    assert "readme.txt" in markup
    assert "notes/chapter3.md" in markup


def test_singular_and_plural_read_correctly(panel: WebPanel, tmp_path: Path) -> None:
    """'1 files' is the kind of detail that makes software feel unfinished."""
    one = tmp_path / "single"
    one.mkdir()
    (one / "only.txt").write_text("x", encoding="utf-8")
    panel.add(str(one))
    label = panel.choices()[0][0]
    assert "1 file" in label and "1 files" not in label


# -- actions -------------------------------------------------------------------


def test_adding_a_folder_reports_what_it_found(panel: WebPanel, sandbox: Path) -> None:
    message = panel.add(str(sandbox))
    assert "2 files" in message
    assert len(panel.workspaces()) == 1


def test_adding_nothing_warns(panel: WebPanel) -> None:
    message = panel.add("   ")
    assert "warn" in message
    assert len(panel.workspaces()) == 0


def test_adding_a_missing_folder_warns_rather_than_raising(
    panel: WebPanel, tmp_path: Path
) -> None:
    message = panel.add(str(tmp_path / "nope"))
    assert "warn" in message
    assert len(panel.workspaces()) == 0


def test_quoted_paths_are_accepted(panel: WebPanel, sandbox: Path) -> None:
    """Windows "Copy as path" wraps the path in quotes; accept that."""
    panel.add(f'"{sandbox}"')
    assert len(panel.workspaces()) == 1


def test_rescan_says_when_nothing_changed(panel: WebPanel, sandbox: Path) -> None:
    panel.add(str(sandbox))
    ws = panel.workspaces()[0]
    assert "Nothing has changed" in panel.rescan(ws.id)


def test_rescan_notices_a_new_file(panel: WebPanel, sandbox: Path) -> None:
    panel.add(str(sandbox))
    ws = panel.workspaces()[0]
    (sandbox / "late.txt").write_text("new", encoding="utf-8")
    assert "1 more file" in panel.rescan(ws.id)


def test_forgetting_a_folder_leaves_the_files_alone(
    panel: WebPanel, sandbox: Path
) -> None:
    panel.add(str(sandbox))
    ws = panel.workspaces()[0]
    message = panel.forget_workspace(ws.id)

    assert "were not touched" in message
    assert panel.workspaces() == []
    assert (sandbox / "readme.txt").exists()
    assert (sandbox / "notes" / "chapter3.md").exists()


def test_forgetting_everything_clears_all_folders(
    panel: WebPanel, sandbox: Path, tmp_path: Path
) -> None:
    other = tmp_path / "second"
    other.mkdir()
    (other / "only.txt").write_text("x", encoding="utf-8")
    panel.add(str(sandbox))
    panel.add(str(other))

    message = panel.forget_everything()
    assert "2 folders" in message
    assert panel.workspaces() == []
    assert (sandbox / "readme.txt").exists()
    assert (other / "only.txt").exists()


def test_acting_without_choosing_a_folder_warns(panel: WebPanel) -> None:
    assert "warn" in panel.rescan(None)
    assert "warn" in panel.forget_workspace(None)
    assert "warn" in panel.forget_everything()


def test_deny_listed_paths_never_reach_the_file_list(
    panel: WebPanel, sandbox: Path
) -> None:
    """The boundary holds in the web surface exactly as it does elsewhere."""
    (sandbox / ".ssh").mkdir()
    (sandbox / ".ssh" / "id_rsa").write_text("key", encoding="utf-8")
    panel.add(str(sandbox))
    ws = panel.workspaces()[0]
    assert "id_rsa" not in panel.files_html(ws.id)


# -- safety --------------------------------------------------------------------


def test_folder_names_are_escaped_into_the_markup(
    panel: WebPanel, tmp_path: Path, store: Store
) -> None:
    """Cards are raw HTML, so anything interpolated must be escaped.

    Windows forbids < and > in filenames, so the hostile name is written
    straight into the store rather than created on disk. That is also the more
    honest test: the rendering must be safe whatever reaches the database,
    regardless of what the filesystem would have permitted.
    """
    real = tmp_path / "ordinary"
    real.mkdir()
    (real / "f.txt").write_text("x", encoding="utf-8")
    panel.add(str(real))

    workspace_id = panel.workspaces()[0].id
    with store._write() as conn:  # noqa: SLF001 - seeding a hostile value
        conn.execute(
            "UPDATE workspaces SET name = ? WHERE id = ?",
            ("<script>alert(1)</script>", workspace_id),
        )

    markup = panel.cards_html()
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup


def test_escape_helper_neutralises_markup() -> None:
    assert "<script>" not in _esc('<script>alert(1)</script>')
    assert _plural(1, "file") == "1 file"
    assert _plural(0, "file") == "0 files"


# -- wiring --------------------------------------------------------------------


def test_the_page_assembles(store: Store) -> None:
    """A mistake in the event wiring only shows when the page is built."""
    page = build(store)
    assert page is not None
    assert page.title == "ARTEMIS"
