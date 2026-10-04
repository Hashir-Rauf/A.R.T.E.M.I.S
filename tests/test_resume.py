"""F1: Pick up where you left off.

The feature's value is that it is *factual*. It is most useful exactly when the
user cannot remember what they were doing, which is the worst possible moment to
hand them a plausible reconstruction. So these tests check that what comes back
is read from recorded state, and that an empty answer is given honestly rather
than filled in.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from artemis.core.broker import WorkspaceBroker
from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.services.resume import ResumeService


@pytest.fixture
def resume(store: Store, broker: WorkspaceBroker) -> ResumeService:
    return ResumeService(store, broker)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


def test_a_first_visit_says_so(resume: ResumeService, workspace_id: int) -> None:
    """No session history is a real answer, not a blank."""
    report = resume.report(workspace_id)

    assert report.is_first_visit is True
    assert "first time" in report.summary()


def test_the_users_own_note_comes_back_verbatim(
    resume: ResumeService, workspace_id: int
) -> None:
    """A paraphrase of a half-finished thought is wrong when it matters."""
    note = "was about to fix the citation in chapter 3"
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id, note=note)

    report = resume.report(workspace_id)

    assert report.note == note
    assert note in report.summary()


def test_files_added_while_away_are_reported(
    resume: ResumeService, indexer: Indexer, workspace_id: int, sandbox: Path
) -> None:
    indexer.scan(workspace_id)
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id)

    (sandbox / "new-chapter.md").write_text("draft", encoding="utf-8")
    indexer.scan(workspace_id)

    report = resume.report(workspace_id)
    added = [c.rel_path for c in report.changes if c.change == "added"]
    assert "new-chapter.md" in added


def test_files_removed_while_away_are_reported(
    resume: ResumeService, indexer: Indexer, workspace_id: int, sandbox: Path
) -> None:
    indexer.scan(workspace_id)
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id)

    (sandbox / "readme.txt").unlink()
    indexer.scan(workspace_id)

    report = resume.report(workspace_id)
    removed = [c.rel_path for c in report.changes if c.change == "removed"]
    assert "readme.txt" in removed


def test_an_edited_file_is_reported_as_modified(
    resume: ResumeService, indexer: Indexer, workspace_id: int, sandbox: Path
) -> None:
    indexer.scan(workspace_id)
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id)

    time.sleep(0.01)
    target = sandbox / "readme.txt"
    target.write_text("changed while away", encoding="utf-8")
    import os

    os.utime(target, (time.time() + 5, time.time() + 5))
    indexer.scan(workspace_id)

    report = resume.report(workspace_id)
    modified = [c.rel_path for c in report.changes if c.change == "modified"]
    assert "readme.txt" in modified


def test_nothing_changing_is_said_plainly(
    resume: ResumeService, indexer: Indexer, workspace_id: int
) -> None:
    indexer.scan(workspace_id)
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id)

    report = resume.report(workspace_id)

    assert report.changes == ()
    assert "Nothing has changed" in report.summary()


def test_open_proposals_are_surfaced_on_return(
    resume: ResumeService, workspace_id: int, store: Store
) -> None:
    """Something ARTEMIS asked about last time should not be silently dropped."""
    store.propose_rule(workspace_id, "move_file::pdf | moving PDF files")
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id)

    report = resume.report(workspace_id)
    assert len(report.open_proposals) == 1


def test_opening_a_listed_file_still_goes_through_the_broker(
    resume: ResumeService, workspace_id: int
) -> None:
    """Being listed in a report does not make a path reachable."""
    assert resume.resolve_for_opening(workspace_id, "readme.txt") is not None
    assert resume.resolve_for_opening(workspace_id, "../private/passwords.txt") is None


def test_a_revoked_workspace_reports_rather_than_crashes(
    resume: ResumeService, manager: WorkspaceManager, workspace_id: int
) -> None:
    manager.revoke(workspace_id)
    report = resume.report(workspace_id)
    assert report.notes


def test_sessions_are_recorded_in_the_audit_log(
    resume: ResumeService, workspace_id: int, store: Store
) -> None:
    session = resume.open_session(workspace_id)
    resume.close_session(session, workspace_id, note="something")

    events = [row for row in store.list_audit() if row["event"] == "resume.session"]
    assert {row["outcome"] for row in events} == {"opened", "closed"}
    assert store.verify_audit_chain()


# -- the path the application actually takes -----------------------------------
#
# Every test above drives the service directly, which is why all of them passed
# while the feature was dead in the running app: nothing called open_session or
# close_session outside the tests, so there was never a closed session to
# compare against and the report said "first visit" forever.
#
# These exercise checkpointing instead, because that is what the interface does.


def test_checkpoint_creates_something_to_compare_against(
    resume: ResumeService, workspace_id: int, indexer: Indexer
) -> None:
    indexer.scan(workspace_id)
    resume.checkpoint(workspace_id)
    assert not resume.report(workspace_id).is_first_visit


def test_checkpoint_leaves_a_session_open(
    resume: ResumeService, workspace_id: int, store: Store, indexer: Indexer
) -> None:
    """The next checkpoint must have a session to close.

    A checkpoint closes the open session and opens a fresh one, so work done
    after it is still attributed somewhere.
    """
    indexer.scan(workspace_id)
    resume.checkpoint(workspace_id)
    assert store.latest_session(workspace_id)["ended_at"] is None


def test_report_reads_the_last_closed_session_not_the_open_one(
    resume: ResumeService, workspace_id: int, indexer: Indexer, sandbox: Path
) -> None:
    """The bug this file missed, stated directly.

    `latest_session` returns the session a checkpoint just opened, which has no
    snapshot. The report has to reach past it to the last closed one.
    """
    indexer.scan(workspace_id)
    resume.checkpoint(workspace_id)

    (sandbox / "brand-new.txt").write_text("x", encoding="utf-8")
    indexer.scan(workspace_id)

    report = resume.report(workspace_id)
    assert not report.is_first_visit
    assert any(c.rel_path == "brand-new.txt" for c in report.changes)


def test_changes_after_a_checkpoint_are_classified(
    resume: ResumeService, workspace_id: int, indexer: Indexer, sandbox: Path
) -> None:
    """Added, modified and removed are each reported as what they are."""
    (sandbox / "stays.txt").write_text("one", encoding="utf-8")
    (sandbox / "goes.txt").write_text("two", encoding="utf-8")
    indexer.scan(workspace_id)
    resume.checkpoint(workspace_id)

    (sandbox / "arrives.txt").write_text("three", encoding="utf-8")
    (sandbox / "stays.txt").write_text("much longer content now", encoding="utf-8")
    (sandbox / "goes.txt").unlink()
    indexer.scan(workspace_id)

    changes = {c.rel_path: c.change for c in resume.report(workspace_id).changes}
    assert changes["arrives.txt"] == "added"
    assert changes["stays.txt"] == "modified"
    assert changes["goes.txt"] == "removed"


def test_a_second_checkpoint_moves_the_comparison_forward(
    resume: ResumeService, workspace_id: int, indexer: Indexer, sandbox: Path
) -> None:
    """Once a change has been reported it is not reported again forever."""
    indexer.scan(workspace_id)
    resume.checkpoint(workspace_id)

    (sandbox / "once.txt").write_text("x", encoding="utf-8")
    indexer.scan(workspace_id)
    assert resume.report(workspace_id).changes

    resume.checkpoint(workspace_id)
    assert not resume.report(workspace_id).changes
