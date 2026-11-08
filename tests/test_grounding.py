"""The stage gate: a claim without a real source renders as unsupported."""

from __future__ import annotations

from artemis.core.context import AssembledContext, Chunk, Provenance
from artemis.core.grounding import check_answer, render_answer


def make_context() -> AssembledContext:
    return AssembledContext(
        chunks=(
            Chunk("summarise my notes", Provenance.USER),
            Chunk("revenue grew 10%", Provenance.WORKSPACE_FILE, 1, "report.md", 4),
        )
    )


def test_a_claim_citing_a_real_file_chunk_is_supported() -> None:
    claims = check_answer("Revenue grew 10% [2].", make_context())
    assert claims[0].supported
    assert claims[0].sources == ("report.md:4",)


def test_a_claim_with_no_citation_is_unsupported() -> None:
    claims = check_answer("The CEO resigned in March.", make_context())
    assert not claims[0].supported


def test_a_citation_to_a_chunk_that_was_not_sent_is_unsupported() -> None:
    claims = check_answer("Revenue grew 10% [9].", make_context())
    assert not claims[0].supported


def test_the_users_own_words_do_not_count_as_a_source() -> None:
    claims = check_answer("Revenue grew 10% [1].", make_context())
    assert not claims[0].supported


def test_an_unsupported_claim_is_labelled_in_the_output() -> None:
    answer = "Revenue grew 10% [2].\nThe CEO resigned in March."
    text = render_answer(check_answer(answer, make_context()))
    assert "[unsupported] The CEO resigned in March." in text
    assert "[unsupported] Revenue" not in text

# -- wording of the checked claims ----------------------------------------------


def test_et_al_does_not_split_a_claim_in_two() -> None:
    """The first half had no citation and was wrongly labelled unsupported."""
    from artemis.core.grounding import split_claims

    claims = split_claims("Takerngsaksiri et al. (2025) report an 82 percent approval rate [3].")
    assert len(claims) == 1


def test_a_removed_citation_leaves_no_stray_space_before_the_full_stop() -> None:
    from artemis.core.context import AssembledContext, Chunk, Provenance
    from artemis.core.grounding import check_answer

    chunk = Chunk(text="x", provenance=Provenance.WORKSPACE_FILE, workspace_id=1, source="a.txt")
    context = AssembledContext(chunks=(chunk,))
    claims = check_answer("It takes fifteen minutes [1].", context)
    assert claims[0].text == "It takes fifteen minutes."
