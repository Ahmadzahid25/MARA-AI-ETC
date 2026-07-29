"""Planning contract — docs/architecture/05-agent-architecture.md §5.2.

    Outputs: "A workflow instance: a reference to the selected template
    plus its parameters, handed to the Supervisor/Workflow Engine."

Per §5.2.1, the Planner selects among a *bounded, versioned* set of
templates — it does not construct new graph topology. ``WorkflowTemplate``
is the catalogue entry it chooses from; ``PlanResult`` is what it hands
back. ``PlanResult.is_escalated`` is ``True`` exactly when
``template_name`` is ``None`` — a schema-enforced way of representing
"ambiguous objective, no template selected" that a caller can't mistake
for a real (if low-confidence) selection.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class WorkflowTemplate(BaseModel):
    """One entry from the bounded catalogue in docs/architecture/
    07-workflow-architecture.md §7.3. ``required_parameters`` names what
    the caller must supply for this template's initial state — the
    Planner validates its selection's parameters against this before
    Delegation begins (§5.2.1: "any reference to a node type or edge not
    present in that schema is rejected")."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required_parameters: tuple[str, ...] = ()


class PlanResult(BaseModel):
    """The Planner's output — a template reference plus parameters, a
    clarification request, or a pure conversational reply.

    Exactly one of these three modes is active:
    - **Workflow selected**: ``template_name`` is set, others are None.
    - **Clarification**: ``template_name`` is None, ``clarification_question``
      is set — the officer's intent was ambiguous.
    - **Conversational**: ``template_name`` is None,
      ``conversational_reply`` is set — the message needed no tool at all
      (greeting, general question, capability enquiry).
    """

    template_name: str | None = Field(
        default=None,
        description='None when no workflow was selected — either because the '
        'intent was ambiguous (clarification_question is set) or because the '
        'message was purely conversational (conversational_reply is set).',
    )
    parameters: dict[str, object] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    clarification_question: str | None = Field(
        default=None,
        description='Set when template_name is None and the intent was '
        'ambiguous — §5.2: "ask a clarifying question instead of guessing."',
    )
    conversational_reply: str | None = Field(
        default=None,
        description='Set when the officer message needed no workflow at all '
        '(greeting, capability question, general chat). The Planner replies '
        'directly without escalating.',
    )

    @property
    def is_escalated(self) -> bool:
        """True when a workflow could not be selected (ambiguous intent)."""
        return self.template_name is None and self.clarification_question is not None

    @property
    def is_conversational(self) -> bool:
        """True when the message needed no tool — just a chat reply."""
        return self.template_name is None and self.conversational_reply is not None

    @model_validator(mode='after')
    def _exactly_one_mode(self) -> 'PlanResult':
        has_template = self.template_name is not None
        has_clarification = self.clarification_question is not None
        has_reply = self.conversational_reply is not None

        if has_template and (has_clarification or has_reply):
            raise ValueError(
                'A PlanResult with a selected template_name must not also '
                'carry clarification_question or conversational_reply.'
            )
        if not has_template and not has_clarification and not has_reply:
            raise ValueError(
                'When template_name is None the result must carry either '
                'clarification_question (ambiguous intent) or '
                'conversational_reply (pure chat) — never both None.'
            )
        if has_clarification and has_reply:
            raise ValueError(
                'clarification_question and conversational_reply are mutually '
                'exclusive — only one may be set.'
            )
        return self
