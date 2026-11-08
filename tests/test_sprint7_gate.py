"""Sprint 7 stage gate: the first outward actions, and the gates hold.

Each test is written to be able to fail. A gate that cannot fail proves nothing.
"""

from __future__ import annotations

import json

import pytest

from artemis.core.actions import Decision, Tier
from artemis.core.broker import WorkspaceBroker
from artemis.core.policy import AUTO, PolicyEngine
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.services.drafter import DocumentDrafter, safe_filename
from artemis.services.mail import MailError, MailService, MailSettings
from artemis.services.search import (
    SearchError, SearchResult, SearchService, StubSearchProvider,
)
from artemis.core.context import Provenance


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTEMIS_HOME", str(tmp_path / "home"))
    folder = tmp_path / "ws"
    folder.mkdir()
    with Store() as store:
        ws = WorkspaceManager(store).grant(folder)
        yield store, ws, folder


def _events(store, event):
    rows = store.query("SELECT outcome, detail FROM audit_log WHERE event = ?", (event,))
    return [(r["outcome"], json.loads(r["detail"])) for r in rows]


def _mail(store, sent):
    settings = MailSettings("smtp.test", 465, "me@test.com", "me@test.com")
    return MailService(
        store,
        settings_loader=lambda: settings,
        password_getter=lambda user: "secret",
        transport=lambda s, p, m: sent.append(m),
    )


# --- Mail ------------------------------------------------------------------

def test_send_mail_is_gated_outward(env):
    store, ws, _ = env
    plan = _mail(store, []).compose(ws.id, ["a@b.com"], "Hi", "Hello")
    verdict = PolicyEngine(store, WorkspaceBroker(store)).classify(plan.calls[0])
    assert verdict.tier is Tier.OUTWARD
    assert verdict.decision is Decision.GATE


def test_send_mail_approval_can_never_be_remembered(env):
    store, ws, _ = env
    policy = PolicyEngine(store, WorkspaceBroker(store))
    call = _mail(store, []).compose(ws.id, ["a@b.com"], "Hi", "Hello").calls[0]
    policy.remember(call, AUTO)
    assert policy.rules(ws.id) == []
    assert policy.classify(call).decision is Decision.GATE


@pytest.mark.parametrize("bad", ["no-at-sign", "a@b", "a@b.com\nBcc: x@y.com", ""])
def test_bad_recipient_is_refused(env, bad):
    store, ws, _ = env
    with pytest.raises(MailError):
        _mail(store, []).compose(ws.id, [bad], "Hi", "Hello")


def test_subject_header_injection_is_refused(env):
    store, ws, _ = env
    with pytest.raises(MailError):
        _mail(store, []).compose(ws.id, ["a@b.com"], "Hi\nBcc: x@y.com", "Hello")


def test_compose_sends_nothing(env):
    store, ws, _ = env
    sent: list = []
    _mail(store, sent).compose(ws.id, ["a@b.com"], "Hi", "Hello")
    assert sent == []


def test_send_records_recipient_and_time(env):
    store, ws, _ = env
    sent: list = []
    svc = _mail(store, sent)
    call = svc.compose(ws.id, ["a@b.com"], "Hi", "Hello").calls[0]
    svc.send(ws.id, call.arguments)
    assert len(sent) == 1
    outcome, detail = _events(store, "mail.sent")[0]
    assert outcome == "sent" and detail["to"] == ["a@b.com"] and detail["sent_at"]


def test_missing_password_means_nothing_is_sent(env):
    store, ws, _ = env
    sent: list = []
    svc = MailService(
        store,
        settings_loader=lambda: MailSettings("h", 465, "u@x.com", "u@x.com"),
        password_getter=lambda user: None,
        transport=lambda s, p, m: sent.append(m),
    )
    with pytest.raises(MailError):
        svc.send(ws.id, {"to": ["a@b.com"], "subject": "s", "body": "b"})
    assert sent == []


# --- Web search -------------------------------------------------------------

def test_web_search_is_gated_outward(env):
    store, ws, _ = env
    plan = SearchService(store, StubSearchProvider()).propose(ws.id, "python typer")
    verdict = PolicyEngine(store, WorkspaceBroker(store)).classify(plan.calls[0])
    assert verdict.tier is Tier.OUTWARD and verdict.decision is Decision.GATE


def test_search_records_every_query(env):
    store, ws, _ = env
    provider = StubSearchProvider(results=[SearchResult("T", "https://x.com", "s")])
    SearchService(store, provider).run(ws.id, "  python   typer ")
    outcome, detail = _events(store, "web.search")[0]
    assert outcome == "sent" and detail["query"] == "python typer"


def test_search_results_are_tagged_web(env):
    store, ws, _ = env
    chunks = SearchService.to_chunks([SearchResult("T", "https://x.com", "s")])
    assert chunks[0].provenance is Provenance.WEB


def test_empty_and_huge_queries_are_refused(env):
    store, ws, _ = env
    svc = SearchService(store, StubSearchProvider())
    with pytest.raises(SearchError):
        svc.propose(ws.id, "   ")
    with pytest.raises(SearchError):
        svc.propose(ws.id, "x" * 1000)


# --- Document drafter -------------------------------------------------------

def test_drafter_never_picks_an_existing_name(env):
    store, ws, folder = env
    (folder / "report.md").write_text("old")
    drafter = DocumentDrafter(store, WorkspaceBroker(store))
    plan = drafter.propose(ws.id, "report.md", "new text")
    assert plan.calls[0].paths == ("report (2).md",)
    assert (folder / "report.md").read_text() == "old"


