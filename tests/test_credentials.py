"""API keys: stored in the OS keyring, never in the ARTEMIS folder.

The architecture promises that a secret never enters the database, the audit
log, or the store directory. These tests hold that line, including the part
that is easy to lose later: that a failure to store safely is reported rather
than quietly downgraded to a file on disk.

The keyring itself is faked, because a test must not write to the real
Credential Manager of whoever runs it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.providers import CLOUD_CATALOGUE, ModelTier, cloud_provider
from artemis.data import credentials


class FakeKeyring:
    """An in-memory stand-in for the platform keyring."""

    def __init__(self) -> None:
        self.saved: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, name: str, value: str) -> None:
        self.saved[(service, name)] = value

    def get_password(self, service: str, name: str) -> str | None:
        return self.saved.get((service, name))

    def delete_password(self, service: str, name: str) -> None:
        del self.saved[(service, name)]


@pytest.fixture
def keyring(monkeypatch: pytest.MonkeyPatch) -> FakeKeyring:
    fake = FakeKeyring()
    monkeypatch.setattr(credentials, "_keyring", lambda: fake)
    return fake


# -- storing -------------------------------------------------------------------


def test_a_key_roundtrips(keyring: FakeKeyring) -> None:
    credentials.set_key("openai", "sk-secret")
    assert credentials.get_key("openai") == "sk-secret"
    assert credentials.has_key("openai")


def test_an_absent_key_is_absent(keyring: FakeKeyring) -> None:
    assert credentials.get_key("openai") is None
    assert not credentials.has_key("openai")


def test_keys_are_per_provider(keyring: FakeKeyring) -> None:
    credentials.set_key("openai", "sk-one")
    credentials.set_key("gemini", "sk-two")
    assert credentials.get_key("openai") == "sk-one"
    assert credentials.get_key("gemini") == "sk-two"


def test_forgetting_a_key_removes_it(keyring: FakeKeyring) -> None:
    credentials.set_key("openai", "sk-secret")
    credentials.forget_key("openai")
    assert not credentials.has_key("openai")


def test_forgetting_nothing_is_not_an_error(keyring: FakeKeyring) -> None:
    credentials.forget_key("never-set")


def test_stored_providers_lists_names_only(keyring: FakeKeyring) -> None:
    credentials.set_key("gemini", "sk-two")
    names = credentials.stored_providers(("gemini", "openai"))
    assert names == ["gemini"]


# -- the promise about where secrets live --------------------------------------


def test_a_key_never_reaches_the_artemis_directory(
    keyring: FakeKeyring, artemis_home: Path
) -> None:
    """Nothing under the store directory may contain the secret."""
    credentials.set_key("openai", "sk-do-not-write-me")
    for path in artemis_home.rglob("*"):
        if path.is_file():
            assert b"sk-do-not-write-me" not in path.read_bytes()


def test_an_unavailable_keyring_is_reported_not_worked_around(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Storing must fail loudly rather than fall back to plaintext.

    A silent downgrade to a file on disk would break the promise the interface
    makes to the user, and they would have no way to discover it.
    """

    def unavailable():
        raise credentials.KeyringUnavailable("no keyring here")

    monkeypatch.setattr(credentials, "_keyring", unavailable)
    with pytest.raises(credentials.KeyringUnavailable):
        credentials.set_key("openai", "sk-secret")
    assert credentials.get_key("openai") is None


# -- the catalogue -------------------------------------------------------------


def test_every_catalogue_entry_is_complete() -> None:
    for entry in CLOUD_CATALOGUE:
        assert entry["name"] and entry["label"] and entry["model"]
        assert entry["base_url"].startswith("https://")
        assert isinstance(entry["tier"], ModelTier)


def test_cloud_providers_are_above_local_tier() -> None:
    """Anything in the catalogue leaves the machine, so none may be tier 0."""
    for entry in CLOUD_CATALOGUE:
        assert entry["tier"] > ModelTier.LOCAL


def test_building_a_provider_uses_the_catalogue() -> None:
    provider = cloud_provider("gemini", "sk-key")
    assert provider.tier == ModelTier.GEMINI
    assert provider.base_url.startswith("https://")


def test_an_unknown_provider_is_refused() -> None:
    """A typo must not quietly reach an unexpected endpoint."""
    with pytest.raises(KeyError):
        cloud_provider("gemnii", "sk-key")
