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
from ..services.clarifying_service import get_clarifying_response
from ..services.validation_service import build_indian_legal_model_query, validate_query

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
    prior_history = db_client.get_recent_messages(session_id, limit=8)
    prior_user_messages = [
        message["content"]
        for message in prior_history
        if message.get("role") == "user" and message.get("content")
    ]
    combined_user_context = "\n".join([*prior_user_messages, query]).strip()
    db_client.append_message(session_id, "user", query)

    greeting_response = _get_greeting_response(query)
    if greeting_response:
        db_client.append_message(session_id, "assistant", greeting_response)
        return ChatResponse(response=greeting_response, session_id=session_id)

    is_valid, fallback_message = validate_query(combined_user_context)
    if not is_valid and not prior_history:
        db_client.append_message(session_id, "assistant", fallback_message)
        return ChatResponse(response=fallback_message, session_id=session_id)

    clarifying_response = get_clarifying_response(combined_user_context)
    if clarifying_response:
        logger.info("Returning clarifying questions instead of full analysis.")
        db_client.append_message(session_id, "assistant", clarifying_response)
        return ChatResponse(response=clarifying_response, session_id=session_id)

    conversation_history = prior_history
    model_query = build_indian_legal_model_query(query)
    if prior_history:
        original_issue = prior_user_messages[0] if prior_user_messages else "the previously discussed legal issue"
        model_query = (
            "This is a follow-up message in an ongoing Indian legal conversation in India. "
            "Do not reject it as non-legal or out of scope. "
            "Use the earlier issue and the new update together, and answer as part of the same Indian legal matter.\n\n"
            f"Original issue: {original_issue}\n"
            f"New follow-up from the user: {model_query}"
        )
    response_text = generate_response(model_query, conversation_history=conversation_history)
    if not response_text:
        response_text = "The legal language model did not return a response."

    db_client.append_message(session_id, "assistant", response_text)
    logger.info("Generated LLM-only response (%d chars).", len(response_text))
    return ChatResponse(response=response_text, session_id=session_id)
