"""
Local, deterministic legal retrieval for chat grounding.

This service does not call any external APIs or models. It loads a compact
statute corpus and curated case-law corpus into memory and returns a small,
prompt-ready context block when retrieval confidence is adequate.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
from threading import Lock

from dotenv import load_dotenv

from .legal_framework import classify_domains
from .legal_corpus_index import CorpusSearchHit, LegalCorpusIndex, _build_query_filters


_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / "tllac" / ".env")

_STATUTES_PATH = _REPO_ROOT / "tllac" / "app" / "data" / "statute_sections.json"
_CASE_LAW_PATH = _REPO_ROOT / "tllac" / "app" / "data" / "case_law_corpus.json"
_DEFAULT_CORPUS_INDEX_PATH = _REPO_ROOT / "tllac" / "app" / "data" / "legal_corpus.sqlite3"
logger = logging.getLogger(__name__)
_WARNED_CORPUS_PATHS: set[str] = set()
_CORPUS_WARNING_LOCK = Lock()

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_SECTION_PATTERN = re.compile(r"\b(?:section|sec\.?|s\.)\s*(\d+[a-z]?(?:\(\d+\))?)\b", re.I)
_ARTICLE_PATTERN = re.compile(r"\b(?:article|art\.?)\s*(\d+[a-z]?(?:\(\d+\))?)\b", re.I)
_CASE_CITATION_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9.&'() -]{1,120}\s+v\.?\s+[A-Z][A-Za-z0-9.&'() -]{1,120})\b")
_ACT_ALIASES = {
    "bns": ("bns", "bharatiya nyaya sanhita", "bharatiya nyay sanhita", "ipc"),
    "bnss": ("bnss", "bharatiya nagarik suraksha sanhita", "crpc"),
    "bsa": ("bsa", "bharatiya sakshya adhiniyam", "bharatiya sakshya", "indian evidence act"),
    "constitution": ("constitution", "articles of the constitution", "article"),
    "contract": ("contract", "contract act", "indian contract act"),
    "mva": ("motor vehicles act", "motor vehicle act", "mva"),
    "cpc": ("cpc", "civil procedure code", "code of civil procedure"),
    "cpa": ("consumer protection act", "consumer act"),
    "ita": ("information technology act", "it act", "cyber law"),
}


@dataclass(frozen=True)
class RetrievedAuthority:
    authority_type: str
    title: str
    reference: str
    summary: str
    score: float
    source_file: str
    act_key: str = ""
    verified: bool = True


@dataclass(frozen=True)
class LegalRagResult:
    query: str
    statute_matches: tuple[RetrievedAuthority, ...]
    case_matches: tuple[RetrievedAuthority, ...]
    confidence: float = 0.0
    grounded: bool = False


@dataclass(frozen=True)
class LegalQueryAnalysis:
    query: str
    normalized_query: str
    tokens: frozenset[str]
    act_keys: frozenset[str]
    section_numbers: frozenset[str]
    article_numbers: frozenset[str]
    case_titles: frozenset[str]


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return max(0, int(value))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def normalize_legal_rag_query(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip())


def _normalize_reference_value(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def _tokenize(value: str) -> set[str]:
    raw_tokens = _TOKEN_PATTERN.findall(_normalize_text(value))
    normalized_tokens: set[str] = set()
    for token in raw_tokens:
        normalized_tokens.add(token)
        if token.endswith("ies") and len(token) > 4:
            normalized_tokens.add(f"{token[:-3]}y")
        elif token.endswith("s") and len(token) > 4:
            normalized_tokens.add(token[:-1])
    return normalized_tokens


def _extract_section_terms(query: str) -> set[str]:
    direct_matches = {match.group(1).lower() for match in _SECTION_PATTERN.finditer(query or "")}
    numeric_matches = set(re.findall(r"\b\d+[a-z]?(?:\(\d+\))?\b", (query or "").lower()))
    return direct_matches | numeric_matches


def _extract_article_terms(query: str) -> set[str]:
    direct_matches = {match.group(1).lower() for match in _ARTICLE_PATTERN.finditer(query or "")}
    return direct_matches


def _extract_act_keys(query: str) -> set[str]:
    lowered = _normalize_text(query)
    matches: set[str] = set()
    for act_key, aliases in _ACT_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            matches.add(act_key)
    return matches


def _extract_case_titles(query: str) -> set[str]:
    titles: set[str] = set()
    for match in _CASE_CITATION_PATTERN.finditer(query or ""):
        titles.add(_normalize_reference_value(match.group(1)))
    return titles


def analyze_legal_query(query: str) -> LegalQueryAnalysis:
    normalized = normalize_legal_rag_query(query)
    return LegalQueryAnalysis(
        query=normalized,
        normalized_query=_normalize_text(normalized),
        tokens=frozenset(_tokenize(normalized)),
        act_keys=frozenset(_extract_act_keys(normalized)),
        section_numbers=frozenset(_extract_section_terms(normalized)),
        article_numbers=frozenset(_extract_article_terms(normalized)),
        case_titles=frozenset(_extract_case_titles(normalized)),
    )


def _split_section_base(section_value: str) -> tuple[str, str]:
    normalized = _normalize_text(section_value)
    if not normalized:
        return ("", "")
    match = re.match(r"^(\d+[a-z]?)(\(\d+\))?$", normalized)
    if not match:
        return (normalized, "")
    return (match.group(1), match.group(2) or "")


def _section_match_score(section_number: str, section_terms: set[str]) -> tuple[float, bool]:
    if not section_terms or not section_number:
        return (0.0, False)

    normalized_section = _normalize_text(section_number)
    base_section, suffix_section = _split_section_base(normalized_section)
    best_score = 0.0

    for raw_term in section_terms:
        normalized_term = _normalize_text(raw_term)
        if normalized_term == normalized_section:
            return (18.0, True)

        base_term, suffix_term = _split_section_base(normalized_term)
        if not base_term or base_term != base_section:
            continue

        if suffix_term and suffix_section and suffix_term == suffix_section:
            return (18.0, True)

        if suffix_term or suffix_section:
            best_score = max(best_score, 12.0)
        else:
            best_score = max(best_score, 14.0)

    return (best_score, best_score > 0.0)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _preferred_section_numbers(query_text: str) -> set[str]:
    preferred: set[str] = set()
    motor_accident_query = _contains_any(
        query_text,
        ("accident", "drunk driver", "drink and drive", "rash driving", "negligent driving", "hit my", "hit me"),
    )
    if motor_accident_query:
        preferred.add("281")
        if _contains_any(query_text, ("death", "died", "killed", "fatal")):
            preferred.add("106")
    return preferred


def _false_case_query(query_text: str) -> bool:
    return _contains_any(
        query_text,
        (
            "false case",
            "false complaint",
            "false dowry",
            "false allegation",
            "false fir",
            "wrong complaint",
            "fake case",
            "threatening to file",
        ),
    )


def _extract_supported_citations(text: str) -> tuple[set[str], set[str]]:
    sections = {match.group(1).lower() for match in _SECTION_PATTERN.finditer(text or "")}
    articles = {match.group(1).lower() for match in _ARTICLE_PATTERN.finditer(text or "")}
    return sections, articles


def _reference_supports_statute(item: RetrievedAuthority, analysis: LegalQueryAnalysis) -> bool:
    reference_text = _normalize_text(" ".join((item.title, item.reference, item.summary, item.source_file)))
    if analysis.act_keys and item.act_key and item.act_key not in analysis.act_keys:
        return False
    if analysis.section_numbers:
        if any(section in reference_text for section in analysis.section_numbers):
            return True
        if item.reference and any(section in _normalize_reference_value(item.reference) for section in analysis.section_numbers):
            return True
        if item.summary and any(section in _normalize_reference_value(item.summary) for section in analysis.section_numbers):
            return True
    if analysis.article_numbers and any(article in reference_text for article in analysis.article_numbers):
        return True
    if analysis.act_keys:
        return any(alias in reference_text for alias in analysis.act_keys)
    return True


def _reference_supports_case(item: RetrievedAuthority, analysis: LegalQueryAnalysis) -> bool:
    title = _normalize_reference_value(item.title)
    if analysis.case_titles and title not in analysis.case_titles:
        return False
    return True


def _dedupe_authorities(items: list[RetrievedAuthority]) -> list[RetrievedAuthority]:
    deduped: list[RetrievedAuthority] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (_normalize_text(item.authority_type), _normalize_text(item.title), _normalize_text(item.reference))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _rerank_authorities(items: list[RetrievedAuthority], analysis: LegalQueryAnalysis) -> list[RetrievedAuthority]:
    def score_item(item: RetrievedAuthority) -> tuple[float, float, float, str, str]:
        normalized_title = _normalize_text(item.title)
        normalized_reference = _normalize_text(item.reference)
        exact_section = any(section in normalized_reference for section in analysis.section_numbers)
        exact_article = any(article in normalized_reference for article in analysis.article_numbers)
        exact_act = bool(analysis.act_keys) and item.act_key in analysis.act_keys
        support_score = 0.0
        if exact_section:
            support_score += 15.0
        if exact_article:
            support_score += 12.0
        if exact_act:
            support_score += 8.0
        if analysis.case_titles and normalized_title in analysis.case_titles:
            support_score += 12.0
        if analysis.tokens:
            title_overlap = len(analysis.tokens & set(_tokenize(item.title)))
            summary_overlap = len(analysis.tokens & set(_tokenize(item.summary)))
            support_score += min(6.0, float(title_overlap) * 1.75)
            support_score += min(4.0, float(summary_overlap) * 0.75)
        if item.verified:
            support_score += 2.0
        support_score += min(4.0, item.score / 5.0)
        return (-support_score, -item.score, 0.0 if item.verified else 1.0, item.title.lower(), item.reference.lower())

    return sorted(items, key=score_item)


def _compute_confidence(statute_matches: list[RetrievedAuthority], case_matches: list[RetrievedAuthority], analysis: LegalQueryAnalysis) -> float:
    all_matches = statute_matches + case_matches
    if not all_matches:
        return 0.0

    top_score = max(item.score for item in all_matches)
    supporting_chunks = len(all_matches)
    exact_section_support = any(
        any(section in _normalize_text(f"{item.reference} {item.summary}") for section in analysis.section_numbers)
        for item in statute_matches
    )
    exact_article_support = any(
        any(article in _normalize_text(f"{item.reference} {item.summary}") for article in analysis.article_numbers)
        for item in statute_matches
    )
    exact_case_support = bool(analysis.case_titles) and any(
        _normalize_reference_value(item.title) in analysis.case_titles for item in case_matches
    )

    score = min(1.0, top_score / 18.0) * 0.45
    score += min(1.0, supporting_chunks / 3.0) * 0.2
    score += 0.2 if (exact_section_support or exact_article_support or exact_case_support) else 0.0
    if statute_matches and case_matches:
        score += 0.05
    if any(not item.verified for item in all_matches):
        score -= 0.1
    return max(0.0, min(1.0, score))


def _apply_contextual_statute_boosts(
    *,
    query_text: str,
    item: dict[str, object],
    item_text: str,
) -> float:
    score = 0.0
    act_key = str(item.get("_act_key") or "")
    title_text = _normalize_text(str(item.get("title") or ""))
    section_number = str(item.get("_section_number") or "")
    false_case_query = _false_case_query(query_text)
    dowry_query = "dowry" in query_text
    threat_query = _contains_any(query_text, ("threat", "threaten", "threatening"))
    arrest_or_bail_query = _contains_any(query_text, ("arrest", "bail", "anticipatory bail"))
    evidence_query = _contains_any(
        query_text,
        ("evidence", "proof", "message", "chat", "whatsapp", "recording", "screenshot", "document"),
    )

    if false_case_query:
        if act_key == "bns":
            if "false charge of offence made with intent to injure" in title_text:
                score += 16.0
            if "false information" in title_text:
                score += 13.0
            if "criminal intimidation" in title_text:
                score += 8.0
            if "defamation" in title_text:
                score += 6.0
            if dowry_query and "dowry death" in title_text:
                score -= 8.0
        elif act_key == "bnss":
            if "direction for grant of bail to person apprehending arrest" in title_text:
                score += 10.0
            if "when police may arrest without warrant" in title_text:
                score += 8.0
            if "person arrested to be taken before magistrate" in title_text:
                score += 5.0
        elif act_key == "bsa":
            if section_number == "57":
                score += 5.0
            if section_number == "58":
                score += 7.0
            if section_number == "60":
                score += 8.0
            if "presumption as to documents produced as record of evidence" in title_text:
                score -= 5.0

    if threat_query and act_key == "bns" and "criminal intimidation" in item_text:
        score += 4.0

    if arrest_or_bail_query and act_key == "bnss":
        if section_number == "482":
            score += 6.0
        if section_number == "35":
            score += 5.0

    if evidence_query and act_key == "bsa":
        if section_number in {"57", "58", "60"}:
            score += 4.0

    return score


def _truncate_text(value: str, max_length: int) -> str:
    compact = re.sub(r"\s+", " ", (value or "").strip())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 3].rstrip()}..."


def _build_domain_hint_tokens(query: str) -> set[str]:
    hints: set[str] = set()
    for mapping in classify_domains(query):
        hints.update(_tokenize(mapping.domain))
        hints.update(_tokenize(mapping.first_bucket))
        for statute in mapping.statutes:
            hints.update(_tokenize(statute))
    return hints


def _corpus_index_path() -> Path:
    configured = os.getenv("LEGAL_RAG_INDEX_PATH", "").strip()
    return Path(configured).expanduser() if configured else _DEFAULT_CORPUS_INDEX_PATH


def _warn_corpus_once(path: Path, message: str) -> None:
    key = f"{path.resolve()}:{message}"
    with _CORPUS_WARNING_LOCK:
        if key in _WARNED_CORPUS_PATHS:
            return
        _WARNED_CORPUS_PATHS.add(key)
    logger.warning("Legal JSON corpus unavailable (%s): %s. Using curated corpus only.", path, message)


def _infer_act_key(title: str) -> str:
    normalized = _normalize_text(title)
    for act_key, aliases in _ACT_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return act_key
    return ""


def _corpus_reference(hit: CorpusSearchHit, query: str) -> str:
    if hit.authority_type == "case":
        court_year = " ".join(part for part in (hit.court, f"({hit.year})" if hit.year else "") if part).strip()
        location = f"p. {hit.page_number}" if hit.page_number else hit.chunk_id
        return ", ".join(part for part in (court_year, location) if part)

    section = hit.section.strip()
    if section and section.lower() != "general":
        return section
    requested_sections = sorted(_extract_section_terms(query))
    requested_articles = sorted(_extract_article_terms(query))
    searchable = f"{hit.title} {hit.chunk_text}".lower()
    for requested_section in requested_sections:
        if re.search(rf"\b(?:section\s*)?{re.escape(requested_section)}\b", searchable, re.I):
            return f"Section {requested_section} ({hit.chunk_id})"
    for requested_article in requested_articles:
        if re.search(rf"\b(?:article\s*)?{re.escape(requested_article)}\b", searchable, re.I):
            return f"Article {requested_article} ({hit.chunk_id})"
    return f"Chunk {hit.chunk_id}"


def _convert_corpus_hit(hit: CorpusSearchHit, query: str, analysis: LegalQueryAnalysis) -> RetrievedAuthority:
    source = f"{hit.source_json} [{hit.chunk_id}"
    if hit.source_path:
        source += f"; source: {hit.source_path}"
    source += "]"
    verified = True
    if hit.authority_type == "statute":
        verified = _reference_supports_statute(
            RetrievedAuthority(
                authority_type="statute",
                title=hit.title or "Indian statute",
                reference=_corpus_reference(hit, query),
                summary=hit.chunk_text,
                score=hit.score,
                source_file=source,
                act_key=_infer_act_key(hit.title),
            ),
            analysis,
        )
    else:
        verified = _reference_supports_case(
            RetrievedAuthority(
                authority_type="case",
                title=hit.title or "Indian judgment",
                reference=_corpus_reference(hit, query),
                summary=hit.chunk_text,
                score=hit.score,
                source_file=source,
            ),
            analysis,
        )
    return RetrievedAuthority(
        authority_type=hit.authority_type,
        title=hit.title or ("Indian statute" if hit.authority_type == "statute" else "Indian judgment"),
        reference=_corpus_reference(hit, query),
        summary=_truncate_text(hit.chunk_text, 520 if hit.authority_type == "statute" else 420),
        score=hit.score,
        source_file=source,
        act_key=_infer_act_key(hit.title) if hit.authority_type == "statute" else "",
        verified=verified,
    )


def _retrieve_corpus_matches(query: str, analysis: LegalQueryAnalysis) -> tuple[list[RetrievedAuthority], list[RetrievedAuthority]]:
    path = _corpus_index_path()
    index = LegalCorpusIndex(path)
    if not index.is_compatible():
        _warn_corpus_once(path, "missing or incompatible index")
        return ([], [])
    candidate_limit = max(1, _env_int("LEGAL_RAG_CORPUS_CANDIDATE_LIMIT", 100))
    statute_limit = _env_int("LEGAL_RAG_CORPUS_MAX_STATUTES", 3)
    case_limit = _env_int("LEGAL_RAG_CORPUS_MAX_CASES", 3)
    try:
        filters = _build_query_filters(query)
        statutes = index.search(query, "statute", limit=statute_limit, candidate_limit=candidate_limit, filters=filters)
        cases = index.search(query, "case", limit=case_limit, candidate_limit=candidate_limit, filters=filters)
    except (OSError, ValueError, sqlite3.Error) as exc:
        _warn_corpus_once(path, str(exc))
        return ([], [])
    return (
        [_convert_corpus_hit(item, query, analysis) for item in statutes],
        [_convert_corpus_hit(item, query, analysis) for item in cases],
    )


def _merge_authorities(
    curated: list[RetrievedAuthority],
    corpus: list[RetrievedAuthority],
    *,
    max_items: int,
    preserve_curated_only: bool = False,
    curated_first: bool = False,
) -> list[RetrievedAuthority]:
    if max_items <= 0:
        return []
    candidates = list(curated)
    if not preserve_curated_only and not curated_first:
        candidates.extend(corpus)
        candidates.sort(
            key=lambda item: (
                -item.score,
                0 if item in curated else 1,
                item.title.lower(),
                item.reference.lower(),
            )
        )
    elif not preserve_curated_only:
        candidates.extend(
            sorted(corpus, key=lambda item: (-item.score, item.title.lower(), item.reference.lower()))
        )
    selected: list[RetrievedAuthority] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = (_normalize_text(item.title), _normalize_text(item.reference))
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= max_items:
            break
    return _dedupe_authorities(selected)


class _LegalRagIndex:
    def __init__(self) -> None:
        self._lock = Lock()
        self._loaded = False
        self._statutes: list[dict[str, object]] = []
        self._cases: list[dict[str, object]] = []

    def ensure_loaded(self) -> None:
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return

            with _STATUTES_PATH.open("r", encoding="utf-8") as handle:
                statutes = json.load(handle)
            with _CASE_LAW_PATH.open("r", encoding="utf-8") as handle:
                cases = json.load(handle)

            self._statutes = [self._prepare_statute_record(item) for item in statutes]
            self._cases = [self._prepare_case_record(item) for item in cases]
            self._loaded = True

    def _prepare_statute_record(self, item: dict[str, object]) -> dict[str, object]:
        text_parts = [
            str(item.get("act_name") or ""),
            str(item.get("section") or ""),
            str(item.get("section_number") or ""),
            str(item.get("title") or ""),
            str(item.get("description") or ""),
            str(item.get("punishment") or ""),
            str(item.get("keywords") or ""),
        ]
        prepared = dict(item)
        prepared["_tokens"] = _tokenize(" ".join(text_parts))
        prepared["_act_key"] = _normalize_text(str(item.get("act_key") or ""))
        prepared["_section_number"] = _normalize_text(str(item.get("section_number") or ""))
        return prepared

    def _prepare_case_record(self, item: dict[str, object]) -> dict[str, object]:
        keywords = item.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = [str(keywords)]

        text_parts = [
            str(item.get("topic_key") or ""),
            str(item.get("title") or ""),
            str(item.get("court") or ""),
            str(item.get("year") or ""),
            str(item.get("holding") or ""),
            " ".join(str(keyword) for keyword in keywords),
            str(item.get("authority_level") or ""),
        ]
        prepared = dict(item)
        prepared["_tokens"] = _tokenize(" ".join(text_parts))
        prepared["_authority_rank"] = 3 if str(item.get("authority_level") or "") == "supreme_court" else 1
        return prepared

    def retrieve(self, query: str) -> tuple[list[RetrievedAuthority], list[RetrievedAuthority]]:
        self.ensure_loaded()

        analysis = analyze_legal_query(query)
        if not analysis.tokens:
            return ([], [])

        domain_tokens = _build_domain_hint_tokens(query)

        statute_matches = self._rank_statutes(analysis, domain_tokens)
        case_matches = self._rank_cases(analysis, domain_tokens)
        return (statute_matches, case_matches)

    def _rank_statutes(
        self,
        analysis: LegalQueryAnalysis,
        domain_tokens: set[str],
    ) -> list[RetrievedAuthority]:
        results: list[tuple[bool, RetrievedAuthority]] = []
        min_score = _env_float("LEGAL_RAG_MIN_STATUTE_SCORE", 4.0)
        query_text = analysis.normalized_query
        query_tokens = set(analysis.tokens)
        section_terms = set(analysis.section_numbers)
        act_keys = set(analysis.act_keys)
        article_terms = set(analysis.article_numbers)
        death_sensitive_query = _contains_any(query_text, ("death", "died", "killed", "fatal"))
        injury_sensitive_query = _contains_any(query_text, ("injury", "injuries", "injured", "hurt", "accident"))
        motor_accident_query = _contains_any(
            query_text,
            ("accident", "drunk driver", "drink and drive", "rash driving", "negligent driving", "hit my", "hit me"),
        )
        police_query = _contains_any(query_text, ("police", "investigation", "arrest", "station"))
        preferred_sections = _preferred_section_numbers(query_text)
        exact_section_query = bool(section_terms)

        for item in self._statutes:
            score = 0.0
            item_tokens = item["_tokens"]
            overlap = len(query_tokens & item_tokens)
            score += overlap

            section_number = str(item["_section_number"])
            section_score, matched_section = _section_match_score(section_number, section_terms)
            score += section_score

            if article_terms and any(term in section_number for term in article_terms):
                score += 10.0

            if section_terms and not matched_section and overlap < 3:
                continue

            if section_number and section_number in preferred_sections:
                score += 12.0

            act_key = str(item["_act_key"])
            if act_keys and act_key in act_keys:
                score += 6.0
            elif act_keys and exact_section_query:
                continue

            if exact_section_query and act_keys and act_key not in act_keys:
                continue

            domain_overlap = len(domain_tokens & item_tokens)
            if domain_overlap:
                score += min(3.0, domain_overlap * 0.5)

            item_text = _normalize_text(
                " ".join(
                    [
                        str(item.get("title") or ""),
                        str(item.get("description") or ""),
                        str(item.get("keywords") or ""),
                    ]
                )
            )
            if injury_sensitive_query and _contains_any(item_text, ("injury", "hurt", "rash", "negligent", "vehicle")):
                score += 1.5
            if not death_sensitive_query and "death" in item_text:
                score -= 2.0
            if motor_accident_query and _contains_any(item_text, ("rash", "negligent", "vehicle", "public way")):
                score += 3.0
            if police_query and _contains_any(item_text, ("investigation", "arrest", "police", "bond", "magistrate")):
                score += 2.0
            score += _apply_contextual_statute_boosts(
                query_text=query_text,
                item=item,
                item_text=item_text,
            )

            if score < min_score:
                continue

            summary_parts = [
                str(item.get("title") or "").strip(),
                _truncate_text(str(item.get("description") or "").strip(), 220),
            ]
            punishment = str(item.get("punishment") or "").strip()
            if punishment:
                summary_parts.append(f"Punishment: {punishment}")

            results.append(
                (
                    matched_section,
                    RetrievedAuthority(
                        authority_type="statute",
                        title=str(item.get("act_name") or "").strip() or "Indian statute",
                        reference=str(item.get("section") or "").strip() or str(item.get("section_number") or "").strip(),
                        summary=_truncate_text(" ".join(part for part in summary_parts if part).strip(), 320),
                        score=score,
                        source_file="tllac/app/data/statute_sections.json",
                        act_key=act_key,
                    ),
                )
            )

        results.sort(
            key=lambda item: (
                item[0],
                item[1].score,
                item[1].title,
                item[1].reference,
            ),
            reverse=True,
        )
        if section_terms and any(item[0] for item in results):
            results = [item for item in results if item[0]]

        ranked = self._select_statute_results(
            [item[1] for item in results],
            max_items=_env_int("LEGAL_RAG_MAX_STATUTES", 3),
        )
        return _dedupe_authorities(_rerank_authorities(ranked, analysis))

    def _select_statute_results(
        self,
        ranked_results: list[RetrievedAuthority],
        *,
        max_items: int,
    ) -> list[RetrievedAuthority]:
        if max_items <= 0 or not ranked_results:
            return []

        selected: list[RetrievedAuthority] = []
        seen_references: set[tuple[str, str]] = set()
        seen_acts: set[str] = set()

        for item in ranked_results:
            key = (item.act_key, item.reference)
            if key in seen_references:
                continue
            if item.act_key and item.act_key not in seen_acts:
                selected.append(item)
                seen_references.add(key)
                seen_acts.add(item.act_key)
                if len(selected) >= max_items:
                    return selected

        for item in ranked_results:
            key = (item.act_key, item.reference)
            if key in seen_references:
                continue
            selected.append(item)
            seen_references.add(key)
            if len(selected) >= max_items:
                break

        return selected

    def _rank_cases(
        self,
        analysis: LegalQueryAnalysis,
        domain_tokens: set[str],
    ) -> list[RetrievedAuthority]:
        results: list[RetrievedAuthority] = []
        min_score = _env_float("LEGAL_RAG_MIN_CASE_SCORE", 3.0)
        query_text = analysis.normalized_query
        query_tokens = set(analysis.tokens)
        motor_accident_query = _contains_any(
            query_text,
            ("accident", "drunk driver", "drink and drive", "rash driving", "negligent driving", "hit my", "hit me"),
        )
        police_query = _contains_any(query_text, ("police", "investigation", "arrest", "bail"))

        for item in self._cases:
            item_tokens = item["_tokens"]
            overlap = len(query_tokens & item_tokens)
            domain_overlap = len(domain_tokens & item_tokens)
            if overlap == 0 and domain_overlap == 0:
                continue

            score = overlap + min(2.0, domain_overlap * 0.5) + (float(item["_authority_rank"]) * 0.25)
            item_text = _normalize_text(
                " ".join(
                    [
                        str(item.get("topic_key") or ""),
                        str(item.get("holding") or ""),
                        " ".join(str(keyword) for keyword in item.get("keywords") or []),
                    ]
                )
            )
            if motor_accident_query and _contains_any(item_text, ("motor accident", "negligence", "mact", "injury")):
                score += 3.0
            if police_query and _contains_any(item_text, ("arrest", "bail", "police", "liberty")):
                score += 1.5

            if score < min_score:
                continue

            results.append(
                RetrievedAuthority(
                    authority_type="case",
                    title=str(item.get("title") or "").strip(),
                    reference=f"{str(item.get('court') or '').strip()} ({str(item.get('year') or '').strip()})".strip(),
                    summary=_truncate_text(str(item.get("holding") or "").strip(), 220),
                    score=score,
                    source_file="tllac/app/data/case_law_corpus.json",
                    verified=True,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        ranked = results[: _env_int("LEGAL_RAG_MAX_CASES", 2)]
        return _dedupe_authorities(_rerank_authorities(ranked, analysis))


_INDEX = _LegalRagIndex()


def legal_rag_enabled() -> bool:
    return _env_flag("LEGAL_RAG_ENABLED", True)


def retrieve_legal_rag_result(query: str) -> LegalRagResult:
    normalized_query = normalize_legal_rag_query(query)
    if not legal_rag_enabled() or not normalized_query:
        return LegalRagResult(query=normalized_query, statute_matches=(), case_matches=(), confidence=0.0, grounded=False)

    analysis = analyze_legal_query(normalized_query)
    curated_statutes, curated_cases = _INDEX.retrieve(normalized_query)
    corpus_statutes, corpus_cases = _retrieve_corpus_matches(normalized_query, analysis)
    exact_curated_section = bool(analysis.section_numbers and analysis.act_keys and curated_statutes)
    statute_matches = _merge_authorities(
        curated_statutes,
        corpus_statutes,
        max_items=_env_int("LEGAL_RAG_MAX_STATUTES", 3),
        preserve_curated_only=exact_curated_section,
        curated_first=True,
    )
    case_matches = _merge_authorities(
        curated_cases,
        corpus_cases,
        max_items=_env_int("LEGAL_RAG_MAX_CASES", 2),
    )
    statute_matches = tuple(_rerank_authorities([item for item in statute_matches if item.verified], analysis))
    case_matches = tuple(_rerank_authorities([item for item in case_matches if item.verified], analysis))
    confidence = _compute_confidence(list(statute_matches), list(case_matches), analysis)
    return LegalRagResult(
        query=normalized_query,
        statute_matches=statute_matches,
        case_matches=case_matches,
        confidence=confidence,
        grounded=bool(statute_matches or case_matches),
    )


def build_legal_rag_context(query: str) -> str:
    return build_legal_rag_context_from_result(retrieve_legal_rag_result(query))


def build_legal_rag_context_from_result(result: LegalRagResult) -> str:
    if not result.statute_matches and not result.case_matches:
        return "The retrieved legal documents do not contain sufficient information to answer this question accurately."

    max_chars = _env_int("LEGAL_RAG_MAX_CHARS", 1800)
    lines = [
        "Retrieved legal authorities:",
        "Answer only from the retrieved authorities below.",
        "If the retrieved authorities are not enough, say: 'The retrieved legal documents do not contain sufficient information to answer this question accurately.'",
        "Do not invent acts, sections, articles, punishments, dates, courts, or case law.",
        "When citing a statute, keep the exact act and section reference from the retrieved authority.",
        f"Retrieval confidence: {result.confidence:.2f}",
        "",
    ]

    if result.statute_matches:
        lines.append("Statutes:")
        for item in result.statute_matches:
            verified = "verified" if item.verified else "unverified"
            lines.append(f"- {item.title} - {item.reference} [{verified}] ({item.source_file}): {item.summary}")

    if result.case_matches:
        if result.statute_matches:
            lines.append("")
        lines.append("Case law:")
        for item in result.case_matches:
            verified = "verified" if item.verified else "unverified"
            lines.append(f"- {item.title} - {item.reference} [{verified}] ({item.source_file}): {item.summary}")

    context = "\n".join(lines).strip()
    if len(context) <= max_chars:
        return context

    trimmed_lines: list[str] = []
    current_length = 0
    for line in lines:
        projected = current_length + len(line) + (1 if trimmed_lines else 0)
        if projected > max_chars:
            break
        trimmed_lines.append(line)
        current_length = projected

    return "\n".join(trimmed_lines).strip()


def build_legal_rag_source_note(query: str) -> str:
    return build_legal_rag_source_note_from_result(retrieve_legal_rag_result(query))


def build_legal_rag_source_note_from_result(result: LegalRagResult) -> str:
    if not result.statute_matches and not result.case_matches:
        return ""

    lines = ["Source Check:"]

    for item in result.statute_matches:
        lines.append(f"- {item.title} - {item.reference} -> {item.source_file}")

    for item in result.case_matches:
        lines.append(f"- {item.title} - {item.reference} -> {item.source_file}")

    return "\n".join(lines)


def build_relevant_laws_note_from_result(result: LegalRagResult) -> str:
    if not result.statute_matches or result.confidence < 0.5:
        return ""

    lines = ["Relevant Laws:"]
    act_order = {"bns": 0, "bnss": 1, "bsa": 2}
    ordered_matches = sorted(
        result.statute_matches,
        key=lambda item: (act_order.get(item.act_key, 9), -item.score, item.reference),
    )
    for item in ordered_matches:
        short_summary = _truncate_text(item.summary, 160)
        lines.append(f"- {item.title} - {item.reference}: {short_summary}")

    return "\n".join(lines)


def build_relevant_sections_note_from_result(result: LegalRagResult) -> str:
    return build_relevant_laws_note_from_result(result)
