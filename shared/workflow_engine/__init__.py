try:
    from shared.workflow_engine.checkpointer import (
        ensure_checkpoint_schema,
        postgres_checkpointer,
    )
except ModuleNotFoundError as exc:
    if not exc.name or not exc.name.startswith('langgraph.checkpoint.postgres'):
        raise

    # The applicant API can run in local dev without the optional Postgres
    # checkpoint extra. Workflow endpoints remain unavailable until the full
    # runtime dependencies are installed, but auth/intake/status stay usable.
    async def ensure_checkpoint_schema(*args, **kwargs):
        raise RuntimeError('Postgres checkpoint dependency is not installed')

    def postgres_checkpointer(*args, **kwargs):
        raise RuntimeError('Postgres checkpoint dependency is not installed')
from shared.workflow_engine.synthetic_trace import run_synthetic_trace

__all__ = [
    'ensure_checkpoint_schema',
    'postgres_checkpointer',
    'run_synthetic_trace',
]
