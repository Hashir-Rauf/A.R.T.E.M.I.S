"""Model providers: the tiers the router chooses between.

A provider is a thin, uniform wrapper around one way of reaching a model. The
router treats providers as configuration rather than as branches, which is what
lets a new endpoint (Grok, Kimi, DeepSeek, a self-hosted vLLM) be registered
without touching routing logic (Architecture Section 5.1).

Every provider answers three questions: what tier am I, am I reachable right
now, and here is a prompt, what do you say. Nothing here knows about workspaces,
egress policy or approval. That separation matters: a provider must not be able
to decide it is allowed to run, because then the egress gate would live in the
component with the least context about the user's choices.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum


class ModelTier(IntEnum):
    """Ordered by how far the user's data travels.

    Tier 0 stays on the machine. Everything above it leaves, which is why the
    numbers are ordered rather than named: the router walks them upward and the
    egress gate only has to ask whether the chosen tier is greater than zero.
    """

    LOCAL = 0
    GEMINI = 1
    OPENAI = 2
    ANTHROPIC = 3
    CUSTOM = 4


class ProviderError(Exception):
    """A provider could not answer. The router treats this as a failed tier."""


@dataclass(frozen=True)
class Completion:
    """What a provider returned, with enough detail to audit the call."""

    text: str
    provider: str
    tier: ModelTier
    latency_s: float
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class Provider(ABC):
    """One way of reaching a model."""

    name: str
    tier: ModelTier
    model: str
    timeout_s: float = 120.0

    @abstractmethod
    def available(self) -> bool:
        """Whether this provider can be reached right now.

        Called before routing to it, so an unreachable tier is skipped rather
        than waited on. Must never raise: an unavailable provider is a normal
        condition, not an error.
        """

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 512) -> Completion:
        """Send a prompt and return the answer, or raise ProviderError."""


@dataclass
class OllamaProvider(Provider):
    """A model running on this machine, through Ollama.

    Tier 0 and the default. The only provider where "the data never leaves"
    is true by construction rather than by policy.
    """

    name: str = "ollama"
    tier: ModelTier = ModelTier.LOCAL
    model: str = "gemma4:e4b"
    host: str = "http://127.0.0.1:11434"
    timeout_s: float = 180.0

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=4) as response:
                tags = json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            return False
        names = {m.get("name", "") for m in tags.get("models", [])}
        return self.model in names

    def installed_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=4) as response:
                tags = json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            return []
        return sorted(m.get("name", "") for m in tags.get("models", []))

    def complete(self, prompt: str, max_tokens: int = 512) -> Completion:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.1},
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
            raise ProviderError(f"{self.name}: {exc}") from exc
        return Completion(
            text=body.get("response", ""),
            provider=self.name,
            tier=self.tier,
            latency_s=time.time() - started,
            tokens_in=body.get("prompt_eval_count", 0) or 0,
            tokens_out=body.get("eval_count", 0) or 0,
        )

    def warm(self) -> bool:
        """Load the model into memory without asking it for anything.

        Worth doing because the first call after a cold start pays the whole
        load cost. Ollama keeps a model resident for a few minutes after use,
        so warming before the user's first request moves that wait off the
        interactive path (Architecture Section 10.2).
        """
        payload = json.dumps({"model": self.model, "prompt": "", "stream": False}).encode()
        request = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s):
                return True
        except (urllib.error.URLError, OSError, TimeoutError):
            return False


@dataclass
class OpenAICompatibleProvider(Provider):
    """Any endpoint speaking the OpenAI chat-completions shape.

    Covers OpenAI itself and every service that copied its API, which is most
    of them. Registering Grok, Kimi, DeepSeek or a self-hosted vLLM is a config
    entry rather than a code change, which is the point of routing by tier
    instead of by vendor.

    The API key is passed in by the caller. This class never reads it from the
    environment or from disk, so a provider cannot quietly acquire credentials
    the user did not hand it.
    """

    name: str = "openai"
    tier: ModelTier = ModelTier.OPENAI
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    timeout_s: float = 60.0

    def available(self) -> bool:
        # Availability is a local question: do we have what we need to try.
        # Reaching out to check would itself be egress, which the router has
        # not yet authorised at this point.
        return bool(self.api_key)

    def complete(self, prompt: str, max_tokens: int = 512) -> Completion:
        if not self.api_key:
            raise ProviderError(f"{self.name}: no API key configured")
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.1,
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
            raise ProviderError(f"{self.name}: {exc}") from exc

        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"{self.name}: unexpected response shape") from exc

        usage = body.get("usage", {})
        return Completion(
            text=text,
            provider=self.name,
            tier=self.tier,
            latency_s=time.time() - started,
            tokens_in=usage.get("prompt_tokens", 0) or 0,
            tokens_out=usage.get("completion_tokens", 0) or 0,
        )


@dataclass
class StubProvider(Provider):
    """A provider that answers from a script, for tests.

    Exists so the routing rules, the egress gate and the planner can be tested
    without a model. Every guarantee this sprint makes is about what the system
    refuses to do, and none of those tests should depend on a 9 GB download or
    on a network.
    """

    name: str = "stub"
    tier: ModelTier = ModelTier.LOCAL
    model: str = "stub"
    replies: list[str] = field(default_factory=list)
    reachable: bool = True
    fail_with: str | None = None
    calls: list[str] = field(default_factory=list)

    def available(self) -> bool:
        return self.reachable

    def complete(self, prompt: str, max_tokens: int = 512) -> Completion:
        self.calls.append(prompt)
        if self.fail_with:
            raise ProviderError(f"{self.name}: {self.fail_with}")
        text = self.replies.pop(0) if self.replies else ""
        return Completion(
            text=text,
            provider=self.name,
            tier=self.tier,
            latency_s=0.0,
            tokens_in=len(prompt.split()),
            tokens_out=len(text.split()),
        )
