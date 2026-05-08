"""
Deterministic first-pass legal query framework.

This module does not decide the final legal answer. It gives the LLM a
lawyer-style intake scaffold: likely domains, first legal buckets, evidence,
forums, and cautions to consider before applying legal judgment.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DomainMapping:
    domain: str
    triggers: tuple[str, ...]
    first_bucket: str
    statutes: tuple[str, ...]
    evidence: tuple[str, ...]
    forums: tuple[str, ...]
    remedies: tuple[str, ...]


_DOMAIN_MAPPINGS = (
    DomainMapping(
        domain="Criminal law",
        triggers=(
            "assault",
            "beaten",
            "hurt",
            "threat",
            "blackmail",
            "theft",
            "stolen",
            "forgery",
            "arrest",
            "fir",
            "police",
            "police station",
            "investigation",
            "complaint against me",
        ),
        first_bucket="criminal intimidation, hurt/assault, theft, cheating, forgery, police investigation procedure, arrest risk, or other BNS offence depending on facts",
        statutes=("Bharatiya Nyaya Sanhita, 2023", "Bharatiya Nagarik Suraksha Sanhita, 2023", "Bharatiya Sakshya Adhiniyam, 2023", "Prevention of Corruption Act, 1988 where a public servant demands illegal gratification"),
        evidence=("medical records", "witness details", "messages/calls", "CCTV", "complaint copies", "identity of accused", "notice/summons details", "proof of money demand"),
        forums=("local police station", "senior police officer/SP or DCP", "Magistrate", "Anti-Corruption Bureau/Vigilance", "Sessions Court/High Court where needed"),
        remedies=("police complaint/FIR", "written representation to senior officer", "protection from immediate harm", "bail/anticipatory bail if accused", "complaint against illegal gratification demand", "compensation where available"),
    ),
    DomainMapping(
        domain="Cyber law",
        triggers=("cyber", "online", "instagram", "facebook", "whatsapp", "telegram", "hacked", "fake profile", "impersonation", "morphed", "revenge porn", "account compromised"),
        first_bucket="cyber harassment, obscenity, impersonation, identity misuse, extortion, stalking, or privacy harm",
        statutes=("Information Technology Act, 2000", "Bharatiya Nyaya Sanhita, 2023", "Bharatiya Sakshya Adhiniyam, 2023"),
        evidence=("screenshots", "URLs", "profile links/usernames", "metadata", "device details", "transaction IDs", "platform reports"),
        forums=("National Cyber Crime Reporting Portal", "cyber cell", "local police station", "Magistrate"),
        remedies=("preserve electronic evidence", "platform takedown/report", "cyber complaint", "FIR where ingredients are met", "injunction/damages in serious cases"),
    ),
    DomainMapping(
        domain="Family law",
        triggers=("husband", "wife", "marriage", "divorce", "maintenance", "custody", "domestic violence", "dowry", "in-laws"),
        first_bucket="matrimonial dispute, domestic violence, maintenance, custody, divorce, or related criminal issue",
        statutes=("Protection of Women from Domestic Violence Act, 2005", "personal law/Special Marriage Act as applicable", "BNS/BNSS where criminal conduct exists"),
        evidence=("marriage documents", "messages", "medical records", "financial records", "child details", "witnesses", "prior complaints"),
        forums=("Family Court", "Magistrate under DV Act", "police", "mediation center"),
        remedies=("protection order", "residence/maintenance relief", "custody/visitation", "divorce or restitution strategy", "criminal complaint where justified"),
    ),
    DomainMapping(
        domain="Property law",
        triggers=("property", "possession", "land", "flat", "rent", "tenant", "landlord", "eviction", "partition", "title", "lease"),
        first_bucket="title dispute, possession dispute, tenancy issue, partition, injunction, or specific performance",
        statutes=("Transfer of Property Act, 1882", "Registration Act, 1908", "state rent law where applicable", "Specific Relief Act, 1963"),
        evidence=("title deed", "sale agreement", "rent agreement", "revenue/mutation records", "possession proof", "notices", "photos"),
        forums=("civil court", "rent authority/court where applicable", "revenue authority for records", "High Court in limited writ situations"),
        remedies=("legal notice", "injunction", "possession/title suit", "rent proceedings", "specific performance where available"),
    ),
    DomainMapping(
        domain="Contract/civil",
        triggers=("contract", "agreement", "breach", "not paying", "payment due", "recovery", "loaned", "promise", "invoice"),
        first_bucket="breach of contract, money recovery, specific performance, damages, or civil injunction",
        statutes=("Indian Contract Act, 1872", "Specific Relief Act, 1963", "Limitation Act, 1963"),
        evidence=("agreement", "invoices", "emails/messages", "payment proof", "delivery proof", "legal notices"),
        forums=("civil court", "commercial court where applicable", "arbitration if agreement provides", "mediation"),
        remedies=("demand notice", "recovery suit", "specific performance", "damages", "arbitration invocation"),
    ),
    DomainMapping(
        domain="Consumer law",
        triggers=("consumer", "refund", "defective", "warranty", "seller", "service", "order", "product", "ecommerce", "e-commerce"),
        first_bucket="deficiency in service, defective goods, unfair trade practice, refund/replacement/compensation",
        statutes=("Consumer Protection Act, 2019", "Consumer Protection (E-Commerce) Rules, 2020"),
        evidence=("bill/invoice", "warranty", "complaint history", "photos/videos", "delivery proof", "seller responses"),
        forums=("National Consumer Helpline", "e-Daakhil", "District/State/National Consumer Commission"),
        remedies=("pre-litigation grievance", "refund/replacement", "consumer complaint", "compensation and costs"),
    ),
    DomainMapping(
        domain="Employment law",
        triggers=("salary", "wages", "termination", "fired", "employer", "employee", "workplace", "hr", "pf", "gratuity"),
        first_bucket="unpaid salary, wrongful termination, workplace harassment, statutory dues, or contract claim",
        statutes=("labour codes/state shops and establishments law where applicable", "Industrial Disputes Act where applicable", "POSH Act where applicable", "Indian Contract Act, 1872"),
        evidence=("offer letter", "employment contract", "payslips", "attendance records", "termination email", "HR complaints", "bank statements"),
        forums=("Labour Commissioner", "Labour Court/Industrial Tribunal", "Internal Committee for POSH", "civil court for contract claims"),
        remedies=("salary demand", "labour complaint", "reinstatement/compensation where available", "internal complaint", "settlement/legal notice"),
    ),
    DomainMapping(
        domain="Banking/finance",
        triggers=("loan", "bank", "emi", "sarfaesi", "drt", "cheque", "bounce", "credit card", "upi", "transaction"),
        first_bucket="loan recovery, SARFAESI/DRT issue, cheque bounce, cyber payment fraud, or banking deficiency",
        statutes=("Negotiable Instruments Act, 1881", "SARFAESI Act, 2002", "Recovery of Debts and Bankruptcy Act, 1993", "IT Act, 2000 where cyber fraud exists"),
        evidence=("loan documents", "notices", "bank statements", "cheque and return memo", "payment IDs", "complaint records"),
        forums=("bank grievance channel", "RBI Ombudsman where applicable", "DRT/DRAT", "Magistrate/civil court", "cyber portal for fraud"),
        remedies=("reply to notice", "statutory compliance", "DRT appeal/application", "cheque notice/complaint", "fraud complaint"),
    ),
    DomainMapping(
        domain="Constitutional/writ",
        triggers=("government", "authority", "inaction", "writ", "fundamental right", "state authority", "police not taking"),
        first_bucket="administrative inaction, rights violation, mandamus, certiorari, habeas corpus, or alternative statutory remedy",
        statutes=("Constitution of India Articles 32 and 226", "relevant parent statute/rules"),
        evidence=("representations", "orders/notices", "RTI replies", "proof of authority inaction", "timeline"),
        forums=("High Court under Article 226", "Supreme Court under Article 32", "statutory appellate authority first where required"),
        remedies=("representation", "statutory appeal", "writ petition", "interim directions"),
    ),
    DomainMapping(
        domain="Motor accident/insurance",
        triggers=("accident", "vehicle", "insurance", "injury", "mact", "driver", "rash driving"),
        first_bucket="motor accident compensation, insurance claim, criminal rash/negligent driving issue",
        statutes=("Motor Vehicles Act, 1988", "BNS/BNSS where criminal offence exists"),
        evidence=("FIR", "MLC/medical records", "insurance policy", "vehicle details", "income proof", "disability certificate"),
        forums=("MACT", "police", "insurance grievance channel"),
        remedies=("MACT claim", "insurance claim", "interim compensation", "criminal complaint where applicable"),
    ),
)


_FALLBACK_INTAKE_FIELDS = (
    "parties, age, gender, and relationship",
    "act or omission complained of",
    "place/jurisdiction",
    "date/timeline and urgency",
    "available proof",
    "client's desired outcome",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _matches(mapping: DomainMapping, text: str) -> bool:
    return any(trigger in text for trigger in mapping.triggers)


def classify_domains(query: str) -> list[DomainMapping]:
    """Return likely first-pass domain mappings for the user's facts."""
    text = _normalize(query)
    if not text:
        return []

    matches = [mapping for mapping in _DOMAIN_MAPPINGS if _matches(mapping, text)]
    return matches[:3]


