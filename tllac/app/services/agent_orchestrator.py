"""
Agent Orchestrator service enforcing deterministic command routing,
state lifecycle transitions, token cost bounds, and auditable tool execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any

from ..db.db_client import db_client
from .agent_models import AgentCommand, AgentRunResponse, AgentRunState, ToolCallRecord
from .agent_tools import execute_approved_tool
from .bedrock_llm_service import generate_response
from .research_service import run_research
from .matter_context_service import matter_context_service

logger = logging.getLogger("tllac.services.agent_orchestrator")


class AgentOrchestrator:
    """Orchestrates agent runs deterministically without model classification."""

    def parse_command(self, raw_input: str) -> tuple[AgentCommand, str]:
        """
        Deterministically parses slash command from input text in application code.
        Defaults to /research if no command slash prefix is provided.
        """
        stripped = raw_input.strip()
        match = re.match(r"^(/([a-zA-Z0-9_-]+))(?:\s+(.*))?$", stripped, re.DOTALL)
        if not match:
            # Default to /research if free text query
            return AgentCommand.RESEARCH, stripped

        cmd_str = match.group(1).lower()
        query_text = (match.group(3) or "").strip()

        for valid_cmd in AgentCommand:
            if valid_cmd.value.lower() == cmd_str:
                return valid_cmd, query_text

        # Unknown slash command defaults to research
        return AgentCommand.RESEARCH, stripped

    def run_agent(
        self,
        user_id: str,
        matter_id: str,
        raw_input: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> AgentRunResponse:
        """
        Executes an agent run for a matter with deterministic routing, state tracking,
        context assembly, approved tool invocation, and complete persistence auditing.
        """
        # 1. Deterministic Application-Code Parsing (NO model call!)
        command, query = self.parse_command(raw_input)
        logger.info(f"Routed command '{command.value}' deterministically for matter '{matter_id}'")

        tool_call_records: list[ToolCallRecord] = []
        total_tokens = 0

        # 2. Strict Ownership Validation FIRST
        try:
            db_client.get_matter(user_id, matter_id)
        except ValueError as val_err:
            logger.error(f"Ownership validation failed for matter '{matter_id}': {val_err}")
            return AgentRunResponse(
                agent_run_id="",
                user_id=user_id,
                matter_id=matter_id,
                command=command.value,
                status=AgentRunState.FAILED,
                error_text=str(val_err),
                token_count=0,
                tool_calls=[],
            )

        # 3. State: CREATED (persisted in DB)
        run_record = db_client.create_agent_run(
            user_id=user_id,
            matter_id=matter_id,
            command=command.value,
            input_text=raw_input,
            status=AgentRunState.CREATED.value,
            model_id="mistral.mistral-large-3-675b-instruct",
        )
        agent_run_id = run_record["agent_run_id"]

        try:
            # Context Assembly -> State: CONTEXT_READY
            context = matter_context_service.build_matter_context(
                user_id=user_id,
                matter_id=matter_id,
                conversation_history=conversation_history,
                max_tokens=3000,
            )
            context_snapshot = context.model_dump()

            db_client.update_agent_run(
                user_id=user_id,
                matter_id=matter_id,
                agent_run_id=agent_run_id,
                status=AgentRunState.CONTEXT_READY.value,
            )

            # Helper for auditable tool calls
            def log_and_exec_tool(tool_name: str, args: dict[str, Any]) -> Any:
                tc_rec = db_client.create_agent_tool_call(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    tool_name=tool_name,
                    input_payload=args,
                    status="started",
                )
                try:
                    res = execute_approved_tool(tool_name, args, user_id=user_id, matter_id=matter_id)
                    db_client._v1_list_related  # touch check
                    # Update tool call status
                    if db_client._backend != "postgres":
                        db_client._memory_v1_tables["agent_tool_calls"][tc_rec["tool_call_id"]].update({
                            "status": "completed",
                            "output_payload": res if isinstance(res, dict) else {"result": res},
                            "completed_at": db_client._now(),
                        })
                    tool_call_records.append(
                        ToolCallRecord(
                            tool_call_id=tc_rec["tool_call_id"],
                            tool_name=tool_name,
                            status="completed",
                            input_payload=args,
                            output_payload=res if isinstance(res, dict) else {"result": res},
                        )
                    )
                    return res
                except Exception as ex:
                    logger.error(f"Tool execution error for {tool_name}: {ex}")
                    if db_client._backend != "postgres":
                        db_client._memory_v1_tables["agent_tool_calls"][tc_rec["tool_call_id"]].update({
                            "status": "failed",
                            "error_text": str(ex),
                            "completed_at": db_client._now(),
                        })
                    tool_call_records.append(
                        ToolCallRecord(
                            tool_call_id=tc_rec["tool_call_id"],
                            tool_name=tool_name,
                            status="failed",
                            input_payload=args,
                            error_text=str(ex),
                        )
                    )
                    raise ex

            # 4. Command Workflows Execution
            output_text = ""
            final_state = AgentRunState.COMPLETED

            if command == AgentCommand.TIMELINE:
                # Deterministic execution (0 Bedrock tokens)
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                events = log_and_exec_tool("save_timeline", {"event_type": "view", "title": "Timeline Requested", "description": query or "Viewed timeline"})
                all_events = db_client.list_matter_events(user_id, matter_id)
                output_text = f"### Matter Timeline: {context.title}\n\n"
                if not all_events:
                    output_text += "No timeline events recorded yet.\n"
                else:
                    output_text += "| Date/Time | Event Type | Title | Description |\n"
                    output_text += "| --- | --- | --- | --- |\n"
                    for ev in all_events:
                        output_text += f"| {ev.get('event_at', '')[:16]} | {ev.get('event_type', '')} | {ev.get('title', '')} | {ev.get('description', '')} |\n"

            elif command == AgentCommand.NEXT:
                # Deterministic aggregation of open tasks and upcoming hearings
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                tasks = log_and_exec_tool("get_tasks", {})
                hearings = log_and_exec_tool("get_hearings", {})
                
                output_text = f"### Next Action Items for {context.title}\n\n"
                output_text += "#### Upcoming Hearings:\n"
                if hearings:
                    for h in hearings:
                        output_text += f"- **{h.get('title')}** on {h.get('hearing_at', 'TBD')} ({h.get('court', 'N/A')})\n"
                else:
                    output_text += "- No upcoming hearings scheduled.\n\n"

                output_text += "#### Open Tasks:\n"
                if tasks:
                    for t in tasks:
                        output_text += f"- [{t.get('priority', 'normal').upper()}] **{t.get('title')}** (Due: {t.get('due_at', 'N/A')}) - {t.get('description')}\n"
                else:
                    output_text += "- No pending tasks.\n"

            elif command == AgentCommand.DIARY:
                # Deterministic tool call to create/manage diary entries
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.COMMITTING.value,
                )
                entry_title = query or "Matter Activity Entry"
                res = log_and_exec_tool(
                    "create_draft_diary_or_task_entry",
                    {
                        "title": entry_title,
                        "description": f"Created via agent /diary command: {raw_input}",
                        "entry_type": "task",
                    },
                )
                output_text = f"Successfully recorded diary entry:\n- **Title**: {entry_title}\n- **ID**: {res.get('task_id') or res.get('hearing_id')}"

            elif command == AgentCommand.RESEARCH:
                # Retrieving -> Analyzing -> Verifying -> Committing -> Completed/Review Required
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.RETRIEVING.value,
                )
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                research_query = query or context.title
                research_result = run_research(
                    user_id=user_id,
                    matter_id=matter_id,
                    query=research_query,
                    conversation_history=conversation_history,
                )
                output_text = research_result.output_text
                total_tokens += research_result.tokens_used

                # Verifying
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.VERIFYING.value,
                )

                # Committing
                if research_result.verification.verified and research_result.saved_research:
                    final_state = AgentRunState.COMPLETED
                else:
                    final_state = AgentRunState.REVIEW_REQUIRED

                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.COMMITTING.value,
                )

            elif command == AgentCommand.DRAFT:
                # Analyzing -> Committing -> Completed
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                prompt = (
                    f"Draft legal document for matter '{context.title}'.\n"
                    f"Court: {context.court or 'N/A'}, Case No: {context.case_number or 'N/A'}\n"
                    f"Parties: {context.parties}\n"
                    f"Draft Instructions: {query or 'Draft standard legal notice/pleading'}\n"
                )
                output_text, tokens_used = generate_response(prompt)
                total_tokens += tokens_used

                # Committing
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.COMMITTING.value,
                )
                log_and_exec_tool(
                    "save_draft_version",
                    {
                        "content": output_text,
                        "title": f"Draft: {query[:40] if query else context.title}",
                        "document_type": "legal_draft",
                    },
                )

            elif command == AgentCommand.REVIEW:
                # Analyzing -> Review Required -> Completed
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                prompt = (
                    f"Perform legal review and critique for matter '{context.title}'.\n"
                    f"Review Request: {query or 'Identify key legal risks, missing evidence, and compliance gaps.'}\n"
                    f"Context Summary: {context.description}\n"
                )
                output_text, tokens_used = generate_response(prompt)
                total_tokens += tokens_used

                final_state = AgentRunState.REVIEW_REQUIRED

            elif command == AgentCommand.BRIEF:
                # Analyzing -> Completed
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                prompt = (
                    f"Generate a concise executive case brief for matter '{context.title}'.\n"
                    f"Parties: {context.parties}\n"
                    f"Court/Case: {context.court} - {context.case_number}\n"
                    f"Stage: {context.stage}\n"
                    f"Description: {context.description}\n"
                )
                output_text, tokens_used = generate_response(prompt)
                total_tokens += tokens_used

            # Update final state in agent_runs table
            now = datetime.now(timezone.utc)
            db_client.update_agent_run(
                user_id=user_id,
                matter_id=matter_id,
                agent_run_id=agent_run_id,
                status=final_state.value,
                output_text=output_text,
                token_count=total_tokens,
                completed_at=now,
            )

            return AgentRunResponse(
                agent_run_id=agent_run_id,
                user_id=user_id,
                matter_id=matter_id,
                command=command.value,
                status=final_state,
                output_text=output_text,
                token_count=total_tokens,
                context_snapshot=context_snapshot,
                tool_calls=tool_call_records,
                started_at=run_record.get("started_at"),
                completed_at=now.isoformat(),
            )

        except Exception as ex:
            logger.error(f"Agent run failed for matter '{matter_id}': {ex}")
            err_msg = str(ex)
            now = datetime.now(timezone.utc)
            db_client.update_agent_run(
                user_id=user_id,
                matter_id=matter_id,
                agent_run_id=agent_run_id,
                status=AgentRunState.FAILED.value,
                error_text=err_msg,
                completed_at=now,
            )
            return AgentRunResponse(
                agent_run_id=agent_run_id,
                user_id=user_id,
                matter_id=matter_id,
                command=command.value,
                status=AgentRunState.FAILED,
                error_text=err_msg,
                token_count=total_tokens,
                tool_calls=tool_call_records,
                started_at=run_record.get("started_at"),
                completed_at=now.isoformat(),
            )


agent_orchestrator = AgentOrchestrator()
