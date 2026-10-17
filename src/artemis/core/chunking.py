"""Cutting a file's text into pieces small enough to search and cite.

Each piece remembers which lines it came from, so an answer can point to
notes/a.md:12 and not just to the file. Each piece also has a hash of its text,
so when a file changes only the pieces whose text changed need embedding again.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

MAX_CHARS = 800


@dataclass(frozen=True)
class TextChunk:
    text: str
    line_start: int
    line_end: int
    content_hash: str


def add_chunk(chunks: list[TextChunk], lines: list[str], start: int, end: int) -> None:
    body = "\n".join(lines)
    if not body.strip():
        return
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    chunks.append(TextChunk(body, start, end, digest))


def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current: list[str] = []
    start = 1
    last = 1
    size = 0

    for number, line in enumerate(text.splitlines(), start=1):
        pieces = [line[i : i + max_chars] for i in range(0, len(line), max_chars)] or [""]
        for piece in pieces:
            if current and size + len(piece) + 1 > max_chars:
                add_chunk(chunks, current, start, last)
                current = []
                size = 0
            if not current:
                start = number
            current.append(piece)
            size += len(piece) + 1
            last = number

    if current:
        add_chunk(chunks, current, start, last)
    return chunks