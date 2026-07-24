"""Evaluate the Indian legal RAG pipeline on a small benchmark set."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from app.services.legal_rag_service import retrieve_legal_rag_result


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / "tllac" / ".env")
DEFAULT_BENCHMARK_PATH = REPO_ROOT / "tllac" / "app" / "data" / "legal_rag_benchmark.json"


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_SECTION_PATTERN = re.compile(r"\b(?:section|sec\.?|s\.)\s*(\d+[a-z]?(?:\(\d+\))?)\b", re.I)
_CASE_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9.&'() -]{1,120}\s+v\.?\s+[A-Z][A-Za-z0-9.&'() -]{1,120})\b")


@dataclass(frozen=True)
class BenchmarkItem:
    query: str
    expected_statutes: tuple[dict[str, str], ...]
    expected_cases: tuple[dict[str, str], ...]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _tokenize(text: str) -> set[str]:
    return {token for token in _TOKEN_PATTERN.findall(_normalize(text)) if len(token) > 1}


def _load_benchmark(path: Path) -> list[BenchmarkItem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    benchmark: list[BenchmarkItem] = []
    for item in raw:
        benchmark.append(
            BenchmarkItem(
                query=str(item["query"]),
                expected_statutes=tuple(item.get("expected_statutes", [])),
                expected_cases=tuple(item.get("expected_cases", [])),
            )
        )
    return benchmark


def _statute_matches_expected(item, expected: dict[str, str]) -> bool:
    act_key = _normalize(expected.get("act_key", ""))
    reference = _normalize(expected.get("reference", ""))
    title_contains = _normalize(expected.get("title_contains", ""))
    if act_key and item.act_key != act_key:
        return False
    if reference and reference not in _normalize(item.reference):
        return False
    if title_contains and title_contains not in _normalize(item.title):
        return False
    return True


def _case_matches_expected(item, expected: dict[str, str]) -> bool:
    title_contains = _normalize(expected.get("title_contains", ""))
    if title_contains and title_contains not in _normalize(item.title):
        return False
    court_contains = _normalize(expected.get("court_contains", ""))
    if court_contains and court_contains not in _normalize(item.reference):
        return False
    return True


def _extract_response_citations(text: str) -> tuple[set[str], set[str]]:
    return (
        {match.group(1).lower() for match in _SECTION_PATTERN.finditer(text or "")},
        {_normalize(match.group(1)) for match in _CASE_PATTERN.finditer(text or "")},
    )


def _response_relevance(query: str, response: str) -> float:
    query_tokens = _tokenize(query)
    response_tokens = _tokenize(response)
    if not query_tokens or not response_tokens:
        return 0.0
    overlap = len(query_tokens & response_tokens)
    union = len(query_tokens | response_tokens)
    return overlap / union if union else 0.0


def _evaluate_item(item: BenchmarkItem, response: str | None = None) -> dict[str, float]:
    rag_result = retrieve_legal_rag_result(item.query)
    statute_hits = [
        stat
        for stat in rag_result.statute_matches
        if any(_statute_matches_expected(stat, expected) for expected in item.expected_statutes)
    ]
    case_hits = [
        case
        for case in rag_result.case_matches
        if any(_case_matches_expected(case, expected) for expected in item.expected_cases)
    ]

    relevant_retrieved = len(statute_hits) + len(case_hits)
    retrieved_total = len(rag_result.statute_matches) + len(rag_result.case_matches)
    expected_total = len(item.expected_statutes) + len(item.expected_cases)

    precision = relevant_retrieved / retrieved_total if retrieved_total else 0.0
    recall = relevant_retrieved / expected_total if expected_total else 0.0
    groundedness = (
        sum(1 for auth in (*rag_result.statute_matches, *rag_result.case_matches) if auth.verified) / retrieved_total
        if retrieved_total
        else 1.0
    )
    citation_accuracy = precision
    hallucination_rate = 1.0 - citation_accuracy if retrieved_total else 0.0

    response_score = rag_result.confidence
    if response is not None:
        response_score = _response_relevance(item.query, response)

    return {
        "precision": precision,
        "recall": recall,
        "groundedness": groundedness,
        "citation_accuracy": citation_accuracy,
        "hallucination_rate": hallucination_rate,
        "response_relevance": response_score,
        "confidence": rag_result.confidence,
    }


def _aggregate(metrics: list[dict[str, float]]) -> dict[str, float]:
    if not metrics:
        return {}
    keys = metrics[0].keys()
    return {key: sum(item[key] for item in metrics) / len(metrics) for key in keys}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH, help="Benchmark JSON file")
    parser.add_argument("--responses", type=Path, default=None, help="Optional JSON mapping query text to response text")
    args = parser.parse_args()

    benchmark = _load_benchmark(args.benchmark)
    responses = json.loads(args.responses.read_text(encoding="utf-8")) if args.responses else {}

    per_item: list[dict[str, float]] = []
    for item in benchmark:
        response = responses.get(item.query) if isinstance(responses, dict) else None
        metrics = _evaluate_item(item, response=response if isinstance(response, str) else None)
        per_item.append(metrics)
        print(
            f"- {item.query}\n"
            f"  precision@k={metrics['precision']:.2f}, recall@k={metrics['recall']:.2f}, "
            f"groundedness={metrics['groundedness']:.2f}, citation_accuracy={metrics['citation_accuracy']:.2f}, "
            f"hallucination_rate={metrics['hallucination_rate']:.2f}, response_relevance={metrics['response_relevance']:.2f}, "
            f"confidence={metrics['confidence']:.2f}"
        )

    summary = _aggregate(per_item)
    print("\nAverages:")
    for key in ("precision", "recall", "groundedness", "citation_accuracy", "hallucination_rate", "response_relevance", "confidence"):
        print(f"  {key}: {summary.get(key, math.nan):.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
