"""F4: Notice a repeated task.

Watches the audit log for the same action happening again and again, and after
the third time offers to do it automatically.

**It may propose. It may never install.** There is no method in this module
that creates an accepted rule, and the store's `propose_rule` only ever writes
status `proposed`. Accepting is a separate act by the user. This is the whole
feature: an assistant that notices a pattern and asks is helpful, and one that
notices a pattern and acts is something people switch off.

**Three is the threshold, and it is deliberate.** Twice is coincidence often
enough that asking would be noise. The number comes from the proposal rather
than from tuning, and it is a constant here so it stays visible.

**A declined proposal stays declined.** If the user says no, the same pattern
is not raised again. An assistant that keeps asking after being told no is
worse than one that never asked.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from artemis.data.store import Store

#: How many repetitions before ARTEMIS says anything.
REPEAT_THRESHOLD = 3

#: How far back to look. A pattern from six months ago is not a habit.
WINDOW_DAYS = 30

#: Statuses an automation rule can hold.
PROPOSED = "proposed"
ACCEPTED = "accepted"
DECLINED = "declined"

#: Audit events worth mining. Reads are excluded: noticing that someone opens
#: a file a lot is surveillance, not helpfulness.
WATCHED_OPERATIONS = frozenset({"move_file", "create_dir", "write_file"})


@dataclass(frozen=True)
class Pattern:
    """Something the user has done enough times to be worth asking about."""

    signature: str
    description: str
    occurrences: int
    example: str = ""

    def proposal_text(self) -> str:
        return (
            f"You have done this {self.occurrences} times: {self.description}. "
            "Would you like ARTEMIS to offer it automatically next time?"
        )


class PatternWatcher:
    """Finds repetition in what has already happened, and offers to help."""

    def __init__(self, store: Store) -> None:
        self._store = store

    # -- detection ---------------------------------------------------------

    def detect(self, workspace_id: int, limit: int = 500) -> list[Pattern]:
        """Patterns repeated at least three times in the recent window.

        Reads the audit log, which records what was actually executed rather
        than what was planned. A pattern built from proposals would count
        things the user declined, which is precisely backwards.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
        rows = self._store.query(
            "SELECT ts, detail FROM audit_log"
            " WHERE workspace_id = ? AND event = 'dispatch.execute'"
            " AND outcome = 'executed' ORDER BY id DESC LIMIT ?",
            (workspace_id, limit),
        )

        counts: Counter[str] = Counter()
        examples: dict[str, str] = {}

        for row in rows:
            if not _within(row["ts"], cutoff):
                continue
            try:
                detail = json.loads(row["detail"])
            except (json.JSONDecodeError, TypeError):
                continue

            call = str(detail.get("call", ""))
            operation = call.split("(", 1)[0]
            if operation not in WATCHED_OPERATIONS:
                continue

            signature = _signature(operation, call)
            counts[signature] += 1
            examples.setdefault(signature, call)

        declined = self._declined_signatures(workspace_id)

        patterns: list[Pattern] = []
        for signature, count in counts.most_common():
            if count < REPEAT_THRESHOLD or signature in declined:
                continue
            patterns.append(
                Pattern(
                    signature=signature,
                    description=_describe(signature),
                    occurrences=count,
                    example=examples.get(signature, ""),
                )
            )
        return patterns

    # -- proposing ---------------------------------------------------------

    def propose(self, workspace_id: int, pattern: Pattern) -> int:
        """Record an offer to automate. Creates a proposal and nothing else."""
        rule_id = self._store.propose_rule(
            workspace_id, f"{pattern.signature} | {pattern.description}"
        )
        self._store.append_audit(
            event="patterns.propose",
            outcome="proposed",
            workspace_id=workspace_id,
            detail={
                "signature": pattern.signature,
                "occurrences": pattern.occurrences,
                "rule_id": rule_id,
            },
        )
        return rule_id

    def propose_new(self, workspace_id: int) -> list[int]:
        """Offer every unproposed pattern. Returns the new proposal ids."""
        already = self._known_signatures(workspace_id)
        created: list[int] = []
        for pattern in self.detect(workspace_id):
            if pattern.signature in already:
                continue
            created.append(self.propose(workspace_id, pattern))
        return created

    # -- the user's answer -------------------------------------------------

    def accept(self, workspace_id: int, rule_id: int) -> None:
        """Record that the user said yes.

        Accepting marks the rule. It does not run anything: an accepted rule
        still produces a plan that goes through policy and approval like any
        other, because "you may offer this" is not "you may do this".
        """
        self._store.set_rule_status(rule_id, ACCEPTED)
        self._store.append_audit(
            event="patterns.decide",
            outcome="accepted",
            workspace_id=workspace_id,
            detail={"rule_id": rule_id},
        )

    def decline(self, workspace_id: int, rule_id: int) -> None:
        """Record that the user said no, and stop raising it."""
        self._store.set_rule_status(rule_id, DECLINED)
        self._store.append_audit(
            event="patterns.decide",
            outcome="declined",
            workspace_id=workspace_id,
            detail={"rule_id": rule_id},
        )

    def open_proposals(self, workspace_id: int) -> list[dict]:
        return [
            {
                "rule_id": row["id"],
                "description": row["description"].split("|", 1)[-1].strip(),
                "created_at": row["created_at"],
            }
            for row in self._store.list_rules(workspace_id, status=PROPOSED)
        ]

    def accepted_rules(self, workspace_id: int) -> list[dict]:
        return [
            {"rule_id": row["id"], "description": row["description"]}
            for row in self._store.list_rules(workspace_id, status=ACCEPTED)
        ]

    # -- internals ---------------------------------------------------------

    def _known_signatures(self, workspace_id: int) -> set[str]:
        """Signatures already proposed, accepted or declined."""
        return {
            row["description"].split("|", 1)[0].strip()
            for row in self._store.list_rules(workspace_id)
        }

    def _declined_signatures(self, workspace_id: int) -> set[str]:
        return {
            row["description"].split("|", 1)[0].strip()
            for row in self._store.list_rules(workspace_id, status=DECLINED)
        }


def _signature(operation: str, call: str) -> str:
    """A stable key for "the same kind of action".

    Groups by operation and by the folder involved, not by the exact filename,
    so moving three different PDFs into Documents counts as one pattern rather
    than three unrelated events.
    """
    inside = call[call.find("(") + 1 : call.rfind(")")] if "(" in call else ""
    first = inside.split(",")[0].strip()
    folder = first.rsplit("/", 1)[0] if "/" in first else ""
    extension = first.rsplit(".", 1)[-1].lower() if "." in first else ""
    return f"{operation}:{folder}:{extension}"


def _describe(signature: str) -> str:
    """The signature as something a person would recognise."""
    operation, folder, extension = (signature.split(":", 2) + ["", ""])[:3]
    verb = {
        "move_file": "moving",
        "create_dir": "creating a folder for",
        "write_file": "writing",
    }.get(operation, operation)
    what = f"{extension.upper()} files" if extension else "files"
    where = f" in {folder}" if folder else ""
    return f"{verb} {what}{where}"


def _within(timestamp: str, cutoff: datetime) -> bool:
    try:
        when = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return False
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when >= cutoff
