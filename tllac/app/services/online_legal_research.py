"""
Optional online legal research helpers.

The chat flow uses this as supplemental context only. If a site is unavailable,
slow, blocked, or returns an unexpected page, the model still answers from the
base prompt and model knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urljoin
from urllib.request import Request, urlopen


logger = logging.getLogger("tllac.services.online_legal_research")

INDIA_KANOON_SEARCH_URL = "https://indiankanoon.org/search/?formInput={query}"
DEFAULT_TIMEOUT_SECONDS = 6
DEFAULT_MAX_RESULTS = 4


@dataclass(frozen=True)
class OnlineLegalResult:
    source: str
    title: str
    url: str
    snippet: str = ""


class _IndiaKanoonSearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[OnlineLegalResult] = []
        self._in_link = False
        self._current_href = ""
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        href = dict(attrs).get("href") or ""
        if re.match(r"^/doc(?:fragment)?/\d+/?", href):
            self._in_link = True
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._in_link:
            return

        title = _clean_text(" ".join(self._current_text))
        if title and self._current_href and title.lower() != "full document":
            doc_match = re.match(r"^/doc(?:fragment)?/(\d+)/?", self._current_href)
            normalized_href = f"/doc/{doc_match.group(1)}/" if doc_match else self._current_href
            url = urljoin("https://indiankanoon.org", normalized_href)
            if not any(result.url == url for result in self.results):
                self.results.append(
                    OnlineLegalResult(
                        source="IndiaKanoon",
                        title=title,
                        url=url,
                    )
                )

        self._in_link = False
        self._current_href = ""
        self._current_text = []


def _clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _online_research_enabled() -> bool:
    return os.getenv("ONLINE_LEGAL_RESEARCH_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _fetch_url(url: str, timeout_seconds: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "TLLAC-LegalResearch/1.0 (+local legal assistant)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def search_indiakanoon(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[OnlineLegalResult]:
    compact_query = _clean_text(query)
    if not compact_query:
        return []

    timeout_seconds = int(os.getenv("ONLINE_LEGAL_RESEARCH_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
    search_url = INDIA_KANOON_SEARCH_URL.format(query=quote_plus(compact_query))

    try:
        html = _fetch_url(search_url, timeout_seconds=timeout_seconds)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        logger.info("IndiaKanoon lookup skipped: %s", exc)
        return []

    parser = _IndiaKanoonSearchParser()
    parser.feed(html)
    return parser.results[:max_results]


def build_online_legal_research_context(query: str) -> str:
    """
    Return compact online legal research context for the model prompt.
    """
    if not _online_research_enabled():
        return ""

    max_results = int(os.getenv("ONLINE_LEGAL_RESEARCH_MAX_RESULTS", str(DEFAULT_MAX_RESULTS)))
    results = search_indiakanoon(query, max_results=max_results)
    if not results:
        return ""

    lines = [
        "Supplemental online legal research context:",
        "Use this only as a lead for better legal reasoning. Do not quote it as final authority unless the result itself supports the point.",
        "Verify legal propositions from statutes, binding judgments, and current Indian procedure before relying on them.",
        "",
        "IndiaKanoon search results:",
    ]
    for index, result in enumerate(results, start=1):
        lines.append(f"{index}. {result.title} - {result.url}")
        if result.snippet:
            lines.append(f"   Snippet: {result.snippet}")

    return "\n".join(lines)
