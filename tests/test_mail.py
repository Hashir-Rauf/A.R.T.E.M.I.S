"""Setting up a mail account from the interface."""

from __future__ import annotations

import pytest


# -- setting up an account from the interface ---------------------------------------


def test_an_account_is_saved_with_the_password_in_the_keyring_not_the_file(monkeypatch) -> None:
    from artemis.data import paths
    from artemis.services import mail

    stored = {}
    monkeypatch.setattr(mail, "set_password", lambda user, pw: stored.update({user: pw}))

    mail.save_settings(mail.MailSettings("smtp.example.com", 465, "me@example.com", "me@example.com"), "s3cret")

    text = paths.config_path().read_text(encoding="utf-8")
    assert "smtp.example.com" in text and "s3cret" not in text
    assert stored == {"me@example.com": "s3cret"}
    loaded = mail.load_settings()
    assert loaded is not None and loaded.host == "smtp.example.com" and loaded.port == 465


def test_saving_again_replaces_the_account_and_keeps_other_settings(monkeypatch) -> None:
    from artemis.data import paths
    from artemis.services import mail

    monkeypatch.setattr(mail, "set_password", lambda user, pw: None)
    path = paths.config_path()
    path.write_text('[other]\nkeep = "yes"\n', encoding="utf-8")

    mail.save_settings(mail.MailSettings("a.example.com", 465, "a@example.com", "a@example.com"), "x")
    mail.save_settings(mail.MailSettings("b.example.com", 587, "b@example.com", "b@example.com", "starttls"), "y")

    text = path.read_text(encoding="utf-8")
    assert text.count("[mail]") == 1 and "b.example.com" in text and "a.example.com" not in text
    assert 'keep = "yes"' in text


@pytest.mark.parametrize("host, port, security, password", [
    ("not a host", 465, "ssl", "pw"),
    ("smtp.example.com", 0, "ssl", "pw"),
    ("smtp.example.com", 465, "plain", "pw"),
    ("smtp.example.com", 465, "ssl", ""),
])
def test_an_account_that_cannot_be_right_is_refused_and_nothing_is_written(
    monkeypatch, host, port, security, password
) -> None:
    from artemis.data import paths
    from artemis.services import mail

    monkeypatch.setattr(mail, "set_password", lambda user, pw: None)
    with pytest.raises(mail.MailError):
        mail.save_settings(mail.MailSettings(host, port, "me@example.com", "me@example.com", security), password)
    assert not paths.config_path().exists()


def test_a_keyring_failure_means_nothing_is_saved(monkeypatch) -> None:
    from artemis.data import paths
    from artemis.services import mail

    def broken(user, pw):
        raise RuntimeError("no keyring backend")

    monkeypatch.setattr(mail, "set_password", broken)
    with pytest.raises(mail.MailError, match="nothing was saved"):
        mail.save_settings(mail.MailSettings("smtp.example.com", 465, "me@example.com", "me@example.com"), "pw")
    assert not paths.config_path().exists()


def test_forgetting_the_account_removes_it(monkeypatch) -> None:
    from artemis.services import mail

    monkeypatch.setattr(mail, "set_password", lambda user, pw: None)
    mail.save_settings(mail.MailSettings("smtp.example.com", 465, "me@example.com", "me@example.com"), "pw")
    mail.forget_settings()
    assert mail.load_settings() is None
