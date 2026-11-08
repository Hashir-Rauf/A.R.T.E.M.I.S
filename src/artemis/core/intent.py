"""What kind of request did the user type?

Most of what people type into ARTEMIS is not "arrange these files". It is a
question about their documents, a request to fix a bug, to draft something, to
send an email, or to look something up. Each of those has a service built for
it. Without this step every one of them went to the file planner, which can only
list, read and move files, so a question about a file came back as the raw text
of the file.

This is plain rule-matching on purpose. It is cheap, instant and predictable,
and it only chooses *which* service handles the request. Every service still
works inside the same boundary and the same approval gate, so a wrong guess here
costs a worse answer, never a wrong action.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

PLAN = "plan"
QUESTION = "question"
CODE = "code"
DRAFT = "draft"
MAIL = "mail"
SEARCH = "search"

CODE_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".sql", ".sh", ".ps1",
    ".html", ".css", ".json", ".yaml", ".yml", ".toml",
})

_ADDRESS = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

#: Wording that means "change this code", as opposed to "tell me about it".
_FIX_WORDS = re.compile(
    r"\b(fix|bug|buggy|wrong|incorrect|error|broken|doesn'?t work|does not work|"
    r"not working|refactor|improve|rewrite|patch|diff|correct|repair|"
    r"gives the wrong|returns the wrong|off by)\b",
    re.IGNORECASE,
)

#: A request about the files themselves, which the planner already handles well.
_FILE_TASKS = re.compile(
    r"\b(move|put|copy|rename|tidy|organi[sz]e|sort|group|create a folder|"
    r"make a folder|new folder|list|how many files|what files|files do i have|"
    r"what'?s in|what is in|show me (the )?files|undo)\b",
    re.IGNORECASE,
)

_QUESTION_START = re.compile(
    r"^(what|who|when|where|which|why|how|is|are|was|were|does|do|did|can you tell|"
    r"could you tell|tell me|explain|summari[sz]e|summary of|describe|compare|"
    r"find out|show me what|pull together|combine|put together|synthesi[sz]e|"
    r"give me (a |the )?(summary|notes|overview)|make (short )?notes|take notes)\b",
    re.IGNORECASE,
)

_NOTES_WORDS = re.compile(
    r"\b(cite|citation|citations|sources?|cited notes|pull together|"
    r"synthesi[sz]e|notes from|notes across)\b",
    re.IGNORECASE,
)

_DRAFT = re.compile(
    r"^(please )?(draft|compose|write( me)?( up)?|create|make|produce)\b"
    r".*\b(draft|document|report|letter|summary|outline|update|essay|proposal|"
    r"memo|readme|page|article|abstract|agenda|minutes|plan)\b",
    re.IGNORECASE,
)

_SEARCH_WEB = re.compile(
    r"^(please )?(search|look up|look for|find|research|google)\b.*"
    r"\b(the web|the internet|online|google|duckduckgo|on the net)\b",
    re.IGNORECASE,
)
_GOOGLE = re.compile(r"^(please )?google\b", re.IGNORECASE)


@dataclass(frozen=True)
class Intent:
    kind: str
    text: str
    #: The workspace file the request names, for code questions.
    file: str | None = None
    #: Email addresses found in the request.
    recipients: tuple[str, ...] = ()
    #: The cleaned web query, for searches.
    query: str = ""


def _named_file(text: str, files: list[str]) -> str | None:
    """The workspace file the request mentions by name, if any.

    Matches the whole file name, or the name without its extension when that is
    unambiguous, and prefers the longest match so "utils_test.py" beats "utils.py".
    """
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for rel in files:
        name = PurePosixPath(rel).name.lower()
        if name and name in lowered:
            if best is None or len(name) > best[0]:
                best = (len(name), rel)
    return best[1] if best else None


def _web_query(text: str) -> str:
    """Strip the instruction off a search request, leaving what to look for."""
    cleaned = re.sub(r"^(please )?", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(search|look up|look for|find|research|google)\s+"
        r"(the web|the internet|online|on the net|google|duckduckgo)?\s*"
        r"(for|about|on)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s+(on the web|on the internet|online|on google)\s*$", "", cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" .?!\"'") or text.strip()


def classify(text: str, files: list[str] | None = None) -> Intent:
    """Decide which service should handle this request."""
    files = files or []
    stripped = (text or "").strip()
    lowered = stripped.lower()
    addresses = tuple(dict.fromkeys(_ADDRESS.findall(stripped)))

    # Email. An address, or the word "email" used as a verb at the start.
    if re.match(r"^(please )?(e-?mail|send an? e-?mail|send a message|write an? e-?mail)\b", lowered) or (
        addresses and re.search(r"\b(e-?mail|send|tell|let|notify|message|write to)\b", lowered)
    ):
        return Intent(MAIL, stripped, recipients=addresses)

    if _SEARCH_WEB.match(stripped) or _GOOGLE.match(stripped):
        return Intent(SEARCH, stripped, query=_web_query(stripped))

    if _DRAFT.match(stripped) and not _FILE_TASKS.search(lowered):
        return Intent(DRAFT, stripped)

    named = _named_file(stripped, files)
    if named is not None and PurePosixPath(named).suffix.lower() in CODE_EXTENSIONS:
        if _FIX_WORDS.search(stripped):
            return Intent(CODE, stripped, file=named)
        if _QUESTION_START.match(stripped) or "?" in stripped:
            return Intent(QUESTION, stripped, file=named)

    if _FILE_TASKS.search(lowered) and not _NOTES_WORDS.search(lowered):
        return Intent(PLAN, stripped)

    if _QUESTION_START.match(stripped) or _NOTES_WORDS.search(stripped):
        return Intent(QUESTION, stripped, file=named)

    if stripped.endswith("?"):
        return Intent(QUESTION, stripped, file=named)

    return Intent(PLAN, stripped)
