"""
Unit tests for Agent Context, Orchestration and Command Routing (LAW-56).
"""

import pytest
from uuid import uuid4

from tllac.app.db.db_client import db_client
from tllac.app.services.agent_models import AgentCommand, AgentRunState
from tllac.app.services.agent_orchestrator import agent_orchestrator
from tllac.app.services.agent_tools import execute_approved_tool
from tllac.app.services.matter_context_service import matter_context_service


@pytest.fixture
def setup_matter():
    """Sets up a test user and test matter in memory db."""
    user_id = str(uuid4())
    db_client._memory_users[user_id] = {
        "user_id": user_id,
        "email": f"test_{user_id[:8]}@example.com",
        "hashed_password": "hashed_pass_test",
        "full_name": "Test Advocate",
    }
    matter = db_client.create_matter(
        user_id=user_id,
        title="Check Bounce Notice Case",
        description="Matter under Section 138 of Negotiable Instruments Act",
        case_number="CC 1042/2026",
        court="Metropolitan Magistrate Court, Delhi",
        stage="Pleadings",
    )
    matter_id = matter["matter_id"]
    return user_id, matter_id


def test_deterministic_command_parsing():
    """Verify slash commands are parsed deterministically without model calls."""
    assert agent_orchestrator.parse_command("/research Sec 138 case law")[0] == AgentCommand.RESEARCH
    assert agent_orchestrator.parse_command("/next")[0] == AgentCommand.NEXT
    assert agent_orchestrator.parse_command("/timeline")[0] == AgentCommand.TIMELINE
    assert agent_orchestrator.parse_command("/draft Notice document")[0] == AgentCommand.DRAFT
    assert agent_orchestrator.parse_command("/review check risk")[0] == AgentCommand.REVIEW
    assert agent_orchestrator.parse_command("/brief")[0] == AgentCommand.BRIEF
    assert agent_orchestrator.parse_command("/diary Schedule hearing")[0] == AgentCommand.DIARY
    # Default fallback
    assert agent_orchestrator.parse_command("Just general legal question")[0] == AgentCommand.RESEARCH


def test_ownership_validation_enforcement(setup_matter):
    """Verify context generation fails for unauthorized user_id."""
    user_id, matter_id = setup_matter
    unauthorized_user_id = str(uuid4())

    with pytest.raises(ValueError, match="Matter not found"):
        matter_context_service.build_matter_context(unauthorized_user_id, matter_id)

    res = agent_orchestrator.run_agent(unauthorized_user_id, matter_id, "/next")
    assert res.status == AgentRunState.FAILED
    assert "Matter not found" in (res.error_text or "")


def test_approved_tool_registry_security(setup_matter):
    """Verify only approved tools can be executed and unapproved tools throw an error."""
    user_id, matter_id = setup_matter

    # Approved tool execution
    res = execute_approved_tool("get_matter", {}, user_id, matter_id)
    assert res["matter_id"] == matter_id

    # Unapproved tool execution must raise ValueError
    with pytest.raises(ValueError, match="not in the approved tool registry"):
        execute_approved_tool("drop_tables_tool", {}, user_id, matter_id)


def test_timeline_command_deterministic_execution(setup_matter):
    """Verify /timeline runs deterministically with 0 Bedrock tokens and audits run."""
    user_id, matter_id = setup_matter

    # Add a hearing and event first
    db_client.create_matter_hearing(
        user_id=user_id,
        matter_id=matter_id,
        title="First Framing Hearing",
        court="Court 3",
    )

    res = agent_orchestrator.run_agent(user_id, matter_id, "/timeline")
    assert res.status == AgentRunState.COMPLETED
    assert res.token_count == 0  # 0 LLM tokens
    assert "Matter Timeline" in res.output_text
    assert len(res.tool_calls) > 0


def test_next_command_execution(setup_matter):
    """Verify /next command collects open tasks and hearings."""
    user_id, matter_id = setup_matter

    db_client.create_matter_task(
        user_id=user_id,
        matter_id=matter_id,
        title="File Evidence Affidavit",
        priority="high",
    )

    res = agent_orchestrator.run_agent(user_id, matter_id, "/next")
    assert res.status == AgentRunState.COMPLETED
    assert "File Evidence Affidavit" in res.output_text


def test_diary_command_execution(setup_matter):
    """Verify /diary creates task/hearing entry via approved tool."""
    user_id, matter_id = setup_matter

    res = agent_orchestrator.run_agent(user_id, matter_id, "/diary File Written Statement")
    assert res.status == AgentRunState.COMPLETED
    assert "File Written Statement" in res.output_text

    tasks = db_client.list_matter_tasks(user_id, matter_id)
    assert any(t["title"] == "File Written Statement" for t in tasks)


def test_conversation_history_truncation(setup_matter):
    """Verify older conversation history is truncated to fit token limits."""
    user_id, matter_id = setup_matter

    long_history = [
        {"role": "user", "content": f"Message number {i} " + "legal details " * 20}
        for i in range(50)
    ]

    ctx = matter_context_service.build_matter_context(
        user_id=user_id,
        matter_id=matter_id,
        conversation_history=long_history,
        max_tokens=2000,
    )

    assert ctx.estimated_tokens <= 3000
    assert "Message number 49" in ctx.compact_conversation_summary
