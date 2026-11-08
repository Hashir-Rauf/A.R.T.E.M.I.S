"""Which service a typed request is sent to.

A wrong guess here costs a worse answer, never a wrong action, but the cases
below are the ones that were routed badly when every request went to the file
planner: questions were answered with the raw file, and web searches and emails
were refused as off topic.
"""

from __future__ import annotations

import pytest

from artemis.core.intent import (
    CODE,
    DRAFT,
    MAIL,
    PLAN,
    QUESTION,
    SEARCH,
    classify,
)

FILES = ["calc.py", "paper-a.txt", "paper-b.txt", "meeting-notes-oct.md", "todo.txt"]


@pytest.mark.parametrize("text, kind", [
    ("What does calc.py do?", QUESTION),
    ("calc.py gives the wrong average, can you find the bug and show me a fix?", CODE),
    ("Just fix the bug in calc.py for me", CODE),
    ("Pull together paper-a.txt and paper-b.txt into short notes and cite which file each point comes from", QUESTION),
    ("Which paper mentions an 82 percent approval rate?", QUESTION),
    ("Summarise the meeting notes", QUESTION),
    ("Search the web for python typer cli tutorial", SEARCH),
    ("google typer cli tutorial", SEARCH),
    ("Look up pandas groupby online", SEARCH),
    ("Email supervisor@example.com to say I will be late to Friday's meeting", MAIL),
    ("send supervisor@example.com a note that the draft is ready", MAIL),
    ("Draft a one page project update from my meeting notes", DRAFT),
    ("Write a short report on the survey results", DRAFT),
])
def test_requests_go_to_the_service_built_for_them(text: str, kind: str) -> None:
    assert classify(text, FILES).kind == kind


@pytest.mark.parametrize("text", [
    "Put my invoice and any pdf files into a new folder called Finance",
    "Make a folder called Archive and move the three report draft files into it",
    "Move paper-a.txt into ../PrivateStuff",
    "Tidy up this folder",
    "List the files in this folder",
    "What files do I have?",
    "Rename todo.txt to tasks.txt",
    "search my files for budget",
])
def test_file_work_still_goes_to_the_planner(text: str) -> None:
    assert classify(text, FILES).kind == PLAN


def test_a_code_question_names_the_file() -> None:
    intent = classify("calc.py gives the wrong average, show me a fix", FILES)
    assert intent.kind == CODE and intent.file == "calc.py"


def test_the_search_query_drops_the_instruction() -> None:
    assert classify("Search the web for python typer cli tutorial", FILES).query == (
        "python typer cli tutorial"
    )
    assert classify("Look up pandas groupby online", FILES).query == "pandas groupby"


def test_mail_collects_every_address() -> None:
    intent = classify("email a@x.com and b@y.org that we are done", FILES)
    assert intent.kind == MAIL and intent.recipients == ("a@x.com", "b@y.org")


def test_mail_with_no_address_is_still_mail() -> None:
    """So the interface can ask who it should go to, instead of guessing."""
    intent = classify("Email my supervisor that I will be late", FILES)
    assert intent.kind == MAIL and intent.recipients == ()


# -- conversation ---------------------------------------------------------------

from artemis.core.intent import CHAT  # noqa: E402


@pytest.mark.parametrize("text", [
    "hello",
    "thanks, that helped",
    "I am working on my final year project",
    "good morning ARTEMIS",
])
def test_ordinary_conversation_is_chat_not_a_file_task(text: str) -> None:
    assert classify(text, FILES).kind == CHAT


@pytest.mark.parametrize("text", [
    "What is the capital of France?",
    "Explain what a hash chain is",
    "How do I delete a file in Python?",
])
def test_a_general_question_is_a_question_not_a_file_task(text: str) -> None:
    """The answer service then decides whether any of the files are relevant."""
    assert classify(text, FILES).kind == QUESTION


def test_a_request_to_delete_still_reaches_the_boundary_explanation() -> None:
    assert classify("Delete todo.txt", FILES).kind == PLAN
    assert classify("Delete all the old report drafts to free space", FILES).kind == PLAN


@pytest.mark.parametrize("text", [
    "List three fruits as bullet points and make the names bold",
    "list the planets in order",
    "List some ideas for my project",
])
def test_the_word_list_alone_does_not_make_it_a_file_task(text: str) -> None:
    assert classify(text, FILES).kind != PLAN


@pytest.mark.parametrize("text", [
    "List the files in this folder",
    "list all files",
    "list my documents",
])
def test_listing_files_is_still_a_file_task(text: str) -> None:
    assert classify(text, FILES).kind == PLAN
