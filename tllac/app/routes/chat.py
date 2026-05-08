"""
Chat route for the new LLM-only TLLAC flow.

Request:
  { "query": "..." }

Response:
  { "response": "..." }
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
import re

from ..db.db_client import db_client
from ..services.bedrock_llm_service import generate_response
from ..services.legal_framework import build_lawyer_ai_framework_context
from ..services.online_legal_research import build_online_legal_research_context
from ..services.validation_service import (
    build_indian_legal_model_query,
    is_indian_legal_query,
    validate_query,
)

logger = logging.getLogger("tllac.routes.chat")
logging.basicConfig(level=logging.INFO)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        max_length=4000,
        description="The user's legal query.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional chat session id for remembering previous messages.",
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="LLM response or fallback message.")
    session_id: str = Field(..., description="Chat session id.")
    recommend_legal_notice: bool = Field(
        default=False,
        description="Whether the frontend should offer legal notice generation.",
    )
    notice_prefill: str | None = Field(
        default=None,
        description="Case details to prefill when generating a legal notice from chat.",
    )


_GREETING_RESPONSES = {
    "hi": "Hi.",
    "hello": "Hello.",
    "hey": "Hey.",
    "good morning": "Good morning.",
    "good afternoon": "Good afternoon.",
    "good evening": "Good evening.",
}


def _normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _get_greeting_response(query: str) -> str | None:
    normalized = _normalize_query(query).lower().rstrip("!.?")
    return _GREETING_RESPONSES.get(normalized)


def _is_illegal_bribe_facilitation_query(query: str) -> bool:
    lowered = _normalize_query(query).lower()
    if not any(term in lowered for term in ("bribe", "pay money", "give money", "cash payment")):
        return False

    public_authority_terms = ("judge", "police", "officer", "public servant", "court staff")
    facilitation_terms = ("can i", "how to", "how can i", "way to", "help me")
    return any(term in lowered for term in public_authority_terms) and any(
        term in lowered for term in facilitation_terms
    )


def _is_police_legal_help_query(query: str) -> bool:
    lowered = _normalize_query(query).lower()
    if "police" not in lowered:
        return False

    money_demand_terms = (
        "asking for money",
        "asked for money",
        "demanding money",
        "demanded money",
        "bribe",
        "illegal gratification",
        "close a complaint",
        "settle the complaint",
    )
    attendance_terms = (
        "come to police station",
        "called me to police station",
        "calling me to police station",
        "help in an investigation",
        "for investigation",
        "against a complaint against me",
    )

    return any(term in lowered for term in money_demand_terms) or any(
        term in lowered for term in attendance_terms
    )


def _is_motor_accident_legal_help_query(query: str) -> bool:
    lowered = _normalize_query(query).lower()
    accident_terms = (
        "accident",
        "drunk driving",
        "drink and drive",
        "rash driving",
        "negligent driving",
        "hit me",
        "hit my vehicle",
        "hit from behind",
        "rear ended",
        "rear-ended",
        "injury",
        "injured",
        "multiple injuries",
    )
    vehicle_terms = (
        "car",
        "bike",
        "motorcycle",
        "scooter",
        "vehicle",
        "driver",
        "driving",
        "licence",
        "license",
        "learner",
    )
    return any(term in lowered for term in accident_terms) and any(
        term in lowered for term in vehicle_terms
    )


def _should_recommend_legal_notice(text: str) -> bool:
    lowered = _normalize_query(text).lower()
    if not lowered:
        return False

    legal_notice_domains = (
        "refund",
        "payment",
        "not paying",
        "unpaid",
        "salary",
        "rent",
        "tenant",
        "landlord",
        "property",
        "contract",
        "agreement",
        "breach",
        "consumer",
        "defective",
        "service",
        "cheque",
        "defamation",
        "harassment",
        "employer",
        "employee",
        "vendor",
        "builder",
        "loan",
        "notice",
    )
    excluded_domains = (
        "arrest",
        "bail",
        "fir",
        "police is asking",
        "come to police station",
        "bribe",
        "illegal gratification",
        "habeas corpus",
    )

    return any(term in lowered for term in legal_notice_domains) and not any(
        term in lowered for term in excluded_domains
    )


def _is_general_section_explanation_query(query: str) -> bool:
    lowered = _normalize_query(query).lower()
    if not re.search(r"\b(section|sec\.?|s\.)\s*\d+[a-z]?\b", lowered):
        return False

    explanation_terms = (
        "explain",
        "what is",
        "meaning",
        "define",
        "overview",
        "tell me about",
        "bare act",
    )
    case_specific_terms = (
        "against me",
        "file",
        "complaint",
        "fir",
        "police",
        "notice",
        "bail",
        "arrest",
        "what do i do",
        "my case",
        "my friend",
        "my client",
    )

    return any(term in lowered for term in explanation_terms) and not any(
        term in lowered for term in case_specific_terms
    )


def _is_general_explanation_query(query: str) -> bool:
    lowered = _normalize_query(query).lower().strip(" ?!.")

    explanation_starts = (
        "what is ",
        "what are ",
        "explain ",
        "explain this",
        "explain that",
        "meaning of ",
        "define ",
        "tell me about ",
        "give an overview of ",
        "overview of ",
    )
    case_specific_terms = (
        "against me",
        "against my",
        "my case",
        "my client",
        "my friend",
        "my company",
        "what do i do",
        "what should i do",
        "can i file",
        "file a complaint",
        "file fir",
        "police",
        "arrest",
        "bail",
        "notice received",
        "summons",
        "sent me",
        "asking me",
        "threatening me",
    )

    if _is_general_section_explanation_query(query):
        return True

    return lowered.startswith(explanation_starts) and not any(
        term in lowered for term in case_specific_terms
    )


def _find_original_legal_issue(messages: list[dict[str, str]], fallback: str) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        content = _normalize_query(message.get("content", ""))
        if content and is_indian_legal_query(content):
            return content
    return fallback


def _build_user_timeline(messages: list[dict[str, str]], current_query: str) -> str:
    user_turns = [
        _normalize_query(message.get("content", ""))
        for message in messages
        if message.get("role") == "user" and _normalize_query(message.get("content", ""))
    ]
    user_turns.append(current_query)
    recent_turns = user_turns[-16:]
    return "\n".join(f"{index + 1}. {turn}" for index, turn in enumerate(recent_turns))


def _latest_assistant_question_context(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        content = _normalize_query(message.get("content", ""))
        if "?" in content:
            return content[-1800:]
    return ""


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    LLM-only chat endpoint for the new UI.
    """
    query = _normalize_query(request.query)
    logger.info("Incoming query: %s", query[:120])

    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    session_id = db_client.ensure_session(request.session_id, title_hint=query)
    full_prior_history = db_client.get_messages(session_id)
    prior_history = db_client.get_messages(session_id, limit=14)
    prior_user_messages = [
        message["content"]
        for message in full_prior_history
        if message.get("role") == "user" and message.get("content")
    ]
    combined_user_context = "\n".join([*prior_user_messages, query]).strip()
    db_client.append_message(session_id, "user", query)

    greeting_response = _get_greeting_response(query)
    if greeting_response:
        db_client.append_message(session_id, "assistant", greeting_response)
        return ChatResponse(response=greeting_response, session_id=session_id)

    if _is_illegal_bribe_facilitation_query(query):
        fallback_message = "I can help with Indian legal and legal-adjacent issues such as police complaints, cyberbullying, harassment, fraud, hacking, family disputes, contracts, property, employment, and consumer matters."
        db_client.append_message(session_id, "assistant", fallback_message)
        return ChatResponse(response=fallback_message, session_id=session_id)

    original_legal_issue = _find_original_legal_issue(full_prior_history, query)
    session_legal_context = "\n".join([original_legal_issue, combined_user_context]).strip()
    is_valid, fallback_message = validate_query(session_legal_context)
    if not is_valid and not full_prior_history:
        db_client.append_message(session_id, "assistant", fallback_message)
        return ChatResponse(response=fallback_message, session_id=session_id)

    is_general_explanation = _is_general_explanation_query(query)
    conversation_history = [] if is_general_explanation else prior_history
    if is_general_explanation:
        model_query = (
            "Answer directly and concisely as an Indian legal assistant. "
            "This is a general legal explanation query, not a case intake and not a follow-up requiring facts. "
            "Do not use headings such as Short Classification, Intake Extraction, Known Facts, Missing Facts, "
            "Evidence, Remedies and Forum, Risk, Next Step, Disclaimer, or Follow-Up Questions. "
            "Do not ask any follow-up questions. "
            "Use this compact structure only: meaning, key elements, legal effect, simple example, and current-law note "
            "where relevant. Keep it practical and under 450 words.\n\n"
            f"User query: {query}"
        )
    else:
        model_query = build_lawyer_ai_framework_context(build_indian_legal_model_query(query))

    if _is_police_legal_help_query(query):
        model_query = (
            "This is a valid Indian legal-help query involving police procedure, complaint handling, "
            "possible illegal gratification/extortion by a public servant, and/or the user's rights while "
            "being called for investigation. Do not reject it as non-legal. Do not provide instructions "
            "to bribe or evade lawful investigation. Provide Indian legal guidance, practical next steps, "
            "risk cautions, evidence preservation, and escalation options.\n\n"
            f"{model_query}"
        )

    if _is_motor_accident_legal_help_query(session_legal_context):
        model_query = (
            "This is a valid Indian motor accident and criminal-law legal-help query. "
            "Do not reject it as non-legal or merely conceptual. Analyze it under Indian law for a victim "
            "hit by a drunk/rash/negligent driver, including learner licence implications where relevant. "
            "Cover immediate medical/legal steps, MLC, police complaint/FIR, relevant BNS/BNSS issues in substance, "
            "Motor Vehicles Act/MACT compensation, insurance claim, evidence preservation, limitation/urgency, "
            "and practical next actions. If exact provisions are uncertain, describe the law in substance instead "
            "of inventing section numbers. For rash driving or riding on a public way, use BNS Section 281. "
            "For an act endangering life or personal safety, consider BNS Section 125 only if supported by facts. "
            "For death by negligence, use BNS Section 106 only if death occurred. Do not cite IPC section numbers "
            "as current BNS sections.\n\n"
            f"{model_query}"
        )

    online_research_context = (
        "" if is_general_explanation else build_online_legal_research_context(session_legal_context)
    )
    if online_research_context:
        model_query = f"{model_query}\n\n{online_research_context}"

    if full_prior_history and not is_general_explanation:
        user_timeline = _build_user_timeline(full_prior_history, query)
        latest_questions = _latest_assistant_question_context(full_prior_history)
        model_query = (
            "This is a follow-up message in an ongoing Indian legal conversation in India. "
            "Do not reject it as non-legal or out of scope. "
            "The user's latest message may be a short answer such as yes/no/place/name; interpret it against "
            "the prior assistant questions and the user timeline below. Do not ask questions that the user has "
            "already answered in the timeline. Update known facts incrementally and continue the legal guidance. "
            "If enough facts are available, give the next practical step instead of repeating intake analysis. "
            "Do not invent legal sections; if you are not sure of the exact provision, describe the law in "
            "substance instead.\n\n"
            f"Original legal issue: {original_legal_issue}\n\n"
            f"User answer timeline:\n{user_timeline}\n\n"
            f"Latest assistant questions/context:\n{latest_questions or '[No prior assistant questions found]'}\n\n"
            f"New follow-up to answer:\n{query}\n\n"
            f"Legal analysis scaffold for this turn:\n{model_query}"
        )
    retrieval_query = session_legal_context if full_prior_history and not is_general_explanation else query
    if _is_motor_accident_legal_help_query(session_legal_context):
        retrieval_query = f"{retrieval_query}\nBNS section 281 rash driving\nBNS section 125 act endangering life"
    response_text = generate_response(
        model_query,
        conversation_history=conversation_history,
        retrieval_query=retrieval_query,
    )
    if not response_text:
        response_text = "The legal language model did not return a response."

    db_client.append_message(session_id, "assistant", response_text)
    logger.info("Generated LLM-only response (%d chars).", len(response_text))
    recommend_legal_notice = _should_recommend_legal_notice(combined_user_context)
    notice_prefill = combined_user_context if recommend_legal_notice else None
    return ChatResponse(
        response=response_text,
        session_id=session_id,
        recommend_legal_notice=recommend_legal_notice,
        notice_prefill=notice_prefill,
    )
