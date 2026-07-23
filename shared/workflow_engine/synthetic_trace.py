"""Synthetic end-to-end trace — Milestone 0 acceptance criterion only.

docs/architecture/14-roadmap.md §14.2: "a synthetic end-to-end trace
(Gateway -> dummy workflow -> Postgres checkpoint) is visible in
Grafana/Langfuse." This module is that dummy workflow — a trivial,
two-node bounded graph with no business logic, used to prove the
Gateway -> Workflow Engine -> Postgres checkpointer path actually works
before any real agent exists.

This is NOT a template under workflows/ on purpose: every real template
there implements the eight-stage model (docs/architecture/
07-workflow-architecture.md §7.1) against real agents, none of which are
built yet (Milestone 1+). Keeping this smoke-test graph out of workflows/
means nobody mistakes it for a real bounded template when Milestone 1
starts.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from shared.config import Settings
from shared.workflow_engine.checkpointer import postgres_checkpointer


class SyntheticTraceState(TypedDict):
    correlation_id: str
    stage_log: list[str]


def _start_node(state: SyntheticTraceState) -> SyntheticTraceState:
    return {'stage_log': [*state['stage_log'], 'start']}


def _checkpoint_node(state: SyntheticTraceState) -> SyntheticTraceState:
    return {'stage_log': [*state['stage_log'], 'checkpoint']}


def build_synthetic_trace_graph():
    graph = StateGraph(SyntheticTraceState)
    graph.add_node('start', _start_node)
    graph.add_node('checkpoint', _checkpoint_node)
    graph.add_edge(START, 'start')
    graph.add_edge('start', 'checkpoint')
    graph.add_edge('checkpoint', END)
    return graph


async def run_synthetic_trace(
    settings: Settings, correlation_id: str
) -> SyntheticTraceState:
    """Runs the dummy graph once, checkpointed against the primary Postgres
    instance, and returns the final state. Called by
    services/api_gateway/routers/diagnostics.py's ``/diagnostics/synthetic-trace``
    endpoint — see that module for how this is wired to OTel/Langfuse so the
    resulting trace is actually visible per the Milestone 0 acceptance
    criterion, not just executed silently.
    """

    graph = build_synthetic_trace_graph()
    async with postgres_checkpointer(settings) as checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
        config = {'configurable': {'thread_id': correlation_id}}
        result = await compiled.ainvoke(
            {'correlation_id': correlation_id, 'stage_log': []},
            config=config,
        )
        return result
