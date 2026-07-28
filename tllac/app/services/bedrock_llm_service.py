"""
Direct Bedrock invoke_model service for TLLAC chat flow.
Supports Mistral Large 3 chat/messages format on Amazon Bedrock.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import dotenv_values, load_dotenv

from ..utils.prompt_builder import get_system_prompt


logger = logging.getLogger("tllac.services.bedrock")
_REPO_ROOT = Path(__file__).resolve().parents[3]
#load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / "tllac" / ".env")
_DOTENV_PATH = _REPO_ROOT / "tllac" / ".env"
_DOTENV_VALUES = {
    key: value
    for key, value in dotenv_values(_DOTENV_PATH).items()
    if value is not None
}


def _resolve_model_id() -> str:
    return (
        os.getenv("MODEL_ID")
        or os.getenv("TLLAC_MODEL_ID")
        or os.getenv("LEGAL_MODEL_ID")
        or os.getenv("BEDROCK_MODEL_ID")
        or os.getenv("BEDROCK_MODEL")
        or "mistral.mistral-large-3-675b-instruct"
    )


def _resolve_guardrail_config() -> tuple[str, str] | tuple[None, None]:
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID") or os.getenv("GUARDRAIL_ID")
    guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION") or os.getenv("GUARDRAIL_VERSION")

    if not guardrail_id or not guardrail_version:
        return (None, None)

    normalized_version = guardrail_version.strip()
    if normalized_version.lower().startswith("v") and normalized_version[1:].isdigit():
        normalized_version = normalized_version[1:]

    return (guardrail_id.strip(), normalized_version)


def _get_setting(*names: str) -> str | None:
    for name in names:
        value = _DOTENV_VALUES.get(name)
        if value and str(value).strip():
            return str(value).strip()

    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()

    return None


def _resolve_aws_credentials() -> tuple[dict[str, str], str]:
    region = _get_setting("AWS_REGION", "BEDROCK_REGION")
    profile = _get_setting("AWS_PROFILE")

    dotenv_access_key = _DOTENV_VALUES.get("AWS_ACCESS_KEY_ID")
    dotenv_secret_key = _DOTENV_VALUES.get("AWS_SECRET_ACCESS_KEY")
    dotenv_session_token = _DOTENV_VALUES.get("AWS_SESSION_TOKEN")

    if dotenv_access_key and dotenv_secret_key:
        credentials = {
            "aws_access_key_id": dotenv_access_key.strip(),
            "aws_secret_access_key": dotenv_secret_key.strip(),
        }
        if dotenv_session_token and dotenv_session_token.strip():
            credentials["aws_session_token"] = dotenv_session_token.strip()
        if region:
            credentials["region_name"] = region
        return credentials, "tllac/.env"

    env_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    env_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    env_session_token = os.getenv("AWS_SESSION_TOKEN")

    if env_access_key and env_secret_key:
        credentials = {
            "aws_access_key_id": env_access_key.strip(),
            "aws_secret_access_key": env_secret_key.strip(),
        }
        if env_session_token and env_session_token.strip():
            credentials["aws_session_token"] = env_session_token.strip()
        if region:
            credentials["region_name"] = region
        return credentials, "environment"

    if profile:
        credentials = {"profile_name": profile}
        if region:
            credentials["region_name"] = region
        return credentials, "profile"

    credentials = {}
    if region:
        credentials["region_name"] = region
    return credentials, "default"


def _build_bedrock_client(service_name: str = "bedrock-runtime"):
    client_kwargs, credential_source = _resolve_aws_credentials()

    if credential_source == "profile":
        session = boto3.session.Session(
            profile_name=client_kwargs["profile_name"],
            region_name=client_kwargs.get("region_name"),
        )
        return session.client(service_name), credential_source

    return boto3.client(service_name, **client_kwargs), credential_source


def _build_messages(
    user_question: str,
    conversation_history: list[dict[str, str]] | None = None,
    system_prompt_override: str | None = None,
) -> list[dict[str, str]]:
    system_content = system_prompt_override.strip() if system_prompt_override else get_system_prompt().strip()
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": system_content,
        }
    ]

    for message in conversation_history or []:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", "")).strip()

        if role in {"user", "assistant"} and content:
            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    messages.append(
        {
            "role": "user",
            "content": user_question.strip(),
        }
    )

    return messages


def _build_request_body(
    user_question: str,
    conversation_history: list[dict[str, str]] | None = None,
    system_prompt_override: str | None = None,
) -> str:
    return json.dumps(
        {
            "messages": _build_messages(user_question, conversation_history, system_prompt_override),
            "max_tokens": int(os.getenv("MAX_TOKENS", "4000")),
            "temperature": float(os.getenv("TEMPERATURE", "0.7")),
            "top_p": float(os.getenv("TOP_P", "0.9")),
        }
    )


def _extract_text(response_body: dict) -> str:
    if "choices" in response_body and response_body["choices"]:
        choice = response_body["choices"][0]

        if "message" in choice and "content" in choice["message"]:
            return str(choice["message"]["content"]).strip()

        if "text" in choice:
            return str(choice["text"]).strip()

    if "outputs" in response_body and response_body["outputs"]:
        return str(response_body["outputs"][0].get("text", "")).strip()

    if "generation" in response_body:
        return str(response_body["generation"]).strip()

    if "text" in response_body:
        return str(response_body["text"]).strip()

    if "completion" in response_body:
        return str(response_body["completion"]).strip()

    return ""


def _extract_token_count(response_body: dict, fallback_text: str = "") -> int:
    """Return the exact token count from Bedrock's usage field.

    Bedrock (Mistral and most other models) returns a ``usage`` dict in the
    response body with ``input_tokens`` and ``output_tokens``.  We sum both
    because we want to track the total tokens billed per call.

    Falls back to the 4-chars-per-token heuristic only when the usage field
    is absent (e.g. older model versions or unexpected response shapes).
    """
    usage = response_body.get("usage") or {}
    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
    output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")

    if input_tokens is not None and output_tokens is not None:
        total = max(1, int(input_tokens) + int(output_tokens))
        logger.info(
            "Bedrock token usage — input: %d, output: %d, total: %d",
            int(input_tokens), int(output_tokens), total,
        )
        return total

    # Fallback: char/4 heuristic on the returned text only
    fallback = max(1, len(fallback_text) // 4)
    logger.warning(
        "Bedrock usage field missing from response (keys: %s). "
        "Falling back to char/4 heuristic → %d tokens.",
        list(response_body.keys()),
        fallback,
    )
    return fallback


def _looks_like_scope_rejection(text: str) -> bool:
    normalized = (text or "").strip().lower()

    rejection_markers = [
        "i can only assist with indian legal queries",
        "please ask a question related to indian law",
        "out of context",
        "indian legal queries such as laws, cases, and legal concepts",
    ]

    return any(marker in normalized for marker in rejection_markers)


def generate_response(
    user_question: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, int]:
    """Call Bedrock and return (response_text, tokens_used).

    *tokens_used* is the sum of input + output tokens as reported by Bedrock.
    Falls back to a char/4 heuristic if the usage field is absent.
    """
    try:
        client, _credential_source = _build_bedrock_client()
        model_id = _resolve_model_id()
        guardrail_id, guardrail_version = _resolve_guardrail_config()

        logger.info("Preparing Bedrock request for model '%s'.", model_id)

        invoke_kwargs = {
            "modelId": model_id,
            "body": _build_request_body(user_question, conversation_history),
            "contentType": "application/json",
            "accept": "application/json",
        }

        if guardrail_id and guardrail_version:
            logger.info("Applying configured Bedrock guardrail.")
            invoke_kwargs["guardrailIdentifier"] = guardrail_id
            invoke_kwargs["guardrailVersion"] = guardrail_version

        def invoke_once(current_question: str) -> tuple[str, int]:
            current_kwargs = dict(invoke_kwargs)
            current_kwargs["body"] = _build_request_body(
                current_question,
                conversation_history,
            )

            response = client.invoke_model(**current_kwargs)
            response_body = json.loads(response["body"].read())
            logger.info("Received Bedrock response payload.")

            extracted = _extract_text(response_body) or json.dumps(response_body, indent=2)
            tokens = _extract_token_count(response_body, fallback_text=extracted)
            return extracted, tokens

        text, tokens_used = invoke_once(user_question)

        if _looks_like_scope_rejection(text):
            logger.info("Retrying Bedrock request with stronger Indian legal framing.")

            retry_question = (
                "This is an Indian legal-help request. "
                "Do not reject it as out of scope. "
                "Analyze it under Indian law and provide the requested answer.\n\n"
                f"User query: {user_question}"
            )

            retry_text, retry_tokens = invoke_once(retry_question)
            # Accumulate tokens from both the initial and retry call
            return retry_text, tokens_used + retry_tokens

        return text, tokens_used

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        logger.exception("Bedrock client error during response generation.")
        if error_code == "UnrecognizedClientException":
            return (
                "The legal language model could not authenticate with the configured AI provider. "
                "Check the Bedrock credentials and region in the environment configuration.",
                0,
            )
        return "The legal language model is temporarily unavailable due to an upstream service error.", 0

    except Exception as exc:
        logger.exception("Unexpected error during Bedrock response generation.")
        return "The legal language model is temporarily unavailable. Please try again.", 0


def generate_notice_response(
    user_question: str,
    system_prompt: str,
    apply_guardrails: bool = False,
) -> tuple[str, int]:
    """Generate a response using a custom system prompt (used for notice and document drafting).

    Unlike ``generate_response``, this function replaces the default Lawyer AI
    system prompt with the caller-supplied *system_prompt* so the model receives
    clean, uncontradicted instructions for notice and document generation.
    By default, guardrails are disabled (`apply_guardrails=False`) so form inputs
    and legal drafting are not rejected by chat guardrail filters.

    Returns (response_text, tokens_used) where tokens_used is the exact sum of
    Bedrock input + output tokens (falls back to char/4 heuristic if unavailable).
    """
    try:
        client, _credential_source = _build_bedrock_client()
        model_id = _resolve_model_id()
        guardrail_id, guardrail_version = _resolve_guardrail_config() if apply_guardrails else (None, None)

        logger.info("Preparing Bedrock notice/document request for model '%s'.", model_id)

        invoke_kwargs = {
            "modelId": model_id,
            "contentType": "application/json",
            "accept": "application/json",
        }

        if guardrail_id and guardrail_version:
            invoke_kwargs["guardrailIdentifier"] = guardrail_id
            invoke_kwargs["guardrailVersion"] = guardrail_version

        def invoke_once(current_question: str) -> tuple[str, int]:
            current_kwargs = dict(invoke_kwargs)
            body = _build_request_body(current_question, None, system_prompt)
            response = client.invoke_model(**current_kwargs, body=body)
            response_body = json.loads(response["body"].read())
            logger.info("Received Bedrock notice/document response payload.")

            extracted = _extract_text(response_body) or json.dumps(response_body, indent=2)
            tokens = _extract_token_count(response_body, fallback_text=extracted)
            return extracted, tokens

        text, tokens_used = invoke_once(user_question)

        if _looks_like_scope_rejection(text):
            logger.info("Retrying Bedrock notice/document drafting request with explicit Indian legal drafting framing.")
            retry_question = (
                "Draft the requested Indian legal document using only the details provided below. "
                "Do not refuse or reject this request as out of scope. "
                "Output only the complete formal legal document text.\n\n"
                f"{user_question}"
            )
            invoke_kwargs.pop("guardrailIdentifier", None)
            invoke_kwargs.pop("guardrailVersion", None)
            retry_text, retry_tokens = invoke_once(retry_question)
            return retry_text, tokens_used + retry_tokens

        return text, tokens_used

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        logger.exception("Bedrock client error during notice generation.")
        if error_code == "UnrecognizedClientException":
            return (
                "The legal language model could not authenticate with the configured AI provider. "
                "Check the Bedrock credentials and region in the environment configuration.",
                0,
            )
        return "The legal language model is temporarily unavailable due to an upstream service error.", 0

    except Exception as exc:
        logger.exception("Unexpected error during Bedrock notice generation.")
        return "The legal language model is temporarily unavailable. Please try again.", 0

