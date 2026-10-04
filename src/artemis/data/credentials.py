"""API keys, kept in the operating system keyring.

Secrets never enter the ARTEMIS directory, the database, or the audit log
(Architecture Section 7.1). This module is the only code that reads or writes
them, so there is one place to audit rather than one per provider.

What the rest of the system may know is whether a key *exists*, never what it
is. `has_key` is the question the interface asks; `get_key` is called only at
the moment a request is actually sent.
"""

from __future__ import annotations

SERVICE = "ARTEMIS"


class KeyringUnavailable(RuntimeError):
    """The platform keyring could not be reached."""


def _keyring():
    try:
        import keyring
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise KeyringUnavailable(
            "the keyring package is not installed, so API keys cannot be "
            "stored safely"
        ) from exc
    return keyring


def set_key(provider: str, key: str) -> None:
    """Store a provider's API key.

    Raises rather than falling back to a file. A silent downgrade to plaintext
    on disk would break the promise the architecture makes about secrets, and
    the user would have no way to know it had happened.
    """
    _keyring().set_password(SERVICE, provider, key)


def get_key(provider: str) -> str | None:
    """The stored key, or None. Called only when a request is being sent."""
    try:
        return _keyring().get_password(SERVICE, provider)
    except KeyringUnavailable:
        return None


def has_key(provider: str) -> bool:
    """Whether a key exists. This is what the interface is allowed to ask."""
    return bool(get_key(provider))


def forget_key(provider: str) -> None:
    """Remove a stored key. Safe to call when there is nothing stored."""
    try:
        keyring = _keyring()
    except KeyringUnavailable:
        return
    try:
        keyring.delete_password(SERVICE, provider)
    except Exception:
        # Nothing stored is the normal case here, not an error worth raising.
        pass


def stored_providers(names: tuple[str, ...]) -> list[str]:
    """Which of `names` currently have a key. Names only, never values."""
    return [name for name in names if has_key(name)]
