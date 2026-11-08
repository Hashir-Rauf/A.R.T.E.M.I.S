"""Choosing which model each provider uses, and seeing which models were found."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from artemis.core.modelconfig import (
    DEFAULT_LOCAL_MODEL,
    ModelNameError,
    ModelSettings,
    check_model_name,
)
from artemis.core.providers import OllamaProvider
from artemis.core.router import CLOUD_ALLOWED, ModelRouter
from artemis.core.workspace import WorkspaceManager
from artemis.data import credentials
from artemis.data.store import Store


def _ollama(monkeypatch, models: list[tuple[str, int]] | None) -> None:
    """Pretend Ollama has these models, or is not running when None."""

    class _Reply(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        if models is None:
            raise OSError("connection refused")
        body = {"models": [{"name": n, "size": s} for n, s in models]}
        return _Reply(json.dumps(body).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


@pytest.fixture
def settings(store: Store) -> ModelSettings:
    return ModelSettings(store)


# -- names are free text, but only text that could be a model name -------------


@pytest.mark.parametrize("name", [
    "gpt-4.1-mini", "gemini-2.5-pro", "claude-sonnet-4@20250514", "llama3.2:3b",
    "models/gemini-2.0-flash", "o4-mini",
])
def test_real_model_names_are_accepted(name: str) -> None:
    assert check_model_name(name) == name


@pytest.mark.parametrize("bad", ["", "   ", "gpt 4", "gpt-4; rm -rf", "a" * 101, "-leading", 'x"y'])
def test_things_that_are_not_model_names_are_refused(bad: str) -> None:
    with pytest.raises(ModelNameError):
        check_model_name(bad)


def test_pasted_quotes_and_spaces_are_trimmed() -> None:
    assert check_model_name('  "gpt-4.1-mini" ') == "gpt-4.1-mini"


# -- the local models -----------------------------------------------------------


def test_local_models_found_on_the_computer_are_listed(settings, monkeypatch) -> None:
    _ollama(monkeypatch, [("gemma4:e4b", 9_600_000_000), ("llama3.2:3b", 2_000_000_000)])
    status = settings.local_status(refresh=True)
    assert status.running is True
    assert status.names == ["gemma4:e4b", "llama3.2:3b"]
    assert status.models[1].size_label == "2.0 GB"


def test_the_default_model_is_used_when_it_is_installed(settings, monkeypatch) -> None:
    _ollama(monkeypatch, [("llama3.2:3b", 1), ("gemma4:e4b", 1)])
    status = settings.local_status(refresh=True)
    assert status.active == DEFAULT_LOCAL_MODEL and status.chosen is False


def test_the_first_installed_model_is_used_when_the_default_is_missing(settings, monkeypatch) -> None:
    """It used to ask for gemma4:e4b whatever was installed, and fail."""
    _ollama(monkeypatch, [("mistral:7b", 1), ("llama3.2:3b", 1)])
    status = settings.local_status(refresh=True)
    assert status.active == "llama3.2:3b" and status.active_installed is True


def test_a_chosen_local_model_is_the_one_in_use(settings, monkeypatch) -> None:
    _ollama(monkeypatch, [("gemma4:e4b", 1), ("llama3.2:3b", 1)])
    settings.set_local_model("llama3.2:3b")
    status = settings.local_status(refresh=True)
    assert status.active == "llama3.2:3b" and status.chosen is True


def test_a_chosen_model_that_is_not_installed_is_reported_not_hidden(settings, monkeypatch) -> None:
    _ollama(monkeypatch, [("gemma4:e4b", 1)])
    settings.set_local_model("qwen3:8b")
    status = settings.local_status(refresh=True)
    assert status.active == "qwen3:8b" and status.active_installed is False


def test_ollama_not_running_is_said_plainly(settings, monkeypatch) -> None:
    _ollama(monkeypatch, None)
    status = settings.local_status(refresh=True)
    assert status.running is False and status.models == ()


def test_resetting_goes_back_to_the_automatic_choice(settings, monkeypatch) -> None:
    _ollama(monkeypatch, [("gemma4:e4b", 1)])
    settings.set_local_model("llama3.2:3b")
    settings.reset_local_model()
    assert settings.local_status(refresh=True).chosen is False


# -- the cloud services ----------------------------------------------------------


def test_each_cloud_service_has_its_own_model(settings) -> None:
    settings.set_cloud_model("openai", "gpt-4.1-mini")
    assert settings.cloud_model("openai") == "gpt-4.1-mini"
    assert settings.cloud_model("gemini") == settings.default_cloud_model("gemini")
    assert settings.cloud_model_is_custom("openai") and not settings.cloud_model_is_custom("gemini")


def test_resetting_a_cloud_model_restores_the_default(settings) -> None:
    settings.set_cloud_model("anthropic", "claude-opus-4")
    settings.reset_cloud_model("anthropic")
    assert settings.cloud_model("anthropic") == settings.default_cloud_model("anthropic")


def test_an_unknown_service_is_refused_not_invented(settings) -> None:
    with pytest.raises(KeyError):
        settings.set_cloud_model("notaservice", "gpt-4")


def test_the_choice_survives_a_restart(store: Store, artemis_home: Path) -> None:
    ModelSettings(store).set_cloud_model("openai", "gpt-4.1-mini")
    store.close()
    reopened = Store()
    try:
        assert ModelSettings(reopened).cloud_model("openai") == "gpt-4.1-mini"
    finally:
        reopened.close()


# -- the router follows the choices ---------------------------------------------


def test_the_router_gets_the_chosen_local_model(settings, store, monkeypatch) -> None:
    _ollama(monkeypatch, [("gemma4:e4b", 1), ("llama3.2:3b", 1)])
    settings.set_local_model("llama3.2:3b")
    router = ModelRouter(store=store)
    settings.sync(router)
    local = next(p for p in router.providers if isinstance(p, OllamaProvider))
    assert local.model == "llama3.2:3b"


def test_a_model_change_reaches_a_router_that_already_exists(settings, store, monkeypatch) -> None:
    _ollama(monkeypatch, [("gemma4:e4b", 1), ("llama3.2:3b", 1)])
    router = ModelRouter(store=store)
    settings.sync(router)
    settings.set_local_model("llama3.2:3b")
    settings.sync(router)
    assert [p.model for p in router.providers if isinstance(p, OllamaProvider)] == ["llama3.2:3b"]


def test_a_cloud_service_is_only_in_the_router_while_a_key_is_stored(settings, store, monkeypatch) -> None:
    _ollama(monkeypatch, [("gemma4:e4b", 1)])
    keys = {}
    monkeypatch.setattr(credentials, "get_key", lambda name: keys.get(name))
    router = ModelRouter(store=store)

    settings.sync(router)
    assert [p.name for p in router.providers] == ["ollama"]

    keys["openai"] = "sk-test"
    settings.set_cloud_model("openai", "gpt-4.1-mini")
    settings.sync(router)
    cloud = next(p for p in router.providers if p.name == "openai")
    assert cloud.model == "gpt-4.1-mini" and cloud.api_key == "sk-test"

    del keys["openai"]
    settings.sync(router)
    assert [p.name for p in router.providers] == ["ollama"]


def test_a_cloud_model_is_still_refused_for_a_folder_kept_local(
    settings, store, manager: WorkspaceManager, sandbox: Path, monkeypatch
) -> None:
    """Choosing a model never opens the door: the folder's own setting still decides."""
    _ollama(monkeypatch, [("gemma4:e4b", 1)])
    monkeypatch.setattr(credentials, "get_key", lambda name: "sk-test" if name == "openai" else None)
    router = ModelRouter(store=store)
    settings.sync(router)
    ws = manager.grant(sandbox).id

    assert [p.name for p in router.permitted_tiers(ws)] == ["ollama"]

    store.set_cloud_policy(ws, CLOUD_ALLOWED)
    assert {p.name for p in router.permitted_tiers(ws)} == {"ollama", "openai"}
