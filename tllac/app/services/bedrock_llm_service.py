"""
Direct Bedrock invoke_model service for TLLAC chat flow.
Supports Mistral Large 3 chat/messages format on Amazon Bedrock.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from ..utils.prompt_builder import get_system_prompt


_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / "tllac" / ".env")


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


def _build_bedrock_client(service_name: str = "bedrock-runtime"):
    region = os.getenv("AWS_REGION") or os.getenv("BEDROCK_REGION")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")
    profile = os.getenv("AWS_PROFILE")

    client_kwargs = {}

    if region:
        client_kwargs["region_name"] = region

    if access_key and secret_key:
        client_kwargs["aws_access_key_id"] = access_key
        client_kwargs["aws_secret_access_key"] = secret_key

        if session_token:
            client_kwargs["aws_session_token"] = session_token

        return boto3.client(service_name, **client_kwargs)

    if profile:
        session = boto3.session.Session(profile_name=profile, region_name=region)
        return session.client(service_name)

    return boto3.client(service_name, **client_kwargs)


def _build_messages(
    user_question: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": get_system_prompt().strip(),
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
) -> str:
    return json.dumps(
        {
            "messages": _build_messages(user_question, conversation_history),
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
) -> str:
    print("Initializing Bedrock client...")

    try:
        client = _build_bedrock_client()
        model_id = _resolve_model_id()
        guardrail_id, guardrail_version = _resolve_guardrail_config()

        print(f"Using model: {model_id}")

        invoke_kwargs = {
            "modelId": model_id,
            "body": _build_request_body(user_question, conversation_history),
            "contentType": "application/json",
            "accept": "application/json",
        }

        if guardrail_id and guardrail_version:
            print(f"Applying guardrail: {guardrail_id} version {guardrail_version}")
            invoke_kwargs["guardrailIdentifier"] = guardrail_id
            invoke_kwargs["guardrailVersion"] = guardrail_version

        def invoke_once(current_question: str) -> str:
            current_kwargs = dict(invoke_kwargs)
            current_kwargs["body"] = _build_request_body(
                current_question,
                conversation_history,
            )

            print("Sending request to Bedrock...")
            response = client.invoke_model(**current_kwargs)

            print("Response received!")
            response_body = json.loads(response["body"].read())

            print(f"Response structure: {list(response_body.keys())}")

            return _extract_text(response_body) or json.dumps(response_body, indent=2)

        text = invoke_once(user_question)

        if _looks_like_scope_rejection(text):
            print("Retrying with stronger Indian legal framing...")

            retry_question = (
                "This is an Indian legal-help request. "
                "Do not reject it as out of scope. "
                "Analyze it under Indian law and provide the requested answer.\n\n"
                f"User query: {user_question}"
            )

            text = invoke_once(retry_question)

        return text

    except ClientError as exc:
        return f"AWS Client Error: {exc}"

    except Exception as exc:
        return f"Error: {exc}"