def build_lawyer_ai_framework_context(query: str) -> str:
    """
    Build compact instructions to prepend to the model query.

    The LLM must still reason independently and may reject or revise the
    preliminary mapping if the client's facts do not satisfy legal ingredients.
    """
    mappings = classify_domains(query)

    lines = [
        "Apply the universal Indian legal-query framework as Lawyer AI.",
        "First separate facts, assumptions, emotions, and missing information.",
        "Do not assume guilt, limitation, jurisdiction, contract validity, evidence sufficiency, or facts not stated.",
        "Use BNS, BNSS, and BSA for current Indian criminal-law framing where criminal issues arise.",
        "",
        "Intake fields to check:",
    ]
    lines.extend(f"- {field}" for field in _FALLBACK_INTAKE_FIELDS)

    if mappings:
        lines.extend(["", "Preliminary deterministic mapping, subject to legal judgment:"])
        for mapping in mappings:
            lines.extend(
                [
                    f"- Domain: {mapping.domain}",
                    f"  First legal bucket: {mapping.first_bucket}",
                    f"  Likely statutes: {', '.join(mapping.statutes)}",
                    f"  Evidence matrix: {', '.join(mapping.evidence)}",
                    f"  Possible forum/remedy path: {', '.join(mapping.forums)}; {', '.join(mapping.remedies)}",
                ]
            )
    else:
        lines.extend(
            [
                "",
                "No deterministic domain mapping was strong enough. Classify the legal domain from the facts before answering.",
            ]
        )

    lines.extend(
        [
            "",
            "Critical-thinking checks:",
            "- Is this legal, social/moral, civil, criminal, regulatory, or mixed?",
            "- What is the strongest cause of action and quickest practical remedy?",
            "- What evidence is admissible or weak, especially electronic evidence under BSA?",
            "- Which forum has jurisdiction, and is limitation or urgency an issue?",
            "- What risk exists if the client acts wrongly or makes unsupported allegations?",
            "",
            f"Client query: {query.strip()}",
        ]
    )
    return "\n".join(lines)
