"""Where the store lives, and moving it.

Relocation is the riskiest operation in the codebase: it copies the user's
entire store and then deletes the original. These tests cover the ways that can
go wrong, because a partial move would lose everything ARTEMIS knows.

The ARTEMIS_HOME fixture in conftest sets the environment variable, which takes
precedence over the pointer file. Tests that exercise the pointer therefore
clear it first, so they are reading what a real user would.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.data import paths
from artemis.data.store import Store


@pytest.fixture
def pointer_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the pointer file itself somewhere disposable.

    Without this a test would write to the developer's real config directory
    and change where their own ARTEMIS store lives.
    """
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setattr(paths, "_pointer_file", lambda: config / "location")
    monkeypatch.delenv(paths.ENV_HOME, raising=False)
    return config


def test_env_var_wins_over_everything(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ARTEMIS_HOME is how tests and portable installs stay isolated."""
    forced = tmp_path / "forced"
    monkeypatch.setenv(paths.ENV_HOME, str(forced))
    assert paths.artemis_home() == forced


def test_default_when_nothing_is_configured(pointer_isolated: Path) -> None:
    assert paths.configured_home() is None
    assert paths.artemis_home() == paths.default_home()


def test_choosing_a_location_is_remembered(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    chosen = tmp_path / "elsewhere"
    paths.set_home(chosen, move_existing=False)

    assert paths.configured_home() == chosen.resolve()
    assert paths.artemis_home() == chosen.resolve()


def test_resetting_returns_to_the_default(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    paths.set_home(tmp_path / "elsewhere", move_existing=False)
    paths.reset_home()

    assert paths.configured_home() is None
    assert paths.artemis_home() == paths.default_home()


def test_moving_carries_the_store_across(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    """The database must survive the move with its contents intact."""
    start = tmp_path / "start"
    paths.set_home(start, move_existing=False)

    with Store() as store:
        store.append_audit("test.before-move", "recorded")
    assert (start / "artemis.db").exists()

    destination = tmp_path / "destination"
    paths.set_home(destination, move_existing=True)

    assert (destination / "artemis.db").exists()
    assert not (start / "artemis.db").exists()

    with Store() as store:
        assert any(row["event"] == "test.before-move" for row in store.list_audit())
        assert store.verify_audit_chain()


def test_moving_to_the_same_place_is_a_no_op(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    here = tmp_path / "here"
    paths.set_home(here, move_existing=False)
    with Store() as store:
        store.append_audit("test.stay", "recorded")

    paths.set_home(here, move_existing=True)

    assert (here / "artemis.db").exists()
    with Store() as store:
        assert any(row["event"] == "test.stay" for row in store.list_audit())


def test_moving_into_a_subfolder_of_itself_is_refused(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    """Otherwise the copy would recurse into its own destination."""
    outer = tmp_path / "outer"
    paths.set_home(outer, move_existing=False)

    with pytest.raises(ValueError, match="inside itself"):
        paths.set_home(outer / "inner", move_existing=True)


def test_moving_onto_an_occupied_folder_is_refused(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    """Refuse rather than overwrite: the folder may hold someone else's data."""
    start = tmp_path / "start"
    paths.set_home(start, move_existing=False)
    with Store():
        pass

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "artemis.db").write_text("not ours", encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        paths.set_home(occupied, move_existing=True)

    # The original store is untouched by the refusal.
    assert (start / "artemis.db").exists()


def test_a_file_cannot_be_used_as_the_store(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    not_a_folder = tmp_path / "afile.txt"
    not_a_folder.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="Not a folder"):
        paths.set_home(not_a_folder)


def test_store_paths_follow_the_configured_root(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    chosen = tmp_path / "chosen"
    paths.set_home(chosen, move_existing=False)
    root = chosen.resolve()

    assert paths.database_path() == root / "artemis.db"
    assert paths.index_dir(7) == root / "index" / "7"
    assert paths.blobs_dir() == root / "blobs"
    assert paths.config_path() == root / "config.toml"


def test_moving_while_the_database_is_open(
    pointer_isolated: Path, tmp_path: Path
) -> None:
    """The realistic case: the store is in use when the user moves it.

    Every other test here opens the store in a `with` block that closes before
    the move. The running interface does not: it holds one connection for the
    life of the page. Windows will not delete an open file, so leaving it open
    made the copy succeed and the cleanup fail, stranding a second copy of the
    store. The caller must close the connection first, and this test fails if
    it stops doing so.
    """
    start = tmp_path / "start"
    paths.set_home(start, move_existing=False)

    store = Store()
    store.append_audit("test.open-during-move", "recorded")

    destination = tmp_path / "destination"
    store.close()  # what the interface must do before moving
    paths.set_home(destination, move_existing=True)

    assert (destination / "artemis.db").exists()
    assert not (start / "artemis.db").exists(), (
        "the old database survived the move, so the store now exists twice"
    )

    with Store() as reopened:
        assert any(
            row["event"] == "test.open-during-move" for row in reopened.list_audit()
        )
