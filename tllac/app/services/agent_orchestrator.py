"""
Agent Orchestrator service enforcing deterministic command routing,
state lifecycle transitions, token cost bounds, and auditable tool execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any

from ..db.db_client import db_client
from .agent_models import AgentCommand, AgentRunResponse, AgentRunState, ToolCallRecord
from .agent_command_service import (
    build_brief_preview,
    build_draft_preview,
    build_next_preview,
    build_review_report,
    build_timeline_preview,
    command_enabled,
)
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
        if not raw_input or not raw_input.strip():
            logger.warning("Agent run rejected because no prompt was supplied for matter '%s'.", matter_id)
            return AgentRunResponse(
                agent_run_id="",
                user_id=user_id,
                matter_id=matter_id,
                command=AgentCommand.RESEARCH.value,
                status=AgentRunState.FAILED,
                error_text="Agent prompt is required.",
                token_count=0,
                tool_calls=[],
            )

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
            if not context.selected_documents:
                logger.info(
                    "No uploaded matter documents were found while building context for matter '%s'.",
                    matter_id,
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
            error_text: str | None = None

            if not command_enabled(command.value):
                final_state = AgentRunState.FAILED
                output_text = f"{command.value} is disabled until advanced agent commands are enabled."
                error_text = output_text
                logger.warning(
                    "Agent command '%s' is disabled for matter '%s'.",
                    command.value,
                    matter_id,
                )

            elif command == AgentCommand.TIMELINE:
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                preview = build_timeline_preview(user_id, matter_id)
                output_text = f"### Matter Timeline: {preview['title']}\n\n"
                events = preview.get("events", [])
                hearings = preview.get("hearings", [])
                tasks = preview.get("tasks", [])
                notes = preview.get("notes", [])
                documents = preview.get("documents", [])
                output_text += f"Events: {len(events)} | Hearings: {len(hearings)} | Tasks: {len(tasks)} | Notes: {len(notes)} | Documents: {len(documents)}\n"
                if events:
                    output_text += "\n#### Recent Events\n"
                    for event in events[:8]:
                        output_text += f"- {event.get('event_type', 'event')}: {event.get('title', '')} ({event.get('created_at', event.get('event_at', ''))})\n"
                if hearings:
                    output_text += "\n#### Hearings\n"
                    for hearing in hearings[:8]:
                        output_text += f"- {hearing.get('title', 'Hearing')} on {hearing.get('hearing_at', 'TBD')} ({hearing.get('court', 'N/A')})\n"
                if tasks:
                    output_text += "\n#### Tasks\n"
                    for task in tasks[:8]:
                        output_text += f"- [{task.get('status', 'open')}] {task.get('title', '')}\n"

            elif command == AgentCommand.NEXT:
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                preview = build_next_preview(user_id, matter_id)
                output_text = f"### Next Action Items for {preview['title']}\n\n"
                hearings = preview.get("hearings", [])
                deadlines = preview.get("deadlines", [])
                tasks = preview.get("tasks", [])
                output_text += "#### Upcoming Hearings:\n"
                if hearings:
                    for hearing in hearings:
                        output_text += f"- **{hearing.get('title', 'Hearing')}** on {hearing.get('hearing_at', 'TBD')} ({hearing.get('court', 'N/A')})\n"
                else:
                    output_text += "- No upcoming hearings scheduled.\n"

                output_text += "\n#### Deadlines:\n"
                if deadlines:
                    for deadline in deadlines:
                        output_text += f"- {deadline.get('title', 'Deadline')} due {deadline.get('due_at', 'TBD')} [{deadline.get('priority', 'normal')}]\n"
                else:
                    output_text += "- No deadlines identified.\n"

                output_text += "\n#### Open Tasks:\n"
                if tasks:
                    for task in tasks:
                        output_text += f"- [{task.get('priority', 'normal').upper()}] {task.get('title', '')}\n"
                else:
                    output_text += "- No pending tasks.\n"

            elif command == AgentCommand.DIARY:
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.REVIEW_REQUIRED.value,
                )
                preview = {
                    "date": datetime.now(timezone.utc).date().isoformat(),
                    "duration": "unspecified",
                    "category": "diary",
                    "description": query or raw_input,
                    "follow_up_task": "Confirm and save the diary entry from the diary preview endpoint.",
                    "read_only": True,
                }
                output_text = json.dumps(preview, indent=2, ensure_ascii=False)

            elif command == AgentCommand.DRAFT:
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                verified_research = [
                    research
                    for research in db_client.list_matter_research(user_id, matter_id)
                    if str(research.get("verification_status") or "").lower() == "verified"
                ]
                draft_text, tokens_used = build_draft_preview(
                    user_id,
                    matter_id,
                    document_type="legal_draft",
                    document_type_label="Legal Draft",
                    case_details=query or context.description or context.title,
                    relevant_info="\n".join(
                        f"- {item.get('title', 'Verified research')}: {str(item.get('content') or '')[:400]}"
                        for item in verified_research
                    ),
                    skill_name="agent-draft",
                    skill_prompt="",
                )
                total_tokens += tokens_used
                output_text = draft_text
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.COMMITTING.value,
                )
                draft = db_client.create_matter_draft(
                    user_id=user_id,
                    matter_id=matter_id,
                    title=f"Draft: {query[:40] if query else context.title}",
                    document_type="legal_draft",
                )
                db_client.create_draft_version(
                    user_id=user_id,
                    matter_id=matter_id,
                    draft_id=draft["draft_id"],
                    content=output_text,
                    citations=[
                        {
                            "source_id": research.get("research_id"),
                            "title": research.get("title", ""),
                        }
                        for research in verified_research
                    ],
                )

            elif command == AgentCommand.REVIEW:
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                preview = build_review_report(
                    user_id,
                    matter_id,
                    source_type="document" if query else "research",
                    source_id=query,
                    query=query,
                )
                output_text = json.dumps(preview, indent=2, ensure_ascii=False)
                final_state = AgentRunState.REVIEW_REQUIRED

            elif command == AgentCommand.BRIEF:
                db_client.update_agent_run(
                    user_id=user_id,
                    matter_id=matter_id,
                    agent_run_id=agent_run_id,
                    status=AgentRunState.ANALYZING.value,
                )
                preview = build_brief_preview(user_id, matter_id)
                output_text = preview.get("brief_text", "")
                draft = db_client.create_matter_draft(
                    user_id=user_id,
                    matter_id=matter_id,
                    title=str(preview.get("title") or "Hearing Brief"),
                    document_type="brief",
                )
                db_client.create_draft_version(
                    user_id=user_id,
                    matter_id=matter_id,
                    draft_id=draft["draft_id"],
                    content=output_text,
                    citations=[
                        {
                            "source_id": research.get("research_id"),
                            "title": research.get("title", ""),
                        }
                        for research in preview.get("verified_research", [])
                    ],
                )

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
                error_text=error_text,
                token_count=total_tokens,
                context_snapshot=context_snapshot,
                tool_calls=tool_call_records,
                started_at=run_record.get("started_at"),
                completed_at=now.isoformat(),
            )

        except Exception as ex:
            logger.exception("Agent run failed for matter '%s'.", matter_id)
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
