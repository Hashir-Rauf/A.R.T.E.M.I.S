"""Turning text into a list of numbers, so similar text can be found by meaning.

Two embedders. The fake one needs no model, so tests never depend on a download
or a network. The ollama one talks to a model on this machine, so the text of
the user's files never leaves it.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


class EmbedError(Exception):
    pass


class Embedder:
    name = "base"

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


@dataclass
class FakeEmbedder(Embedder):
    name: str = "fake"
    size: int = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.size
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            slot = int(hashlib.sha256(word.encode()).hexdigest(), 16) % self.size
            vector[slot] += 1.0
        length = math.sqrt(sum(v * v for v in vector))
        if length == 0:
            return vector
        return [v / length for v in vector]


@dataclass
class OllamaEmbedder(Embedder):
    name: str = "ollama"
    model: str = "nomic-embed-text"
    host: str = "http://127.0.0.1:11434"
    timeout_s: float = 60.0

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": self.model, "prompt": text}).encode()
        request = urllib.request.Request(
            f"{self.host}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
            raise EmbedError(f"{self.name}: {exc}") from exc
        vector = body.get("embedding")
        if not vector:
            raise EmbedError(f"{self.name}: no embedding in the reply")
        return [float(v) for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    length_a = math.sqrt(sum(x * x for x in a))
    length_b = math.sqrt(sum(y * y for y in b))
    if length_a == 0 or length_b == 0:
        return 0.0
    return dot / (length_a * length_b)