"""The stage gate: a claim with no real source is shown as unsupported.

The model writes an answer and cites the numbered chunks it was given, like [1].
This checks each claim against the chunks that were really sent. A claim is
supported only if it cites a chunk that exists and came from a workspace file.
Anything else is labelled unsupported, so it never reads as fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from artemis.core.context import AssembledContext, Provenance

CITATION = re.compile(r"\[(\d+)\]")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?!\[\d)")


@dataclass(frozen=True)
class Claim:
    text: str
    sources: tuple[str, ...]

    @property
    def supported(self) -> bool:
        return len(self.sources) > 0

    def render(self) -> str:
        if self.supported:
            return f"{self.text} ({', '.join(self.sources)})"
        return f"[unsupported] {self.text}"


def split_claims(answer: str) -> list[str]:
    claims = []
    for line in answer.splitlines():
        for part in SENTENCE_END.split(line):
            part = part.strip()
            if part:
                claims.append(part)
    return claims


def check_answer(answer: str, context: AssembledContext) -> list[Claim]:
    results = []
    for claim in split_claims(answer):
        sources = []
        for number in CITATION.findall(claim):
            index = int(number) - 1
            if index < 0 or index >= len(context.chunks):
                continue
            chunk = context.chunks[index]
            if chunk.provenance is Provenance.WORKSPACE_FILE:
                sources.append(chunk.citation())
        text = CITATION.sub("", claim).strip()
        results.append(Claim(text, tuple(sources)))
    return results


def render_answer(claims: list[Claim]) -> str:
    return "\n".join(c.render() for c in claims)


