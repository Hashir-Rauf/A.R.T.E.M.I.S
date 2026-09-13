"""The Model Router: which model answers, and whether it is allowed to.

The egress tests are the ones that matter. A local-only workspace must never
reach a cloud tier, and the interesting case is not "cloud is deprioritised" but
"the local model is down and cloud is still refused". A system that quietly
promotes to cloud when local fails would break the promise on exactly the day it
mattered.

Every test here uses stub providers. The guarantees are about what the router
refuses, and none of them should depend on a 9 GB model or a network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.providers import ModelTier, StubProvider
from artemis.core.router import (
    EgressRefused,
    ModelRouter,
    NoModelAvailable,
)
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


@pytest.fixture
def local_workspace(manager: WorkspaceManager, sandbox: Path) -> int:
    """A workspace that has not opted into cloud. The default."""
    return manager.grant(sandbox, name="Local").id


@pytest.fixture
def cloud_workspace(manager: WorkspaceManager, tmp_path: Path) -> int:
    folder = tmp_path / "cloudy"
    folder.mkdir()
    (folder / "a.txt").write_text("x", encoding="utf-8")
    return manager.grant(folder, name="Cloudy", cloud_policy="cloud_allowed").id


def _router(store: Store, *providers: StubProvider) -> ModelRouter:
    router = ModelRouter(store=store)
    for provider in providers:
        router.register(provider)
    return router


def _local(**kwargs) -> StubProvider:
    return StubProvider(name="ollama", tier=ModelTier.LOCAL, model="gemma", **kwargs)


def _cloud(**kwargs) -> StubProvider:
    return StubProvider(name="gemini", tier=ModelTier.GEMINI, model="g", **kwargs)


# -- egress --------------------------------------------------------------------


def test_a_local_only_workspace_sees_only_the_local_tier(
    store: Store, local_workspace: int
) -> None:
    router = _router(store, _local(replies=["hi"]), _cloud(replies=["hi"]))
    assert [p.name for p in router.permitted_tiers(local_workspace)] == ["ollama"]


def test_a_cloud_workspace_sees_every_tier(
    store: Store, cloud_workspace: int
) -> None:
    router = _router(store, _local(replies=["hi"]), _cloud(replies=["hi"]))
    names = [p.name for p in router.permitted_tiers(cloud_workspace)]
    assert names == ["ollama", "gemini"]


def test_local_is_preferred_even_when_cloud_is_allowed(
    store: Store, cloud_workspace: int
) -> None:
    """Local-first is the default, not a fallback."""
    router = _router(store, _local(replies=["local"]), _cloud(replies=["cloud"]))
    assert router.complete(cloud_workspace, "hello").completion.provider == "ollama"


def test_sending_a_confined_workspace_to_cloud_is_refused(
    store: Store, local_workspace: int
) -> None:
    router = _router(store, _local(replies=["hi"]), _cloud(replies=["hi"]))
    cloud = next(p for p in router.providers if p.name == "gemini")

    with pytest.raises(EgressRefused):
        router.check_egress(local_workspace, cloud)


def test_a_refused_egress_is_recorded(
    store: Store, local_workspace: int
) -> None:
    router = _router(store, _local(replies=["hi"]), _cloud(replies=["hi"]))
    cloud = next(p for p in router.providers if p.name == "gemini")

    with pytest.raises(EgressRefused):
        router.check_egress(local_workspace, cloud)

    refused = [
        row
        for row in store.list_audit()
        if row["event"] == "router.egress" and row["outcome"] == "refused"
    ]
    assert len(refused) == 1
    assert store.verify_audit_chain()


def test_a_local_only_workspace_is_not_promoted_when_local_fails(
    store: Store, local_workspace: int
) -> None:
    """The case the promise is really about."""
    cloud = _cloud(replies=["cloud answered"])
    router = _router(store, _local(fail_with="model is down"), cloud)

    with pytest.raises(NoModelAvailable):
        router.complete(local_workspace, "hello")

    assert cloud.calls == [], "a confined workspace reached a cloud provider"


def test_what_left_the_machine_is_recorded(
    store: Store, cloud_workspace: int
) -> None:
    router = _router(store, _cloud(replies=["cloud answered"]))
    router.complete(cloud_workspace, "hello")

    sent = [
        row
        for row in store.list_audit()
        if row["event"] == "router.egress" and row["outcome"] == "sent"
    ]
    assert len(sent) == 1


def test_a_local_answer_is_not_logged_as_egress(
    store: Store, local_workspace: int
) -> None:
    """Nothing left, so nothing should claim it did."""
    router = _router(store, _local(replies=["hi"]))
    router.complete(local_workspace, "hello")

    egress = [row for row in store.list_audit() if row["event"] == "router.egress"]
    assert egress == []


# -- failover ------------------------------------------------------------------


def test_failover_advances_after_one_retry(
    store: Store, cloud_workspace: int
) -> None:
    """One retry per tier, then move on. Retrying harder just delays the truth."""
    router = _router(
        store, _local(fail_with="down"), _cloud(replies=["fallback answered"])
    )
    decision = router.complete(cloud_workspace, "hello")

    assert decision.completion.provider == "gemini"
    assert decision.degraded is True
    assert decision.attempted == ("ollama", "ollama", "gemini")


def test_an_unreachable_provider_is_skipped_not_waited_on(
    store: Store, cloud_workspace: int
) -> None:
    unreachable = _local(reachable=False, replies=["never"])
    router = _router(store, unreachable, _cloud(replies=["cloud"]))

    decision = router.complete(cloud_workspace, "hello")

    assert decision.completion.provider == "gemini"
    assert unreachable.calls == []


def test_every_tier_failing_gives_a_clear_refusal(
    store: Store, cloud_workspace: int
) -> None:
    router = _router(store, _local(fail_with="down"), _cloud(fail_with="also down"))

    with pytest.raises(NoModelAvailable, match="Tried"):
        router.complete(cloud_workspace, "hello")


def test_no_providers_at_all_is_explained_not_crashed(
    store: Store, local_workspace: int
) -> None:
    router = ModelRouter(store=store)

    with pytest.raises(NoModelAvailable, match="no model is configured"):
        router.complete(local_workspace, "hello")


def test_describe_tiers_says_what_is_permitted_and_what_leaves(
    store: Store, local_workspace: int
) -> None:
    """What a user would need to answer 'where does my data go'."""
    router = _router(store, _local(replies=["hi"]), _cloud(replies=["hi"]))
    described = {row["name"]: row for row in router.describe_tiers(local_workspace)}

    assert described["ollama"]["permitted"] is True
    assert described["ollama"]["leaves_machine"] is False
    assert described["gemini"]["permitted"] is False
    assert described["gemini"]["leaves_machine"] is True
