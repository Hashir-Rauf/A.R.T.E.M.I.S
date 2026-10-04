"""F2: Tidy up a folder.

Proposes a grouping for the loose files in a workspace, shows every move
before anything happens, and moves nothing until the user approves.

Three constraints, and the first is the one the whole project rests on:

**It cannot delete.** There is no delete in this module, no call to `unlink`,
no overwrite. A tidy that would land on an existing file renames the incoming
one instead. The policy engine would refuse a deletion anyway, but a capability
that never asks is better than one that asks and is told no.

**It proposes; it does not act.** `propose` returns a `TidyProposal` and a
`Plan`. Executing that plan is the dispatcher's job, after the approval broker
has a decision. This module has no reference to either.

**Grouping is explainable.** Files are grouped by kind and by date using rules
a person can predict, not by a model's judgement. When the user is deciding
whether to approve twelve moves, "all the PDFs" is a reason they can check;
"the model thought these belonged together" is not.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from artemis.core.actions import Plan, ToolCall
from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.errors import BoundaryRefusal
from artemis.data.store import Store

#: Extension to folder name. Deliberately coarse: a handful of obvious groups
#: a person would have made themselves, rather than a taxonomy to learn.
KINDS: dict[str, tuple[str, ...]] = {
    "Documents": ("pdf", "doc", "docx", "odt", "rtf", "tex", "md", "txt", "pages"),
    "Spreadsheets": ("xls", "xlsx", "csv", "tsv", "ods", "numbers"),
    "Presentations": ("ppt", "pptx", "odp", "key"),
    "Images": ("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "heic", "tiff"),
    "Audio": ("mp3", "wav", "flac", "m4a", "ogg", "aac"),
    "Video": ("mp4", "mov", "avi", "mkv", "webm"),
    "Archives": ("zip", "tar", "gz", "7z", "rar", "bz2"),
    "Code": ("py", "js", "ts", "java", "c", "cpp", "h", "cs", "go", "rs", "rb", "php",
             "html", "css", "json", "yaml", "yml", "sql", "sh", "ipynb"),
    "Data": ("db", "sqlite", "parquet", "pickle", "npy", "mat"),
}

_EXTENSION_TO_KIND = {
    extension: folder for folder, extensions in KINDS.items() for extension in extensions
}

#: Below this, tidying is not worth the interruption.
MIN_FILES_TO_SUGGEST = 4

#: A group smaller than this is left alone rather than given a folder.
MIN_GROUP = 2


@dataclass(frozen=True)
class PlannedMove:
    """One file, and where it would go."""

    rel_path: str
    destination: str
    group: str

    @property
    def filename(self) -> str:
        return Path(self.rel_path).name

    def describe(self) -> str:
        return f"{self.filename}  →  {self.group}/"


@dataclass
class TidyProposal:
    """What tidying this folder would do, and what it would leave alone."""

    workspace_id: int
    moves: tuple[PlannedMove, ...] = ()
    new_folders: tuple[str, ...] = ()
    left_alone: tuple[str, ...] = ()
    reason_not_suggested: str = ""

    @property
    def is_worth_doing(self) -> bool:
        return bool(self.moves)

    def groups(self) -> dict[str, list[PlannedMove]]:
        grouped: dict[str, list[PlannedMove]] = defaultdict(list)
        for move in self.moves:
            grouped[move.group].append(move)
        return dict(grouped)

    def summary(self) -> str:
        if not self.moves:
            return self.reason_not_suggested or "Nothing here needs tidying."
        folders = len(self.new_folders)
        files = len(self.moves)
        bits = [f"move {files} file{'' if files == 1 else 's'}"]
        if folders:
            bits.append(f"create {folders} folder{'' if folders == 1 else 's'}")
        tail = ""
        if self.left_alone:
            tail = f", leaving {len(self.left_alone)} where they are"
        return f"Would {' and '.join(bits)}{tail}. Nothing is deleted."


class TidyService:
    """Proposes a tidy. Never performs one."""

    def __init__(self, store: Store, broker: WorkspaceBroker) -> None:
        self._store = store
        self._broker = broker

    def propose(
        self, workspace_id: int, by_date: bool = False
    ) -> TidyProposal:
        """Work out how the loose files at the top of a workspace could group.

        Only the top level is considered. Files the user has already filed away
        in subfolders are left alone: reorganising someone's existing structure
        is a different and much ruder operation than tidying loose files.
        """
        loose = self._loose_files(workspace_id)

        if len(loose) < MIN_FILES_TO_SUGGEST:
            return TidyProposal(
                workspace_id=workspace_id,
                reason_not_suggested=(
                    f"Only {len(loose)} loose file"
                    f"{'' if len(loose) == 1 else 's'} here, which is tidy enough."
                ),
            )

        buckets: dict[str, list[str]] = defaultdict(list)
        for rel_path, mtime in loose:
            buckets[self._group_for(rel_path, mtime, by_date)].append(rel_path)

        moves: list[PlannedMove] = []
        left_alone: list[str] = []
        folders: set[str] = set()

        for group, paths in sorted(buckets.items()):
            # A group of one is not a group; it is a file with a folder around it.
            if len(paths) < MIN_GROUP:
                left_alone.extend(paths)
                continue
            folders.add(group)
            for rel_path in sorted(paths):
                destination = self._free_destination(workspace_id, group, rel_path)
                moves.append(PlannedMove(rel_path, destination, group))

        if not moves:
            return TidyProposal(
                workspace_id=workspace_id,
                left_alone=tuple(sorted(left_alone)),
                reason_not_suggested=(
                    "These files do not fall into groups, so tidying them would "
                    "just move them around."
                ),
            )

        return TidyProposal(
            workspace_id=workspace_id,
            moves=tuple(moves),
            new_folders=tuple(sorted(folders)),
            left_alone=tuple(sorted(left_alone)),
        )

    def to_plan(self, proposal: TidyProposal) -> Plan:
        """Turn a proposal into calls the dispatcher could run, once approved.

        Folder creation comes first so the moves have somewhere to land. The
        plan is returned, not executed: this service has no way to run it.
        """
        calls: list[ToolCall] = [
            ToolCall("create_dir", proposal.workspace_id, (folder,))
            for folder in proposal.new_folders
        ]
        calls.extend(
            ToolCall(
                "move_file",
                proposal.workspace_id,
                (move.rel_path,),
                {"destination": move.destination},
            )
            for move in proposal.moves
        )
        return Plan(calls=tuple(calls), intent="Tidy up this folder")

    # -- internals ---------------------------------------------------------

    def _loose_files(self, workspace_id: int) -> list[tuple[str, float]]:
        """Indexed files sitting directly in the workspace root."""
        return [
            (row["rel_path"], row["mtime"])
            for row in self._store.list_files(workspace_id)
            if "/" not in row["rel_path"]
        ]

    @staticmethod
    def _group_for(rel_path: str, mtime: float, by_date: bool) -> str:
        if by_date:
            when = datetime.fromtimestamp(mtime, tz=timezone.utc)
            return when.strftime("%Y-%m")
        extension = Path(rel_path).suffix.lstrip(".").lower()
        return _EXTENSION_TO_KIND.get(extension, "Other")

    def _free_destination(
        self, workspace_id: int, group: str, rel_path: str
    ) -> str:
        """A destination inside `group` that is not already taken.

        Never overwrites. If `report.pdf` already exists in the target folder,
        the incoming file becomes `report (2).pdf`. Overwriting would be a
        destructive operation, and this service does not have one.
        """
        name = Path(rel_path).name
        stem, suffix = Path(name).stem, Path(name).suffix
        candidate = f"{group}/{name}"
        counter = 2
        while self._exists(workspace_id, candidate):
            candidate = f"{group}/{stem} ({counter}){suffix}"
            counter += 1
        return candidate

    def _exists(self, workspace_id: int, rel_path: str) -> bool:
        try:
            resolved = self._broker.resolve(workspace_id, rel_path, Operation.READ)
        except BoundaryRefusal:
            # Unreachable counts as taken: we will not propose moving a file
            # somewhere the broker would refuse to put it.
            return True
        return resolved.path.exists()
