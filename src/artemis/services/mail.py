"""F7: Mail composer.

Draft, approve, send. Sending is T2, so it is gated whatever the user has
configured, and an approval to send mail can never be remembered (FR-26, UC-4).

The password is never stored by ARTEMIS. It lives in the operating system
keyring (NFR-7). Only non-secret settings (server, port, address) are read
from config.toml, in a [mail] section:

    [mail]
    host = "smtp.gmail.com"
    port = 465
    username = "me@example.com"
    from_addr = "me@example.com"
    security = "ssl"        # or "starttls"
"""

from __future__ import annotations

import hashlib
import re
import smtplib
import ssl
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage

from artemis.core.actions import Plan, ToolCall
from artemis.data import paths
from artemis.data.store import Store

KEYRING_SERVICE = "ARTEMIS-mail"
MAX_RECIPIENTS = 10
MAX_BODY_CHARS = 20000
_ADDRESS = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")


class MailError(ValueError):
    """The message is not acceptable, or could not be sent.

    A ValueError on purpose: the dispatcher treats ValueError as "skip this
    step and report it", instead of crashing the whole plan.
    """


@dataclass(frozen=True)
class MailSettings:
    host: str
    port: int
    username: str
    from_addr: str
    security: str = "ssl"


def load_settings() -> MailSettings | None:
    """Non-secret mail settings from config.toml, or None if not set up."""
    try:
        with paths.config_path().open("rb") as handle:
            section = tomllib.load(handle).get("mail")
    except (OSError, tomllib.TOMLDecodeError):
        return None
    if not section:
        return None
    try:
        return MailSettings(
            host=str(section["host"]),
            port=int(section.get("port", 465)),
            username=str(section["username"]),
            from_addr=str(section.get("from_addr", section["username"])),
            security=str(section.get("security", "ssl")),
        )
    except (KeyError, ValueError):
        return None


def get_password(username: str) -> str | None:
    import keyring  # imported late so the rest of ARTEMIS works without it

    return keyring.get_password(KEYRING_SERVICE, username)


def set_password(username: str, password: str) -> None:
    import keyring

    keyring.set_password(KEYRING_SERVICE, username, password)


def validate_address(address: str) -> str:
    cleaned = address.strip()
    if "\r" in cleaned or "\n" in cleaned or not _ADDRESS.match(cleaned):
        raise MailError(f"not a valid email address: {address!r}")
    return cleaned


def _check_subject(subject: str) -> str:
    # A newline in a header lets someone add extra headers (header injection).
    if "\r" in subject or "\n" in subject:
        raise MailError("the subject cannot contain line breaks")
    return subject.strip()


def _smtp_send(settings: MailSettings, password: str, message: EmailMessage) -> None:
    try:
        if settings.security == "ssl":
            with smtplib.SMTP_SSL(
                settings.host, settings.port, timeout=30,
                context=ssl.create_default_context(),
            ) as server:
                server.login(settings.username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(settings.host, settings.port, timeout=30) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(settings.username, password)
                server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"the mail server refused or could not be reached: {exc}") from exc


class MailService:
    def __init__(
        self,
        store: Store,
        settings_loader: Callable[[], MailSettings | None] = load_settings,
        password_getter: Callable[[str], str | None] = get_password,
        transport: Callable[[MailSettings, str, EmailMessage], None] = _smtp_send,
    ) -> None:
        self._store = store
        self._settings_loader = settings_loader
        self._password_getter = password_getter
        self._transport = transport

    def compose(self, workspace_id: int, to: list[str], subject: str, body: str) -> Plan:
        """Check the draft and return a plan with one send_mail call.

        Nothing is sent. The user approves the exact recipient and content
        first, because the approval preview shows them.
        """
        recipients = [validate_address(a) for a in to]
        if not recipients:
            raise MailError("a message needs at least one recipient")
        if len(recipients) > MAX_RECIPIENTS:
            raise MailError(f"no more than {MAX_RECIPIENTS} recipients at once")
        if len(body) > MAX_BODY_CHARS:
            raise MailError(f"the message is longer than {MAX_BODY_CHARS} characters")
        call = ToolCall(
            "send_mail",
            workspace_id,
            (),
            {"to": recipients, "subject": _check_subject(subject), "body": body},
        )
        return Plan(calls=(call,), intent=f"Send an email to {', '.join(recipients)}")

    def send(self, workspace_id: int, arguments: dict) -> dict:
        """Send the message. Called only by the dispatcher, after approval."""
        settings = self._settings_loader()
        if settings is None:
            raise MailError("no mail account is set up yet")
        password = self._password_getter(settings.username)
        if not password:
            raise MailError("no password for the mail account was found in the keyring")

        recipients = [validate_address(a) for a in arguments.get("to", [])]
        subject = _check_subject(str(arguments.get("subject", "")))
        body = str(arguments.get("body", ""))
        if not recipients:
            raise MailError("a message needs at least one recipient")

        message = EmailMessage()
        message["From"] = settings.from_addr
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)

        when = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            self._transport(settings, password, message)
        except MailError as exc:
            self._store.append_audit(
                event="mail.sent",
                outcome="failed",
                workspace_id=workspace_id,
                detail={"to": recipients, "subject": subject, "error": str(exc)},
            )
            raise

        # Who, what and when. The body is recorded as a fingerprint and length,
        # so the log can prove what was sent without storing a second copy.
        self._store.append_audit(
            event="mail.sent",
            outcome="sent",
            workspace_id=workspace_id,
            detail={
                "to": recipients,
                "subject": subject,
                "body_chars": len(body),
                "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "sent_at": when,
            },
        )
        return {"sent_to": recipients, "subject": subject, "sent_at": when}