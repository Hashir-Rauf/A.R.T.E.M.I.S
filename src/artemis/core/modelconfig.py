"""Which model each provider uses, and which models ARTEMIS found.

Two things used to be fixed in code. The local model was always `gemma4:e4b`,
whether or not it was the one installed, and each cloud service had one model
named in the catalogue. Neither could be changed without editing the source.

Now the person chooses. A model name is free text on purpose: services publish
new models every few weeks, and a list baked into the program would be out of
date by the time it shipped. The local list is the opposite: it is read from the
computer, so it only offers what is really installed.

Nothing here sends anything anywhere. Looking for local models is a request to
Ollama on this machine, and a cloud provider is only registered when a key for
it is stored, and is still refused for any folder not set to allow the cloud.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from artemis.core.providers import CLOUD_CATALOGUE, OllamaProvider, cloud_provider
from artemis.data import credentials
from artemis.data.store import Store

DEFAULT_LOCAL_MODEL = "gemma4:e4b"

LOCAL_KEY = "model.local"

#: Letters, digits and the few separators real model names use ("llama3.2:3b",
#: "gpt-4.1-mini", "models/gemini-2.5-pro", "claude-sonnet-4@20250514"). Anything
#: else is refused, so a pasted sentence or a stray quote cannot become a name
#: that is sent to a service.
MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,99}$")


class ModelNameError(ValueError):
    """The text is not something that could be a model name."""


def cloud_setting(provider: str) -> str:
    return f"model.cloud.{provider}"


def check_model_name(name: str) -> str:
    cleaned = (name or "").strip().strip("\"'")
    if not cleaned:
        raise ModelNameError("Type a model name first.")
    if not MODEL_NAME.match(cleaned):
        raise ModelNameError(
            "That does not look like a model name. Use letters, numbers and "
            "the characters . : / - _ only, for example gpt-4.1-mini."
        )
    return cleaned


@dataclass(frozen=True)
class LocalModel:
    name: str
    size_bytes: int = 0

    @property
    def size_label(self) -> str:
        if not self.size_bytes:
            return ""
        return f"{self.size_bytes / 1e9:.1f} GB"


@dataclass(frozen=True)
class LocalStatus:
    """What was found on this computer, and which model is being used."""

    running: bool
    models: tuple[LocalModel, ...]
    #: The model ARTEMIS will ask. Either the one chosen, or a sensible default.
    active: str
    #: True when `active` is something Ollama actually has.
    active_installed: bool
    #: True when the person picked it, false when ARTEMIS chose it.
    chosen: bool

    @property
    def names(self) -> list[str]:
        return [m.name for m in self.models]


class ModelSettings:
    """Reads and writes the model choices, and keeps a router in step with them."""

    def __init__(self, store: Store, host: str = "http://127.0.0.1:11434") -> None:
        self._store = store
        self._host = host
        self._cache: tuple[float, list[LocalModel] | None] | None = None

    # -- the local models ----------------------------------------------------

    def _installed(self, max_age: float) -> list[LocalModel] | None:
        """What Ollama reports, or None if it cannot be reached.

        Ollama on this computer answers in milliseconds, so waiting longer only
        slows things down when it is switched off (Windows takes about two seconds
        to refuse a closed port). Cached briefly because the sidebar asks on every click, and a computer
        with Ollama switched off would otherwise wait for a timeout each time.
        """
        now = time.monotonic()
        if self._cache and now - self._cache[0] < max_age:
            return self._cache[1]
        found: list[LocalModel] | None
        try:
            with urllib.request.urlopen(f"{self._host}/api/tags", timeout=0.6) as response:
                body = json.loads(response.read())
            found = sorted(
                (
                    LocalModel(str(m.get("name", "")), int(m.get("size", 0) or 0))
                    for m in body.get("models", [])
                    if m.get("name")
                ),
                key=lambda m: m.name,
            )
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            found = None
        self._cache = (now, found)
        return found

    def local_status(self, refresh: bool = False) -> LocalStatus:
        installed = self._installed(max_age=0 if refresh else 10)
        chosen = self._store.get_setting(LOCAL_KEY)
        names = [m.name for m in installed or []]
        if chosen:
            active = chosen
        elif DEFAULT_LOCAL_MODEL in names or not names:
            active = DEFAULT_LOCAL_MODEL
        else:
            active = names[0]
        return LocalStatus(
            running=installed is not None,
            models=tuple(installed or ()),
            active=active,
            active_installed=active in names,
            chosen=bool(chosen),
        )

    def set_local_model(self, name: str) -> str:
        cleaned = check_model_name(name)
        self._store.set_setting(LOCAL_KEY, cleaned)
        return cleaned

    def reset_local_model(self) -> None:
        self._store.delete_setting(LOCAL_KEY)

    # -- the cloud services ----------------------------------------------------

    @staticmethod
    def default_cloud_model(provider: str) -> str:
        entry = next((e for e in CLOUD_CATALOGUE if e["name"] == provider), None)
        if entry is None:
            raise KeyError(f"unknown cloud provider: {provider}")
        return entry["model"]

    def cloud_model(self, provider: str) -> str:
        chosen = self._store.get_setting(cloud_setting(provider))
        return chosen or self.default_cloud_model(provider)

    def cloud_model_is_custom(self, provider: str) -> bool:
        return self._store.get_setting(cloud_setting(provider)) is not None

    def set_cloud_model(self, provider: str, name: str) -> str:
        self.default_cloud_model(provider)  # raises for an unknown service
        cleaned = check_model_name(name)
        self._store.set_setting(cloud_setting(provider), cleaned)
        return cleaned

    def reset_cloud_model(self, provider: str) -> None:
        self.default_cloud_model(provider)
        self._store.delete_setting(cloud_setting(provider))

    # -- keeping a router in step -----------------------------------------------

    def sync(self, router) -> None:
        """Make the router's providers match what has been chosen and stored.

        Safe to call as often as needed: after a model is chosen, after a key is
        saved or forgotten, and once at start-up. A cloud service is present in
        the router only while a key for it is stored. Whether a given folder may
        use it is still the router's own egress rule, which this does not touch.
        """
        status = self.local_status()
        local = next((p for p in router.providers if isinstance(p, OllamaProvider)), None)
        if local is None:
            local = OllamaProvider()
            router.register(local)
        local.model = status.active

        for entry in CLOUD_CATALOGUE:
            name = entry["name"]
            existing = next((p for p in router.providers if p.name == name), None)
            try:
                key = credentials.get_key(name)
            except credentials.KeyringUnavailable:
                key = None
            if not key:
                if existing is not None:
                    router.providers.remove(existing)
                continue
            model = self.cloud_model(name)
            if existing is None:
                router.register(cloud_provider(name, key, model))
            else:
                existing.api_key = key
                existing.model = model
