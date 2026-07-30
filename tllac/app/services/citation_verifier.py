from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import logging
import re
from typing import Any


logger = logging.getLogger("tllac.services.citation_verifier")


@dataclass(frozen=True)
class EvidenceSource:
    source_id: str
    source_type: str
    title: str
    citation: str = ""
    court: str = ""
    date: str = ""
    section: str = ""
    page: str = ""
    paragraph: str = ""
    url: str = ""
    extracted_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "citation": self.citation,
            "court": self.court,
            "date": self.date,
            "section": self.section,
            "page": self.page,
            "paragraph": self.paragraph,
            "url": self.url,
            "extracted_text": self.extracted_text,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ResearchClaim:
    claim_id: str
    text: str
    source_ids: list[str] = field(default_factory=list)
    source_locations: list[str] = field(default_factory=list)
    material: bool = True
    confidence: float | None = None
    claim_type: str = "analysis"

    def normalized_text(self) -> str:
        return re.sub(r"\s+", " ", self.text or "").strip().lower()


@dataclass(frozen=True)
class SourceMapping:
    source_id: str
    claim_ids: list[str] = field(default_factory=list)
    support: str = ""


@dataclass(frozen=True)
class ResearchDraft:
    memo_title: str
    memo_summary: str
    confidence: float
    claims: list[ResearchClaim] = field(default_factory=list)
    source_mappings: list[SourceMapping] = field(default_factory=list)
    review_notes: str = ""
    raw_text: str = ""


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    review_required: bool
    memo_title: str
    memo_text: str
    confidence: float
    claims: list[ResearchClaim] = field(default_factory=list)
    source_mappings: list[SourceMapping] = field(default_factory=list)
    sources: list[EvidenceSource] = field(default_factory=list)
    rejected_claims: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


_CLAIM_SECTION_PATTERN = re.compile(r"\bsection\s+(\d+[a-z]?(?:\(\d+\))?)\b", re.I)
_PAGE_PATTERN = re.compile(r"\bpage\s+(\d+)\b", re.I)
_PARAGRAPH_PATTERN = re.compile(r"\bparagraph\s+(\d+)\b", re.I)


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Empty research response.")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start:end + 1]
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Research response must be a JSON object.")
    return data


def parse_research_draft(text: str) -> ResearchDraft:
    try:
        payload = _extract_json_object(text)
    except Exception:
        payload = {
            "memo_title": "Verified Research Memo",
            "memo_summary": (text or "").strip(),
            "confidence": 0.0,
            "claims": [],
            "source_mappings": [],
            "review_notes": "The model response was not valid JSON.",
        }

    claims: list[ResearchClaim] = []
    for item in payload.get("claims") or []:
        if not isinstance(item, dict):
            continue
        source_locations = item.get("source_locations") or item.get("locations") or []
        if not isinstance(source_locations, list):
            source_locations = [str(source_locations)]
        source_ids = item.get("source_ids") or item.get("sources") or []
        if not isinstance(source_ids, list):
            source_ids = [str(source_ids)]
        claims.append(
            ResearchClaim(
                claim_id=str(item.get("claim_id") or f"claim_{len(claims) + 1}"),
                text=str(item.get("text") or item.get("claim") or "").strip(),
                source_ids=[str(source_id).strip() for source_id in source_ids if str(source_id).strip()],
                source_locations=[str(location).strip() for location in source_locations if str(location).strip()],
                material=bool(item.get("material", True)),
                confidence=_as_float(item.get("confidence")),
                claim_type=str(item.get("claim_type") or "analysis").strip() or "analysis",
            )
        )

    source_mappings: list[SourceMapping] = []
    for item in payload.get("source_mappings") or []:
        if not isinstance(item, dict):
            continue
        claim_ids = item.get("claim_ids") or item.get("claims") or []
        if not isinstance(claim_ids, list):
            claim_ids = [str(claim_ids)]
        source_mappings.append(
            SourceMapping(
                source_id=str(item.get("source_id") or "").strip(),
                claim_ids=[str(claim_id).strip() for claim_id in claim_ids if str(claim_id).strip()],
                support=str(item.get("support") or item.get("note") or "").strip(),
            )
        )

    return ResearchDraft(
        memo_title=str(payload.get("memo_title") or payload.get("title") or "Verified Research Memo").strip(),
        memo_summary=str(payload.get("memo_summary") or payload.get("summary") or "").strip(),
        confidence=_as_float(payload.get("confidence"), default=0.0),
        claims=claims,
        source_mappings=source_mappings,
        review_notes=str(payload.get("review_notes") or payload.get("notes") or "").strip(),
        raw_text=text or "",
    )


def _as_float(value: Any, default: float | None = None) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0 if default is None else default


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _normalize(text)))


def _source_support_text(source: EvidenceSource) -> str:
    return " ".join(
        part
        for part in (
            source.title,
            source.citation,
            source.court,
            source.date,
            source.section,
            source.page,
            source.paragraph,
            source.url,
            source.extracted_text,
        )
        if part
    )


def _parse_location(location: str) -> tuple[str, str]:
    text = _normalize(location)
    if ":" not in text:
        return (text, "")
    kind, raw_value = text.split(":", 1)
    return (kind.strip(), raw_value.strip())


def _location_supported(location: str, source: EvidenceSource) -> bool:
    kind, raw_value = _parse_location(location)
    if not kind:
        return False
    if kind == "section":
        return raw_value and (
            raw_value == _normalize(source.section)
            or raw_value in _normalize(source.citation)
            or raw_value in _normalize(source.extracted_text)
        )
    if kind in {"page", "paragraph"}:
        return raw_value == _normalize(getattr(source, kind))
    if kind == "url":
        return raw_value in _normalize(source.url)
    if kind == "source":
        return raw_value == _normalize(source.source_id)
    return False


