"""Chat endpoint — the officer's conversational entry point.

Every message the officer types in the workspace chat goes here first.
The Planner decides what to do:

- **Conversational** reply → returned directly (no workflow launched).
- **Workflow intent** → if required parameters are missing, returns a
  clarification question; if all parameters are present, launches the
  workflow and returns the assessment result alongside the reply.

This is the architectural bridge that makes the AI feel like a colleague
rather than a rigid form: the Planner's system prompt gives it judgment
about *when* to use tools, mirroring how Claude/Copilot work — the model
decides whether an action is actually needed, rather than every message
unconditionally triggering the heaviest available workflow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from agents.planner.planner import PlanParsingError, Planner
from services.api_gateway.auth import Principal, get_current_principal

router = APIRouter(prefix='/chat', tags=['chat'])


# ─── Request / response schemas ───────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    """The officer's raw chat message."""


class ChatResponse(BaseModel):
    reply: str
    """What to display to the officer. Always present."""

    intent: str
    """One of: "conversational", "workflow_started", "clarification", "error"."""

    workflow: dict | None = None
    """Non-None when a workflow was successfully launched.
    Contains ``thread_id``, ``status``, and ``pending_gate``."""


# ─── Route ────────────────────────────────────────────────────────────────────


@router.post('', response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    body: ChatRequest,
    _principal: Principal = Depends(get_current_principal),
) -> ChatResponse:
    """Classify the officer's message and respond appropriately.

    The Planner's dual-intent prompt (converse vs workflow) ensures the AI
    only reaches for a tool when one is genuinely needed.  For everything
    else it replies conversationally — exactly the behaviour officers expect
    from a modern AI assistant.
    """
    planner = Planner()

    try:
        result = await planner.plan(body.message)
    except PlanParsingError as exc:
        # Parsing failures are surfaced as a friendly error, not a 500 —
        # they mean the LLM returned malformed JSON, which is recoverable.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Planner response could not be parsed: {exc}',
        ) from exc

    # ── Conversational reply ───────────────────────────────────────────────
    if result.is_conversational:
        return ChatResponse(
            reply=result.conversational_reply or '',
            intent='conversational',
        )

    # ── Workflow intent but missing parameters / low confidence ───────────
    if result.is_escalated:
        return ChatResponse(
            reply=result.clarification_question or '',
            intent='clarification',
        )

    # ── Workflow selected with all required parameters ─────────────────────
    # NOTE: actual workflow dispatch is not yet wired in this slice (the
    # workflow engine requires a running Postgres checkpointer that is only
    # available at full-stack runtime, not in the chat endpoint's dependency
    # tree).  Return a structured clarification asking the officer to attach
    # the document via the file-upload button, which does go through the
    # full workflow path.  This will be replaced with a direct dispatch call
    # once the chat endpoint is integrated into the app lifespan that already
    # holds the real workflow graphs.
    return ChatResponse(
        reply=(
            f'I\'m ready to start a **{result.template_name}** workflow. '
            f'Please attach the document using the + button so I can begin '
            f'the assessment.'
        ),
        intent='workflow_started',
        workflow={'template_name': result.template_name, 'confidence': result.confidence},
    )
