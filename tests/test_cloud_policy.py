"""When a cloud model may be used, and what the person is told when nothing can answer."""

from __future__ import annotations

from pathlib import Path

from artemis.core.providers import ModelTier, StubProvider
from artemis.core.router import ModelRouter
from artemis.core.workspace import WorkspaceManager
from artemis.data import credentials
from artemis.data.store import Store
from artemis.ui.assistant import AssistantPanel


def _router(store: Store) -> ModelRouter:
    router = ModelRouter(store=store)
    router.register(StubProvider(name="local", tier=ModelTier.LOCAL))
    router.register(StubProvider(name="cloudy", tier=ModelTier.GEMINI))
    return router


def test_chat_with_no_folder_stays_local_until_the_person_opts_in(store: Store) -> None:
    router = _router(store)
    assert [p.name for p in router.permitted_tiers(None)] == ["local"]

    store.set_setting("cloud.chat", "1")
    assert {p.name for p in router.permitted_tiers(None)} == {"local", "cloudy"}

    store.set_setting("cloud.chat", "0")
    assert [p.name for p in router.permitted_tiers(None)] == ["local"]


def test_a_folder_decides_for_itself_whatever_the_chat_setting_says(
    store: Store, manager: WorkspaceManager, sandbox: Path
) -> None:
    router = _router(store)
    ws = manager.grant(sandbox).id
    store.set_setting("cloud.chat", "1")
    assert [p.name for p in router.permitted_tiers(ws)] == ["local"]

    store.set_cloud_policy(ws, "cloud_allowed")
    assert {p.name for p in router.permitted_tiers(ws)} == {"local", "cloudy"}


def test_when_nothing_answers_the_message_says_what_to_do(store: Store, monkeypatch) -> None:
    panel = AssistantPanel(store)
    monkeypatch.setattr(credentials, "has_key", lambda name: name == "gemini")
    monkeypatch.setattr(panel._models, "local_status", lambda refresh=False: type(
        "S", (), {"running": False, "active": "gemma4:e4b", "active_installed": False})())

    text = panel.no_model_help(None)

    assert "Open the Ollama app" in text
    assert "Google Gemini key saved" in text and "Use cloud models for plain chat" in text
