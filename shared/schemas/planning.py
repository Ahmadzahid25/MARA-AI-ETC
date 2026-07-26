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
    """The Planner's output — a template reference plus parameters, or an
    escalation. Never both, and never neither."""

    template_name: str | None = Field(
        default=None,
        description='None when the objective was ambiguous or matched no '
        'template with sufficient confidence (§5.2.1) — escalated, not a '
        'best-guess selection.',
    )
    parameters: dict[str, object] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    clarification_question: str | None = Field(
        default=None,
        description='Set exactly when template_name is None — §5.2: "ask a '
        'clarifying question instead of guessing the workflow."',
    )

    @property
    def is_escalated(self) -> bool:
        return self.template_name is None

    @model_validator(mode='after')
    def _escalation_xor_selection(self) -> 'PlanResult':
        if self.template_name is None and self.clarification_question is None:
            raise ValueError(
                'An escalated PlanResult (template_name=None) must carry a '
                'clarification_question — never a silent non-selection'
            )
        if self.template_name is not None and self.clarification_question is not None:
            raise ValueError(
                'A PlanResult with a selected template_name must not also '
                'carry a clarification_question'
            )
        return self
