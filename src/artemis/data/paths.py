"""Locations of the local store, per Architecture Section 7.1.

    <store root>/
    |-- artemis.db          SQLite, the system of record
    |-- index/<ws_id>/      vector index, one directory per workspace
    |-- blobs/              content-addressed snapshots
    |-- cache/              derived artefacts, safely deletable
    `-- config.toml         non-secret settings

Secrets are never written into this tree; they belong in the OS keyring.

Where the root actually is
--------------------------
The user can move the store, so the root is resolved in this order:

    1. the ARTEMIS_HOME environment variable, for tests and portable installs
    2. a pointer file recorded when the user chooses a location
    3. ~/.artemis

The pointer cannot live inside the store, because it is what tells us where the
store is. It goes in the per-user config directory instead, which is the one
location that is known before anything else is read. It holds a path and
nothing else: no user data, so moving the store does not strand anything here.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import platformdirs

ENV_HOME = "ARTEMIS_HOME"
APP_NAME = "ARTEMIS"

#: Files and directories that make up a store, used when moving one.
STORE_CONTENTS = ("artemis.db", "index", "blobs", "cache", "config.toml")


def _pointer_file() -> Path:
    """Where the chosen store location is recorded.

    Deliberately outside the store. This is the bootstrap: it is read before we
    know where anything else lives.
    """
    return Path(platformdirs.user_config_dir(APP_NAME, appauthor=False)) / "location"


def default_home() -> Path:
    """Where the store lives when the user has not chosen otherwise."""
    return Path.home() / ".artemis"


def configured_home() -> Path | None:
    """The location the user chose, or None if they never chose one."""
    pointer = _pointer_file()
    try:
        recorded = pointer.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None
    return Path(recorded).expanduser() if recorded else None


def artemis_home() -> Path:
    """The root of the local store, created if it does not yet exist."""
    override = os.environ.get(ENV_HOME)
    if override:
        root = Path(override).expanduser()
    else:
        root = configured_home() or default_home()
    root.mkdir(parents=True, exist_ok=True)
    return root


def set_home(new_root: Path | str, move_existing: bool = True) -> Path:
    """Record a new store location, optionally moving the current store into it.

    Returns the resolved new root. Raises ValueError if the location cannot be
    used, so the caller can report the reason rather than failing silently.

    Moving is a copy followed by a delete rather than a rename, because the new
    location is frequently on a different drive, where rename fails. The old
    store is only removed once every piece has arrived.
    """
    target = Path(new_root).expanduser()

    if target.exists() and not target.is_dir():
        raise ValueError(f"Not a folder: {target}")

    current = artemis_home().resolve()
    try:
        resolved_target = target.resolve()
    except OSError as exc:
        raise ValueError(f"Cannot use that folder: {exc}") from exc

    if resolved_target == current:
        return current

    # Moving a store inside itself would copy it into its own subdirectory.
    if current in resolved_target.parents:
        raise ValueError("Cannot move the store inside itself")

    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".artemis-write-test"
        probe.touch()
        probe.unlink()
    except OSError as exc:
        raise ValueError(f"Cannot write to that folder: {exc}") from exc

    if move_existing and current.exists():
        copied: list[Path] = []
        for name in STORE_CONTENTS:
            source = current / name
            if not source.exists():
                continue
            destination = target / name
            if destination.exists():
                raise ValueError(
                    f"'{name}' already exists in that folder. Choose an empty one."
                )
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            copied.append(source)
        # Everything arrived, so the originals can go.
        for source in copied:
            if source.is_dir():
                shutil.rmtree(source, ignore_errors=True)
            else:
                source.unlink(missing_ok=True)

    pointer = _pointer_file()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(str(resolved_target), encoding="utf-8")
    return resolved_target


def reset_home() -> Path:
    """Forget the chosen location and fall back to the default.

    Does not move anything: the caller decides whether to move the store first.
    """
    pointer = _pointer_file()
    pointer.unlink(missing_ok=True)
    return default_home()


def database_path() -> Path:
    """The SQLite system of record."""
    return artemis_home() / "artemis.db"


def index_dir(workspace_id: int) -> Path:
    """The vector index directory for one workspace.

    Per-workspace isolation is deliberate: it makes revoking a workspace a
    directory deletion, and means one workspace's embeddings cannot be read
    while another is active.
    """
    return artemis_home() / "index" / str(workspace_id)


def blobs_dir() -> Path:
    """Content-addressed snapshot storage, shared across workspaces by hash."""
    path = artemis_home() / "blobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    """Derived artefacts. Anything here may be deleted without data loss."""
    path = artemis_home() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    """Non-secret settings."""
    return artemis_home() / "config.toml"
