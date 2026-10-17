"""F6: Web search.

Runs only when the user explicitly asks (FR-25). There is no background
browsing: nothing in this module runs on a timer or on its own.

Searching leaves the computer, so the call is T2 and always needs approval.
Every query is recorded in the audit log (Architecture Table 6.2, F6).
Results come back tagged `web`, the least trusted provenance, so text on a
web page can be read by the planner but can never give it an order.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from artemis.core.actions import Plan, ToolCall
from artemis.core.context import Chunk, Provenance
from artemis.data.store import Store

MAX_QUERY_CHARS = 300
MAX_RESULTS = 8


class SearchError(ValueError):
    """The search could not be run, or the query was not acceptable."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""


class SearchProvider(ABC):
    name: str = "provider"

    @abstractmethod
    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Return results, or raise SearchError."""


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo's HTML page. Needs no API key.

    It reads a web page rather than an official API, so it can break if the
    page layout changes. Swap in another SearchProvider if that happens.
    """

    name = "duckduckgo"
    URL = "https://html.duckduckgo.com/html/"

    def __init__(self, timeout_s: float = 15.0) -> None:
        self._timeout = timeout_s

    def search(self, query: str, limit: int) -> list[SearchResult]:
        data = urllib.parse.urlencode({"q": query}).encode()
        request = urllib.request.Request(
            self.URL, data=data, headers={"User-Agent": "Mozilla/5.0 ARTEMIS"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                page = response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise SearchError(f"{self.name}: {exc}") from exc
        return _parse_duckduckgo(page)[:limit]


def _strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _parse_duckduckgo(page: str) -> list[SearchResult]:
    results: list[SearchResult] = []
    for chunk in page.split('class="result__a"')[1:]:
        href = re.search(r'href="([^"]+)"', chunk)
        title = re.search(r">(.*?)</a>", chunk, re.S)
        if not href or not title:
            continue
        link = html.unescape(href.group(1))
        if "uddg=" in link:
            link = urllib.parse.unquote(link.split("uddg=", 1)[1].split("&", 1)[0])
        elif link.startswith("//"):
            link = "https:" + link
        snippet = re.search(r'result__snippet[^>]*>(.*?)</a>', chunk, re.S)
        results.append(
            SearchResult(
                title=_strip_tags(title.group(1)),
                url=link,
                snippet=_strip_tags(snippet.group(1)) if snippet else "",
            )
        )
    return results


@dataclass
class StubSearchProvider(SearchProvider):
    """For tests: answers from a fixed list and never touches the network."""

    name: str = "stub"
    results: list[SearchResult] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)

    def search(self, query: str, limit: int) -> list[SearchResult]:
        self.queries.append(query)
        return self.results[:limit]


class SearchService:
    def __init__(self, store: Store, provider: SearchProvider) -> None:
        self._store = store
        self._provider = provider

    @staticmethod
    def clean_query(query: str) -> str:
        cleaned = " ".join(query.split())
        if not cleaned:
            raise SearchError("the search query is empty")
        if len(cleaned) > MAX_QUERY_CHARS:
            raise SearchError(f"the search query is longer than {MAX_QUERY_CHARS} characters")
        return cleaned

    def propose(self, workspace_id: int, query: str) -> Plan:
        """A plan holding one web_search call. It does not search."""
        cleaned = self.clean_query(query)
        call = ToolCall("web_search", workspace_id, (), {"query": cleaned})
        return Plan(calls=(call,), intent=f"Search the web for: {cleaned}")

    def run(self, workspace_id: int, query: str, limit: int = 5) -> list[SearchResult]:
        """Do the search. Called only by the dispatcher, after approval."""
        cleaned = self.clean_query(query)
        limit = max(1, min(int(limit), MAX_RESULTS))
        try:
            results = self._provider.search(cleaned, limit)
        except SearchError as exc:
            self._store.append_audit(
                event="web.search",
                outcome="failed",
                workspace_id=workspace_id,
                detail={"query": cleaned, "error": str(exc)},
            )
            raise
        self._store.append_audit(
            event="web.search",
            outcome="sent",
            workspace_id=workspace_id,
            detail={"query": cleaned, "provider": self._provider.name, "results": len(results)},
        )
        return results

    @staticmethod
    def to_chunks(results: list[SearchResult]) -> list[Chunk]:
        """Results as context chunks, tagged `web` so they are data only."""
        return [
            Chunk(
                text=f"{r.title}\n{r.snippet}",
                provenance=Provenance.WEB,
                workspace_id=None,
                source=r.url,
                score=1.0 - index * 0.1,
            )
            for index, r in enumerate(results)
        ]