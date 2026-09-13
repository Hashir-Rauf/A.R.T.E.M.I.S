"""Shared fixtures.

Every test runs against a throwaway ARTEMIS store, pointed there by ARTEMIS_HOME
so that nothing touches the developer's real one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.broker import WorkspaceBroker
from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


@pytest.fixture(autouse=True)
def artemis_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "artemis-home"
    home.mkdir()
    monkeypatch.setenv("ARTEMIS_HOME", str(home))
    return home


@pytest.fixture
def store(artemis_home: Path) -> Store:
    with Store() as s:
        yield s


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A folder standing in for the user's own files."""
    folder = tmp_path / "project"
    (folder / "notes").mkdir(parents=True)
    (folder / "notes" / "chapter3.md").write_text("draft chapter", encoding="utf-8")
    (folder / "readme.txt").write_text("hello", encoding="utf-8")
    return folder


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    """A folder the user has NOT opted in. Nothing may reach into it."""
    folder = tmp_path / "private"
    folder.mkdir()
    (folder / "secrets.txt").write_text("do not read", encoding="utf-8")
    return folder


@pytest.fixture
def manager(store: Store) -> WorkspaceManager:
    return WorkspaceManager(store)


@pytest.fixture
def broker(store: Store) -> WorkspaceBroker:
    return WorkspaceBroker(store)


@pytest.fixture
def indexer(store: Store, broker: WorkspaceBroker) -> Indexer:
    return Indexer(store, broker)
