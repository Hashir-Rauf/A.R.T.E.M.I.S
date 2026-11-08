"""Handlers for the outward and drafting operations, wired to the dispatcher.

Same contract as registry.py: a handler receives an ExecutionContext and
returns a result. These two need a service object (they must log and use the
keyring), so they are built by a factory instead of being plain functions.

By the time a handler runs, the dispatcher has already checked the verdict and
the approval. A handler never decides whether it is allowed to run.
"""

from __future__ import annotations

from artemis.core.dispatch import ExecutionContext, Handler
from artemis.services.mail import MailService
from artemis.services.search import SearchService


def make_web_search_handler(search: SearchService) -> Handler:
    def handle_web_search(context: ExecutionContext) -> list[dict]:
        call = context.call
        results = search.run(
            call.workspace_id,
            str(call.arguments.get("query", "")),
            int(call.arguments.get("limit", 5)),
        )
        return [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results]

    return handle_web_search


def make_send_mail_handler(mail: MailService) -> Handler:
    def handle_send_mail(context: ExecutionContext) -> dict:
        call = context.call
        return mail.send(call.workspace_id, call.arguments)

    return handle_send_mail


def register_outward(dispatcher, search: SearchService, mail: MailService) -> None:
    """Attach the Sprint 7 outward handlers. Drafting needs none: it uses write_file."""
    dispatcher.register("web_search", make_web_search_handler(search))
    dispatcher.register("send_mail", make_send_mail_handler(mail))