"""
Direct Bedrock invoke_model service for TLLAC chat flow.
Supports Mistral Large 3 chat/messages format on Amazon Bedrock.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
import re

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from ..utils.prompt_builder import get_system_prompt


_REPO_ROOT = Path(__file__).resolve().parents[3]
_STATUTE_INDEX_PATH = _REPO_ROOT / "tllac" / "app" / "data" / "statute_sections.json"
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


def _resolve_knowledge_base_id() -> str:
    return (
        os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
        or os.getenv("KNOWLEDGE_BASE_ID")
        or os.getenv("AWS_BEDROCK_KNOWLEDGE_BASE_ID")
        or ""
    ).strip()


def _knowledge_base_enabled() -> bool:
    return os.getenv("BEDROCK_KNOWLEDGE_BASE_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _clean_retrieval_query(query: str) -> str:
    """
    Keep KB search focused on the user's legal issue, not our internal prompt.
    RAG quality drops sharply if the vector query includes framework headings,
    instructions, disclaimers, or long conversation scaffolds.
    """
    query = re.sub(r"\s+", " ", (query or "")).strip()
    if not query:
        return ""

    markers = (
        "Client query:",
        "User query:",
        "New follow-up to answer:",
        "Original legal issue:",
    )
    for marker in markers:
        if marker in query:
            query = query.rsplit(marker, 1)[-1].strip()

    return query[:1200]


def _extract_query_signals(query: str) -> tuple[set[str], set[str]]:
    lowered = query.lower()
    acts: set[str] = set()

    if re.search(r"\b(bns|bharatiya nyaya)\b", lowered):
        acts.add("bns")
    if re.search(r"\b(bnss|bharatiya nagarik|nagrik suraksha)\b", lowered):
        acts.add("bnss")
    if re.search(r"\b(bsa|bharatiya sakshya)\b", lowered):
        acts.add("bsa")

    sections = set(re.findall(r"\b(?:section|sec\.?|s\.)\s*(\d+[a-z]?)\b", lowered))
    return acts, sections


@lru_cache(maxsize=1)
def _load_statute_index() -> list[dict[str, str]]:
    try:
        return json.loads(_STATUTE_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _build_exact_statute_context(query: str) -> str:
    query_acts, query_sections = _extract_query_signals(query)
    if not query_acts or not query_sections:
        return ""

    matches = [
        record
        for record in _load_statute_index()
        if record.get("act_key") in query_acts and record.get("section_number") in query_sections
    ]
    if not matches:
        return ""

    lines = ["Exact structured statute row from local BNS/BNSS/BSA sheets:"]
    for record in matches[:3]:
        lines.extend(
            [
                f"Act: {record.get('act_name') or record.get('act_key', '').upper()}",
                f"Section: {record.get('section', '')}",
                f"Title: {record.get('title', '')}",
                f"Description: {record.get('description', '')}",
                f"Punishment: {record.get('punishment', '')}",
                f"Keywords: {record.get('keywords', '')}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _chunk_rank(content: str, query_acts: set[str], query_sections: set[str]) -> int:
    lowered = content.lower()
    rank = 0

    act_terms = {
        "bns": ("bhartiya nyay sanhita", "bharatiya nyaya sanhita", "(bns)", " bns"),
        "bnss": ("bhartiya nagrik suraksha", "bharatiya nagarik suraksha", "(bnss)", " bnss"),
        "bsa": ("bhartiya sakshya", "bharatiya sakshya", "(bsa)", " bsa"),
    }
    for act in query_acts:
        if any(term in lowered for term in act_terms.get(act, ())):
            rank += 10

    for section in query_sections:
        section_heading_pattern = rf"(?:^|[\t\r\n])\s*Section\s+{re.escape(section)}\b"
        if re.search(section_heading_pattern, content):
            rank += 20
        elif re.search(rf"\bsection\s+{re.escape(section)}\b", lowered):
            rank += 2

    return rank


def _focus_chunk_content(content: str, query_sections: set[str]) -> str:
    if not query_sections:
        return content.strip()

    section_matches: list[tuple[re.Match[str], bool]] = []
    for section in query_sections:
        heading_matches = list(
            re.finditer(rf"(?:^|[\t\r\n])\s*Section\s+{re.escape(section)}\b", content)
        )
        if heading_matches:
            section_matches.extend((match, True) for match in heading_matches)
        else:
            section_matches.extend(
                (match, False)
                for match in re.finditer(rf"\bsection\s+{re.escape(section)}\b", content, re.IGNORECASE)
            )

    if not section_matches:
        return content.strip()

    snippets: list[str] = []
    for match, is_heading in sorted(section_matches, key=lambda item: item[0].start())[:3]:
        start = max(0, match.start() - (100 if is_heading else 450))
        end = min(len(content), match.end() + 1800)
        snippet = content[start:end].strip()
        if snippet:
            snippets.append(snippet)

    return "\n...\n".join(snippets) or content.strip()


def _retrieve_from_kb(query: str) -> str:
    retrieval_query = _clean_retrieval_query(query)
    if not retrieval_query:
        return ""

    exact_statute_context = _build_exact_statute_context(retrieval_query)

    if not _knowledge_base_enabled():
        return exact_statute_context

    kb_id = _resolve_knowledge_base_id()
    if not kb_id or kb_id == "PLACEHOLDER_REPLACE_ME":
        return exact_statute_context

    try:
        print(f"Retrieving context from Knowledge Base: {kb_id}")
        client = _build_bedrock_client(service_name="bedrock-agent-runtime")
        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": retrieval_query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": int(os.getenv("BEDROCK_KB_RESULTS", "20")),
                    "overrideSearchType": os.getenv("BEDROCK_KB_SEARCH_TYPE", "HYBRID"),
                }
            },
        )

        query_acts, query_sections = _extract_query_signals(retrieval_query)
        ranked_chunks: list[tuple[int, float, str]] = []
        for result in response.get("retrievalResults", []):
            content = result.get("content", {}).get("text", "")
            if content:
                local_rank = _chunk_rank(content, query_acts, query_sections)
                focused_content = _focus_chunk_content(content, query_sections)
                score = float(result.get("score") or 0)
                ranked_chunks.append((local_rank, score, focused_content))

        if not ranked_chunks:
            print("No context found in KB.")
            return ""

        ranked_chunks.sort(key=lambda item: (item[0], item[1]), reverse=True)
        max_chunks = int(os.getenv("BEDROCK_KB_CONTEXT_CHUNKS", "10"))
        max_chars = int(os.getenv("BEDROCK_KB_CONTEXT_CHARS", "22000"))

        selected: list[str] = []
        if exact_statute_context:
            selected.append(f"[Exact statute match]\n{exact_statute_context}")

        total_chars = 0
        for index, (local_rank, score, content) in enumerate(ranked_chunks[:max_chunks], start=1):
            remaining_chars = max_chars - total_chars
            if remaining_chars <= 0:
                break

            clipped_content = content[:remaining_chars]
            selected.append(
                f"[KB result {index}; local_rank={local_rank}; score={score:.4f}]\n{clipped_content}"
            )
            total_chars += len(clipped_content)

        print(
            f"Retrieved {len(ranked_chunks)} KB chunks; using {len(selected)} "
            f"chunks for query: {retrieval_query[:160]}"
        )
        return "\n\n".join(selected)
    except Exception as exc:
        print(f"Error retrieving from KB: {exc}")
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
    retrieval_query: str | None = None,
    use_knowledge_base: bool = True,
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
            kb_context = _retrieve_from_kb(retrieval_query or current_question) if use_knowledge_base else ""
            enhanced_question = current_question
            
            if kb_context:
                enhanced_question = (
                    "CRITICAL INSTRUCTION: You are operating in a professional, academic legal context. "
                    "Use ONLY the following search results from official Indian Acts to answer the user's question. "
                    "If the answer is not in the search results, state that clearly. "
                    "Do not use any markdown formatting like bold, italics, headers, or bullet points in your response. Provide the answer in plain text.\n\n"
                    "Search Results:\n"
                    f"{kb_context}\n\n"
                    f"User query: {current_question}"
                )

            current_kwargs = dict(invoke_kwargs)
            current_kwargs["body"] = _build_request_body(
                enhanced_question,
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
