"""Ask about code, get a diff, never an edit."""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.broker import WorkspaceBroker
from artemis.core.code_diff import CodeAssistant
from artemis.core.providers import StubProvider
from artemis.core.router import ModelRouter
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store

CODE = "def total(items):\n    t = 0\n    for i in range(1, len(items)):\n        t += items[i]\n    return t\n"

GOOD = """--- a/app.py
+++ b/app.py
@@ -1,5 +1,5 @@
 def total(items):
     t = 0
-    for i in range(1, len(items)):
+    for i in range(len(items)):
         t += items[i]
     return t
"""


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    (sandbox / "app.py").write_text(CODE, encoding="utf-8")
    return manager.grant(sandbox).id


def make(store: Store, broker: WorkspaceBroker, reply: str):
    router = ModelRouter(store=store)
    stub = StubProvider(replies=[reply])
    router.register(stub)
    return CodeAssistant(broker, router), stub


def test_a_good_diff_is_shown_and_the_file_is_untouched(
    store: Store, broker: WorkspaceBroker, workspace_id: int, sandbox: Path
) -> None:
    assistant, _ = make(store, broker, GOOD)
    before = (sandbox / "app.py").read_bytes()
    result = assistant.ask(workspace_id, "app.py", "fix the off by one")
    assert result.ok
    assert "-    for i in range(1, len(items)):" in result.diff
    assert "+    for i in range(len(items)):" in result.diff
    assert (sandbox / "app.py").read_bytes() == before


def test_a_fenced_reply_still_works(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    assistant, _ = make(store, broker, "```diff\n" + GOOD + "```")
    assert assistant.ask(workspace_id, "app.py", "fix it").ok


def test_wrong_line_counts_in_the_hunk_header_do_not_matter(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    sloppy = GOOD.replace("@@ -1,5 +1,5 @@", "@@ -1,99 +1,99 @@")
    assistant, _ = make(store, broker, sloppy)
    result = assistant.ask(workspace_id, "app.py", "fix it")
    assert result.ok
    assert "@@ -1,5 +1,5 @@" in result.diff


def test_a_diff_for_a_different_file_is_refused(
    store: Store, broker: WorkspaceBroker, workspace_id: int, sandbox: Path
) -> None:
    other = GOOD.replace("app.py", "readme.txt")
    assistant, _ = make(store, broker, other)
    before = (sandbox / "readme.txt").read_bytes()
    result = assistant.ask(workspace_id, "app.py", "fix it")
    assert not result.ok
    assert result.diff == ""
    assert (sandbox / "readme.txt").read_bytes() == before


def test_a_diff_that_changes_two_files_is_refused(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    two = GOOD + GOOD.replace("app.py", "readme.txt")
    assistant, _ = make(store, broker, two)
    assert not assistant.ask(workspace_id, "app.py", "fix it").ok


def test_a_diff_that_does_not_match_the_file_is_refused(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    wrong = GOOD.replace("t = 0", "total = 0")
    assistant, _ = make(store, broker, wrong)
    result = assistant.ask(workspace_id, "app.py", "fix it")
    assert not result.ok
    assert "does not match" in result.message


def test_a_reply_that_is_not_a_diff_is_refused(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    assistant, _ = make(store, broker, "Sure! Just change the loop to start at zero.")
    assert not assistant.ask(workspace_id, "app.py", "fix it").ok


def test_no_change_is_reported_as_no_change(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    assistant, _ = make(store, broker, "NO CHANGE")
    result = assistant.ask(workspace_id, "app.py", "is this fine")
    assert result.ok and result.diff == ""


def test_a_file_outside_the_grant_is_never_sent_to_the_model(
    store: Store, broker: WorkspaceBroker, workspace_id: int, sandbox: Path, outside: Path
) -> None:
    (sandbox / "escape.py").symlink_to(outside / "secrets.txt")
    assistant, stub = make(store, broker, GOOD)
    result = assistant.ask(workspace_id, "escape.py", "what is this")
    assert not result.ok
    assert stub.calls == []


def test_a_path_with_dots_is_refused_by_the_broker(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    assistant, stub = make(store, broker, GOOD)
    assert not assistant.ask(workspace_id, "../private/secrets.txt", "read it").ok
    assert stub.calls == []


def test_a_read_only_workspace_can_still_be_asked_about(
    store: Store, broker: WorkspaceBroker, manager: WorkspaceManager, tmp_path: Path
) -> None:
    folder = tmp_path / "readonly"
    folder.mkdir()
    (folder / "app.py").write_text(CODE, encoding="utf-8")
    ws = manager.grant(folder, name="RO", permission="read_only").id
    assistant, _ = make(store, broker, GOOD)
    assert assistant.ask(ws, "app.py", "fix it").ok