"""Refusals raised by the enforcement layer.

A refusal is not an error in the ordinary sense. It is the system working correctly:
something asked for a resource outside the boundary and the boundary held. Every
refusal carries the reason it was refused, because the audit log records refusals as
well as actions (Architecture Section 4, invariant three).
"""

from __future__ import annotations

from enum import Enum


class RefusalReason(str, Enum):
    """Why the broker refused to resolve a path.

    These map one to one onto the assertions in Architecture Section 6.1, so a
    refusal in the log can be traced back to the specific rule that produced it.
    """

    OUTSIDE_GRANT = "outside_grant"
    """The canonical path resolved outside the workspace's grant root."""

    DENY_LISTED = "deny_listed"
    """The path is a system, hidden or credential path."""

    PERMISSION_EXCEEDED = "permission_exceeded"
    """The requested operation exceeds the permission granted to the workspace."""

    NO_ACTIVE_GRANT = "no_active_grant"
    """No workspace grant covers this request."""

    UNRESOLVABLE = "unresolvable"
    """The path could not be canonicalised at all."""


class BoundaryRefusal(Exception):
    """Raised when the Workspace Broker refuses to resolve a path.

    Carries the requested reference, the reason, and the workspace it was
    evaluated against. The resolved path is deliberately not carried: a refusal
    must not leak the location it refused to reach.
    """

    def __init__(
        self,
        reason: RefusalReason,
        requested: str,
        workspace_id: int | None = None,
        detail: str = "",
    ) -> None:
        self.reason = reason
        self.requested = requested
        self.workspace_id = workspace_id
        self.detail = detail
        message = f"refused ({reason.value}): {requested!r}"
        if detail:
            message = f"{message} — {detail}"
        super().__init__(message)


class WorkspaceError(Exception):
    """Raised for workspace lifecycle problems, such as granting a missing folder."""
