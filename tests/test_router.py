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

from artemis.core.providers import ModelTier, ProviderError, StubProvider
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


# -- streaming -----------------------------------------------------------------
#
# Streaming goes through the same egress gate as a blocking call. The one rule
# that differs is failover: once a piece has been handed to the caller it is on
# screen, and switching providers would splice two different answers together.


def test_stream_yields_the_pieces(store: Store, local_workspace: int) -> None:
    router = _router(store, _local(replies=["one two three"]))
    assert "".join(router.stream(local_workspace, "go")) == "one two three"


def test_stream_will_not_reach_a_cloud_model_for_a_local_only_workspace(
    store: Store, local_workspace: int
) -> None:
    """The gate is not bypassed by using the streaming path.

    A cloud provider is filtered out of the permitted tiers before egress is
    even considered, so this reports that no model is available rather than
    refusing a provider it was about to use. Either way nothing is sent.
    """
    router = _router(store, _cloud(replies=["leaked"]))
    cloud = router._providers[0] if hasattr(router, "_providers") else None
    with pytest.raises(NoModelAvailable):
        list(router.stream(local_workspace, "go"))
    if cloud is not None:
        assert cloud.calls == []


def test_stream_falls_back_before_the_first_piece(
    store: Store, cloud_workspace: int
) -> None:
    """A provider that fails before producing anything is replaced."""
    router = _router(
        store, _local(fail_with="down"), _cloud(replies=["from the cloud"])
    )
    assert "".join(router.stream(cloud_workspace, "go")) == "from the cloud"


def test_stream_does_not_fall_back_once_text_has_been_shown(
    store: Store, cloud_workspace: int
) -> None:
    """A failure after the first piece is raised, not papered over.

    Falling back here would append a second provider's answer to the half of
    the first one the user can already read.
    """

    class HalfWay(StubProvider):
        def stream(self, prompt: str, max_tokens: int = 512):
            yield "the beginning"
            raise ProviderError("died halfway")

    router = _router(
        store,
        HalfWay(name="ollama", tier=ModelTier.LOCAL, model="gemma"),
        _cloud(replies=["should not be used"]),
    )
    seen: list[str] = []
    with pytest.raises(ProviderError):
        for piece in router.stream(cloud_workspace, "go"):
            seen.append(piece)
    assert seen == ["the beginning"]


def test_stream_records_egress_in_the_audit_log(
    store: Store, cloud_workspace: int
) -> None:
    """Anything that left the machine is recorded, streamed or not."""
    router = _router(store, _cloud(replies=["hello"]))
    list(router.stream(cloud_workspace, "go"))
    events = [row["event"] for row in store.query("SELECT event FROM audit_log")]
    assert "router.egress" in events
