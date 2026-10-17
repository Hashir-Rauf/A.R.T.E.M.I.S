"""Embedders and the chunker: the two small parts under the vector index."""

from __future__ import annotations

import pytest

from artemis.core.chunking import chunk_text
from artemis.core.embedder import EmbedError, FakeEmbedder, OllamaEmbedder, cosine


def test_the_same_text_gives_the_same_vector() -> None:
    embedder = FakeEmbedder()
    assert embedder.embed("revenue grew") == embedder.embed("revenue grew")


def test_related_text_scores_higher_than_unrelated_text() -> None:
    embedder = FakeEmbedder()
    question = embedder.embed("how much did revenue grow")
    related = embedder.embed("revenue grew 10% this year")
    unrelated = embedder.embed("the cat sat on the mat")
    assert cosine(question, related) > cosine(question, unrelated)


def test_empty_text_gives_a_zero_vector_and_zero_score() -> None:
    embedder = FakeEmbedder()
    assert cosine(embedder.embed(""), embedder.embed("anything")) == 0.0


def test_an_unreachable_ollama_raises_embed_error() -> None:
    embedder = OllamaEmbedder(host="http://127.0.0.1:9", timeout_s=2)
    with pytest.raises(EmbedError):
        embedder.embed("hello")


def test_a_short_file_is_one_chunk_with_its_lines() -> None:
    chunks = chunk_text("one\ntwo\nthree")
    assert len(chunks) == 1
    assert (chunks[0].line_start, chunks[0].line_end) == (1, 3)


def test_a_long_file_is_split_and_line_numbers_follow() -> None:
    text = "\n".join(f"line number {n} " + "x" * 40 for n in range(1, 41))
    chunks = chunk_text(text, max_chars=300)
    assert len(chunks) > 1
    assert chunks[0].line_start == 1
    assert chunks[-1].line_end == 40
    for before, after in zip(chunks, chunks[1:]):
        assert after.line_start == before.line_end + 1


def test_one_very_long_line_is_split_into_pieces() -> None:
    chunks = chunk_text("y" * 2000, max_chars=800)
    assert len(chunks) == 3
    assert all(len(c.text) <= 800 for c in chunks)


def test_blank_text_gives_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("\n\n   \n") == []


def test_editing_the_last_line_changes_only_the_last_chunk_hash() -> None:
    lines = [f"line number {n} " + "x" * 40 for n in range(1, 41)]
    before = chunk_text("\n".join(lines), max_chars=300)
    lines[-1] = "a different last line"
    after = chunk_text("\n".join(lines), max_chars=300)
    assert [c.content_hash for c in before[:-1]] == [c.content_hash for c in after[:-1]]
    assert before[-1].content_hash != after[-1].content_hash