"""The vocabulary of proposed work: tool calls, risk tiers, and verdicts.

This module is deliberately inert. It defines what a proposed action *is* and
carries no ability to perform one, which is what lets the planner, the policy
engine, the approval broker and the dispatcher all speak about the same object
without any of them being able to act on it alone.

The four tiers come from Architecture Section 5.3. The important one is T3:
it exists so that "ARTEMIS deletes nothing" is a property of the system rather
than a promise about a model's behaviour. There is no approval dialogue for T3
because there is no code path to it.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Tier(str, Enum):
    """How much trust an action needs before it may run."""

    READ = "T0"
    """Reads inside the granted workspace. No mutation, no egress."""

    REVERSIBLE = "T1"
    """Mutates workspace state, fully invertible from a snapshot."""

    OUTWARD = "T2"
    """Leaves the machine. Always gated, whatever the user has configured."""

    DESTRUCTIVE = "T3"
    """Deletion, unsnapshotted overwrite, out-of-workspace write. Refused."""


class Decision(str, Enum):
    """What the policy engine concluded about one call."""

    ALLOW = "allow"
    """Run it now. Reads only."""

    GATE = "gate"
    """Ask the user first."""

    DENY = "deny"
    """Refuse. Never reaches the dispatcher."""


#: Operations that mutate the workspace but can be undone from a snapshot.
REVERSIBLE_OPS = frozenset(
    {"write_file", "create_dir", "move_file", "rename", "append_file"}
)

#: Operations that leave the machine.
OUTWARD_OPS = frozenset({"send_mail", "web_search", "http_request", "cloud_model_call"})

#: Operations ARTEMIS will not perform at all. Listing them is documentation;
#: the enforcement is that no service implements them and the dispatcher has no
#: branch that would call one.
DESTRUCTIVE_OPS = frozenset({"delete_file", "delete_dir", "overwrite_file", "truncate"})

#: Operations that only read.
READ_OPS = frozenset(
    {"list_dir", "read_file", "read_metadata", "stat", "search_index"}
)


@dataclass(frozen=True)
class ToolCall:
    """One proposed action.

    Produced by the planner, classified by the policy engine, executed by the
    dispatcher. Immutable, so a verdict cannot be attached to one call and then
    the call quietly changed before it runs.

    `paths` are workspace-relative; the broker resolves them at execution time.
    Keeping them relative here means a call cannot smuggle an absolute path past
    the boundary by being constructed carefully.
    """

    operation: str
    workspace_id: int
    paths: tuple[str, ...] = ()
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def describe(self) -> str:
        """A short human-readable line, for previews and the audit log."""
        if self.paths:
            shown = ", ".join(self.paths[:3])
            if len(self.paths) > 3:
                shown += f", and {len(self.paths) - 3} more"
            return f"{self.operation}({shown})"
        return f"{self.operation}()"

    def fingerprint(self) -> str:
        """Identifies the *shape* of this call, ignoring which paths it touches.

        Remembered approvals are scoped by this, so approving one folder tidy
        does not silently approve a mail send. It deliberately excludes paths:
        the user is approving a kind of operation in a workspace, not a
        particular set of files forever.
        """
        return f"{self.workspace_id}:{self.operation}"


@dataclass(frozen=True)
class Verdict:
    """The policy engine's conclusion about one call.

    The dispatcher refuses any call whose verdict is missing or does not match
    the call it arrived with (Architecture Section 4, invariant four). That
    match is what stops a call being classified as a read and then executed as
    something else.
    """

    call_id: str
    tier: Tier
    decision: Decision
    reason: str
    rule_applied: str
    remembered: bool = False

    @property
    def needs_approval(self) -> bool:
        return self.decision is Decision.GATE

    @property
    def refused(self) -> bool:
        return self.decision is Decision.DENY

    def matches(self, call: ToolCall) -> bool:
        return self.call_id == call.call_id


@dataclass(frozen=True)
class Plan:
    """An ordered set of proposed calls, approved and undone as one unit.

    The plan is the unit the user is asked about, so it is also the unit undo
    works at: reversing a folder tidy restores all twelve moves together, in
    reverse order, because twelve separate undos is not what was approved
    (Architecture Section 6.2).
    """

    calls: tuple[ToolCall, ...]
    intent: str = ""
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __len__(self) -> int:
        return len(self.calls)

    def __iter__(self):
        return iter(self.calls)

    def summarise(self) -> str:
        """One line naming what the plan does, grouped by operation."""
        if not self.calls:
            return "nothing to do"
        counts: dict[str, int] = {}
        for call in self.calls:
            counts[call.operation] = counts.get(call.operation, 0) + 1
        parts = [
            f"{count} {operation.replace('_', ' ')}"
            + ("" if count == 1 else "s")
            for operation, count in counts.items()
        ]
        return ", ".join(parts)

    def to_json(self) -> str:
        return json.dumps(
            {
                "plan_id": self.plan_id,
                "intent": self.intent,
                "calls": [
                    {
                        "call_id": c.call_id,
                        "operation": c.operation,
                        "workspace_id": c.workspace_id,
                        "paths": list(c.paths),
                        "arguments": c.arguments,
                    }
                    for c in self.calls
                ],
            },
            sort_keys=True,
        )
