"""
Scope validation for the new TLLAC chat flow.

This service intentionally does not perform trained-data or RAG lookups.
It gates whether a query appears to be asking for legal or legal-adjacent
help that can be answered in Indian legal context.
"""

from typing import List, Tuple
import logging
import re

logger = logging.getLogger("tllac.services.validation")

_INDIAN_LEGAL_KEYWORDS: List[str] = [
    "legal",
    "law",
    "act",
    "section",
    "article",
    "statute",
    "regulation",
    "india",
    "indian",
    "bharat",
    "supreme court",
    "high court",
    "district court",
    "tribunal",
    "ipc",
    "crpc",
    "cpc",
    "bns",
    "bnss",
    "bsa",
    "constitution",
    "fundamental rights",
    "contract",
    "property",
    "possession",
    "criminal",
    "civil",
    "family",
    "divorce",
    "maintenance",
    "arbitration",
    "mediation",
    "bail",
    "fir",
    "chargesheet",
    "writ",
    "habeas corpus",
    "mandamus",
    "certiorari",
    "limitation act",
    "transfer of property",
    "consumer protection",
    "rti",
    "dpdp",
    "it act",
    "cyber",
    "gst",
    "income tax",
    "insolvency",
    "bankruptcy",
    "labour",
    "labor",
    "motor accident",
    "mact",
    "drunk driving",
    "drink and drive",
    "drink driving",
    "rash driving",
    "negligent driving",
    "learner's license",
    "learner license",
    "learner licence",
    "driving licence",
    "driving license",
    "road accident",
    "traffic accident",
    "hit and run",
    "hit me",
    "hit my vehicle",
    "hit from behind",
    "rear ended",
    "rear-ended",
    "multiple injuries",
    "injury",
    "injured",
    "medical expenses",
    "consumer commission",
    "national consumer helpline",
    "cheque bounce",
    "negotiable instruments",
    "sarfaesi",
    "drt",
    "drat",
    "nclt",
    "roc",
    "trademark",
    "copyright",
    "patent",
    "ngt",
    "environment",
    "pollution",
    "insurance",
    "legal notice",
    "injunction",
    "compensation",
    "limitation",
    "jurisdiction",
    "evidence",
    "bsa",
    "bharatiya sakshya",
    "bharatiya nyaya",
    "bharatiya nagarik",
]

_LEGAL_PROBLEM_PATTERNS: List[str] = [
    "bullied",
    "bullying",
    "harassed",
    "harassment",
    "threatened",
    "threat",
    "blackmail",
    "stalked",
    "stalking",
    "defamed",
    "defamation",
    "abuse",
    "abused",
    "abusive",
    "scam",
    "scammed",
    "fraud",
    "cheated",
    "cheating",
    "hacked",
    "hack",
    "cyber attack",
    "cybercrime",
    "cyber crime",
    "account stolen",
    "account compromised",
    "identity theft",
    "identity stolen",
    "phone stolen",
    "data leak",
    "privacy breach",
    "revenge porn",
    "morphed photo",
    "fake profile",
    "fake account",
    "impersonating me",
    "impersonation",
    "instagram profile",
    "facebook profile",
    "whatsapp account",
    "impersonation",
    "extortion",
    "police",
    "police station",
    "investigation",
    "asking for money",
    "demanding money",
    "bribe demand",
    "close a complaint",
    "complaint against me",
    "police complaint",
    "fir",
    "complaint",
    "notice",
    "arrest",
    "landlord",
    "tenant",
    "rent",
    "eviction",
    "salary",
    "wages",
    "employer",
    "termination",
    "divorce",
    "maintenance",
    "custody",
    "dowry",
    "domestic violence",
    "consumer",
    "refund",
    "seller",
    "property dispute",
    "contract breach",
    "not paying",
    "troubling me",
    "cheque bounced",
    "loan default",
    "bank notice",
    "credit card",
    "upi fraud",
    "accident",
    "drunk driving",
    "drink and drive",
    "rash driving",
    "negligent driving",
    "learner's license",
    "learner license",
    "learner licence",
    "driving licence",
    "driving license",
    "road accident",
    "traffic accident",
    "hit and run",
    "hit me",
    "hit my vehicle",
    "hit from behind",
    "rear ended",
    "rear-ended",
    "multiple injuries",
    "injury",
    "injured",
    "medical expenses",
    "insurance claim",
    "government inaction",
    "police not taking",
    "copyright copied",
    "trademark copied",
    "pollution",
    "company dispute",
    "director dispute",
    "tax notice",
    "gst notice",
    "income tax notice",
    "legal notice",
    "agreement draft",
    "petition",
]

_LEGAL_INTENT_PATTERNS: List[str] = [
    "what do i do",
    "what should i do",
    "what can i do",
    "is this legal",
    "is this illegal",
    "can i file",
    "can i complain",
    "can i sue",
    "what are my rights",
    "what is the law",
    "legal action",
    "where should i complain",
    "which court",
    "send notice",
    "file fir",
    "file complaint",
    "claim compensation",
]

_NON_LEGAL_EXCLUSIONS: List[str] = [
    "weather",
    "movie",
    "song",
    "recipe",
    "cricket score",
    "football score",
    "translate",
    "joke",
]


def is_indian_legal_query(query: str) -> bool:
    """Return True if the query appears to relate to Indian law."""
    q_lower = (query or "").lower()
    compact = re.sub(r"\s+", " ", q_lower).strip()

    if not compact:
        return False

    if any(term in compact for term in _INDIAN_LEGAL_KEYWORDS):
        return True

    has_problem_pattern = any(term in compact for term in _LEGAL_PROBLEM_PATTERNS)
    has_legal_intent = any(term in compact for term in _LEGAL_INTENT_PATTERNS)

    if has_problem_pattern:
        return True

    if has_legal_intent and not any(term in compact for term in _NON_LEGAL_EXCLUSIONS):
        return True

    return False


def build_indian_legal_model_query(query: str) -> str:
    """
    Rewrite legal-adjacent plain-language problems into explicit Indian-legal
    requests so model-side guardrails do not reject them as non-legal.
    """
    original = (query or "").strip()
    compact = re.sub(r"\s+", " ", original).strip()
    lowered = compact.lower()

    if not compact:
        return compact

    if any(term in lowered for term in _INDIAN_LEGAL_KEYWORDS):
        return compact

    if any(term in lowered for term in _LEGAL_PROBLEM_PATTERNS) or any(
        term in lowered for term in _LEGAL_INTENT_PATTERNS
    ):
        return (
            "Under Indian law, analyze this as a legal-help query. "
            "Use the Lawyer AI framework: intake facts, legal domain, assumptions, legal issues, "
            "evidence matrix, forum/remedies, risks, and immediate next steps. Explain the user's rights, "
            "possible offences or remedies, relevant Indian legal provisions, complaint options, and practical action plan.\n\n"
            f"User situation: {compact}"
        )

    return compact


def validate_query(query: str) -> Tuple[bool, str]:
    """
    Validate only the Indian legal scope.

    Returns:
        (is_valid, fallback_message)
    """
    if not is_indian_legal_query(query):
        logger.info("Query rejected: not Indian legal context.")
        return (
            False,
            "I can help with Indian legal and legal-adjacent issues such as police complaints, cyberbullying, harassment, fraud, hacking, family disputes, contracts, property, employment, and consumer matters.",
        )
    return (True, "")
