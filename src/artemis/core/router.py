"""The Model Router: which model answers, and whether it is allowed to.

Two jobs, and the second is the important one.

**Tier selection.** Providers are tried in tier order, local first, one retry
each before advancing (Architecture Section 5.1). Failover is bounded so an
unreachable chain degrades in a few seconds with an explanation, rather than
hanging while it works through every provider twice.

**Egress enforcement.** The router is the only component that knows both the
workspace's cloud policy and which tier is about to be used, so it is the only
place the two can be compared. Putting this check in the tool layer would be too
late, and putting it in the prompt would not be a check at all.

A workspace that has not opted into cloud has exactly one tier available. If the
local model is unreachable, the answer is a clear refusal, never a quiet
promotion to a cloud provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from artemis.core.providers import (
    Completion,
    ModelTier,
    Provider,
    ProviderError,
)
from artemis.data.store import Store

#: Workspace cloud_policy values, as written by the workspace manager.
LOCAL_ONLY = "local_only"
CLOUD_ALLOWED = "cloud_allowed"


class EgressRefused(Exception):
    """Raised when a request would leave a machine the user confined it to."""


class NoModelAvailable(Exception):
    """Raised when every permitted tier failed or was unreachable."""


@dataclass
class RoutingDecision:
    """Which provider answered, and what was tried on the way there."""

    completion: Completion
    attempted: tuple[str, ...] = ()
    degraded: bool = False


@dataclass
class ModelRouter:
    """Chooses a provider, enforces egress, records what left the machine."""

    store: Store
    providers: list[Provider] = field(default_factory=list)
    retries_per_tier: int = 1

    def register(self, provider: Provider) -> None:
        """Add a provider. Order is by tier, not by registration order."""
        self.providers.append(provider)
        self.providers.sort(key=lambda p: (int(p.tier), p.name))

    # -- policy ------------------------------------------------------------

    def permitted_tiers(self, workspace_id: int) -> list[Provider]:
        """The providers this workspace is allowed to use, in tier order.

        A local-only workspace gets exactly the local tier. This is the list the
        egress gate produces, and everything downstream works from it, so a
        cloud provider is not merely deprioritised for such a workspace: it is
        absent.
        """
        row = self.store.get_workspace(workspace_id)
        policy = row["cloud_policy"] if row else LOCAL_ONLY
        if policy == CLOUD_ALLOWED:
            return list(self.providers)
        return [p for p in self.providers if p.tier == ModelTier.LOCAL]

    def check_egress(self, workspace_id: int, provider: Provider) -> None:
        """Refuse if this provider would take data off a confined workspace."""
        if provider.tier == ModelTier.LOCAL:
            return
        row = self.store.get_workspace(workspace_id)
        policy = row["cloud_policy"] if row else LOCAL_ONLY
        if policy != CLOUD_ALLOWED:
            self.store.append_audit(
                event="router.egress",
                outcome="refused",
                workspace_id=workspace_id,
                detail={"provider": provider.name, "tier": int(provider.tier)},
            )
            raise EgressRefused(
                f"{provider.name} would send this workspace's content off this "
                "computer, and the workspace is set to stay local"
            )

    # -- routing -----------------------------------------------------------

    def complete(
        self, workspace_id: int, prompt: str, max_tokens: int = 512
    ) -> RoutingDecision:
        """Answer a prompt using the first permitted tier that works."""
        permitted = self.permitted_tiers(workspace_id)
        if not permitted:
            raise NoModelAvailable(
                "no model is configured for this workspace. ARTEMIS needs a "
                "local model, or permission to use a cloud one."
            )

        attempted: list[str] = []
        failures: list[str] = []

        for provider in permitted:
            self.check_egress(workspace_id, provider)

            if not provider.available():
                attempted.append(provider.name)
                failures.append(f"{provider.name}: not reachable")
                continue

            # One retry, then move on. Retrying harder does not fix an
            # unreachable service and delays the honest answer.
            for attempt in range(self.retries_per_tier + 1):
                attempted.append(provider.name)
                try:
                    completion = provider.complete(prompt, max_tokens=max_tokens)
                except ProviderError as exc:
                    failures.append(str(exc))
                    continue

                if provider.tier != ModelTier.LOCAL:
                    # Anything that left the machine is recorded, so the
                    # disclosure panel can show exactly what went where.
                    self.store.append_audit(
                        event="router.egress",
                        outcome="sent",
                        workspace_id=workspace_id,
                        detail={
                            "provider": provider.name,
                            "tier": int(provider.tier),
                            "model": provider.model,
                            "tokens_in": completion.tokens_in,
                            "tokens_out": completion.tokens_out,
                        },
                    )

                return RoutingDecision(
                    completion=completion,
                    attempted=tuple(attempted),
                    degraded=provider is not permitted[0],
                )

        self.store.append_audit(
            event="router.complete",
            outcome="failed",
            workspace_id=workspace_id,
            detail={"attempted": attempted, "failures": failures},
        )
        raise NoModelAvailable(
            "no model could answer. Tried: " + ", ".join(attempted or ["nothing"])
        )

    def describe_tiers(self, workspace_id: int) -> list[dict]:
        """What the user would see if they asked which models are in play."""
        permitted = {p.name for p in self.permitted_tiers(workspace_id)}
        return [
            {
                "name": p.name,
                "tier": int(p.tier),
                "model": p.model,
                "permitted": p.name in permitted,
                "available": p.available(),
                "leaves_machine": p.tier != ModelTier.LOCAL,
            }
            for p in self.providers
        ]