def test_drafter_asks_for_create_only(env):
    store, ws, _ = env
    plan = DocumentDrafter(store, WorkspaceBroker(store)).propose(ws.id, "a.md", "x")
    assert plan.calls[0].arguments["create_only"] is True


def test_drafter_write_is_reversible_and_gated(env):
    store, ws, _ = env
    plan = DocumentDrafter(store, WorkspaceBroker(store)).propose(ws.id, "a.md", "x")
    verdict = PolicyEngine(store, WorkspaceBroker(store)).classify(plan.calls[0])
    assert verdict.tier is Tier.REVERSIBLE and verdict.decision is Decision.GATE


def test_filename_cannot_climb_out(env):
    assert "/" not in safe_filename("../../Windows/evil.txt")
    assert safe_filename("notes").endswith(".md")


# --- End to end: through the real gateway, approval broker and dispatcher ----

from artemis.core.gateway import Gateway
from artemis.core.providers import StubProvider
from artemis.core.router import ModelRouter
from artemis.services.outward import register_outward


def _gateway(store, reply, sent=None, results=None, send_error=None):
    router = ModelRouter(store)
    router.register(StubProvider(replies=[json.dumps(reply)]))
    gateway = Gateway.build(store, router)
    sent = sent if sent is not None else []

    def transport(settings, password, message):
        if send_error:
            raise send_error
        sent.append(message)

    mail = MailService(
        store,
        settings_loader=lambda: MailSettings("h", 465, "me@t.com", "me@t.com"),
        password_getter=lambda user: "pw",
        transport=transport,
    )
    search = SearchService(store, StubSearchProvider(results=results or []))
    register_outward(gateway.dispatcher, search, mail)
    return gateway, sent


MAIL_STEP = {"steps": [{"operation": "send_mail", "paths": [], "arguments": {
    "to": ["bob@x.com"], "subject": "Hello", "body": "Hi Bob"}}]}


def test_e2e_mail_waits_shows_content_then_sends_once_approved(env):
    store, ws, _ = env
    gateway, sent = _gateway(store, MAIL_STEP)
    outcome = gateway.handle(ws.id, "email bob hello")
    assert outcome.needs_approval and sent == []
    details = outcome.preview["steps"][0]["details"]
    assert details == {"to": ["bob@x.com"], "subject": "Hello", "body": "Hi Bob"}
    assert outcome.preview["leaves_machine"] is True

    result = gateway.approve_and_run(outcome, remember=True)
    assert result.did_anything and len(sent) == 1
    # "remember" was asked for, and refused for an outward operation.
    assert PolicyEngine(store, WorkspaceBroker(store)).rules(ws.id) == []


def test_e2e_rejected_mail_never_sends_even_if_dispatched_directly(env):
    store, ws, _ = env
    gateway, sent = _gateway(store, MAIL_STEP)
    outcome = gateway.handle(ws.id, "email bob hello")
    gateway.reject(outcome, reason="not now")
    result = gateway.dispatcher.execute_plan(outcome.plan, outcome.verdicts)
    assert sent == [] and not result.did_anything


def test_e2e_mail_failure_is_a_skipped_step_not_a_crash(env):
    store, ws, _ = env
    gateway, sent = _gateway(store, MAIL_STEP, send_error=MailError("server down"))
    outcome = gateway.handle(ws.id, "email bob hello")
    result = gateway.approve_and_run(outcome)
    assert not result.did_anything and len(result.skipped) == 1
    assert _events(store, "mail.sent")[0][0] == "failed"


def test_e2e_web_search_is_gated_then_returns_results(env):
    store, ws, _ = env
    step = {"steps": [{"operation": "web_search", "paths": [],
                       "arguments": {"query": "typer docs"}}]}
    found = [SearchResult("Typer", "https://typer.tiangolo.com", "CLI library")]
    gateway, _ = _gateway(store, step, results=found)
    outcome = gateway.handle(ws.id, "search the web for typer docs")
    assert outcome.needs_approval and _events(store, "web.search") == []
    result = gateway.approve_and_run(outcome)
    value = next(iter(result.results.values()))
    assert value[0]["url"] == "https://typer.tiangolo.com"
    assert _events(store, "web.search")[0][1]["query"] == "typer docs"


def test_e2e_draft_is_written_as_new_file_and_undo_removes_it(env):
    store, ws, folder = env
    step = {"steps": [{"operation": "write_file", "paths": ["draft.md"],
                       "arguments": {"content": "# Draft", "create_only": True}}]}
    gateway, _ = _gateway(store, step)
    outcome = gateway.handle(ws.id, "write a draft")
    assert outcome.needs_approval and not (folder / "draft.md").exists()
    gateway.approve_and_run(outcome)
    assert (folder / "draft.md").read_text() == "# Draft"
    reversed_count, problems = gateway.undo(outcome.plan.plan_id)
    assert not problems and not (folder / "draft.md").exists()


def test_e2e_draft_never_overwrites_a_file_that_appeared_after_planning(env):
    store, ws, folder = env
    step = {"steps": [{"operation": "write_file", "paths": ["draft.md"],
                       "arguments": {"content": "new", "create_only": True}}]}
    gateway, _ = _gateway(store, step)
    outcome = gateway.handle(ws.id, "write a draft")
    (folder / "draft.md").write_text("precious")   # appears while waiting
    result = gateway.approve_and_run(outcome)
    assert not result.did_anything
    assert (folder / "draft.md").read_text() == "precious"