"""Wiring the capability services to the dispatcher.

This module is where FA-VNGA is made true: every service reaches the filesystem
through the Workspace Broker and nowhere else.

The handlers below replace the Sprint 3 placeholders. They differ from those
placeholders in one way that matters: a placeholder did the smallest thing its
operation implied, whereas these are the operations the nine features actually
need. What has not changed is the contract. A handler receives paths that the
dispatcher has already resolved through the broker, and has no means of
constructing a path of its own.

That is the enforcement, and it is structural rather than conventional. A
handler is handed a resolved `Path`; it never sees a workspace root, never
performs string concatenation on a path, and so cannot address a file outside
the grant even if it tried. The one operation that needs a second location,
`move_file`, is given a destination the dispatcher resolved for it.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from artemis.core.dispatch import ExecutionContext, Handler

#: Files above this are summarised rather than read whole. A capability that
#: reads a gigabyte into memory because a plan asked it to is a denial of
#: service with extra steps.
MAX_READ_BYTES = 2 * 1024 * 1024


def handle_read_file(context: ExecutionContext) -> str:
    """Read a file the broker has already approved."""
    target = context.resolved[0]
    if target.stat().st_size > MAX_READ_BYTES:
        raise ValueError(
            f"{target.name} is too large to read in one go "
            f"({target.stat().st_size // 1024} KB)"
        )
    return target.read_text(encoding="utf-8", errors="replace")


def handle_read_metadata(context: ExecutionContext) -> dict:
    """Size, modification time and kind, without opening the file."""
    target = context.resolved[0]
    stat = target.stat()
    return {
        "name": target.name,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "suffix": target.suffix.lstrip(".").lower(),
        "is_dir": target.is_dir(),
    }


def handle_stat(context: ExecutionContext) -> dict:
    return handle_read_metadata(context)


def handle_list_dir(context: ExecutionContext) -> list[str]:
    """List one directory, not the tree beneath it.

    Shallow on purpose: a recursive listing of a large workspace is both slow
    and more than any single step needs.
    """
    root = context.resolved[0] if context.resolved else None
    if root is None or not root.is_dir():
        return []
    return sorted(entry.name for entry in root.iterdir())


def handle_write_file(context: ExecutionContext) -> int:
    """Write content to a file. The undo journal has already snapshotted it."""
    content = str(context.call.arguments.get("content", ""))
    target = context.resolved[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return len(content)


def handle_append_file(context: ExecutionContext) -> int:
    """Add to the end of a file, leaving what is already there alone."""
    content = str(context.call.arguments.get("content", ""))
    target = context.resolved[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(content)
    return len(content)


def handle_create_dir(context: ExecutionContext) -> str:
    target = context.resolved[0]
    target.mkdir(parents=True, exist_ok=True)
    return str(target)


def handle_move_file(context: ExecutionContext) -> str:
    """Move a file to a destination the dispatcher resolved.

    Refuses to land on an existing file. Moving onto something would destroy
    it, which is a T3 operation this system does not have; the tidy service
    avoids the situation by picking a free name, and this is the backstop for
    any other caller.
    """
    target = context.destination
    if target is None:
        raise ValueError("move_file needs a 'destination' argument")
    if target.exists():
        raise ValueError(
            f"{target.name} already exists there. ARTEMIS will not overwrite it."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(context.resolved[0]), str(target))
    return str(target)


def handle_rename(context: ExecutionContext) -> str:
    """Rename in place. Same refusal to overwrite as a move."""
    return handle_move_file(context)


def handle_search_index(context: ExecutionContext) -> list[str]:
    """Match filenames beneath a resolved directory.

    Operates on the resolved path rather than querying the index, so it cannot
    return a result from another workspace even if the index were wrong.
    """
    root = context.resolved[0] if context.resolved else None
    if root is None or not root.is_dir():
        return []
    needle = str(context.call.arguments.get("query", "")).lower()
    if not needle:
        return []
    return sorted(
        str(path.relative_to(root).as_posix())
        for path in root.rglob("*")
        if path.is_file() and needle in path.name.lower()
    )[:50]


def capability_handlers() -> dict[str, Handler]:
    """The operations ARTEMIS can perform, as of Sprint 5.

    Registration is an allowlist. An operation absent from this mapping cannot
    run, whatever a plan asks for, which is why adding a capability is a visible
    edit here rather than something that happens by configuration.

    There is no delete, no overwrite and no execute, and their absence is the
    point rather than an oversight.
    """
    return {
        # Reading (T0)
        "read_file": handle_read_file,
        "read_metadata": handle_read_metadata,
        "stat": handle_stat,
        "list_dir": handle_list_dir,
        "search_index": handle_search_index,
        # Changing, reversibly (T1)
        "write_file": handle_write_file,
        "append_file": handle_append_file,
        "create_dir": handle_create_dir,
        "move_file": handle_move_file,
        "rename": handle_rename,
    }


def register_capabilities(dispatcher) -> None:
    """Attach every capability handler to a dispatcher."""
    for operation, handler in capability_handlers().items():
        dispatcher.register(operation, handler)