def _claim_is_supported_by_source(claim: ResearchClaim, source: EvidenceSource) -> bool:
    claim_text = _normalize(claim.text)
    source_text = _normalize(_source_support_text(source))
    if not claim_text or not source_text:
        return False

    claim_tokens = _tokenize(claim.text)
    source_tokens = _tokenize(_source_support_text(source))
    overlap = claim_tokens & source_tokens
    if len(overlap) >= 3:
        return True

    section_matches = _CLAIM_SECTION_PATTERN.findall(claim.text)
    if section_matches:
        for section in section_matches:
            if section in _normalize(source.section) or section in _normalize(source.citation) or section in _normalize(source.extracted_text):
                return True
        return False

    page_matches = _PAGE_PATTERN.findall(claim.text)
    if page_matches and source.page:
        if any(page == _normalize(source.page) for page in page_matches):
            return True

    paragraph_matches = _PARAGRAPH_PATTERN.findall(claim.text)
    if paragraph_matches and source.paragraph:
        if any(paragraph == _normalize(source.paragraph) for paragraph in paragraph_matches):
            return True

    return len(overlap) >= 1 and len(claim_tokens) <= 25


def _render_verified_memo(title: str, summary: str, claims: list[ResearchClaim], sources: dict[str, EvidenceSource]) -> str:
    lines = [title.strip() or "Verified Research Memo"]
    if summary.strip():
        lines.extend(["", summary.strip()])

    if claims:
        lines.extend(["", "Verified claims:"])
        for index, claim in enumerate(claims, start=1):
            claim_sources = ", ".join(claim.source_ids) if claim.source_ids else "none"
            lines.append(f"{index}. {claim.text} [{claim_sources}]")
    else:
        lines.extend(["", "No verified claims were produced."])

    if sources:
        lines.extend(["", "Verified sources:"])
        for source in sources.values():
            location_bits = [bit for bit in (source.section, source.page, source.paragraph) if bit]
            location_text = ", ".join(location_bits)
            lines.append(f"- {source.source_id}: {source.title} ({location_text or source.citation or 'no location'})")

    return "\n".join(lines).strip()


def verify_research_draft(
    draft: ResearchDraft,
    evidence_sources: list[EvidenceSource],
) -> VerificationResult:
    source_map = {source.source_id: source for source in evidence_sources}
    verified_claims: list[ResearchClaim] = []
    rejected_claims: list[dict[str, Any]] = []
    notes: list[str] = []

    for claim in draft.claims:
        if not claim.text.strip():
            rejected_claims.append({"claim_id": claim.claim_id, "reason": "empty claim text"})
            continue

        if claim.material and not claim.source_ids:
            rejected_claims.append({"claim_id": claim.claim_id, "reason": "material claim without source id"})
            continue

        unknown_sources = [source_id for source_id in claim.source_ids if source_id not in source_map]
        if unknown_sources:
            rejected_claims.append(
                {
                    "claim_id": claim.claim_id,
                    "reason": "unknown source id",
                    "source_ids": unknown_sources,
                }
            )
            continue

        location_mismatches = []
        for location in claim.source_locations:
            if not any(_location_supported(location, source_map[source_id]) for source_id in claim.source_ids):
                location_mismatches.append(location)
        if location_mismatches:
            rejected_claims.append(
                {
                    "claim_id": claim.claim_id,
                    "reason": "unsupported source location",
                    "locations": location_mismatches,
                }
            )
            continue

        if not any(_claim_is_supported_by_source(claim, source_map[source_id]) for source_id in claim.source_ids):
            rejected_claims.append(
                {
                    "claim_id": claim.claim_id,
                    "reason": "claim/source mismatch",
                }
            )
            continue

        verified_claims.append(claim)

    verified_claim_ids = {claim.claim_id for claim in verified_claims}
    verified_mappings: list[SourceMapping] = []
    for mapping in draft.source_mappings:
        if mapping.source_id not in source_map:
            notes.append(f"Rejected unknown source mapping: {mapping.source_id}")
            continue
        claim_ids = [claim_id for claim_id in mapping.claim_ids if claim_id in verified_claim_ids]
        if mapping.claim_ids and not claim_ids:
            notes.append(f"Mapping {mapping.source_id} did not link to any verified claims.")
            continue
        verified_mappings.append(
            SourceMapping(
                source_id=mapping.source_id,
                claim_ids=claim_ids,
                support=mapping.support,
            )
        )

    confidence = min(1.0, max(0.0, draft.confidence))
    review_required = bool(rejected_claims) or confidence < 0.65
    verified = bool(verified_claims) and not review_required

    if not verified_claims:
        notes.append("No claims survived verification.")

    memo_text = _render_verified_memo(
        draft.memo_title,
        draft.memo_summary,
        verified_claims if verified else verified_claims,
        source_map,
    )
    if review_required:
        memo_text = f"{memo_text}\n\nReview required: the verifier removed unsupported claims or detected low confidence."

    return VerificationResult(
        verified=verified,
        review_required=review_required,
        memo_title=draft.memo_title,
        memo_text=memo_text,
        confidence=confidence,
        claims=verified_claims,
        source_mappings=verified_mappings,
        sources=[source_map[source_id] for source_id in source_map],
        rejected_claims=rejected_claims,
        notes=notes,
    )
