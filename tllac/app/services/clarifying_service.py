"""
Generic deterministic clarifying-question service.

This service does not try to enumerate every possible user query. Instead it:
1. Detects a broad legal issue family.
2. Checks which fact dimensions are present.
3. Asks only the most relevant missing questions for that family.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ClarifyingProfile:
    name: str
    trigger_terms: tuple[str, ...]
    preferred_dimensions: tuple[str, ...]
    why_it_matters: str


_PROFILES = (
    ClarifyingProfile(
        name="cyber_harm",
        trigger_terms=(
            "bullied online",
            "online bullying",
            "cyberbullying",
            "cyber bullying",
            "harassed online",
            "online harassment",
            "hacked",
            "hack",
            "fake profile",
            "fake account",
            "impersonation",
            "blackmail",
            "morphed photo",
            "revenge porn",
            "account compromised",
            "privacy breach",
        ),
        preferred_dimensions=(
            "victim_age",
            "victim_gender",
            "platform",
            "conduct",
            "actor_identity",
            "timeline",
            "evidence",
            "immediate_risk",
        ),
        why_it_matters=(
            "These facts affect whether the matter may involve cyber harassment, stalking, "
            "criminal intimidation, obscenity, impersonation, extortion, child-protection "
            "issues, platform takedown steps, or urgent police intervention under Indian law."
        ),
    ),
    ClarifyingProfile(
        name="property_housing",
        trigger_terms=(
            "landlord",
            "tenant",
            "rent",
            "evict",
            "eviction",
            "property dispute",
            "possession",
            "flat",
            "house owner",
            "lease",
        ),
        preferred_dimensions=(
            "location",
            "relationship",
            "timeline",
            "documents",
            "money_amount",
            "current_status",
            "police_or_notice",
        ),
        why_it_matters=(
            "These facts affect tenancy rights, notice requirements, possession remedies, "
            "documentary proof, police role, and the proper forum under Indian law."
        ),
    ),
    ClarifyingProfile(
        name="employment",
        trigger_terms=(
            "salary",
            "wages",
            "employer",
            "employee",
            "job",
            "termination",
            "fired",
            "resigned",
            "workplace harassment",
            "pf",
            "gratuity",
        ),
        preferred_dimensions=(
            "relationship",
            "timeline",
            "documents",
            "money_amount",
            "location",
            "current_status",
            "internal_complaint",
        ),
        why_it_matters=(
            "These facts affect labour remedies, salary recovery, harassment process, "
            "contract rights, and the proper authority or forum."
        ),
    ),
    ClarifyingProfile(
        name="family",
        trigger_terms=(
            "husband",
            "wife",
            "marriage",
            "divorce",
            "maintenance",
            "domestic violence",
            "child custody",
            "dowry",
            "in-laws",
        ),
        preferred_dimensions=(
            "victim_gender",
            "relationship",
            "timeline",
            "location",
            "children",
            "violence_or_threat",
            "current_status",
            "documents",
        ),
        why_it_matters=(
            "These facts affect matrimonial remedies, maintenance, custody, domestic violence "
            "protection, and urgent court or police steps."
        ),
    ),
    ClarifyingProfile(
        name="consumer_fraud",
        trigger_terms=(
            "scam",
            "scammed",
            "fraud",
            "cheated",
            "consumer",
            "refund",
            "seller",
            "order",
            "product",
            "service",
            "upi",
            "bank",
            "transaction",
        ),
        preferred_dimensions=(
            "money_amount",
            "timeline",
            "platform",
            "documents",
            "actor_identity",
            "bank_or_payment_mode",
            "current_status",
        ),
        why_it_matters=(
            "These facts affect whether the matter is mainly consumer, civil recovery, "
            "cyber fraud, or criminal cheating, and they determine the right complaint path."
        ),
    ),
    ClarifyingProfile(
        name="criminal_general",
        trigger_terms=(
            "assault",
            "beaten",
            "threatened",
            "threat",
            "stolen",
            "theft",
            "fraud",
            "forgery",
            "blackmail",
            "defamation",
            "police complaint",
            "fir",
            "arrest",
        ),
        preferred_dimensions=(
            "location",
            "timeline",
            "conduct",
            "actor_identity",
            "injury_or_harm",
            "evidence",
            "police_or_notice",
            "immediate_risk",
        ),
        why_it_matters=(
            "These facts affect the possible offences, urgency, evidence strategy, and whether "
            "police, magistrate, or another authority is the right next step."
        ),
    ),
    ClarifyingProfile(
        name="banking_finance",
        trigger_terms=(
            "loan",
            "emi",
            "bank notice",
            "sarfaesi",
            "drt",
            "cheque bounce",
            "cheque bounced",
            "credit card",
            "upi fraud",
            "bank fraud",
        ),
        preferred_dimensions=(
            "money_amount",
            "timeline",
            "documents",
            "bank_or_payment_mode",
            "current_status",
            "police_or_notice",
            "location",
        ),
        why_it_matters=(
            "These facts affect whether the route is cheque-bounce action, banking grievance, "
            "DRT/SARFAESI response, cyber-fraud complaint, or civil recovery."
        ),
    ),
    ClarifyingProfile(
        name="constitutional_writ",
        trigger_terms=(
            "government inaction",
            "police not taking",
            "authority not",
            "writ",
            "fundamental right",
            "state authority",
        ),
        preferred_dimensions=(
            "location",
            "timeline",
            "documents",
            "current_status",
            "police_or_notice",
            "remedy_sought",
        ),
        why_it_matters=(
            "These facts affect whether a writ is maintainable, whether an alternative "
            "statutory remedy exists, and what interim direction can realistically be sought."
        ),
    ),
    ClarifyingProfile(
        name="motor_accident",
        trigger_terms=(
            "accident",
            "vehicle accident",
            "rash driving",
            "insurance claim",
            "mact",
        ),
        preferred_dimensions=(
            "location",
            "timeline",
            "injury_or_harm",
            "documents",
            "police_or_notice",
            "money_amount",
            "current_status",
        ),
        why_it_matters=(
            "These facts affect MACT jurisdiction, insurance liability, compensation, "
            "criminal reporting, and urgent medical or evidentiary steps."
        ),
    ),
)

_DIMENSION_QUESTIONS = {
    "victim_age": "What is your age, and is the victim a minor or an adult?",
    "victim_gender": "Are you male, female, or is gender relevant to what happened?",
    "platform": "Which platform, app, website, or communication channel was involved?",
    "conduct": "What exactly happened: what was said or done, and how many times did it happen?",
    "actor_identity": "Do you know who the other person is, or is it an anonymous or fake account?",
    "timeline": "When did this start, and is it still ongoing?",
    "evidence": "Do you have screenshots, messages, recordings, links, usernames, or any other proof saved?",
    "immediate_risk": "Is there any immediate safety risk, threat, extortion, or risk of further harm right now?",
    "location": "Which city and state did this happen in, or where are the parties located?",
    "relationship": "What is your relationship with the other person or party?",
    "documents": "Do you have any written documents, contracts, notices, bills, rent agreement, emails, or chats related to this?",
    "money_amount": "What amount of money is involved, if any?",
    "current_status": "What is the current stage: still ongoing, already reported, notice received, blocked, terminated, or something else?",
    "police_or_notice": "Have you already filed a police complaint, received a notice, or spoken to any authority?",
    "internal_complaint": "Have you complained to HR, an Internal Committee, or any workplace authority yet?",
    "children": "Are any children involved, and if yes, what are their ages?",
    "violence_or_threat": "Has there been any physical violence, threat, coercion, or immediate danger?",
    "bank_or_payment_mode": "How was the payment made: UPI, card, bank transfer, wallet, cash, or something else?",
    "injury_or_harm": "Was there any physical injury, financial loss, reputational harm, or mental harassment?",
    "remedy_sought": "What outcome do you want: FIR, compensation, injunction, refund, notice, appeal, protection, or another remedy?",
}


def _normalize(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _has_age_context(text: str) -> bool:
    return bool(
        re.search(r"\b(\d{1,2})\s*(years? old|yo|y/o)\b", text)
        or any(term in text for term in ("minor", "child", "adult", "student"))
    )


def _has_gender_context(text: str) -> bool:
    return any(term in text for term in ("woman", "female", "girl", "man", "male", "boy", "mother", "father", "wife", "husband"))


def _has_platform_context(text: str) -> bool:
    return any(term in text for term in ("instagram", "facebook", "whatsapp", "telegram", "twitter", "x ", "youtube", "snapchat", "discord", "email", "sms", "website", "app"))


def _has_actor_context(text: str) -> bool:
    return any(term in text for term in ("classmate", "teacher", "coworker", "ex", "neighbor", "relative", "friend", "stranger", "boss", "landlord", "tenant", "seller", "employer", "employee"))


def _has_timeline_context(text: str) -> bool:
    return any(term in text for term in ("today", "yesterday", "last week", "last month", "since", "started", "ongoing", "for "))


def _has_evidence_context(text: str) -> bool:
    return any(term in text for term in ("screenshot", "recording", "proof", "evidence", "chat log", "message saved", "invoice", "agreement", "notice", "bill"))


def _has_location_context(text: str) -> bool:
    return " in " in f" {text} " and any(term in text for term in ("delhi", "mumbai", "bangalore", "bengaluru", "kolkata", "chennai", "hyderabad", "pune", "india"))


def _has_documents_context(text: str) -> bool:
    return any(term in text for term in ("agreement", "contract", "offer letter", "notice", "bill", "invoice", "email", "document", "letter"))


def _has_money_amount_context(text: str) -> bool:
    return bool(re.search(r"(?:rs\.?|rupees?|inr|₹)\s*\d+|\b\d+\s*(?:rupees|rs)\b", text))


def _has_police_or_notice_context(text: str) -> bool:
    return any(term in text for term in ("police", "fir", "complaint", "notice", "court", "lawyer", "hr", "cyber cell"))


def _has_current_status_context(text: str) -> bool:
    return any(term in text for term in ("ongoing", "already", "still", "blocked", "terminated", "fired", "evicted", "reported", "resolved"))


def _has_children_context(text: str) -> bool:
    return any(term in text for term in ("child", "children", "son", "daughter", "minor"))


def _has_violence_or_threat_context(text: str) -> bool:
    return any(term in text for term in ("threat", "violent", "violence", "attack", "assault", "beat", "kill", "hurt", "danger"))


def _has_bank_or_payment_mode_context(text: str) -> bool:
    return any(term in text for term in ("upi", "bank transfer", "account", "wallet", "card", "credit card", "debit card", "cash", "gpay", "phonepe", "paytm"))


def _has_injury_or_harm_context(text: str) -> bool:
    return any(term in text for term in ("injury", "injured", "loss", "money lost", "mental harassment", "defamed", "reputation", "harm"))


def _has_relationship_context(text: str) -> bool:
    return _has_actor_context(text) or any(term in text for term in ("my husband", "my wife", "my employer", "my landlord", "my tenant", "my boss", "my ex"))


_DIMENSION_CHECKS = {
    "victim_age": _has_age_context,
    "victim_gender": _has_gender_context,
    "platform": _has_platform_context,
    "conduct": lambda text: any(term in text for term in ("threat", "abuse", "post", "message", "call", "harass", "hack", "stalk", "leak", "defame", "fake profile", "not paying", "locked out", "cheated")),
    "actor_identity": _has_actor_context,
    "timeline": _has_timeline_context,
    "evidence": _has_evidence_context,
    "immediate_risk": lambda text: _has_violence_or_threat_context(text)
    or any(term in text for term in ("extort", "blackmail", "urgent", "immediate danger")),
    "location": _has_location_context,
    "relationship": _has_relationship_context,
    "documents": _has_documents_context,
    "money_amount": _has_money_amount_context,
    "current_status": _has_current_status_context,
    "police_or_notice": _has_police_or_notice_context,
    "internal_complaint": lambda text: any(term in text for term in ("hr", "internal complaint", "committee", "manager")),
    "children": _has_children_context,
    "violence_or_threat": _has_violence_or_threat_context,
    "bank_or_payment_mode": _has_bank_or_payment_mode_context,
    "injury_or_harm": _has_injury_or_harm_context,
    "remedy_sought": lambda text: any(term in text for term in ("fir", "compensation", "injunction", "refund", "notice", "appeal", "protection", "divorce", "bail", "complaint")),
}


def _match_profile(text: str) -> ClarifyingProfile | None:
    for profile in _PROFILES:
        if _contains_any(text, profile.trigger_terms):
            return profile
    return None


def _generic_issue_like_query(text: str) -> bool:
    return len(text.split()) <= 18 and any(
        term in text
        for term in (
            "problem",
            "issue",
            "dispute",
            "harass",
            "bully",
            "hack",
            "cheat",
            "fraud",
            "landlord",
            "salary",
            "threat",
            "blackmail",
            "divorce",
            "custody",
            "maintenance",
            "cheque",
            "sarfaesi",
            "accident",
            "insurance",
            "government",
            "writ",
            "notice",
        )
    )


def _missing_dimensions(text: str, dimensions: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for dimension in dimensions:
        checker = _DIMENSION_CHECKS[dimension]
        if not checker(text):
            missing.append(dimension)
    return missing


def _format_clarifying_response(summary: str, dimensions: list[str], why_it_matters: str) -> str:
    questions = [_DIMENSION_QUESTIONS[dimension] for dimension in dimensions[:6]]
    lines = [
        "Need More Facts:",
        f"- {summary}",
        "",
        "Questions:",
    ]
    for question in questions:
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "Why It Matters:",
            f"- {why_it_matters}",
        ]
    )
    return "\n".join(lines)


def get_clarifying_response(query: str) -> str | None:
    """
    Return a deterministic clarifying response when key facts are missing.
    """
    text = _normalize(query)
    if not text:
        return None

    profile = _match_profile(text)
    if profile:
        missing = _missing_dimensions(text, profile.preferred_dimensions)
        if len(missing) >= 3:
            return _format_clarifying_response(
                "I need a few key facts before I can give a precise legal response.",
                missing,
                profile.why_it_matters,
            )
        return None

    if _generic_issue_like_query(text):
        generic_dimensions = (
            "location",
            "timeline",
            "relationship",
            "conduct",
            "documents",
            "evidence",
            "remedy_sought",
            "current_status",
        )
        missing = _missing_dimensions(text, generic_dimensions)
        if len(missing) >= 3:
            return _format_clarifying_response(
                "The issue is too broad right now for a precise legal answer.",
                missing,
                (
                    "These facts help determine the correct legal category, the applicable Indian law, "
                    "the urgency, and the right next forum or remedy."
                ),
            )

    return None
