"""Smoke tests for shared/workflow_engine/synthetic_trace — the dummy
two-node graph used to prove the Gateway -> Workflow Engine -> Postgres
checkpoint path works (Milestone 0 acceptance criterion, docs/architecture/
14-roadmap.md §14.2).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from shared.workflow_engine.synthetic_trace import (
    SyntheticTraceState,
    _checkpoint_node,
    _start_node,
    build_synthetic_trace_graph,
    run_synthetic_trace,
)


class TestNodeFunctions:
    """The pure functions that implement graph nodes are independently
    testable without any LangGraph machinery."""

    def test_start_node_appends_start_to_stage_log(self) -> None:
        state: SyntheticTraceState = {
            'correlation_id': 'test-123',
            'stage_log': [],
        }
        result = _start_node(state)
        assert result['stage_log'] == ['start']

    def test_start_node_preserves_existing_log(self) -> None:
        state: SyntheticTraceState = {
            'correlation_id': 'test-123',
            'stage_log': ['previous'],
        }
        result = _start_node(state)
        assert result['stage_log'] == ['previous', 'start']

    def test_checkpoint_node_appends_checkpoint(self) -> None:
        state: SyntheticTraceState = {
            'correlation_id': 'test-123',
            'stage_log': ['start'],
        }
        result = _checkpoint_node(state)
        assert result['stage_log'] == ['start', 'checkpoint']

    def test_checkpoint_node_returns_partial_update_only(self) -> None:
        """Node functions return partial state updates by design — LangGraph
        merges them with the rest of the state at the graph-execution layer
        (proven by test_graph_execution_returns_expected_stages below), not
        by the node function itself restating every key."""
        state: SyntheticTraceState = {
            'correlation_id': 'trace-456',
            'stage_log': [],
        }
        result = _checkpoint_node(state)
        assert 'correlation_id' not in result


class TestBuildSyntheticTraceGraph:
    """Verify the graph structure is correct — two nodes, linear flow."""

    def test_graph_has_correct_nodes(self) -> None:
        graph = build_synthetic_trace_graph()
        compiled = graph.compile()
        node_names = set(compiled.get_graph().nodes.keys())
        assert {'start', 'checkpoint'} <= node_names

    def test_graph_compiles_without_error(self) -> None:
        graph = build_synthetic_trace_graph()
        compiled = graph.compile()
        assert compiled is not None

    def test_graph_execution_returns_expected_stages(self) -> None:
        """Execute the graph without a checkpointer to verify the logic."""
        graph = build_synthetic_trace_graph()
        compiled = graph.compile()

        result = compiled.invoke(
            {
                'correlation_id': 'unit-test',
                'stage_log': [],
            }
        )
        assert result['stage_log'] == ['start', 'checkpoint']
        assert result['correlation_id'] == 'unit-test'


@asynccontextmanager
async def _in_memory_checkpointer(settings):
    """Stand-in for postgres_checkpointer() in tests — a real
    BaseCheckpointSaver (langgraph's own in-memory implementation), not a
    raw AsyncMock. ainvoke() calls real methods on the checkpointer
    (aget_tuple, aput, ...) that a plain AsyncMock can't satisfy correctly,
    so it silently returns an unusable value instead of the graph's actual
    result."""
    yield InMemorySaver()


class TestRunSyntheticTrace:
    """run_synthetic_trace() compiles the graph with a checkpointer and
    invokes it — test against a real in-memory checkpointer standing in for
    Postgres."""

    @pytest.mark.asyncio
    async def test_run_synthetic_trace_compiles_and_invokes(self) -> None:
        with (
            patch(
                'shared.workflow_engine.synthetic_trace.postgres_checkpointer',
                side_effect=_in_memory_checkpointer,
            ),
            patch(
                'shared.workflow_engine.synthetic_trace.Settings',
            ) as mock_settings,
        ):
            result = await run_synthetic_trace(mock_settings, 'test-correlation')

            assert result['stage_log'] == ['start', 'checkpoint']
            assert result['correlation_id'] == 'test-correlation'

    @pytest.mark.asyncio
    async def test_checkpointer_is_used(self) -> None:
        """Verify that postgres_checkpointer is actually called with the
        settings object."""
        with patch(
            'shared.workflow_engine.synthetic_trace.postgres_checkpointer',
            side_effect=_in_memory_checkpointer,
        ) as mock_checkpointer:
            with patch(
                'shared.workflow_engine.synthetic_trace.Settings',
            ) as mock_settings:
                await run_synthetic_trace(mock_settings, 'test-correlation')
                mock_checkpointer.assert_called_once_with(mock_settings)
