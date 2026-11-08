"""What a remote device may ask for, and the rules that keep it below local access.

The bridge is a narrow door into the same assistant the local screen uses. It has no
privileged path: a request is an `ask`, an `approve` or a `reject`, and it goes through the
same gateway, so every boundary check and approval gate applies. On top of that it is
stricter than local, never looser:

* only folders the owner marked "available remotely" can be seen or used (default: none);
* anything that leaves the computer (an email, a web search) cannot be approved from a
  remote device while "approve outward actions here only" is on (default: on);
* it can do nothing but those requests: no settings, no keys, no adding or removing folders;
* every request is written to the audit log with the device that made it.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Callable

from artemis.data.store import Store

ALLOWED_KEY = "remote.allowed_workspaces"
LOCAL_OUTWARD_KEY = "remote.outward_approval_stays_local"


def _plain(markup: str) -> str:
    text = re.sub(r"<[^>]+>", " ", markup or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


class RemoteBridge:
    def __init__(self, store: Store, panel_factory: Callable[[], Any]) -> None:
        self._store = store
        self._panel_factory = panel_factory
        self._panels: dict[str, Any] = {}

    # -- what the owner allows -------------------------------------------------

    def allowed_workspaces(self) -> set[int]:
        raw = self._store.get_setting(ALLOWED_KEY, "[]") or "[]"
        try:
            return {int(i) for i in json.loads(raw)}
        except (ValueError, TypeError):
            return set()

    def allow_workspace(self, workspace_id: int, allowed: bool) -> None:
        ids = self.allowed_workspaces()
        (ids.add if allowed else ids.discard)(workspace_id)
        self._store.set_setting(ALLOWED_KEY, json.dumps(sorted(ids)))

    @property
    def outward_stays_local(self) -> bool:
        return (self._store.get_setting(LOCAL_OUTWARD_KEY, "1") or "1") != "0"

    def set_outward_stays_local(self, on: bool) -> None:
        self._store.set_setting(LOCAL_OUTWARD_KEY, "1" if on else "0")

    # -- requests ----------------------------------------------------------------

    def handle(self, device_id: str, request: dict) -> dict:
        op = str(request.get("op", ""))
        handlers = {
            "workspaces": self._workspaces,
            "ask": self._ask,
            "approve": self._approve,
            "reject": self._reject,
        }
        handler = handlers.get(op)
        if handler is None:
            self._audit(device_id, op or "?", "refused", "not available remotely")
            return {"error": "That is not available from a remote device."}
        return handler(device_id, request)

    def _audit(self, device_id: str, op: str, outcome: str, why: str = "") -> None:
        self._store.append_audit(
            f"remote.{op}", outcome, detail={"device": device_id, "why": why} if why else {"device": device_id}
        )

    def _panel(self, device_id: str):
        if device_id not in self._panels:
            self._panels[device_id] = self._panel_factory()
        return self._panels[device_id]

    def _workspaces(self, device_id: str, request: dict) -> dict:
        allowed = self.allowed_workspaces()
        rows = [
            {"id": int(r["id"]), "name": r["name"]}
            for r in self._store.list_workspaces()
            if int(r["id"]) in allowed
        ]
        self._audit(device_id, "workspaces", "done")
        return {"workspaces": rows}

    def _ask(self, device_id: str, request: dict) -> dict:
        try:
            workspace_id = int(request.get("workspace_id"))
        except (TypeError, ValueError):
            return {"error": "Choose a folder first."}
        if workspace_id not in self.allowed_workspaces():
            # Same answer as for a folder that does not exist: a hidden folder stays hidden.
            self._audit(device_id, "ask", "refused", "folder not available remotely")
            return {"error": "That folder is not available remotely."}
        panel = self._panel(device_id)
        message, card = panel.ask(workspace_id, str(request.get("text", "")))
        self._audit(device_id, "ask", "done")
        return {
            "message": _plain(message),
            "card": _plain(card),
            "pending": bool(panel.has_pending),
            "leaves_computer": self._leaves(panel),
        }

    @staticmethod
    def _leaves(panel) -> bool:
        outcome = panel.state.outcome
        return bool(outcome and (outcome.preview or {}).get("leaves_machine"))

    def _approve(self, device_id: str, request: dict) -> dict:
        panel = self._panel(device_id)
        if not panel.has_pending:
            return {"error": "There is nothing waiting for an answer."}
        if self._leaves(panel) and self.outward_stays_local:
            self._audit(device_id, "approve", "refused", "outward action needs local approval")
            return {
                "waiting_on_computer": True,
                "message": "This would leave the computer, so it has to be approved on the computer itself.",
            }
        message, _card = panel.approve()
        self._audit(device_id, "approve", "approved")
        return {"message": _plain(message), "pending": bool(panel.has_pending)}

    def _reject(self, device_id: str, request: dict) -> dict:
        panel = self._panel(device_id)
        message, _card = panel.reject()
        self._audit(device_id, "reject", "declined")
        return {"message": _plain(message), "pending": False}
